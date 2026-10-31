"""
Governance Telemetry Engine for BrandGuard.
Computes live telemetry, ambiguity friction scores, and policy diagnoses
strictly from AuditEvent rows inside the selected time window.
"""

import csv
import io
import math
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Case, When, Value, IntegerField, Max
from governance.models import (
    AuditEvent, BrandRule, FactLedger, Submission, SubmissionVersion, SystemSettings
)


def is_fact_or_accessibility_rule(rule_code: str, pillar: str = '', title: str = '') -> bool:
    """
    Identifies if a rule is a fact verification or an accessibility standard (e.g. WCAG).
    Facts and accessibility rules cannot be overridden; their override rate is 0 by design.
    """
    code_upper = (rule_code or '').upper()
    pillar_upper = (pillar or '').upper()
    title_upper = (title or '').upper()

    if pillar_upper in ('FACTUAL', 'ACCESSIBILITY'):
        return True
    if code_upper.startswith('FACT') or code_upper.startswith('FACT_'):
        return True
    if 'WCAG' in code_upper or 'CONTRAST' in code_upper or 'ACCESSIBILITY' in code_upper:
        return True
    if 'WCAG' in title_upper or 'CONTRAST' in title_upper or 'ACCESSIBILITY' in title_upper:
        return True

    return False


def diagnose_rule(triggers: int, override_rate_pct: float, is_fact_or_accessibility: bool = False, min_triggers: int = 10) -> dict:
    """
    Unified ambiguity diagnosis function — single central definition across BrandGuard.
    Requirements:
    - Only when triggers >= MIN_TRIGGERS:
        override_rate >= 40% -> NEEDS_CLARIFICATION (rule too rigid or poorly written)
        override_rate <= 15% -> TRAINING_GAP (rule is valid, writers keep making mistakes)
        otherwise            -> HEALTHY_GOVERNANCE
    - Below MIN_TRIGGERS show "Not enough data"
    - Facts and accessibility rules cannot be overridden, so their override rate is 0 by design.
      Show them as TRAINING_GAP candidates only, never NEEDS_CLARIFICATION.
    """
    if triggers < min_triggers:
        return {
            "diagnosis": "NOT_ENOUGH_DATA",
            "diagnosis_label": "Not enough data",
            "diagnosis_badge_color": "slate",
            "hint": f"Collect more audit samples (minimum {min_triggers} triggers required).",
        }

    if is_fact_or_accessibility:
        # Override rate is 0% by design. Must be TRAINING_GAP candidates only, never NEEDS_CLARIFICATION.
        return {
            "diagnosis": "TRAINING_GAP",
            "diagnosis_label": "Training Gap",
            "diagnosis_badge_color": "amber",
            "hint": "Rule is strictly enforced and cannot be overridden; writers need guidance on product truth/accessibility standards.",
        }

    if override_rate_pct >= 40.0:
        return {
            "diagnosis": "NEEDS_CLARIFICATION",
            "diagnosis_label": "Needs Clarification",
            "diagnosis_badge_color": "purple",
            "hint": "Review rule scope or clarify permissible exceptions with brand lead; writers frequently require overrides.",
        }
    elif override_rate_pct <= 15.0:
        return {
            "diagnosis": "TRAINING_GAP",
            "diagnosis_label": "Training Gap",
            "diagnosis_badge_color": "amber",
            "hint": "Rule is valid and adhered to when enforced; writers need additional training to avoid repeated violations.",
        }
    else:
        return {
            "diagnosis": "HEALTHY_GOVERNANCE",
            "diagnosis_label": "Healthy Governance",
            "diagnosis_badge_color": "emerald",
            "hint": "Policy is performing well with balanced compliance and justifiable exceptions.",
        }


def calculate_window_telemetry(profile, days: int = 30, channel: str = None):
    """
    Computes all telemetry metrics and rule performance tables strictly from AuditEvent
    rows inside the requested time window [now - days, now].
    """
    settings_obj = SystemSettings.get_settings()
    min_triggers = int(getattr(settings_obj, 'min_triggers', 10))
    minutes_per_audit = int(getattr(settings_obj, 'minutes_per_audit', 5))

    now = timezone.now()
    start_date = now - timedelta(days=days)

    chan_filter = {'channel': channel} if channel and channel != 'ALL' else {}

    # 1. Audit Volume = distinct submissions scanned in window (filter by channel)
    scan_events = AuditEvent.objects.filter(
        profile=profile,
        event_type='SCAN',
        timestamp__gte=start_date,
        **chan_filter
    )
    scanned_submission_ids = list(scan_events.values_list('submission_id', flat=True).distinct())
    audit_volume = len([sid for sid in scanned_submission_ids if sid is not None])

    # 2. First-pass rate = submissions whose version 1 had 0 open BLOCKERS / total.
    # Single aggregated query, no per-row loops.
    first_pass_agg = Submission.objects.filter(
        profile=profile,
        id__in=scanned_submission_ids
    ).annotate(
        v1_open_blockers=Count(
            'versions__findings',
            filter=Q(
                versions__version_number=1,
                versions__findings__severity='BLOCKER',
                versions__findings__status='OPEN'
            )
        )
    ).aggregate(
        total=Count('id'),
        clean=Count(Case(When(v1_open_blockers=0, then=Value(1)), output_field=IntegerField()))
    )

    total_submissions = first_pass_agg['total'] or 0
    clean_submissions = first_pass_agg['clean'] or 0
    first_pass_rate = round((clean_submissions / total_submissions) * 100.0, 1) if total_submissions > 0 else 100.0

    # 3. Review time saved = audits x MINUTES_PER_AUDIT / 60
    review_time_saved_hours = round((audit_volume * minutes_per_audit) / 60.0, 1)

    # 4. Total violations and approved overrides in window
    violation_events = AuditEvent.objects.filter(
        profile=profile,
        event_type='RULE_VIOLATED',
        timestamp__gte=start_date,
        **chan_filter
    )
    total_violations = violation_events.count()

    approved_events = AuditEvent.objects.filter(
        profile=profile,
        event_type='EXCEPTION_APPROVED',
        timestamp__gte=start_date,
        **chan_filter
    )
    total_approved_overrides = approved_events.count()

    # Pre-aggregate violations and overrides by rule_code in window
    violations_by_code = dict(
        violation_events.values('rule_code').annotate(cnt=Count('id')).values_list('rule_code', 'cnt')
    )
    overrides_by_code = dict(
        approved_events.values('rule_code').annotate(cnt=Count('id')).values_list('rule_code', 'cnt')
    )
    last_triggered_by_code = dict(
        violation_events.values('rule_code').annotate(max_ts=Max('timestamp')).values_list('rule_code', 'max_ts')
    )

    # 5. Build Rule Performance Table
    rule_table = []

    # Active Brand Rules
    active_rules = BrandRule.objects.filter(profile=profile, is_active=True).order_by('rule_code')
    for rule in active_rules:
        code = rule.rule_code
        triggers = violations_by_code.get(code, 0)
        overrides = overrides_by_code.get(code, 0)

        is_fact_or_acc = is_fact_or_accessibility_rule(code, pillar=rule.pillar, title=rule.title)
        if is_fact_or_acc:
            overrides = 0  # Cannot be overridden by design

        override_rate = (overrides / triggers) if triggers > 0 else 0.0
        override_rate_pct = round(override_rate * 100.0, 1)

        # Friction = override_rate * ln(triggers + 1)
        friction_score = round(override_rate * math.log(triggers + 1), 3)

        diag = diagnose_rule(
            triggers=triggers,
            override_rate_pct=override_rate_pct,
            is_fact_or_accessibility=is_fact_or_acc,
            min_triggers=min_triggers
        )

        last_ts = last_triggered_by_code.get(code)

        rule_table.append({
            "id": str(rule.id),
            "type": "RULE",
            "rule_code": code,
            "title": rule.title,
            "pillar": rule.pillar,
            "severity": rule.severity,  # From the rule's own severity field!
            "enforcement": rule.enforcement,
            "triggers": triggers,
            "overrides": overrides,
            "override_rate_pct": override_rate_pct,
            "friction_score": friction_score,
            "is_fact_or_accessibility": is_fact_or_acc,
            "last_triggered": last_ts.isoformat() if last_ts else None,
            "last_triggered_display": last_ts.strftime('%Y-%m-%d %H:%M') if last_ts else "Never in window",
            **diag,
        })

    # Fact Ledger Items
    facts = FactLedger.objects.filter(profile=profile).order_by('fact_code')
    for fact in facts:
        code = fact.fact_code
        triggers = violations_by_code.get(code, 0)
        overrides = 0  # Facts cannot be overridden by design
        override_rate = 0.0
        override_rate_pct = 0.0
        friction_score = 0.0

        diag = diagnose_rule(
            triggers=triggers,
            override_rate_pct=0.0,
            is_fact_or_accessibility=True,
            min_triggers=min_triggers
        )

        last_ts = last_triggered_by_code.get(code)

        rule_table.append({
            "id": str(fact.id),
            "type": "FACT",
            "rule_code": code,
            "title": f"Fact: {fact.category}",
            "pillar": "FACTUAL",
            "severity": "BLOCKER",
            "enforcement": "Block publish",
            "triggers": triggers,
            "overrides": 0,
            "override_rate_pct": 0.0,
            "friction_score": friction_score,
            "is_fact_or_accessibility": True,
            "last_triggered": last_ts.isoformat() if last_ts else None,
            "last_triggered_display": last_ts.strftime('%Y-%m-%d %H:%M') if last_ts else "Never in window",
            **diag,
        })

    # Sort rules: friction_score desc, triggers desc
    rule_table.sort(key=lambda r: (r['friction_score'], r['triggers']), reverse=True)

    # 6. Per-Writer Breakdown in window
    writer_stats = []
    writer_events = AuditEvent.objects.filter(
        profile=profile,
        event_type='RULE_VIOLATED',
        timestamp__gte=start_date,
        user__isnull=False,
        **chan_filter
    ).values('user__id', 'user__username', 'user__first_name', 'user__last_name').annotate(
        violation_count=Count('id'),
        submissions_scanned=Count('submission_id', distinct=True)
    ).order_by('-violation_count')

    for ws in writer_events:
        name = f"{ws['user__first_name']} {ws['user__last_name']}".strip() or ws['user__username']
        writer_stats.append({
            "user_id": ws['user__id'],
            "username": ws['user__username'],
            "name": name,
            "violations_count": ws['violation_count'],
            "submissions_scanned": ws['submissions_scanned'],
        })

    # 7. Trend Sparkline (daily data points over window)
    sparkline_points = []
    day_steps = min(days, 30)
    step_size = max(1, days // 30)
    for i in range(day_steps, -1, -1):
        bucket_date = (now - timedelta(days=i * step_size)).date()
        next_date = bucket_date + timedelta(days=step_size)
        bucket_audits = AuditEvent.objects.filter(
            profile=profile,
            event_type='SCAN',
            timestamp__date__gte=bucket_date,
            timestamp__date__lt=next_date,
            **chan_filter
        ).values('submission_id').distinct().count()

        bucket_violations = AuditEvent.objects.filter(
            profile=profile,
            event_type='RULE_VIOLATED',
            timestamp__date__gte=bucket_date,
            timestamp__date__lt=next_date,
            **chan_filter
        ).count()

        sparkline_points.append({
            "date": bucket_date.strftime('%b %d'),
            "audits": bucket_audits,
            "violations": bucket_violations,
        })

    kpis = {
        "audit_volume": audit_volume,
        "first_pass_rate": first_pass_rate,
        "review_time_saved_hours": review_time_saved_hours,
        "review_time_saved_label": f"{review_time_saved_hours} hrs (estimated)",
        "total_violations": total_violations,
        "total_approved_overrides": total_approved_overrides,
        "minutes_per_audit": minutes_per_audit,
        "min_triggers": min_triggers,
        "selected_window_days": days,
        "selected_channel": channel or 'ALL',
    }

    return {
        "kpis": kpis,
        "rules": rule_table,
        "writers": writer_stats,
        "trend_sparkline": sparkline_points,
    }


def generate_telemetry_csv(telemetry_data: dict) -> str:
    """Exports rule performance table to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Rule Code", "Title", "Pillar", "Severity", "Triggers", "Overrides",
        "Override Rate (%)", "Friction Score", "Diagnosis", "Last Triggered", "Next Step Hint"
    ])

    for r in telemetry_data.get('rules', []):
        writer.writerow([
            r['rule_code'],
            r['title'],
            r['pillar'],
            r['severity'],
            r['triggers'],
            r['overrides'],
            r['override_rate_pct'],
            r['friction_score'],
            r['diagnosis_label'],
            r['last_triggered_display'],
            r.get('hint', '')
        ])

    return output.getvalue()


# Backwards compatibility alias
def get_telemetry_report(profile=None, days=30, channel=None):
    from governance.models import BrandProfile
    if not profile:
        profile = BrandProfile.objects.first()
    return calculate_window_telemetry(profile=profile, days=days, channel=channel)

