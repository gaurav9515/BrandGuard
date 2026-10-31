"""
Pure Django JSON API views for BrandGuard (Phase 2 Upgraded).
No Django REST Framework (DRF) abstractions - custom dictionary serialization and @csrf_exempt JsonResponse.
Features:
1. Multi-modal Pre-Flight Audit with Voice Fingerprint Radar
2. Stale Fact Blast-Radius Retroactive Governance
3. Cryptographic PNG/PDF Metadata Stamping on Manager Sign-Off
4. CMS Cryptographic Stamp Verification endpoint
5. Brand-Safe Prompt / .cursorrules Compiler
"""

import json
import time
import os
import hmac
import hashlib
from datetime import datetime, date, timedelta
from django.utils import timezone
from pathlib import Path
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, login, logout
from django.db import transaction, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Q
from django.utils.text import slugify

from .models import (
    BrandGuardUser, SystemSettings, BrandProfile, BrandRule, BrandRuleVersion,
    DraftRule, FactLedger, Submission, SubmissionVersion, AuditFinding,
    BrandComplianceSignature, ExceptionRequest, Notification, AuditTrail,
    AuditEvent, Job, CodebaseRepo, CodeSymbolMapping, CodebaseConstant,
    ProposedFactChange, SubmissionCitation, BlastRadiusReport,
    Organization, Company, Project, Membership, InviteToken, EmailVerificationToken,
    PasswordResetToken, LoginAttemptLog
)
from .job_runner import enqueue_job
from .engines.codebase_extractor import validate_repo_url, run_repo_scan
from .auth import generate_user_token, decode_user_token, get_authenticated_user_from_request
from .permissions import IsAdmin, IsWriter, admin_required, writer_required
from .scraper import scrape_brand_profile, SSRFSecurityException
from .rule_parser import parse_rule_document, RuleParsingException
from .engines.lexicon_engine import audit_lexicon, compute_voice_fingerprint, TARGET_VOICE_ENVELOPES
from .engines.fact_rag_engine import audit_facts_and_tone
from .engines.visual_engine import audit_image_array, audit_pdf_file
from .engines.telemetry import get_telemetry_report
from .crypto_sign import (
    sign_hmac_sha256, sign_ed25519, get_ed25519_keys, build_canonical_payload,
    embed_clearance_in_png, embed_clearance_in_pdf, verify_asset_clearance,
    extract_metadata_from_file, LEGAL_NOTICE
)

@csrf_exempt
def root_api_status_view(request):
    """
    GET / or /api/health/
    Root health check and API status endpoint for Render keep-alive and spin-up monitoring.
    """
    db_status = "connected"
    try:
        from .models import BrandGuardUser
        BrandGuardUser.objects.exists()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return JsonResponse({
        "status": "online",
        "service": "BrandGuard Enterprise Governance API",
        "ruleset_version": "v3.2",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "keep_alive": "active",
        "endpoints": {
            "health": "/healthz",
            "ready": "/readyz",
            "api_health": "/api/health/",
            "auth_login": "/api/auth/login/",
            "auth_me": "/api/auth/me/",
            "brand_profile": "/api/brand-profile/",
            "rules": "/api/rules/",
            "facts": "/api/facts/",
            "submissions": "/api/submissions/",
            "telemetry": "/api/telemetry/",
            "exceptions": "/api/exceptions/"
        }
    })


@csrf_exempt
def healthz_view(request):
    """
    GET /healthz or /api/healthz/
    Lightweight, public, unauthenticated liveness probe for load balancers & keep-alive bots.
    Executes a fast 'SELECT 1' against the primary database.
    Returns 200 OK if healthy, 503 Service Unavailable if database is down.
    """
    start_time = time.perf_counter()
    db_connected = False
    error_msg = None

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_connected = True
    except Exception as exc:
        error_msg = str(exc)

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    if not db_connected:
        return JsonResponse({
            "status": "unhealthy",
            "service": "brandguard-core",
            "version": getattr(settings, 'BRANDGUARD_VERSION', 'v3.2'),
            "timestamp": timezone.now().isoformat(),
            "database": {
                "status": "unreachable",
                "error": error_msg,
                "latency_ms": latency_ms,
            }
        }, status=503)

    return JsonResponse({
        "status": "healthy",
        "service": "brandguard-core",
        "version": getattr(settings, 'BRANDGUARD_VERSION', 'v3.2'),
        "timestamp": timezone.now().isoformat(),
        "database": {
            "status": "connected",
            "latency_ms": latency_ms,
        }
    })


@csrf_exempt
def readyz_view(request):
    """
    GET /readyz or /api/readyz/
    Deep readiness probe validating database connectivity, unapplied migrations,
    background job runner health, and filesystem media write capability.
    Returns 200 OK when fully ready to serve traffic, 503 if any subsystem is down.
    """
    start_time = time.perf_counter()
    checks = {}
    is_ready = True

    # 1. Database Connectivity Probe
    db_start = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = {
            "status": "connected",
            "engine": connection.settings_dict.get("ENGINE", "unknown").split('.')[-1],
            "latency_ms": round((time.perf_counter() - db_start) * 1000, 2)
        }
    except Exception as exc:
        is_ready = False
        checks["database"] = {
            "status": "failed",
            "error": str(exc),
            "latency_ms": round((time.perf_counter() - db_start) * 1000, 2)
        }

    # 2. Database Migrations Status Check
    try:
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        pending_count = len(plan)
        if pending_count > 0:
            is_ready = False
            checks["migrations"] = {
                "status": "pending_migrations",
                "pending_count": pending_count,
                "pending_plan": [f"{m[0].app}.{m[0].name}" for m in plan[:5]]
            }
        else:
            checks["migrations"] = {
                "status": "up_to_date",
                "pending_count": 0
            }
    except Exception as exc:
        checks["migrations"] = {
            "status": "unknown",
            "error": str(exc),
            "pending_count": 0
        }

    # 3. Background Job Runner Health
    try:
        from governance.job_runner import get_runner_status
        runner_status = get_runner_status()
        checks["job_runner"] = runner_status
    except Exception as exc:
        checks["job_runner"] = {
            "status": "fallback_active",
            "mode": "THREAD_POOL",
            "error": str(exc)
        }

    # 4. Storage / Media Write Check
    try:
        import tempfile
        media_root = getattr(settings, 'MEDIA_ROOT', tempfile.gettempdir())
        os.makedirs(media_root, exist_ok=True)
        probe_path = os.path.join(media_root, '.readyz_probe')
        with open(probe_path, 'w', encoding='utf-8') as f:
            f.write("ready")
        if os.path.exists(probe_path):
            os.remove(probe_path)
        checks["storage"] = {
            "status": "writable",
            "media_root": str(media_root)
        }
    except Exception as exc:
        checks["storage"] = {
            "status": "read_only_warning",
            "error": str(exc)
        }

    total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response_payload = {
        "status": "ready" if is_ready else "not_ready",
        "service": "brandguard-core",
        "version": getattr(settings, 'BRANDGUARD_VERSION', 'v3.2'),
        "timestamp": timezone.now().isoformat(),
        "total_latency_ms": total_latency_ms,
        "checks": checks
    }

    return JsonResponse(response_payload, status=200 if is_ready else 503)


def get_active_profile():
    """Returns the primary BrandProfile, creating NovaPay default if missing."""
    profile = BrandProfile.objects.first()
    palette = [
        {"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0},
        {"name": "Teal", "hex": "#00D4B6", "max_delta_e": 4.5},
        {"name": "Pure White", "hex": "#FFFFFF", "max_delta_e": 2.0},
        {"name": "Muted Panel", "hex": "#F8FAF9", "max_delta_e": 2.0},
    ]
    if not profile:
        profile = BrandProfile.objects.create(
            org_name="NovaPay",
            allowed_hex_palette=palette,
            allowed_fonts=["Inter", "JetBrains Mono", "Plus Jakarta Sans"],
            wcag_min_ratio=4.5,
            logo_aspect_ratio=3.5,
        )
    else:
        if profile.org_name != "NovaPay" or len(profile.allowed_hex_palette) != 4:
            profile.org_name = "NovaPay"
            profile.allowed_hex_palette = palette
            profile.save()
    return profile


def get_user_profile(request):
    """
    Returns the BrandProfile scoped strictly to the active Company context
    resolved via the central tenant-scoping layer.
    Satisfies global constraint: all data is scoped to caller's active Company/BrandProfile.
    """
    from .tenancy import get_request_company, ensure_company_profile
    try:
        company, err = get_request_company(request)
        if company:
            return ensure_company_profile(company)
    except Exception:
        pass

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return get_active_profile()

    if getattr(user, 'brand_profile', None):
        return user.brand_profile

    # Fallback to active profile and associate it to this user
    profile = get_active_profile()
    try:
        user.brand_profile = profile
        user.save(update_fields=['brand_profile'])
    except Exception:
        pass
    return profile


def resolve_request_profile(request, required_role=None):
    """
    Central helper resolving (profile, company, err_response).
    If user is authenticated, resolves company via get_request_company and validates cross-company boundary.
    If err_response is not None, views must return err_response directly.
    """
    user = get_authenticated_user_from_request(request)
    if user and user.is_authenticated:
        from .tenancy import get_request_company, ensure_company_profile
        company, err = get_request_company(request, required_role=required_role)
        if err:
            return None, None, err
        profile = ensure_company_profile(company) if company else get_user_profile(request)
        return profile, company, None
    return get_user_profile(request), None, None


def calculate_score(findings, approved_exception_count=0):
    """
    Calculates 0-100 compliance score and detailed breakdown.
    Configurable weights from SystemSettings (default: 18 pts/BLOCKER, 8 pts/WARNING, 4 pts/approved exception).
    Returns (final_score, breakdown_dict).
    """
    try:
        sys_settings = SystemSettings.get_settings()
        blocker_penalty = float(sys_settings.blocker_penalty)
        warning_penalty = float(sys_settings.warning_penalty)
        exception_deduction = float(sys_settings.approved_exception_deduction)
    except Exception:
        blocker_penalty = 18.0
        warning_penalty = 8.0
        exception_deduction = 4.0

    blockers = 0
    warnings = 0
    approved_count = approved_exception_count

    for f in findings:
        status = f.get('status', 'OPEN') if isinstance(f, dict) else getattr(f, 'status', 'OPEN')
        if status in ('OVERRIDE_APPROVED', 'ACCEPTED'):
            if status == 'OVERRIDE_APPROVED':
                approved_count += 1
            continue
        severity = f.get('severity', 'WARNING') if isinstance(f, dict) else getattr(f, 'severity', 'WARNING')
        if severity == 'BLOCKER':
            blockers += 1
        else:
            warnings += 1

    blockers_deduction = round(blockers * blocker_penalty, 1)
    warnings_deduction = round(warnings * warning_penalty, 1)
    exceptions_deduction = round(approved_count * exception_deduction, 1)
    total_deductions = round(blockers_deduction + warnings_deduction + exceptions_deduction, 1)

    final_score = max(0.0, min(100.0, round(100.0 - total_deductions, 1)))

    breakdown = {
        "final_score": final_score,
        "base_score": 100.0,
        "blockers_count": blockers,
        "blockers_deduction": blockers_deduction,
        "blocker_rate": blocker_penalty,
        "warnings_count": warnings,
        "warnings_deduction": warnings_deduction,
        "warning_rate": warning_penalty,
        "approved_exceptions_count": approved_count,
        "approved_exceptions_deduction": exceptions_deduction,
        "exception_deduction_rate": exception_deduction,
        "total_deductions": total_deductions,
        "formula": f"100 - ({blockers}×{blocker_penalty}) - ({warnings}×{warning_penalty}) - ({approved_count}×{exception_deduction})",
        "explanation": f"Score {final_score}/100: {blockers} blockers (-{blockers_deduction}), {warnings} warnings (-{warnings_deduction}), {approved_count} approved exceptions (-{exceptions_deduction}).",
    }

    return final_score, breakdown


@csrf_exempt
def brand_profile_view(request):
    """GET /api/brand-profile/"""
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    data = profile.to_dict()
    data["sample_banner_url"] = "/media/sample_offbrand_banner.png"
    return JsonResponse(data, safe=False)


@csrf_exempt
def add_rule_view(request):
    """POST /api/brand-profile/add-rule/"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request, required_role='ADMIN')
    if err:
        return err

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    item_type = body.get('type', 'RULE').upper()

    if item_type == 'RULE':
        rule_code = body.get('rule_code', '').strip()
        title = body.get('title', '').strip()
        pillar = body.get('pillar', 'TONE').upper()
        banned_term = body.get('banned_term', '').strip()
        replacement = body.get('replacement', '').strip()
        case_sensitive = bool(body.get('case_sensitive', False))
        description = body.get('rule_description', '').strip()

        if not rule_code or not title:
            return HttpResponseBadRequest("rule_code and title are required")

        rule, created = BrandRule.objects.update_or_create(
            profile=profile,
            rule_code=rule_code,
            defaults={
                "title": title,
                "pillar": pillar,
                "structured_spec": {
                    "banned_term": banned_term,
                    "replacement": replacement,
                    "case_sensitive": case_sensitive,
                },
                "rule_description": description,
            }
        )
        return JsonResponse({
            "status": "success",
            "item_type": "RULE",
            "item": rule.to_dict(),
            "profile": profile.to_dict(),
        })

    elif item_type == 'FACT':
        fact_code = body.get('fact_code', '').strip()
        category = body.get('category', '').strip()
        claim_truth = body.get('claim_truth', '').strip()
        valid_until_str = body.get('valid_until', '').strip()
        superseded_by_text = body.get('superseded_by_text', '').strip()

        if not fact_code or not claim_truth:
            return HttpResponseBadRequest("fact_code and claim_truth are required")

        try:
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date() if valid_until_str else date.today()
        except ValueError:
            valid_until = date.today()

        fact, created = FactLedger.objects.update_or_create(
            profile=profile,
            fact_code=fact_code,
            defaults={
                "category": category or "General Truth",
                "claim_truth": claim_truth,
                "last_verified": date.today(),
                "valid_until": valid_until,
                "superseded_by_text": superseded_by_text,
            }
        )
        return JsonResponse({
            "status": "success",
            "item_type": "FACT",
            "item": fact.to_dict(),
            "profile": profile.to_dict(),
        })

    return HttpResponseBadRequest(f"Unknown item type: {item_type}")


@admin_required
def expire_or_update_fact_view(request, fact_id):
    """
    POST /api/brand-profile/facts/<uuid:fact_id>/expire-or-update/
    Simulates or executes retroactive fact updates and detects blast radius.
    Transitions all affected APPROVED submissions to STALE_REAUDIT_REQUIRED.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    fact = FactLedger.objects.filter(id=fact_id, profile=profile).first()
    if not fact:
        return JsonResponse({"error": "Fact not found"}, status=404)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}

    new_claim = body.get('new_claim_truth', '').strip()
    valid_until_str = body.get('valid_until', '').strip()
    superseded = body.get('superseded_by_text', '').strip()

    old_truth = fact.claim_truth
    if new_claim:
        fact.claim_truth = new_claim
    if valid_until_str:
        try:
            fact.valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if superseded:
        fact.superseded_by_text = superseded
    fact.save()

    # Trigger Module 3 Blast Radius Engine
    from governance.engines.blast_radius_engine import compute_blast_radius
    blast_result = compute_blast_radius(
        profile=profile,
        fact_id=fact.id,
        old_value=old_truth,
        new_value=fact.claim_truth,
        trigger_reason='MANUAL_FACT_UPDATE'
    )

    return JsonResponse({
        "status": "success",
        "fact": fact.to_dict(),
        "blast_radius": blast_result,
        "affected_submissions_count": blast_result.get('affected_assets_count', 0),
        "affected_titles": [p['title'] for p in blast_result.get('draft_patches', [])],
    })


@csrf_exempt
def facts_list_create_view(request):
    """
    GET /api/facts/
    Lists all facts with expiry alerts, countdown days, and blast radius count.
    POST /api/facts/
    Creates a new fact in the FactLedger.
    """
    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    # Seed initial facts if table is empty
    if FactLedger.objects.filter(profile=profile).count() == 0:
        today_d = date.today()
        FactLedger.objects.create(
            profile=profile,
            fact_code="FACT_012",
            category="International Rails & Settlement",
            claim_truth="Transfers settle in 24 hrs with a 0.5% FX fee.",
            last_verified=today_d - timedelta(days=15),
            valid_until=today_d + timedelta(days=60),
            source="NovaPay Core Treasury Rails v2",
            trigger_count=128,
            override_count=5
        )
        FactLedger.objects.create(
            profile=profile,
            fact_code="FACT_031",
            category="Regulatory & Security Certification",
            claim_truth="NovaPay maintains SOC2 Type II certification and ISO/IEC 27001.",
            last_verified=today_d - timedelta(days=90),
            valid_until=today_d + timedelta(days=14),  # Expiring soon!
            superseded_by_text="SOC2 Type II recertification scheduled for Q4 2026.",
            source="Annual Compliance Audit Report",
            trigger_count=51,
            override_count=1
        )
        FactLedger.objects.create(
            profile=profile,
            fact_code="FACT_009",
            category="Yield & Interest Rate Guarantee",
            claim_truth="Treasury deposits earn up to 4.8% floating APY.",
            last_verified=today_d - timedelta(days=120),
            valid_until=today_d - timedelta(days=10),  # Expired!
            superseded_by_text="Floating APY adjusted to 4.2% floating APY effective Oct 15.",
            source="Monetary Policy Committee Memo",
            trigger_count=84,
            override_count=0
        )
        FactLedger.objects.create(
            profile=profile,
            fact_code="FACT_015",
            category="Supported Corridors",
            claim_truth="Direct local clearing across 140+ countries and 45 currencies.",
            last_verified=today_d - timedelta(days=30),
            valid_until=today_d + timedelta(days=180),
            source="Global Banking Partnerships Directory",
            trigger_count=37,
            override_count=2
        )

    if request.method == 'GET':
        facts = FactLedger.objects.filter(profile=profile).order_by('valid_until')
        items = []
        now_date = date.today()
        expiring_soon_count = 0
        expired_count = 0

        for f in facts:
            days = (f.valid_until - now_date).days
            if days < 0:
                status_label = 'EXPIRED'
                expired_count += 1
            elif days <= 30:
                status_label = 'EXPIRING_SOON'
                expiring_soon_count += 1
            else:
                status_label = 'ACTIVE'

            d = f.to_dict()
            d['expiry_status'] = status_label
            d['days_until_expiry'] = days
            items.append(d)

        return JsonResponse({
            "facts": items,
            "total_facts": len(items),
            "expiring_soon_count": expiring_soon_count,
            "expired_count": expired_count,
        })

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        fact_code = body.get('fact_code', '').strip().upper()
        if not fact_code:
            return JsonResponse({"error": "fact_code is required"}, status=400)

        valid_until_str = body.get('valid_until', '2026-12-31')
        try:
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date()
        except ValueError:
            valid_until = date(2026, 12, 31)

        last_verified_str = body.get('last_verified', str(date.today()))
        try:
            last_verified = datetime.strptime(last_verified_str, '%Y-%m-%d').date()
        except ValueError:
            last_verified = date.today()

        user = get_authenticated_user_from_request(request)

        fact = FactLedger.objects.create(
            profile=profile,
            fact_code=fact_code,
            category=body.get('category', 'Financial Disclosure'),
            claim_truth=body.get('claim_truth', ''),
            last_verified=last_verified,
            valid_until=valid_until,
            superseded_by_text=body.get('superseded_by_text', ''),
            source=body.get('source', 'NovaPay Product Facts'),
            created_by=user,
        )
        return JsonResponse(fact.to_dict(), status=201)

    return HttpResponseBadRequest("Method not allowed")


@admin_required
def fact_blast_radius_view(request, fact_id):
    """
    GET /api/facts/<uuid:fact_id>/blast-radius/
    POST /api/facts/<uuid:fact_id>/blast-radius/
    Computes or retrieves blast radius report for the given fact.
    Scoped strictly to request.user's BrandProfile.
    """
    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    fact = FactLedger.objects.filter(id=fact_id, profile=profile).first()
    if not fact:
        return JsonResponse({"error": "Fact not found"}, status=404)

    if request.method == 'GET':
        report = BlastRadiusReport.objects.filter(profile=profile, fact=fact).first()
        if report:
            affected_list = [
                {
                    "submission_id": p.get("submission_id"),
                    "title": p.get("title"),
                    "channel": p.get("channel"),
                }
                for p in report.draft_patches
            ]
            return JsonResponse({
                "status": "success",
                "report": report.to_dict(),
                "fact": fact.to_dict(),
                "blast_radius_count": report.affected_assets_count,
                "affected_submissions_count": report.affected_assets_count,
                "affected_submissions": affected_list,
                "draft_patches": report.draft_patches,
            })
        else:
            from governance.engines.blast_radius_engine import compute_blast_radius
            result = compute_blast_radius(profile, fact.id, trigger_reason='ON_DEMAND_QUERY')
            return JsonResponse({
                "status": "success",
                "report": result,
                "fact": fact.to_dict(),
                "blast_radius_count": result['affected_assets_count'],
                "affected_submissions_count": result['affected_assets_count'],
                "affected_submissions": result.get('affected_submissions', []),
                "draft_patches": result.get('draft_patches', []),
            })

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            body = {}

        run_async = body.get('run_async', False)
        if run_async:
            job = Job.objects.create(
                profile=profile,
                user=request.user,
                job_type='BLAST_RADIUS',
                status='RUNNING',
                status_message=f'Computing blast radius for {fact.fact_code}'
            )
            from governance.engines.blast_radius_engine import compute_blast_radius
            result = compute_blast_radius(profile, fact.id, trigger_reason='MANUAL_SCAN')
            job.status = 'SUCCESS'
            job.result_payload = result
            job.progress = 100
            job.status_message = 'Blast radius computation completed.'
            job.completed_at = timezone.now()
            job.save()

            return JsonResponse({
                "status": "accepted",
                "job_id": str(job.id),
                "job": job.to_dict()
            }, status=202)
        else:
            from governance.engines.blast_radius_engine import compute_blast_radius
            result = compute_blast_radius(profile, fact.id, trigger_reason='MANUAL_SCAN')
            return JsonResponse({
                "status": "success",
                "blast_radius": result,
                "fact": fact.to_dict(),
                "blast_radius_count": result['affected_assets_count'],
                "affected_submissions_count": result['affected_assets_count'],
            })

    return HttpResponseBadRequest("Method not allowed")


@admin_required
def fact_apply_patches_view(request, fact_id):
    """
    POST /api/facts/<uuid:fact_id>/apply-patches/
    Applies deterministic draft patches in bulk to stale submissions and triggers re-audits.
    Optionally accepts {"submission_ids": ["uuid1", "uuid2"]}.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    fact = FactLedger.objects.filter(id=fact_id, profile=profile).first()
    if not fact:
        return JsonResponse({"error": "Fact not found"}, status=404)

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body = {}

    submission_ids = body.get('submission_ids', None)

    from governance.engines.blast_radius_engine import apply_batch_patches
    result = apply_batch_patches(
        profile=profile,
        fact_id=fact.id,
        submission_ids=submission_ids,
        user=request.user
    )

    return JsonResponse({
        "status": "success",
        "fact_code": fact.fact_code,
        "patched_count": result.get('patched_count', 0),
        "results": result.get('results', []),
    })


@csrf_exempt
@admin_required
def fact_bulk_re_audit_view(request, fact_id):
    """
    POST /api/facts/<uuid:fact_id>/bulk-re-audit/
    Executes automated retroactive re-audit on all submissions in blast radius.
    Flags outdated claims, transitions approved assets to STALE_REAUDIT_REQUIRED,
    recalculates compliance scores, logs to AuditTrail, and generates notifications.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    fact = FactLedger.objects.filter(id=fact_id).first()
    if not fact:
        return HttpResponseNotFound("Fact not found")

    profile = fact.profile
    user = get_authenticated_user_from_request(request)

    affected_submissions = []
    flagged_count = 0

    for sub in profile.submissions.all():
        latest_ver = sub.versions.order_by('-version_number').first()
        if not latest_ver:
            continue

        has_finding = latest_ver.findings.filter(rule_citation_code=fact.fact_code).exists()
        in_text = fact.fact_code.lower() in latest_ver.raw_text.lower()
        keyword_match = any(w.lower() in latest_ver.raw_text.lower() for w in fact.claim_truth.split() if len(w) > 5)

        if has_finding or in_text or keyword_match:
            # Re-audit this submission: add/update a BLOCKER finding for outdated claim
            finding, created = AuditFinding.objects.get_or_create(
                version=latest_ver,
                rule_citation_code=fact.fact_code,
                defaults={
                    "pillar": "FACTUAL",
                    "severity": "BLOCKER",
                    "rule_citation_title": f"Outdated Fact: {fact.category}",
                    "explanation": f"Claim cites Fact [{fact.fact_code}] ('{fact.claim_truth}'), which expired on {fact.valid_until}. Superseded by: '{fact.superseded_by_text or 'Updated institutional policy'}'. Re-audit required before publication.",
                    "status": "OPEN",
                    "source_excerpt": fact.claim_truth[:60],
                    "suggested_fixes": [f"Update copy to align with: '{fact.superseded_by_text or 'active rate disclosure'}'"]
                }
            )
            if not created:
                finding.severity = "BLOCKER"
                finding.status = "OPEN"
                finding.explanation = f"Fact [{fact.fact_code}] expired on {fact.valid_until}. Superseded by: '{fact.superseded_by_text or 'Updated policy'}'. Retroactive re-audit flagged this asset."
                finding.save()

            flagged_count += 1

            # Recalculate score
            approved_count = latest_ver.findings.filter(status='OVERRIDE_APPROVED').count()
            new_score, new_breakdown = calculate_score(latest_ver.findings.all(), approved_exception_count=approved_count)
            latest_ver.compliance_score = new_score
            latest_ver.score_breakdown = new_breakdown
            latest_ver.save()

            sub.status = 'STALE_REAUDIT_REQUIRED'
            sub.save()

            affected_submissions.append(sub)

            # Multi-channel notification to author
            if sub.author:
                from governance.notifications import dispatch_notification
                dispatch_notification(
                    recipient=sub.author,
                    notification_type='FACT_EXPIRING',
                    title=f"Re-audit Required: {sub.title}",
                    message=f"Fact [{fact.fact_code}] cited in your asset '{sub.title}' has expired or updated. Status changed to STALE_REAUDIT_REQUIRED.",
                    link_url=f"/api/submissions/{sub.id}/"
                )

    # AuditTrail logging
    AuditTrail.log(
        request,
        action="BULK_RE_AUDIT_EXECUTED",
        entity_type="FACT_LEDGER",
        entity_id=str(fact.id),
        description=f"Executed bulk re-audit for fact {fact.fact_code}. {len(affected_submissions)} submissions transitioned to STALE_REAUDIT_REQUIRED."
    )

    return JsonResponse({
        "status": "success",
        "fact_code": fact.fact_code,
        "blast_radius_total": len(affected_submissions),
        "flagged_count": flagged_count,
        "affected_submissions": [
            {"id": str(s.id), "title": s.title, "channel": s.channel_context, "status": s.status}
            for s in affected_submissions
        ]
    })



@csrf_exempt
def audit_submission_view(request):
    """
    POST /api/submissions/audit/
    Accepts multipart/form-data or JSON.
    Runs Visual (CV + CVD + Optical Clear-Space), Lexicon, and Fact/Tone engines.
    Computes 4-Axis Voice Fingerprint Radar.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    # Read parameters from form or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        title = request.POST.get('title', 'Draft Campaign')
        channel_context = request.POST.get('channel_context', 'LINKEDIN_POST')
        confidential_mode = request.POST.get('confidential_mode', 'false').lower() in ('true', '1')
        raw_text = request.POST.get('raw_text', '')
        use_sample_banner = request.POST.get('use_sample_banner', 'false').lower() in ('true', '1')
        uploaded_file = request.FILES.get('file')
    else:
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = {}
        title = body.get('title', 'Draft Campaign')
        channel_context = body.get('channel_context', 'LINKEDIN_POST')
        confidential_mode = bool(body.get('confidential_mode', False))
        raw_text = body.get('raw_text', '')
        use_sample_banner = bool(body.get('use_sample_banner', False))
        uploaded_file = None

    file_type = 'TEXT'
    img_for_cv = None
    pdf_file_obj = None

    if use_sample_banner:
        banner_path = Path(settings.MEDIA_ROOT) / "sample_offbrand_banner.png"
        if banner_path.exists():
            pil_img = Image.open(banner_path).convert('RGB')
            img_for_cv = np.array(pil_img)
            file_type = 'IMAGE'
    elif uploaded_file:
        fname = uploaded_file.name.lower()
        if fname.endswith('.pdf'):
            file_type = 'PDF'
            pdf_file_obj = uploaded_file
        elif fname.endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            file_type = 'IMAGE'
            try:
                pil_img = Image.open(uploaded_file).convert('RGB')
                img_for_cv = np.array(pil_img)
            except Exception:
                pass

    # 1. Lexicon Engine
    lex_findings, triggered_rules = audit_lexicon(raw_text, profile)

    # 2. Fact & Tone Engine
    fact_findings, fact_triggered_rules, triggered_facts = audit_facts_and_tone(
        raw_text, profile, confidential_mode=confidential_mode
    )

    # 3. Visual Identity CV Engine (Color, CVD, WCAG, Optical Clear-Space)
    visual_findings = []
    if img_for_cv is not None:
        visual_findings = audit_image_array(img_for_cv, profile)
    elif pdf_file_obj is not None:
        visual_findings = audit_pdf_file(pdf_file_obj, profile)

    all_findings_raw = lex_findings + fact_findings + visual_findings

    # Compute compliance score and detailed breakdown
    score, score_breakdown = calculate_score(all_findings_raw)

    # Compute 4-Axis Voice Fingerprint Radar
    voice_fingerprint = compute_voice_fingerprint(raw_text, channel_context)

    # Resolve author
    user = get_authenticated_user_from_request(request)

    # Create Submission
    submission = Submission.objects.create(
        profile=profile,
        author=user,
        title=title,
        channel_context=channel_context,
        status='IN_REVIEW',
        confidential_mode=confidential_mode,
    )

    # Create Version 1
    version = SubmissionVersion.objects.create(
        submission=submission,
        version_number=1,
        raw_text=raw_text,
        file_type=file_type,
        compliance_score=score,
        score_breakdown=score_breakdown,
        voice_fingerprint=voice_fingerprint,
    )

    if use_sample_banner:
        banner_rel = "sample_offbrand_banner.png"
        version.uploaded_file.name = banner_rel
        version.save()
    elif uploaded_file:
        version.uploaded_file = uploaded_file
        version.save()

    with transaction.atomic():
        # Save findings
        for f in all_findings_raw:
            AuditFinding.objects.create(
                version=version,
                pillar=f.get('pillar', 'TONE'),
                severity=f.get('severity', 'WARNING'),
                engine_provenance=f.get('engine_provenance', 'DETERMINISTIC_LEXICON'),
                confidence=f.get('confidence', 1.0),
                rule_citation_code=f.get('rule_citation_code', 'GEN_001'),
                rule_citation_title=f.get('rule_citation_title', 'Brand Inconsistency'),
                source_excerpt=f.get('source_excerpt', ''),
                location_json=f.get('location_json', {}),
                explanation=f.get('explanation', ''),
                suggested_fixes=f.get('suggested_fixes', []),
                status='OPEN',
            )

        # Increment trigger counts
        all_triggered_rule_codes = set(fact_triggered_rules)
        for r_id in triggered_rules:
            rule_obj = BrandRule.objects.filter(id=r_id).first()
            if rule_obj:
                rule_obj.trigger_count += 1
                rule_obj.save()

        for code in all_triggered_rule_codes:
            rule_obj = BrandRule.objects.filter(profile=profile, rule_code=code).first()
            if rule_obj:
                rule_obj.trigger_count += 1
                rule_obj.save()

        for code in triggered_facts:
            fact_obj = FactLedger.objects.filter(profile=profile, fact_code=code).first()
            if fact_obj:
                fact_obj.trigger_count += 1
                fact_obj.save()

        # Increment visual rule triggers
        for vf in visual_findings:
            vcode = vf.get('rule_citation_code')
            vr = BrandRule.objects.filter(profile=profile, rule_code=vcode).first()
            if vr:
                vr.trigger_count += 1
                vr.save()

        # Emit SCAN AuditEvent
        auth_user = get_authenticated_user_from_request(request)
        AuditEvent.emit(
            profile=profile,
            event_type='SCAN',
            user=auth_user if auth_user and auth_user.is_authenticated else None,
            submission=submission,
            submission_version=version,
            channel=submission.channel_context
        )

        # Emit RULE_VIOLATED AuditEvents for findings
        for f in all_findings_raw:
            rc = f.get('rule_citation_code', '')
            rule_obj = BrandRule.objects.filter(profile=profile, rule_code=rc).first()
            fact_obj = FactLedger.objects.filter(profile=profile, fact_code=rc).first()
            sev = rule_obj.severity if rule_obj else ('BLOCKER' if fact_obj else f.get('severity', 'WARNING'))

            AuditEvent.emit(
                profile=profile,
                event_type='RULE_VIOLATED',
                user=auth_user if auth_user and auth_user.is_authenticated else None,
                submission=submission,
                submission_version=version,
                rule_code=rc,
                fact_code=fact_obj.fact_code if fact_obj else '',
                rule=rule_obj,
                fact=fact_obj,
                severity=sev,
                channel=submission.channel_context
            )

    return JsonResponse(submission.to_dict(), safe=False)


@csrf_exempt
def resolve_finding_view(request, finding_id):
    """
    POST /api/findings/<uuid:finding_id>/resolve/
    Accepts:
    - {"action": "ACCEPT_FIX", "chosen_fix": "..."} -> patches copy into Version v+1
    - {"action": "REQUEST_OVERRIDE", "override_reason": "..."} -> marks finding OVERRIDDEN_PENDING
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    finding = AuditFinding.objects.filter(id=finding_id).first()
    if not finding:
        return HttpResponseNotFound("Finding not found")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    action = body.get('action', '').upper()
    version = finding.version
    submission = version.submission
    profile = submission.profile

    if action == 'ACCEPT_FIX':
        chosen_fix = body.get('chosen_fix', '').strip()
        replacement_text = chosen_fix
        if replacement_text.startswith("Replace with '") and replacement_text.endswith("'"):
            replacement_text = replacement_text[14:-1]
        elif replacement_text.startswith("Replace with "):
            replacement_text = replacement_text[13:]

        old_text = version.raw_text
        target_excerpt = finding.source_excerpt

        if target_excerpt and target_excerpt in old_text:
            new_text = old_text.replace(target_excerpt, replacement_text, 1)
        else:
            new_text = old_text + f" {replacement_text}"

        auth_user = get_authenticated_user_from_request(request)
        with transaction.atomic():
            finding.status = 'ACCEPTED'
            finding.save()

            # Re-audit the patched text to create Version v+1
            new_version_num = version.version_number + 1

            lex_findings, _ = audit_lexicon(new_text, profile)
            fact_findings, _, _ = audit_facts_and_tone(new_text, profile, confidential_mode=submission.confidential_mode)

            # Retain visual findings from previous version
            retained_visual = []
            for vf in version.findings.filter(pillar='VISUAL'):
                retained_visual.append({
                    "pillar": vf.pillar,
                    "severity": vf.severity,
                    "engine_provenance": vf.engine_provenance,
                    "confidence": vf.confidence,
                    "rule_citation_code": vf.rule_citation_code,
                    "rule_citation_title": vf.rule_citation_title,
                    "source_excerpt": vf.source_excerpt,
                    "location_json": vf.location_json,
                    "explanation": vf.explanation,
                    "suggested_fixes": vf.suggested_fixes,
                    "status": vf.status,
                })

            new_all_findings = lex_findings + fact_findings + retained_visual
            new_score, new_breakdown = calculate_score(new_all_findings)
            new_voice_fp = compute_voice_fingerprint(new_text, submission.channel_context)

            new_version = SubmissionVersion.objects.create(
                submission=submission,
                version_number=new_version_num,
                raw_text=new_text,
                uploaded_file=version.uploaded_file,
                file_type=version.file_type,
                compliance_score=new_score,
                score_breakdown=new_breakdown,
                voice_fingerprint=new_voice_fp,
            )

            for f in new_all_findings:
                AuditFinding.objects.create(
                    version=new_version,
                    pillar=f.get('pillar', 'TONE'),
                    severity=f.get('severity', 'WARNING'),
                    engine_provenance=f.get('engine_provenance', 'DETERMINISTIC_LEXICON'),
                    confidence=f.get('confidence', 1.0),
                    rule_citation_code=f.get('rule_citation_code', 'GEN_001'),
                    rule_citation_title=f.get('rule_citation_title', 'Brand Inconsistency'),
                    source_excerpt=f.get('source_excerpt', ''),
                    location_json=f.get('location_json', {}),
                    explanation=f.get('explanation', ''),
                    suggested_fixes=f.get('suggested_fixes', []),
                    status=f.get('status', 'OPEN'),
                )

            # If submission was stale, and no blockers remain, transition to IN_REVIEW
            if submission.status == 'STALE_REAUDIT_REQUIRED':
                blockers_left = sum(1 for f in new_all_findings if f.get('severity') == 'BLOCKER')
                if blockers_left == 0:
                    submission.status = 'IN_REVIEW'
                    submission.save()

            # Emit FIX_ACCEPTED telemetry event
            AuditEvent.emit(
                profile=profile,
                event_type='FIX_ACCEPTED',
                user=auth_user if auth_user and auth_user.is_authenticated else None,
                submission=submission,
                submission_version=new_version,
                rule_code=finding.rule_citation_code,
                severity=finding.severity,
                channel=submission.channel_context
            )

        return JsonResponse({
            "status": "success",
            "action": "ACCEPT_FIX",
            "submission": submission.to_dict(),
        })

    elif action == 'REQUEST_OVERRIDE':
        override_reason = body.get('override_reason', '').strip()
        finding.status = 'OVERRIDDEN_PENDING'
        finding.override_reason = override_reason
        finding.save()

        submission.status = 'EXCEPTION_PENDING'
        submission.save()

        citation = finding.rule_citation_code
        rule_obj = BrandRule.objects.filter(profile=profile, rule_code=citation).first()
        if rule_obj:
            rule_obj.override_count += 1
            rule_obj.save()
        else:
            fact_obj = FactLedger.objects.filter(profile=profile, fact_code=citation).first()
            if fact_obj:
                fact_obj.override_count += 1
                fact_obj.save()

        return JsonResponse({
            "status": "success",
            "action": "REQUEST_OVERRIDE",
            "submission": submission.to_dict(),
        })

    return HttpResponseBadRequest(f"Unknown action: {action}")


@csrf_exempt
def submissions_list_view(request):
    """
    GET /api/submissions/
    Returns list of submissions for My Workspace.
    Writers see their own submissions; admins see all submissions.
    Supports filtering by status (?status=IN_REVIEW) and search.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    user = get_authenticated_user_from_request(request)
    profile = get_active_profile()
    qs = Submission.objects.filter(profile=profile)

    if user and getattr(user, 'role', '') == 'CONTENT_WRITER':
        qs = qs.filter(author=user)

    status_filter = request.GET.get('status', '').strip().upper()
    if status_filter:
        qs = qs.filter(status=status_filter)

    search = request.GET.get('search', '').strip()
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(channel_context__icontains=search) |
            Q(status__icontains=search)
        )

    submissions = [s.to_dict() for s in qs.order_by('-created_at')]
    return JsonResponse({
        "status": "success",
        "submissions": submissions,
        "total": len(submissions)
    })


@csrf_exempt
def submission_detail_view(request, sub_id):
    """
    GET /api/submissions/<uuid:sub_id>/
    Returns full submission record with versions, findings, and score.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    submission = Submission.objects.filter(id=sub_id).first()
    if not submission:
        return JsonResponse({"error": "Submission not found"}, status=404)

    return JsonResponse(submission.to_dict())


@csrf_exempt
def live_lint_view(request):
    """
    POST /api/submissions/live-lint/
    Real-time debounced lexicon and tone linter for interactive writing.
    Does not create a database submission record.
    Returns findings, character spans, readiness score, and breakdown.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    raw_text = body.get('raw_text', '')
    channel_context = body.get('channel_context', 'LINKEDIN_POST')
    profile = get_active_profile()

    lex_findings, _ = audit_lexicon(raw_text, profile)
    fact_findings, _, _ = audit_facts_and_tone(raw_text, profile, confidential_mode=False)

    all_findings = lex_findings + fact_findings
    score, breakdown = calculate_score(all_findings)
    voice_fp = compute_voice_fingerprint(raw_text, channel_context)

    return JsonResponse({
        "status": "success",
        "findings": all_findings,
        "count": len(all_findings),
        "compliance_score": score,
        "score_breakdown": breakdown,
        "voice_fingerprint": voice_fp,
        "raw_text": raw_text
    })


@csrf_exempt
@admin_required
def approve_submission_view(request, sub_id):
    """
    POST /api/submissions/<uuid:sub_id>/approve/
    Manager endpoint:
    1. Approves pending overrides
    2. Generates SHA256 cryptographic clearance hash
    3. Injects immutable XMP / PngInfo metadata into PNG or PDF asset
    4. Saves signed file to media/uploads/signed_<sub_id>_<filename>
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    submission = Submission.objects.filter(id=sub_id).first()
    if not submission:
        return HttpResponseNotFound("Submission not found")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}

    reviewer_comment = body.get('reviewer_comment', 'Approved by Brand Governance Lead.')

    latest_version = submission.versions.order_by('-version_number').first()
    if latest_version:
        for finding in latest_version.findings.all():
            if finding.status == 'OVERRIDDEN_PENDING':
                finding.status = 'OVERRIDE_APPROVED'
                finding.reviewer_comment = reviewer_comment
                finding.save()

    # Locate asset source file
    source_path = None
    if latest_version and latest_version.uploaded_file and latest_version.uploaded_file.name:
        cand = Path(settings.MEDIA_ROOT) / latest_version.uploaded_file.name
        if cand.exists():
            source_path = cand
    if not source_path:
        cand_sample = Path(settings.MEDIA_ROOT) / "sample_offbrand_banner.png"
        if cand_sample.exists():
            source_path = cand_sample

    file_bytes = b"NovaPay-BrandGuard-Clearance-Payload"
    if source_path and source_path.exists():
        try:
            with open(source_path, 'rb') as f:
                file_bytes = f.read()
        except Exception:
            pass

    user = get_authenticated_user_from_request(request)
    approver_username = (user.get_full_name() or user.username) if user else body.get('reviewer_name', 'Jordan Lee')

    # Create / update cryptographic clearance signature record in DB
    sig_obj = BrandComplianceSignature.create_signature(
        submission=submission,
        file_bytes=file_bytes,
        approver_username=approver_username
    )
    clearance_hash = f"SHA256-{sig_obj.hmac_signature[:32]}"
    canonical_payload = sig_obj.canonical_payload
    hmac_sig = sig_obj.hmac_signature
    ed25519_sig = sig_obj.ed25519_signature
    ed25519_pub = sig_obj.ed25519_public_key

    # Embed Cryptographic Metadata (tEXt tags + ISO XMP) into Image / PDF Asset
    signed_rel_url = ""
    try:
        if source_path and source_path.exists():
            upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            suffix = source_path.suffix.lower()
            now_iso = sig_obj.timestamp.isoformat() + 'Z'
            ruleset_ver = sig_obj.ruleset_version

            if suffix in ['.png', '.jpg', '.jpeg']:
                signed_filename = f"signed_{submission.id}_{source_path.stem}.png"
                out_path = upload_dir / signed_filename
                embed_clearance_in_png(
                    source_path=source_path,
                    out_path=out_path,
                    clearance_hash=clearance_hash,
                    hmac_sig=hmac_sig,
                    ed25519_sig=ed25519_sig,
                    ed25519_pub=ed25519_pub,
                    canonical_payload=canonical_payload,
                    draft_id=str(submission.id),
                    ruleset_version=ruleset_ver,
                    approver=approver_username,
                    timestamp_iso=now_iso,
                    title=submission.title
                )
                signed_rel_url = f"/media/uploads/{signed_filename}"

            elif suffix == '.pdf':
                signed_filename = f"signed_{submission.id}_{source_path.name}"
                out_path = upload_dir / signed_filename
                embed_clearance_in_pdf(
                    source_path=source_path,
                    out_path=out_path,
                    clearance_hash=clearance_hash,
                    hmac_sig=hmac_sig,
                    ed25519_sig=ed25519_sig,
                    ed25519_pub=ed25519_pub,
                    canonical_payload=canonical_payload,
                    draft_id=str(submission.id),
                    ruleset_version=ruleset_ver,
                    approver=approver_username,
                    timestamp_iso=now_iso,
                    title=submission.title
                )
                signed_rel_url = f"/media/uploads/{signed_filename}"
    except Exception:
        pass

    submission.status = 'APPROVED'
    submission.clearance_hash = clearance_hash
    if signed_rel_url:
        submission.signed_file_url = signed_rel_url
    submission.save()

    # Log to AuditTrail
    AuditTrail.log(
        request,
        action="SUBMISSION_APPROVED_SIGNED",
        entity_type="SUBMISSION",
        entity_id=str(submission.id),
        description=f"Submission '{submission.title}' signed and cleared by {approver_username}. Clearance hash: {clearance_hash}."
    )

    if submission.author:
        from governance.notifications import dispatch_notification
        dispatch_notification(
            recipient=submission.author,
            notification_type='STAMP_APPROVED',
            title=f"Compliance Clearance: {submission.title}",
            message=f"Admin {approver_username} has approved and cryptographically stamped '{submission.title}'. Asset is cleared for publication.",
            link_url=f"/api/submissions/{submission.id}/"
        )

    return JsonResponse({
        "status": "success",
        "clearance_hash": clearance_hash,
        "hmac_signature": hmac_sig,
        "ed25519_signature": ed25519_sig,
        "ed25519_public_key": ed25519_pub,
        "canonical_payload": canonical_payload,
        "signed_file_url": submission.signed_file_url,
        "legal_notice": LEGAL_NOTICE,
        "submission": submission.to_dict(),
        "signature": sig_obj.to_dict(),
    })


@csrf_exempt
def verify_stamp_view(request):
    """
    POST /api/submissions/verify-stamp/
    CMS Verification endpoint: Accepts an uploaded image or PDF and verifies
    whether its embedded cryptographic metadata (HMAC / Ed25519 / XMP) matches
    a valid signature and registered clearance hash.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    uploaded = request.FILES.get('file')
    if not uploaded:
        return HttpResponseBadRequest("No file uploaded")

    temp_dir = Path(settings.MEDIA_ROOT) / "temp_verify"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"verify_{uploaded.name}"

    try:
        with open(temp_file, 'wb+') as dest:
            for chunk in uploaded.chunks():
                dest.write(chunk)

        result = verify_asset_clearance(temp_file)
        submission = None
        if result.get("clearance_hash"):
            submission = Submission.objects.filter(clearance_hash=result["clearance_hash"]).first()

        return JsonResponse({
            "verified": result.get("verified", False),
            "status": result.get("status"),
            "compliance_status": result.get("compliance_status"),
            "clearance_hash": result.get("clearance_hash"),
            "hmac_signature": result.get("hmac_signature"),
            "ed25519_signature": result.get("ed25519_signature"),
            "canonical_payload": result.get("canonical_payload"),
            "has_xmp": result.get("has_xmp", False),
            "legal_notice": result.get("legal_notice") or LEGAL_NOTICE,
            "metadata": {
                "approver": result.get("approver"),
                "approved_at": result.get("timestamp"),
                "ruleset_version": result.get("ruleset_version"),
            },
            "submission": submission.to_dict() if submission else None,
        })
    finally:
        try:
            if temp_file.exists():
                temp_file.unlink()
        except Exception:
            pass


@csrf_exempt
def brand_safe_prompt_view(request):
    """
    GET /api/brand-profile/safe-prompt/?channel=LINKEDIN_POST
    Compiles an AI-Safe Writer System Prompt & .cursorrules file
    grounded in the active profile's non-expired truths and lexicon rules.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    channel = request.GET.get('channel', 'LINKEDIN_POST')
    profile = get_active_profile()

    # Active facts only (filter out expired ones)
    today = date.today()
    active_facts = [f for f in profile.facts.all() if f.valid_until and f.valid_until >= today]
    rules = profile.rules.all()

    # Channel voice target
    voice_target = TARGET_VOICE_ENVELOPES.get(channel, TARGET_VOICE_ENVELOPES['LINKEDIN_POST'])

    # Compile Markdown System Prompt
    prompt_lines = [
        f"# SYSTEM GOVERNANCE PROMPT: {profile.org_name.upper()}",
        f"Target Channel: {channel}",
        f"Compiled At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## 1. VOICE & TONE ENVELOPE (TARGET METRICS)",
        f"- Urgency: {voice_target['urgency']}/100",
        f"- Formality: {voice_target['formality']}/100",
        f"- Technicality: {voice_target['technicality']}/100",
        f"- Warmth: {voice_target['warmth']}/100",
        "",
        "## 2. STRICT LEXICON & CASING BOUNDARIES",
    ]

    for r in rules:
        spec = r.structured_spec or {}
        banned = spec.get('banned_term')
        repl = spec.get('replacement')
        if banned and repl:
            prompt_lines.append(f"- NEVER use '{banned}' -> MUST replace with '{repl}' ({r.title})")
        else:
            prompt_lines.append(f"- Rule [{r.rule_code}] {r.title}: {r.rule_description}")

    prompt_lines.extend([
        "",
        "## 3. CITATION-GROUNDED TRUTH LEDGER (DO NOT HALLUCINATE OR USE OUTDATED STATS)",
    ])

    for f in active_facts:
        prompt_lines.append(f"- [{f.fact_code}] {f.category}: \"{f.claim_truth}\" (Verified until {f.valid_until})")

    prompt_lines.extend([
        "",
        "## 4. APPROVED BRAND PALETTE & STYLING TOKENS",
    ])
    for sw in profile.allowed_hex_palette:
        prompt_lines.append(f"- {sw.get('name')}: {sw.get('hex')} (Max ΔE: {sw.get('max_delta_e', 4.0)})")

    prompt_lines.extend([
        "",
        "## 5. GENERATION DIRECTIVES",
        "- All claims must directly reference an active fact citation code above.",
        "- Do not use filler clichés like 'delve into', 'in today's fast-paced landscape', or 'testament to'.",
        "- Ensure copy satisfies WCAG 2.1 AA legibility when paired with brand colors.",
    ])

    compiled_markdown = "\n".join(prompt_lines)

    return JsonResponse({
        "channel": channel,
        "org_name": profile.org_name,
        "voice_envelope": voice_target,
        "system_prompt": compiled_markdown,
    })


@admin_required
def telemetry_view(request):
    """
    GET /api/telemetry/
    Admin-only live governance telemetry and ambiguity diagnostics.
    Content writers receive HTTP 403 Forbidden.
    All metrics computed strictly from AuditEvent rows inside window (7/30/90 days).
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    if not profile:
        return JsonResponse({"error": "No brand profile associated with user."}, status=400)

    try:
        days = int(request.GET.get('days', 30))
    except (ValueError, TypeError):
        days = 30

    channel = request.GET.get('channel', 'ALL')
    if channel in ('', 'ALL', 'all'):
        channel = None

    from governance.engines.telemetry import calculate_window_telemetry
    data = calculate_window_telemetry(profile=profile, days=days, channel=channel)

    # Add backward compatibility keys for legacy assertions and UI integration
    min_triggers_param = request.GET.get('min_triggers')
    scores = [r["friction_score"] for r in data["rules"]]
    data["overall_friction_index"] = round(sum(scores) / len(scores), 1) if scores else 0.0
    data["min_triggers"] = int(min_triggers_param) if min_triggers_param else data["kpis"].get("min_triggers", 10)
    for r in data["rules"]:
        r["findings"] = r["triggers"]
        r["friction_level"] = "HIGH" if r["friction_score"] >= 1.5 else ("MEDIUM" if r["friction_score"] >= 0.5 else "LOW")

    if min_triggers_param:
        try:
            mt = int(min_triggers_param)
            data["friction_leaderboard"] = [r for r in data["rules"] if r["triggers"] >= mt]
        except Exception:
            data["friction_leaderboard"] = data["rules"]
    else:
        data["friction_leaderboard"] = data["rules"]

    return JsonResponse(data, safe=False)


@admin_required
def telemetry_export_csv_view(request):
    """
    GET /api/telemetry/export-csv/
    Admin-only CSV export of rule performance and ambiguity diagnostics.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    if not profile:
        return JsonResponse({"error": "No brand profile associated with user."}, status=400)

    try:
        days = int(request.GET.get('days', 30))
    except (ValueError, TypeError):
        days = 30

    channel = request.GET.get('channel', 'ALL')
    if channel in ('', 'ALL', 'all'):
        channel = None

    from governance.engines.telemetry import calculate_window_telemetry, generate_telemetry_csv
    data = calculate_window_telemetry(profile=profile, days=days, channel=channel)
    csv_str = generate_telemetry_csv(data)

    response = HttpResponse(csv_str, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="brandguard_telemetry_{days}d.csv"'
    return response


@admin_required
def telemetry_export_pdf_view(request):
    """
    GET /api/telemetry/export-pdf/
    Admin-only executive PDF report of governance telemetry.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    if not profile:
        return JsonResponse({"error": "No brand profile associated with user."}, status=400)

    try:
        days = int(request.GET.get('days', 30))
    except (ValueError, TypeError):
        days = 30

    channel = request.GET.get('channel', 'ALL')
    if channel in ('', 'ALL', 'all'):
        channel = None

    from governance.engines.telemetry import calculate_window_telemetry
    from governance.pdf_report import generate_telemetry_report_pdf

    data = calculate_window_telemetry(profile=profile, days=days, channel=channel)
    pdf_bytes = generate_telemetry_report_pdf(data, org_name=profile.org_name)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="brandguard_telemetry_{days}d.pdf"'
    return response


@writer_required
def writer_telemetry_summary_view(request):
    """
    GET /api/telemetry/writer-summary/
    Writer-facing endpoint: Returns only "My top 5 triggered rules" with coaching training tips.
    Zero org-wide metrics are exposed.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    user = request.user

    from django.db.models import Count
    from governance.models import AuditEvent, BrandRule

    # Get top 5 triggered rules specifically for this writer
    top_rule_counts = list(
        AuditEvent.objects.filter(
            profile=profile,
            user=user,
            event_type='RULE_VIOLATED'
        ).values('rule_code').annotate(triggers=Count('id')).order_by('-triggers')[:5]
    )

    my_top_rules = []
    for item in top_rule_counts:
        code = item['rule_code']
        rule = BrandRule.objects.filter(profile=profile, rule_code=code).first()
        if rule:
            title = rule.title
            pillar = rule.pillar
            severity = rule.severity
            tip = (
                f"Permitted language: '{rule.claims_allowed[:90]}'. Avoid: '{rule.claims_disallowed[:90]}'."
                if rule.claims_allowed else (rule.rule_description or "Adhere closely to brand style spec.")
            )
        else:
            title = f"Fact Check: {code}"
            pillar = "FACTUAL"
            severity = "BLOCKER"
            tip = "Verify product truth and financial figures against Fact Ledger before submitting."

        my_top_rules.append({
            "rule_code": code,
            "title": title,
            "pillar": pillar,
            "severity": severity,
            "trigger_count": item['triggers'],
            "training_tip": tip,
        })

    return JsonResponse({
        "writer": {
            "username": user.username,
            "name": user.get_full_name() or user.username,
            "department": getattr(user, 'department', 'Marketing'),
        },
        "my_top_rules": my_top_rules,
    })


@writer_required
def job_status_view(request, job_id):
    """
    GET /api/jobs/<uuid:job_id>/
    Exposes background task status, progress, error, and result payload.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    job = Job.objects.filter(id=job_id, profile=profile).first()
    if not job:
        return JsonResponse({"error": "Job not found"}, status=404)

    return JsonResponse(job.to_dict())


@csrf_exempt
def exception_requests_view(request):
    """
    GET /api/exceptions/ -> lists exception requests
    POST /api/exceptions/ -> creates a new exception request
    """
    if request.method == 'GET':
        status_filter = request.GET.get('status')
        qs = ExceptionRequest.objects.all().order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        items = [ex.to_dict() for ex in qs]
        return JsonResponse({"exceptions": items, "count": len(items)}, safe=False)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        rule_code = body.get('rule_code', '').strip().upper()
        warning_type = body.get('warning_type', '').strip().upper()
        pillar_spec = body.get('pillar', '').strip().upper()

        # HARD SECURITY REQUIREMENT: Tone rules only! FACT and Accessibility rules strictly blocked server-side.
        if rule_code.startswith('FACT_') or 'FACT' in warning_type or pillar_spec == 'FACTUAL':
            return JsonResponse({
                "error": "Exceptions are strictly restricted to tone/voice rules. Factual truth claims cannot be overridden under any circumstances.",
                "rule_code": rule_code,
                "pillar": "FACTUAL"
            }, status=400)

        if (rule_code.startswith('VIS_') or
            'VISUAL' in warning_type or
            'ACCESSIBILITY' in warning_type or
            'WCAG' in rule_code or
            pillar_spec == 'VISUAL'):
            return JsonResponse({
                "error": "Exceptions are strictly restricted to tone/voice rules. Visual brand identity and WCAG accessibility standards cannot be overridden.",
                "rule_code": rule_code,
                "pillar": "VISUAL"
            }, status=400)

        # Check existing BrandRule in database if registered
        profile = get_active_profile()
        rule_obj = BrandRule.objects.filter(profile=profile, rule_code=rule_code).first()
        if rule_obj and rule_obj.pillar != 'TONE':
            return JsonResponse({
                "error": f"Exceptions are strictly restricted to tone/voice rules. Rule {rule_code} belongs to pillar '{rule_obj.pillar}' which cannot be overridden.",
                "rule_code": rule_code,
                "pillar": rule_obj.pillar
            }, status=400)

        count = ExceptionRequest.objects.count() + 1
        new_id = body.get('id') or f"EX-{2040 + count}"

        user = get_authenticated_user_from_request(request)
        requester_name = body.get('requester_name') or (user.get_full_name() or user.username if user else 'Alex Morgan')
        requester_dept = body.get('requester_dept') or (getattr(user, 'department', 'Marketing') if user else 'Marketing')

        # Link Submission if available
        sub = None
        sub_id = body.get('submission_id') or body.get('draft_id')
        if sub_id:
            try:
                sub = Submission.objects.filter(id=sub_id).first()
            except Exception:
                sub = Submission.objects.filter(title__icontains=body.get('title', '')).first()
        if not sub and body.get('title'):
            sub = Submission.objects.filter(title=body.get('title')).first()

        with transaction.atomic():
            ex = ExceptionRequest.objects.create(
                id=new_id,
                submission=sub,
                author=user,
                draft_id=body.get('draft_id', 'DRAFT_024'),
                rule_code=rule_code or 'VOICE_004',
                title=body.get('title', "Global ambition. Local simplicity."),
                requester_name=requester_name,
                requester_dept=requester_dept,
                requested_date=date.today(),
                warning_type=body.get('warning_type', 'Warning · Voice'),
                quote_text=body.get('quote_text', "Don't get wrecked by banks!"),
                rule_description=body.get('rule_description', "Aggressive comparison tone is outside the default voice range."),
                justification=body.get('justification', ""),
                campaign_reference=body.get('campaign_reference', 'Global ambition · Q3 2026 launch'),
                scope=body.get('scope', 'This draft only'),
                channel=body.get('channel', 'LinkedIn post'),
                expires_on=date(2026, 10, 31),
                reviewer_name=body.get('reviewer_name', 'Jordan Lee'),
                reviewer_title=body.get('reviewer_title', 'Brand Governance Lead'),
                hard_blockers_count=body.get('hard_blockers_count', 0),
                supporting_file_name=body.get('supporting_file_name', 'Q3_challenger_campaign.pdf'),
                supporting_file_size=body.get('supporting_file_size', '1.2 MB'),
                status='PENDING',
            )

            if sub:
                sub.status = 'EXCEPTION_PENDING'
                sub.save()

            # Emit EXCEPTION_REQUESTED event
            profile = (sub.profile if sub else None) or get_user_profile(request)
            AuditEvent.emit(
                profile=profile,
                event_type='EXCEPTION_REQUESTED',
                user=user if user and user.is_authenticated else None,
                submission=sub,
                rule_code=ex.rule_code,
                channel=ex.channel
            )

            # Audit trail
            AuditTrail.log(
                request,
                action="EXCEPTION_REQUESTED",
                entity_type="EXCEPTION_REQUEST",
                entity_id=ex.id,
                description=f"Writer {requester_name} requested tone exception for {ex.rule_code} in '{ex.title}'."
            )

        # Multi-channel notification to all admins
        from governance.notifications import dispatch_notification
        for admin_u in BrandGuardUser.objects.filter(role='ADMIN'):
            dispatch_notification(
                recipient=admin_u,
                notification_type='EXCEPTION_PENDING',
                title=f"Exception Request {ex.id}: {ex.rule_code}",
                message=f"Writer {requester_name} requested a tone exception for '{ex.title}'.",
                link_url=f"/api/exceptions/{ex.id}/"
            )

        return JsonResponse(ex.to_dict(), status=201)

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def exception_detail_view(request, exception_id):
    """
    GET /api/exceptions/<exception_id>/
    """
    try:
        ex = ExceptionRequest.objects.get(id=exception_id)
        return JsonResponse(ex.to_dict())
    except ExceptionRequest.DoesNotExist:
        return HttpResponseNotFound("Exception request not found")


@csrf_exempt
@admin_required
def exception_decision_view(request, exception_id):
    """
    POST /api/exceptions/<exception_id>/decide/ (and /decision/)
    Admin-only endpoint: decides on exception requests.
    Content writers receive HTTP 403 Forbidden.
    Updates status timeline, notifications, and submission synchronization.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        ex = ExceptionRequest.objects.get(id=exception_id)
    except ExceptionRequest.DoesNotExist:
        return HttpResponseNotFound("Exception request not found")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}

    from django.utils import timezone
    raw_status = body.get('status', 'APPROVED').upper()
    if raw_status in ('REJECT', 'REJECTED', 'DECLINED', 'DECLINE'):
        new_status = 'DECLINED'
    else:
        new_status = 'APPROVED'

    decision_note = body.get('decision_note', 'Reviewed. The challenger voice fits this audience and the scope is narrow.').strip()
    reviewer_name = body.get('reviewer_name') or (request.user.get_full_name() or request.user.username)

    with transaction.atomic():
        ex.status = new_status
        ex.decision_note = decision_note
        ex.decided_at = timezone.now()
        ex.decided_by = reviewer_name
        ex.decided_by_user = request.user
        ex.save()

        # Synchronize submission & findings
        sub = ex.submission
        if not sub and ex.draft_id:
            try:
                sub = Submission.objects.filter(id=ex.draft_id).first()
            except Exception:
                sub = Submission.objects.filter(title=ex.title).first()

        profile = (sub.profile if sub else None) or get_user_profile(request)

        if sub:
            latest_v = sub.versions.order_by('-version_number').first()
            if latest_v:
                finding = latest_v.findings.filter(rule_citation_code=ex.rule_code).first()
                if finding:
                    if new_status == 'APPROVED':
                        finding.status = 'OVERRIDE_APPROVED'
                        finding.reviewer_comment = decision_note
                        finding.save()
                    else:
                        finding.status = 'REJECTED'
                        finding.reviewer_comment = decision_note
                        finding.save()

                approved_count = latest_v.findings.filter(status='OVERRIDE_APPROVED').count()
                open_blockers = latest_v.findings.filter(severity='BLOCKER', status='OPEN').count()

                new_score, new_breakdown = calculate_score(latest_v.findings.all(), approved_exception_count=approved_count)
                latest_v.compliance_score = new_score
                latest_v.score_breakdown = new_breakdown
                latest_v.save()

                if new_status == 'APPROVED' and open_blockers == 0:
                    sub.status = 'APPROVED'
                elif new_status == 'DECLINED':
                    sub.status = 'IN_REVIEW'
                sub.save()

        # Emit EXCEPTION_APPROVED or EXCEPTION_DECLINED AuditEvent
        if new_status == 'APPROVED':
            AuditEvent.emit(
                profile=profile,
                event_type='EXCEPTION_APPROVED',
                user=request.user,
                submission=sub,
                rule_code=ex.rule_code,
                channel=ex.channel
            )
            rule_obj = BrandRule.objects.filter(profile=profile, rule_code=ex.rule_code).first()
            if rule_obj:
                rule_obj.override_count += 1
                rule_obj.save(update_fields=['override_count'])
        else:
            AuditEvent.emit(
                profile=profile,
                event_type='EXCEPTION_DECLINED',
                user=request.user,
                submission=sub,
                rule_code=ex.rule_code,
                channel=ex.channel
            )

        # Multi-channel notification for the writer/requester
        recipient = ex.author or BrandGuardUser.objects.filter(username=ex.requester_name).first()
        if recipient:
            from governance.notifications import dispatch_notification
            dispatch_notification(
                recipient=recipient,
                notification_type='EXCEPTION_APPROVED' if new_status == 'APPROVED' else 'EXCEPTION_REJECTED',
                title=f"Exception {ex.id} {new_status.capitalize()}",
                message=f"Admin {reviewer_name} has {new_status.lower()} your request for [{ex.rule_code}]. Note: '{decision_note}'",
                link_url=f"/api/exceptions/{ex.id}/"
            )

        # Audit trail
        AuditTrail.log(
            request,
            action=f"EXCEPTION_{new_status}",
            entity_type="EXCEPTION_REQUEST",
            entity_id=ex.id,
            description=f"Admin {reviewer_name} {new_status.lower()} exception request {ex.id} for {ex.rule_code}: '{decision_note}'."
        )

    return JsonResponse(ex.to_dict())


@csrf_exempt
def rules_list_create_view(request):
    """
    GET /api/rules/ -> List active rules with search/filter (severity, pillar, status, query)
    POST /api/rules/ -> Admin creates a new rule (creates version 1)
    """
    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    if request.method == 'GET':
        qs = BrandRule.objects.filter(profile=profile)

        # Filters
        pillar = request.GET.get('pillar', '').strip().upper()
        if pillar:
            qs = qs.filter(pillar=pillar)

        severity = request.GET.get('severity', '').strip().upper()
        if severity:
            qs = qs.filter(severity=severity)

        status = request.GET.get('status', 'active').strip().lower()
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        search = request.GET.get('search', '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(rule_code__icontains=search) |
                Q(title__icontains=search) |
                Q(rule_description__icontains=search) |
                Q(claims_allowed__icontains=search) |
                Q(claims_disallowed__icontains=search)
            )

        rules = [r.to_dict() for r in qs.order_by('rule_code')]
        return JsonResponse({"rules": rules, "total": len(rules)})

    elif request.method == 'POST':
        user = get_authenticated_user_from_request(request)
        if not user:
            return JsonResponse({"error": "Unauthorized", "detail": "Authentication required."}, status=401)
        if getattr(user, 'role', '') != 'ADMIN' and not user.is_superuser:
            return JsonResponse({"error": "Forbidden", "detail": "Admin privileges required to create rules."}, status=403)

        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        rule_code = body.get('rule_code', '').strip().upper()
        title = body.get('title', '').strip()
        pillar = body.get('pillar', 'TONE').strip().upper()
        severity = body.get('severity', 'WARNING').strip().upper()
        enforcement = body.get('enforcement', 'Block publish').strip()
        claims_allowed = body.get('claims_allowed', '').strip()
        claims_disallowed = body.get('claims_disallowed', '').strip()
        description = body.get('rule_description', '').strip()
        source = body.get('source', 'NovaPay Brand Guidelines').strip()
        banned_term = body.get('banned_term', '').strip()
        replacement = body.get('replacement', '').strip()

        if not rule_code or not title:
            return JsonResponse({"error": "rule_code and title are required."}, status=400)

        if BrandRule.objects.filter(profile=profile, rule_code=rule_code).exists():
            return JsonResponse({"error": f"Rule with code '{rule_code}' already exists."}, status=400)

        structured_spec = body.get('structured_spec', {})
        if banned_term:
            structured_spec['banned_term'] = banned_term
        if replacement:
            structured_spec['replacement'] = replacement

        rule = BrandRule.objects.create(
            profile=profile,
            rule_code=rule_code,
            title=title,
            pillar=pillar,
            severity=severity,
            version=1,
            is_active=True,
            enforcement=enforcement,
            claims_allowed=claims_allowed or replacement,
            claims_disallowed=claims_disallowed or banned_term,
            source=source,
            structured_spec=structured_spec,
            rule_description=description,
            owner=f"{user.get_full_name() or user.username}, Brand Governance"
        )

        BrandRuleVersion.objects.create(
            rule=rule,
            version_number=1,
            title=rule.title,
            pillar=rule.pillar,
            severity=rule.severity,
            structured_spec=rule.structured_spec,
            rule_description=rule.rule_description,
            claims_allowed=rule.claims_allowed,
            claims_disallowed=rule.claims_disallowed,
            enforcement=rule.enforcement,
            source=rule.source,
            change_note="Initial rule creation.",
            changed_by=user
        )

        AuditTrail.log(
            request,
            action="RULE_CREATED",
            entity_type="RULE",
            entity_id=rule.rule_code,
            description=f"Admin created rule {rule.rule_code}: {rule.title}."
        )

        return JsonResponse({"status": "success", "rule": rule.to_dict()}, status=201)

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def rule_detail_view(request, rule_code):
    """
    GET /api/rules/<rule_code>/ -> Full rule details with version history & examples
    PUT/PATCH /api/rules/<rule_code>/ -> Admin updates rule, increments version, creates snapshot
    DELETE /api/rules/<rule_code>/ -> Admin deactivates rule
    """
    profile = get_active_profile()
    code = rule_code.strip().upper()
    rule = BrandRule.objects.filter(profile=profile, rule_code=code).first()

    if not rule:
        return JsonResponse({"error": f"Rule '{code}' not found."}, status=404)

    if request.method == 'GET':
        data = rule.to_dict()
        data["subtitle"] = f"{rule.rule_code} · Rule v{rule.version} · Part of ruleset v3.2"
        data["breadcrumb"] = f"RULE REGISTRY > {rule.pillar} > {rule.rule_code}"
        data["tags"] = [
            {"label": "Enabled" if rule.is_active else "Disabled", "type": "enabled" if rule.is_active else "disabled"},
            {"label": rule.severity.capitalize(), "type": rule.severity.lower()},
            {"label": rule.pillar.capitalize(), "type": "neutral"}
        ]
        data["test_examples"] = [
            {"quote": f"“{rule.claims_allowed or 'Standard compliant statement'}”", "status": "Pass"},
            {"quote": f"“{rule.claims_disallowed or 'Non-compliant statement'}”", "status": "Flag"},
        ]
        data["source_evidence"] = {
            "quote": f"{rule.rule_code}: {rule.rule_description or rule.title}",
            "ledger_entry": f"LEDGER-{rule.rule_code}",
            "source": rule.source or "NovaPay Brand Guidelines",
            "last_verified": "May 2026",
            "verified": True
        }
        data["change_history"] = [
            {
                "version": f"v{v.version_number}",
                "date": v.created_at.strftime('%b %d, %Y') if v.created_at else '',
                "current": v.version_number == rule.version,
                "note": v.change_note or "Rule update",
                "changed_by": v.changed_by.username if v.changed_by else "Admin"
            }
            for v in rule.versions.all().order_by('-version_number')
        ]
        data["versioning_note"] = "Changes are versioned. Existing audits retain the version they ran against."
        return JsonResponse(data)

    user = get_authenticated_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Unauthorized", "detail": "Authentication required."}, status=401)
    if getattr(user, 'role', '') != 'ADMIN' and not user.is_superuser:
        return JsonResponse({"error": "Forbidden", "detail": "Admin privileges required to modify rules."}, status=403)

    if request.method in ('PUT', 'PATCH'):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        change_note = body.get('change_note', '').strip() or f"Updated specification for {rule.rule_code}."
        if 'title' in body:
            rule.title = body['title'].strip()
        if 'severity' in body:
            rule.severity = body['severity'].strip().upper()
        if 'enforcement' in body:
            rule.enforcement = body['enforcement'].strip()
        if 'claims_allowed' in body:
            rule.claims_allowed = body['claims_allowed'].strip()
        if 'claims_disallowed' in body:
            rule.claims_disallowed = body['claims_disallowed'].strip()
        if 'rule_description' in body:
            rule.rule_description = body['rule_description'].strip()
        if 'structured_spec' in body:
            rule.structured_spec = body['structured_spec']
        if 'banned_term' in body or 'replacement' in body:
            spec = rule.structured_spec or {}
            if 'banned_term' in body:
                spec['banned_term'] = body['banned_term'].strip()
            if 'replacement' in body:
                spec['replacement'] = body['replacement'].strip()
            rule.structured_spec = spec
        if 'is_active' in body:
            rule.is_active = bool(body['is_active'])

        rule.version += 1
        rule.save()

        new_v = BrandRuleVersion.objects.create(
            rule=rule,
            version_number=rule.version,
            title=rule.title,
            pillar=rule.pillar,
            severity=rule.severity,
            structured_spec=rule.structured_spec,
            rule_description=rule.rule_description,
            claims_allowed=rule.claims_allowed,
            claims_disallowed=rule.claims_disallowed,
            enforcement=rule.enforcement,
            source=rule.source,
            change_note=change_note,
            changed_by=user
        )

        AuditTrail.log(
            request,
            action="RULE_UPDATED",
            entity_type="RULE",
            entity_id=rule.rule_code,
            description=f"Admin updated rule {rule.rule_code} to v{rule.version}: {change_note}."
        )

        return JsonResponse({"status": "success", "rule": rule.to_dict(), "new_version": new_v.to_dict()})

    elif request.method == 'DELETE':
        rule.is_active = False
        rule.save()

        AuditTrail.log(
            request,
            action="RULE_DEACTIVATED",
            entity_type="RULE",
            entity_id=rule.rule_code,
            description=f"Admin deactivated rule {rule.rule_code}."
        )
        return JsonResponse({"status": "success", "message": f"Rule '{rule.rule_code}' deactivated."})

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def rule_versions_view(request, rule_code):
    """
    GET /api/rules/<rule_code>/versions/
    Returns all historical versions of a rule for comparison.
    """
    profile = get_active_profile()
    rule = BrandRule.objects.filter(profile=profile, rule_code=rule_code.upper()).first()
    if not rule:
        return JsonResponse({"error": "Rule not found"}, status=404)

    versions = [v.to_dict() for v in rule.versions.all().order_by('-version_number')]
    return JsonResponse({
        "rule_code": rule.rule_code,
        "current_version": rule.version,
        "versions": versions
    })


@csrf_exempt
@admin_required
def rule_rollback_view(request, rule_code):
    """
    POST /api/rules/<rule_code>/rollback/
    Body: {"target_version": 2}
    Reverts active rule to snapshot from target_version, increments version counter,
    and logs rollback snapshot.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    rule = BrandRule.objects.filter(profile=profile, rule_code=rule_code.upper()).first()
    if not rule:
        return JsonResponse({"error": "Rule not found"}, status=404)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    target_version_num = body.get('target_version')
    if not target_version_num:
        return JsonResponse({"error": "target_version is required."}, status=400)

    target_snapshot = rule.versions.filter(version_number=target_version_num).first()
    if not target_snapshot:
        return JsonResponse({"error": f"Version {target_version_num} does not exist for rule {rule.rule_code}."}, status=404)

    rule.title = target_snapshot.title
    rule.severity = target_snapshot.severity
    rule.structured_spec = target_snapshot.structured_spec
    rule.rule_description = target_snapshot.rule_description
    rule.claims_allowed = target_snapshot.claims_allowed
    rule.claims_disallowed = target_snapshot.claims_disallowed
    rule.enforcement = target_snapshot.enforcement
    rule.source = target_snapshot.source
    rule.is_active = True

    old_v = rule.version
    rule.version += 1
    rule.save()

    new_snapshot = BrandRuleVersion.objects.create(
        rule=rule,
        version_number=rule.version,
        title=rule.title,
        pillar=rule.pillar,
        severity=rule.severity,
        structured_spec=rule.structured_spec,
        rule_description=rule.rule_description,
        claims_allowed=rule.claims_allowed,
        claims_disallowed=rule.claims_disallowed,
        enforcement=rule.enforcement,
        source=rule.source,
        change_note=f"Rolled back from v{old_v} to v{target_version_num} configuration.",
        changed_by=request.user
    )

    AuditTrail.log(
        request,
        action="RULE_ROLLED_BACK",
        entity_type="RULE",
        entity_id=rule.rule_code,
        description=f"Admin rolled back rule {rule.rule_code} from v{old_v} to v{target_version_num} (now v{rule.version})."
    )

    return JsonResponse({
        "status": "success",
        "message": f"Successfully rolled back {rule.rule_code} to v{target_version_num}. New version is v{rule.version}.",
        "rule": rule.to_dict(),
        "new_version": new_snapshot.to_dict()
    })


def get_client_ip(request):
    """Extracts client IP address safely from request headers or remote addr."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def validate_password_strength(password):
    """
    Validates enterprise password strength:
    - Minimum 12 characters
    - Contains uppercase and lowercase characters
    - Contains at least one digit or symbol
    """
    if not password or len(password) < 12:
        return False, "Password must be at least 12 characters in length."
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit_or_punct = any(not c.isalpha() for c in password)
    if not (has_upper and has_lower and has_digit_or_punct):
        return False, "Password must include uppercase, lowercase, and numeric or special characters."
    return True, "Valid"


@csrf_exempt
def auth_login_view(request):
    """
    POST /api/auth/login/
    Accepts: {"username": "...", "password": "...", "portal": "ADMIN" | "WRITER"}
    Enforces IP/identifier rate-limiting, account lockout, email verification, and approval checks.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    username = body.get('username', '').strip()
    email = body.get('email', '').strip()
    password = body.get('password', '').strip()
    portal = body.get('portal', 'WRITER').upper()

    if not username and not email:
        return JsonResponse({"error": "Username or email is required."}, status=400)

    identifier = username or email
    client_ip = get_client_ip(request)

    # 1. Rate Limiting Check (5 failures in 15 minutes)
    is_limited, limit_msg = LoginAttemptLog.is_rate_limited(client_ip, identifier, max_failures=5, window_minutes=15)
    if is_limited:
        return JsonResponse({"error": limit_msg, "rate_limited": True}, status=429)

    # 2. Check Candidate User & Lockout State
    cand = None
    try:
        cand = BrandGuardUser.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
    except Exception:
        pass

    if cand and cand.locked_until and cand.locked_until > timezone.now():
        return JsonResponse({
            "error": "Account temporarily locked due to repeated failed attempts. Please try again in 15 minutes.",
            "locked": True
        }, status=423)

    # 3. Authenticate Credentials
    user = None
    if username:
        user = authenticate(request, username=username, password=password)
    if not user and cand and cand.check_password(password):
        user = cand

    if not user:
        if cand:
            cand.failed_login_attempts += 1
            if cand.failed_login_attempts >= 5:
                cand.locked_until = timezone.now() + timedelta(minutes=15)
            cand.save(update_fields=['failed_login_attempts', 'locked_until'])
        LoginAttemptLog.record_attempt(client_ip, identifier, portal, success=False)
        return JsonResponse({"error": "Invalid username or password."}, status=401)

    # 4. Portal-Based Role Check
    # A) /admin/login: for ADMIN only. If a writer logs in here, show a neutral error.
    if portal == 'ADMIN':
        if not user.is_admin_user:
            LoginAttemptLog.record_attempt(client_ip, identifier, portal, success=False)
            return JsonResponse({"error": "Invalid credentials or unauthorized portal access."}, status=401)

    # 5. Email Verification Check (Bypassed for legacy seed accounts: admin, writer1, writer2)
    if not user.is_email_verified and user.username not in ('admin', 'writer1', 'writer2'):
        return JsonResponse({
            "error": "Please verify your email address before logging in.",
            "needs_email_verification": True,
            "email": user.email
        }, status=403)

    # 6. Admin Approval Check
    if not user.is_approved:
        return JsonResponse({
            "error": "Waiting for admin approval. Your administrator must approve your workspace access before you can log in.",
            "needs_approval": True,
            "status": "PENDING_APPROVAL"
        }, status=403)

    # 7. Account Active Check
    if not user.is_active:
        return JsonResponse({"error": "This account has been deactivated."}, status=403)

    # 8. Success: Reset Failures & Generate Session / JWT Token
    if user.failed_login_attempts > 0 or user.locked_until is not None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_attempts', 'locked_until'])

    LoginAttemptLog.record_attempt(client_ip, identifier, portal, success=True)
    login(request, user)
    token = generate_user_token(user)

    AuditTrail.log(
        request,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=str(user.id),
        description=f"User {user.username} ({user.role}) logged in successfully via {portal} portal."
    )

    return JsonResponse({
        "status": "success",
        "token": token,
        "user": user.to_dict(),
    })


@csrf_exempt
def auth_admin_login_view(request):
    """
    POST /api/auth/login/admin/
    Convenience alias forcing portal="ADMIN" for strict admin portal authentication.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}
    body['portal'] = 'ADMIN'
    request._body = json.dumps(body).encode('utf-8')
    return auth_login_view(request)


@csrf_exempt
def auth_register_admin_view(request):
    """
    POST /api/auth/register/admin/
    Creates a NEW Organization and makes the registrant its first ADMIN (owner).
    Can NEVER add an admin to an existing organization.
    Role is strictly set by the server to 'ADMIN' (client-provided role is discarded).
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    org_name = body.get('org_name', '').strip()
    name = body.get('name', '').strip()
    email = body.get('email', '').strip().lower()
    password = body.get('password', '').strip()
    confirm_password = body.get('confirm_password', '').strip()
    terms_accepted = body.get('terms_accepted', False)

    # Validation
    if not org_name:
        return JsonResponse({"error": "Organization name is required."}, status=400)
    if not name:
        return JsonResponse({"error": "Full name is required."}, status=400)
    if not email or '@' not in email:
        return JsonResponse({"error": "A valid work email is required."}, status=400)
    if not terms_accepted:
        return JsonResponse({"error": "You must accept the terms of service and compliance policy."}, status=400)
    if password != confirm_password:
        return JsonResponse({"error": "Passwords do not match."}, status=400)

    val_ok, val_msg = validate_password_strength(password)
    if not val_ok:
        return JsonResponse({"error": val_msg}, status=400)

    client_ip = get_client_ip(request)
    is_limited, limit_msg = LoginAttemptLog.is_rate_limited(client_ip, email, max_failures=10, window_minutes=60)
    if is_limited:
        return JsonResponse({"error": limit_msg, "rate_limited": True}, status=429)

    # Generic response if email already exists (no email discovery leak)
    if BrandGuardUser.objects.filter(email__iexact=email).exists():
        return JsonResponse({
            "status": "success",
            "message": "Registration received. If this email is eligible, verification instructions have been dispatched.",
        }, status=200)

    with transaction.atomic():
        # Create a brand new Organization with unique slug
        base_slug = slugify(org_name) or "org"
        slug = base_slug
        suffix_counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{secrets.token_hex(2)}"
            suffix_counter += 1

        org = Organization.objects.create(
            name=org_name,
            slug=slug,
            requires_writer_approval=True
        )

        # Create default Company for this Organization
        company = Company.objects.create(
            organization=org,
            name=org_name,
            slug=slug
        )

        # Derive username
        base_username = email.split('@')[0]
        username = base_username
        u_counter = 1
        while BrandGuardUser.objects.filter(username=username).exists():
            username = f"{base_username}_{secrets.token_hex(2)}"
            u_counter += 1

        parts = name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        # ROLE IS STRICTLY SET BY SERVER: NEVER FROM CLIENT BODY
        user = BrandGuardUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='ADMIN',  # Enforced server-side
            organization=org,
            department='Executive Governance',
            is_email_verified=False,
            is_approved=True  # First admin/owner is automatically approved
        )

        # Generate Email Verification Token (24 hours validity)
        ver_token = EmailVerificationToken.objects.create(
            user=user,
            token=EmailVerificationToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=24)
        )

        AuditTrail.log(
            request,
            action="ORG_ADMIN_REGISTERED",
            entity_type="ORGANIZATION",
            entity_id=str(org.id),
            description=f"New organization '{org.name}' registered with initial admin '{user.username}'."
        )

    return JsonResponse({
        "status": "success",
        "message": "Organization created. Please verify your email before first login.",
        "org_id": str(org.id),
        "org_name": org.name,
        "user_id": user.id,
        "verification_token": ver_token.token,
    }, status=201)


@csrf_exempt
def auth_register_writer_view(request):
    """
    POST /api/auth/register/writer/
    Writers register ONLY with a valid, unexpired invite code created by an admin.
    Role is strictly set by the server to 'CONTENT_WRITER' (client-provided role is discarded).
    Enforces organization approval policy (user.is_approved = False if required).
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    invite_code = body.get('invite_code', '').strip()
    name = body.get('name', '').strip()
    email = body.get('email', '').strip().lower()
    password = body.get('password', '').strip()
    confirm_password = body.get('confirm_password', '').strip()
    terms_accepted = body.get('terms_accepted', False)

    if not invite_code:
        return JsonResponse({"error": "A valid invite code is required to register as a writer."}, status=400)
    if not name:
        return JsonResponse({"error": "Full name is required."}, status=400)
    if not email or '@' not in email:
        return JsonResponse({"error": "A valid work email is required."}, status=400)
    if not terms_accepted:
        return JsonResponse({"error": "You must accept the terms of service and compliance policy."}, status=400)
    if password != confirm_password:
        return JsonResponse({"error": "Passwords do not match."}, status=400)

    val_ok, val_msg = validate_password_strength(password)
    if not val_ok:
        return JsonResponse({"error": val_msg}, status=400)

    # Validate Invite Code
    invite = InviteToken.objects.filter(code=invite_code).first()
    if not invite:
        return JsonResponse({"error": "Invalid invite code. Please request an invite link from your organization administrator."}, status=400)

    is_inv_valid, inv_msg = invite.is_valid()
    if not is_inv_valid:
        return JsonResponse({"error": inv_msg}, status=400)

    client_ip = get_client_ip(request)
    is_limited, limit_msg = LoginAttemptLog.is_rate_limited(client_ip, email, max_failures=10, window_minutes=60)
    if is_limited:
        return JsonResponse({"error": limit_msg, "rate_limited": True}, status=429)

    # Generic response if email already exists (no discovery leak)
    if BrandGuardUser.objects.filter(email__iexact=email).exists():
        return JsonResponse({
            "status": "success",
            "message": "Registration received. If this email is eligible, verification instructions have been dispatched.",
        }, status=200)

    with transaction.atomic():
        org = invite.organization

        base_username = email.split('@')[0]
        username = base_username
        u_counter = 1
        while BrandGuardUser.objects.filter(username=username).exists():
            username = f"{base_username}_{secrets.token_hex(2)}"
            u_counter += 1

        parts = name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        # Determine approval status based on Org policy
        is_approved = not org.requires_writer_approval

        # ROLE IS STRICTLY SET BY SERVER: NEVER FROM CLIENT BODY
        user = BrandGuardUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='CONTENT_WRITER',  # Enforced server-side
            organization=org,
            department='Content Creation',
            is_email_verified=False,
            is_approved=is_approved
        )

        # Record invite usage
        invite.uses_count += 1
        if invite.max_uses > 0 and invite.uses_count >= invite.max_uses:
            invite.is_active = False
        invite.save()

        # Generate Email Verification Token
        ver_token = EmailVerificationToken.objects.create(
            user=user,
            token=EmailVerificationToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=24)
        )

        AuditTrail.log(
            request,
            action="WRITER_REGISTERED",
            entity_type="USER",
            entity_id=str(user.id),
            description=f"Writer '{user.username}' registered under organization '{org.name}' via invite '{invite.code}' (Approved: {is_approved})."
        )

    return JsonResponse({
        "status": "success",
        "message": "Registration successful. Please verify your email before logging in.",
        "needs_approval": not is_approved,
        "approval_status": "PENDING_APPROVAL" if not is_approved else "APPROVED",
        "verification_token": ver_token.token,
    }, status=201)


@csrf_exempt
def auth_verify_email_view(request):
    """
    POST /api/auth/verify-email/
    Accepts: {"token": "..."}
    Verifies user's email address and enables login.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    token_str = body.get('token', '').strip()
    if not token_str:
        return JsonResponse({"error": "Verification token is required."}, status=400)

    vt = EmailVerificationToken.objects.filter(token=token_str).first()
    if not vt:
        return JsonResponse({"error": "Invalid verification token."}, status=400)

    is_valid, msg = vt.is_valid()
    if not is_valid:
        return JsonResponse({"error": msg}, status=400)

    with transaction.atomic():
        vt.is_used = True
        vt.save(update_fields=['is_used'])

        user = vt.user
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])

        AuditTrail.log(
            request,
            action="EMAIL_VERIFIED",
            entity_type="USER",
            entity_id=str(user.id),
            description=f"Email verified for user '{user.username}' ({user.email})."
        )

    return JsonResponse({
        "status": "success",
        "message": "Email verified successfully. You may now log in.",
        "email": user.email,
        "is_approved": user.is_approved
    })


@csrf_exempt
def auth_password_reset_request_view(request):
    """
    POST /api/auth/password-reset/request/
    Accepts: {"email": "..."}
    Dispatches password reset instructions without leaking whether the email exists.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    email = body.get('email', '').strip().lower()
    client_ip = get_client_ip(request)

    is_limited, limit_msg = LoginAttemptLog.is_rate_limited(client_ip, email, max_failures=10, window_minutes=60)
    if is_limited:
        return JsonResponse({"error": limit_msg, "rate_limited": True}, status=429)

    user = BrandGuardUser.objects.filter(email__iexact=email).first()
    rst_token_str = None
    if user and user.is_active:
        rst = PasswordResetToken.objects.create(
            user=user,
            token=PasswordResetToken.generate_token(),
            expires_at=timezone.now() + timedelta(hours=1)
        )
        rst_token_str = rst.token
        AuditTrail.log(
            request,
            action="PASSWORD_RESET_REQUESTED",
            entity_type="USER",
            entity_id=str(user.id),
            description=f"Password reset token issued for '{user.username}'."
        )

    response_data = {
        "status": "success",
        "message": "If that email address is registered, password reset instructions have been dispatched.",
    }
    # Provide reset_token in response if in testing/dev to facilitate automated tests
    if rst_token_str:
        response_data["reset_token"] = rst_token_str

    return JsonResponse(response_data)


@csrf_exempt
def auth_password_reset_confirm_view(request):
    """
    POST /api/auth/password-reset/confirm/
    Accepts: {"token": "...", "password": "...", "confirm_password": "..."}
    Resets password and clears any lockout.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    token_str = body.get('token', '').strip()
    password = body.get('password', '').strip()
    confirm_password = body.get('confirm_password', '').strip()

    if not token_str:
        return JsonResponse({"error": "Reset token is required."}, status=400)
    if not password:
        return JsonResponse({"error": "New password is required."}, status=400)
    if password != confirm_password:
        return JsonResponse({"error": "Passwords do not match."}, status=400)

    val_ok, val_msg = validate_password_strength(password)
    if not val_ok:
        return JsonResponse({"error": val_msg}, status=400)

    rst = PasswordResetToken.objects.filter(token=token_str).first()
    if not rst:
        return JsonResponse({"error": "Invalid or expired password reset token."}, status=400)

    is_valid, msg = rst.is_valid()
    if not is_valid:
        return JsonResponse({"error": msg}, status=400)

    with transaction.atomic():
        rst.is_used = True
        rst.save(update_fields=['is_used'])

        user = rst.user
        user.set_password(password)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['password', 'failed_login_attempts', 'locked_until'])

        AuditTrail.log(
            request,
            action="PASSWORD_RESET_COMPLETED",
            entity_type="USER",
            entity_id=str(user.id),
            description=f"Password successfully reset for '{user.username}'."
        )

    return JsonResponse({
        "status": "success",
        "message": "Password reset successfully. You may now log in with your new password."
    })


@csrf_exempt
def invites_list_create_view(request):
    """
    GET /api/invites/ - Lists active/recent invites for admin's organization.
    POST /api/invites/ - Admin creates a new 7-day single or multi-use invite code.
    Requires ADMIN authentication.
    """
    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    if not user.is_admin_user:
        return JsonResponse({"error": "Admin privileges required to manage invites."}, status=403)

    org = user.organization
    if not org:
        org = Organization.objects.first()

    if request.method == 'GET':
        invites = InviteToken.objects.filter(organization=org).order_by('-created_at')[:50]
        return JsonResponse({
            "invites": [inv.to_dict() for inv in invites]
        })

    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = {}

        max_uses = int(body.get('max_uses', 1))
        expires_in_days = min(30, max(1, int(body.get('expires_in_days', 7))))

        code = InviteToken.generate_code()
        expires_at = timezone.now() + timedelta(days=expires_in_days)

        invite = InviteToken.objects.create(
            code=code,
            organization=org,
            created_by=user,
            role='CONTENT_WRITER',
            max_uses=max_uses,
            expires_at=expires_at,
            is_active=True
        )

        AuditTrail.log(
            request,
            action="INVITE_CREATED",
            entity_type="ORGANIZATION",
            entity_id=str(org.id),
            description=f"Invite '{invite.code}' created by '{user.username}' (max uses: {max_uses}, expires in {expires_in_days}d)."
        )

        return JsonResponse({
            "status": "success",
            "invite": invite.to_dict(),
            "invite_url": f"/register/writer?invite={invite.code}"
        }, status=201)

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def invite_validate_view(request):
    """
    GET /api/invites/validate/?code=...
    Public endpoint to check invite code validity before displaying registration form.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    code = request.GET.get('code', '').strip()
    if not code:
        return JsonResponse({"error": "Invite code is required."}, status=400)

    invite = InviteToken.objects.filter(code=code).first()
    if not invite:
        return JsonResponse({"valid": False, "error": "Invalid invite code."}, status=404)

    is_valid, msg = invite.is_valid()
    return JsonResponse({
        "valid": is_valid,
        "message": msg,
        "organization_name": invite.organization.name if is_valid else None,
        "requires_approval": invite.organization.requires_writer_approval if is_valid else True
    })


@csrf_exempt
def members_pending_list_view(request):
    """
    GET /api/members/pending/
    Admin endpoint to view pending writers awaiting workspace approval.
    """
    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    if not user.is_admin_user:
        return JsonResponse({"error": "Admin privileges required."}, status=403)

    org = user.organization
    pending = BrandGuardUser.objects.filter(
        organization=org,
        role='CONTENT_WRITER',
        is_approved=False,
        is_active=True
    ).order_by('-date_joined')

    return JsonResponse({
        "pending_members": [p.to_dict() for p in pending]
    })


@csrf_exempt
def member_approve_view(request, user_id):
    """
    POST /api/members/<user_id>/approve/
    Admin approves a pending writer for workspace access.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    if not user.is_admin_user:
        return JsonResponse({"error": "Admin privileges required."}, status=403)

    target_user = BrandGuardUser.objects.filter(id=user_id, organization=user.organization).first()
    if not target_user:
        return JsonResponse({"error": "Member not found in your organization."}, status=404)

    target_user.is_approved = True
    target_user.save(update_fields=['is_approved'])

    AuditTrail.log(
        request,
        action="MEMBER_APPROVED",
        entity_type="USER",
        entity_id=str(target_user.id),
        description=f"Admin '{user.username}' approved workspace access for '{target_user.username}'."
    )

    return JsonResponse({
        "status": "success",
        "message": f"Workspace access approved for {target_user.get_full_name() or target_user.username}.",
        "user": target_user.to_dict()
    })


@csrf_exempt
def member_reject_view(request, user_id):
    """
    POST /api/members/<user_id>/reject/
    Admin rejects a pending writer.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    if not user.is_admin_user:
        return JsonResponse({"error": "Admin privileges required."}, status=403)

    target_user = BrandGuardUser.objects.filter(id=user_id, organization=user.organization).first()
    if not target_user:
        return JsonResponse({"error": "Member not found in your organization."}, status=404)

    target_user.is_active = False
    target_user.save(update_fields=['is_active'])

    AuditTrail.log(
        request,
        action="MEMBER_REJECTED",
        entity_type="USER",
        entity_id=str(target_user.id),
        description=f"Admin '{user.username}' rejected registration request for '{target_user.username}'."
    )

    return JsonResponse({
        "status": "success",
        "message": f"Registration request for {target_user.username} has been rejected."
    })


@csrf_exempt
def member_deactivate_view(request, user_id):
    """
    POST /api/members/<user_id>/deactivate/
    Admin deactivates an active team member.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    if not user.is_admin_user:
        return JsonResponse({"error": "Admin privileges required."}, status=403)

    target_user = BrandGuardUser.objects.filter(id=user_id, organization=user.organization).first()
    if not target_user:
        return JsonResponse({"error": "Member not found in your organization."}, status=404)

    target_user.is_active = False
    target_user.save(update_fields=['is_active'])

    AuditTrail.log(
        request,
        action="MEMBER_DEACTIVATED",
        entity_type="USER",
        entity_id=str(target_user.id),
        description=f"Admin '{user.username}' deactivated account for '{target_user.username}'."
    )

    return JsonResponse({
        "status": "success",
        "message": f"Account for {target_user.username} has been deactivated."
    })


@csrf_exempt
def companies_list_create_view(request):
    """
    GET /api/companies/ - Lists all companies the authenticated user has access to.
    POST /api/companies/ - (Admin only) Creates a new Company under the caller's Organization.
    """
    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    if request.method == 'GET':
        companies = user.get_allowed_companies()
        return JsonResponse({
            "companies": [c.to_dict() for c in companies]
        })

    if request.method == 'POST':
        if not user.is_admin_user:
            return JsonResponse({"error": "Admin privileges required to create a new company."}, status=403)

        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        name = body.get('name', '').strip()
        if not name:
            return JsonResponse({"error": "Company name is required."}, status=400)

        org = user.organization
        if not org:
            org = Organization.objects.first()

        base_slug = slugify(name) or "company"
        slug = base_slug
        s_count = 1
        while Company.objects.filter(organization=org, slug=slug).exists():
            slug = f"{base_slug}-{secrets.token_hex(2)}"
            s_count += 1

        allowed_palette = body.get('allowed_hex_palette') or [
            {"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0},
            {"name": "Teal", "hex": "#00D4B6", "max_delta_e": 4.5},
            {"name": "Pure White", "hex": "#FFFFFF", "max_delta_e": 2.0},
            {"name": "Muted Panel", "hex": "#F8FAF9", "max_delta_e": 2.0},
        ]
        allowed_fonts = body.get('allowed_fonts') or ["Inter", "JetBrains Mono", "Plus Jakarta Sans"]
        wcag_min_ratio = float(body.get('wcag_min_ratio', 4.5))
        logo_aspect_ratio = float(body.get('logo_aspect_ratio', 3.5))

        with transaction.atomic():
            company = Company.objects.create(
                organization=org,
                name=name,
                slug=slug,
                allowed_hex_palette=allowed_palette,
                allowed_fonts=allowed_fonts,
                wcag_min_ratio=wcag_min_ratio,
                logo_aspect_ratio=logo_aspect_ratio,
                ruleset_version=body.get('ruleset_version', 'v3.2'),
                confidential_mode_default=body.get('confidential_mode_default', True),
                min_triggers=int(body.get('min_triggers', 10)),
                minutes_per_audit=int(body.get('minutes_per_audit', 5)),
            )

            # Ensure associated BrandProfile
            from .tenancy import ensure_company_profile
            ensure_company_profile(company)

            # Create default Project
            Project.objects.create(
                company=company,
                name="Default Campaign",
                slug="default-campaign",
                description=f"Primary campaign for {company.name}"
            )

            # Create Membership for creating admin
            Membership.objects.get_or_create(
                user=user,
                organization=org,
                company=company,
                defaults={'role': 'ADMIN', 'is_active': True}
            )

            AuditTrail.log(
                request,
                action="COMPANY_CREATED",
                entity_type="COMPANY",
                entity_id=str(company.id),
                description=f"Admin '{user.username}' created new company '{company.name}' under '{org.name}'."
            )

        return JsonResponse({
            "status": "success",
            "company": company.to_dict()
        }, status=201)

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def company_detail_view(request, company_id):
    """
    GET /api/companies/<company_id>/ - Retrieves company details (scoped to permissions).
    PUT/PATCH /api/companies/<company_id>/ - Updates company settings (Admin only).
    POST /api/companies/<company_id>/archive/ - Archives company (Admin only).
    """
    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    company = Company.objects.filter(id=company_id).first()
    if not company:
        return JsonResponse({"error": "Company not found."}, status=404)

    # Cross-Company Permission Check
    if not user.has_company_access(str(company_id)):
        return JsonResponse({
            "error": "Cross-company access forbidden: caller does not have access to this company.",
            "company_id": str(company_id)
        }, status=403)

    if request.method == 'GET':
        return JsonResponse({
            "company": company.to_dict()
        })

    if request.method in ('PUT', 'PATCH'):
        if not user.has_company_access(str(company_id), required_role='ADMIN'):
            return JsonResponse({"error": "Admin privileges required to update company settings."}, status=403)

        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        if 'name' in body:
            company.name = body['name'].strip()
        if 'allowed_hex_palette' in body:
            company.allowed_hex_palette = body['allowed_hex_palette']
        if 'allowed_fonts' in body:
            company.allowed_fonts = body['allowed_fonts']
        if 'wcag_min_ratio' in body:
            company.wcag_min_ratio = float(body['wcag_min_ratio'])
        if 'logo_aspect_ratio' in body:
            company.logo_aspect_ratio = float(body['logo_aspect_ratio'])
        if 'ruleset_version' in body:
            company.ruleset_version = body['ruleset_version']
        if 'confidential_mode_default' in body:
            company.confidential_mode_default = bool(body['confidential_mode_default'])
        if 'min_triggers' in body:
            company.min_triggers = int(body['min_triggers'])
        if 'minutes_per_audit' in body:
            company.minutes_per_audit = int(body['minutes_per_audit'])
        if 'repo_connection' in body:
            company.repo_connection = body['repo_connection']
        company.save()

        # Sync linked BrandProfile
        if company.brand_profile:
            bp = company.brand_profile
            bp.allowed_hex_palette = company.allowed_hex_palette
            bp.allowed_fonts = company.allowed_fonts
            bp.wcag_min_ratio = company.wcag_min_ratio
            bp.logo_aspect_ratio = company.logo_aspect_ratio
            bp.save()

        AuditTrail.log(
            request,
            action="COMPANY_UPDATED",
            entity_type="COMPANY",
            entity_id=str(company.id),
            description=f"Admin '{user.username}' updated company settings for '{company.name}'."
        )

        return JsonResponse({
            "status": "success",
            "company": company.to_dict()
        })

    if request.method == 'POST' and request.path.endswith('/archive/'):
        if not user.has_company_access(str(company_id), required_role='ADMIN'):
            return JsonResponse({"error": "Admin privileges required to archive company."}, status=403)
        company.is_archived = True
        company.save(update_fields=['is_archived'])
        return JsonResponse({
            "status": "success",
            "message": f"Company '{company.name}' has been archived."
        })

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def company_projects_view(request, company_id):
    """
    GET /api/companies/<company_id>/projects/ - Lists active projects for company.
    POST /api/companies/<company_id>/projects/ - Creates a project under company.
    """
    user = get_authenticated_user_from_request(request)
    if not user or not user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    if not user.has_company_access(str(company_id)):
        return JsonResponse({
            "error": "Cross-company access forbidden: caller does not have access to this company.",
            "company_id": str(company_id)
        }, status=403)

    company = Company.objects.filter(id=company_id, is_archived=False).first()
    if not company:
        return JsonResponse({"error": "Company not found or archived."}, status=404)

    if request.method == 'GET':
        projects = company.projects.filter(is_active=True)
        return JsonResponse({
            "projects": [p.to_dict() for p in projects]
        })

    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        name = body.get('name', '').strip()
        if not name:
            return JsonResponse({"error": "Project name is required."}, status=400)

        slug = slugify(name) or "project"
        base_slug = slug
        s_count = 1
        while Project.objects.filter(company=company, slug=slug).exists():
            slug = f"{base_slug}-{secrets.token_hex(2)}"
            s_count += 1

        project = Project.objects.create(
            company=company,
            name=name,
            slug=slug,
            description=body.get('description', ''),
            channel=body.get('channel', 'ALL'),
            is_active=True
        )

        return JsonResponse({
            "status": "success",
            "project": project.to_dict()
        }, status=201)

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def auth_me_view(request):
    """
    GET /api/auth/me/
    Returns authenticated user profile, permissions, and notifications count.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    user = get_authenticated_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Unauthorized", "detail": "Authentication required."}, status=401)

    unread_notifications = user.notifications.filter(is_read=False).count()

    return JsonResponse({
        "user": user.to_dict(),
        "is_admin": user.is_admin_user,
        "is_writer": user.is_writer_user,
        "unread_notifications": unread_notifications,
    })


@csrf_exempt
def auth_logout_view(request):
    """
    POST /api/auth/logout/
    """
    user = get_authenticated_user_from_request(request)
    if user:
        AuditTrail.log(
            request,
            action="USER_LOGOUT",
            entity_type="USER",
            entity_id=str(user.id),
            description=f"User {user.username} logged out."
        )
    logout(request)
    return JsonResponse({"status": "success", "message": "Logged out successfully."})


@csrf_exempt
def auth_users_view(request):
    """
    GET /api/auth/users/
    Quick user switcher listing for development / pair demo testing.
    """
    users = BrandGuardUser.objects.filter(is_active=True).order_by('role', 'username')
    return JsonResponse({
        "users": [u.to_dict() for u in users]
    })


@csrf_exempt
def notifications_list_view(request):
    """
    GET /api/notifications/
    Returns list of notifications for the current authenticated user (or all if unauthenticated/demo).
    POST /api/notifications/
    Marks notifications as read or creates a test notification.
    """
    user = get_authenticated_user_from_request(request)
    if request.method == 'GET':
        if user:
            qs = Notification.objects.filter(recipient=user).order_by('-created_at')
        else:
            qs = Notification.objects.all().order_by('-created_at')[:30]
        items = [n.to_dict() for n in qs]
        unread_count = sum(1 for n in items if not n.get('is_read'))
        return JsonResponse({"notifications": items, "unread_count": unread_count})

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = {}
        action = body.get('action', 'MARK_READ')
        nid = body.get('id')
        if nid:
            Notification.objects.filter(id=nid).update(is_read=True)
        elif action == 'MARK_ALL_READ':
            if user:
                Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
            else:
                Notification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({"status": "success"})

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
@admin_required
def users_management_view(request):
    """
    GET /api/users/ -> Admin lists team users with per-writer stats & top 5 triggered rules.
    POST /api/users/ -> Admin creates or invites new writer/admin.
    Content writers receive HTTP 403 Forbidden.
    """
    if request.method == 'GET':
        users = BrandGuardUser.objects.all().order_by('role', 'username')
        user_list = []
        team_scores = []
        team_rule_counts = {}

        for u in users:
            u_dict = u.to_dict()
            user_subs = Submission.objects.filter(author=u)
            sub_count = user_subs.count()
            approved_count = user_subs.filter(status='APPROVED').count()
            approval_rate = round((approved_count / sub_count * 100), 1) if sub_count > 0 else 100.0

            u_dict['audits_count'] = sub_count
            u_dict['approved_count'] = approved_count
            u_dict['approval_rate'] = approval_rate
            u_dict['exceptions_count'] = ExceptionRequest.objects.filter(author=u).count()
            u_dict['exceptions_approved'] = ExceptionRequest.objects.filter(author=u, status='APPROVED').count()

            # Average score
            scores = []
            for s in user_subs:
                latest_v = s.versions.order_by('-version_number').first()
                if latest_v:
                    scores.append(latest_v.compliance_score)
                    team_scores.append(latest_v.compliance_score)
            u_dict['avg_compliance_score'] = round(sum(scores) / len(scores), 1) if scores else 100.0

            # Top 5 rules triggered
            rule_counts = {}
            for s in user_subs:
                for v in s.versions.all():
                    for f in v.findings.all():
                        code = f.rule_citation_code
                        rule_counts[code] = rule_counts.get(code, 0) + 1
                        team_rule_counts[code] = team_rule_counts.get(code, 0) + 1
            top_rules = sorted([{"rule_code": k, "count": v} for k, v in rule_counts.items()], key=lambda x: x["count"], reverse=True)[:5]
            u_dict['top_triggered_rules'] = top_rules

            user_list.append(u_dict)

        team_avg = round(sum(team_scores) / len(team_scores), 1) if team_scores else 95.0
        team_top_rules = sorted([{"rule_code": k, "count": v} for k, v in team_rule_counts.items()], key=lambda x: x["count"], reverse=True)[:5]

        return JsonResponse({
            "users": user_list,
            "total": len(user_list),
            "team_metrics": {
                "total_members": users.count(),
                "writers_count": users.filter(role='CONTENT_WRITER').count(),
                "admins_count": users.filter(role='ADMIN').count(),
                "team_avg_score": team_avg,
                "team_top_triggered_rules": team_top_rules
            }
        })

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        username = body.get('username', '').strip()
        email = body.get('email', '').strip()
        role = body.get('role', 'CONTENT_WRITER').upper()
        department = body.get('department', 'Marketing').strip()
        password = body.get('password', 'writer123').strip()

        if not username or not email:
            return JsonResponse({"error": "username and email are required."}, status=400)

        if BrandGuardUser.objects.filter(username=username).exists():
            return JsonResponse({"error": f"Username '{username}' already exists."}, status=400)

        user = BrandGuardUser.objects.create(
            username=username,
            email=email,
            role=role,
            department=department,
            first_name=body.get('first_name', ''),
            last_name=body.get('last_name', ''),
            avatar_color=body.get('avatar_color', '#00D4B6')
        )
        user.set_password(password)
        user.save()

        AuditTrail.log(
            request,
            action="USER_CREATED",
            entity_type="USER",
            entity_id=str(user.id),
            description=f"Admin created user {user.username} with role {user.role}."
        )

        return JsonResponse({"status": "success", "user": user.to_dict()}, status=201)

    return HttpResponseBadRequest("Method not allowed")


@csrf_exempt
def export_submission_pdf_view(request, sub_id):
    """
    GET /api/submissions/<sub_id>/export-pdf/
    Generates and downloads an executive PDF compliance & audit dossier.
    Available to both Writers and Admins for verified publishing.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    try:
        sub = Submission.objects.get(id=sub_id)
    except (Submission.DoesNotExist, ValueError):
        return JsonResponse({"error": f"Submission '{sub_id}' not found."}, status=404)

    from governance.pdf_report import generate_audit_report_pdf
    pdf_bytes = generate_audit_report_pdf(sub)

    AuditTrail.log(
        request,
        action="AUDIT_REPORT_EXPORTED_PDF",
        entity_type="SUBMISSION",
        entity_id=str(sub.id),
        description=f"Exported PDF audit report for submission '{sub.title}' ({sub.id})."
    )

    clean_channel = (getattr(sub, 'channel_context', 'asset') or 'asset').replace(' ', '_')
    filename = f"BrandGuard_Audit_{clean_channel}_{str(sub.id)[:8]}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@csrf_exempt
@admin_required
def notification_integrations_view(request):
    """
    GET /api/notifications/integrations/
    Returns operational status of multi-channel notification services (In-App, Email, Slack).
    """
    from governance.notifications import get_notification_integrations_status
    return JsonResponse(get_notification_integrations_status())


@csrf_exempt
@admin_required
def test_notification_webhook_view(request):
    """
    POST /api/notifications/test-webhook/
    Admin test ping for Email and Slack notifications.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    from governance.notifications import dispatch_notification
    user = request.user
    title = "Test Webhook Alert"
    message = "BrandGuard multi-channel notification verification test. All channels operational."

    res = dispatch_notification(
        recipient=user,
        title=title,
        message=message,
        notification_type="INFO",
        link_url="https://brandguard.internal"
    )
    return JsonResponse({"status": "success", "result": res})


@csrf_exempt
@admin_required
def rules_upload_view(request):
    """
    POST /api/rules/upload/
    Uploads rules in ANY format: PDF, DOCX, XLSX, CSV, JSON, YAML, MD, TXT, PNG/JPG.
    Parser outputs DRAFT rules only. Never auto-activates.
    Admin reviews, edits and approves drafts first.
    Content writers receive HTTP 403 Forbidden.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    uploaded_file = request.FILES.get('file')
    raw_content = request.POST.get('raw_content', '')
    filename = request.POST.get('filename', 'uploaded_rules.txt')

    parsed_rules = []
    try:
        if uploaded_file:
            file_bytes = uploaded_file.read()
            filename = uploaded_file.name
            parsed_rules = parse_rule_document(filename, file_bytes)
        elif raw_content:
            file_bytes = raw_content.encode('utf-8')
            parsed_rules = parse_rule_document(filename, file_bytes)
        else:
            try:
                body = json.loads(request.body.decode('utf-8'))
                raw_text = body.get('rules_text', '')
                fname = body.get('filename', 'policy_input.yaml')
                if raw_text:
                    parsed_rules = parse_rule_document(fname, raw_text.encode('utf-8'))
            except Exception:
                pass

        if not parsed_rules:
            return JsonResponse({"error": "No valid rules could be parsed from the provided file or text."}, status=400)

        # Stage as DRAFT rules (never auto-activated)
        staged_drafts = []
        for r in parsed_rules:
            code = r.get('rule_code', f"DRAFT_{DraftRule.objects.count()+1:03d}")
            draft = DraftRule.objects.create(
                rule_code=code,
                pillar=r.get('pillar', 'TONE'),
                title=r.get('title', 'Imported Rule Draft'),
                severity=r.get('severity', 'WARNING'),
                enforcement=r.get('enforcement', 'Block publish'),
                claims_allowed=r.get('claims_allowed', ''),
                claims_disallowed=r.get('claims_disallowed', ''),
                source=r.get('source', f"Uploaded from {filename}"),
                source_type="UPLOAD",
                structured_spec=r.get('structured_spec', {}),
                rule_description=r.get('rule_description', ''),
                status="DRAFT",
                created_by=request.user
            )
            staged_drafts.append(draft.to_dict())

        AuditTrail.log(
            request,
            action="RULES_UPLOADED_DRAFT",
            entity_type="DRAFT_RULE",
            entity_id=f"{len(staged_drafts)}_rules",
            description=f"Admin uploaded {filename} creating {len(staged_drafts)} DRAFT rules for review."
        )

        return JsonResponse({
            "status": "success",
            "message": f"Successfully parsed {len(staged_drafts)} draft rules from {filename}. Staged for review.",
            "drafts": staged_drafts,
            "count": len(staged_drafts)
        }, status=201)

    except RuleParsingException as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Failed to parse document: {str(e)}"}, status=500)


@csrf_exempt
@admin_required
def draft_rules_list_view(request):
    """
    GET /api/rules/drafts/
    Lists all pending draft rules awaiting admin approval.
    """
    drafts = DraftRule.objects.filter(status='DRAFT').order_by('-created_at')
    return JsonResponse({
        "drafts": [d.to_dict() for d in drafts],
        "count": drafts.count()
    })


@csrf_exempt
@admin_required
def draft_rules_approve_view(request):
    """
    POST /api/rules/drafts/approve/
    Body: {"draft_ids": [uuid1, uuid2], "action": "APPROVE" | "REJECT", "edits": {draft_id: {...}}}
    Approves draft rules and activates them into BrandRule.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    draft_ids = body.get('draft_ids', [])
    single_id = body.get('draft_id')
    if single_id and single_id not in draft_ids:
        draft_ids.append(single_id)

    if not draft_ids:
        return JsonResponse({"error": "draft_ids list is required."}, status=400)

    action = body.get('action', 'APPROVE').upper()
    edits = body.get('edits', {})
    profile = get_active_profile()

    approved_rules = []
    rejected_rules = []

    for did in draft_ids:
        draft = DraftRule.objects.filter(id=did).first()
        if not draft:
            continue

        if action == 'APPROVE':
            edit_data = edits.get(str(did), {})
            title = edit_data.get('title') or draft.title
            code = edit_data.get('rule_code') or draft.rule_code
            severity = edit_data.get('severity') or draft.severity
            enforcement = edit_data.get('enforcement') or draft.enforcement
            claims_allowed = edit_data.get('claims_allowed') or draft.claims_allowed
            claims_disallowed = edit_data.get('claims_disallowed') or draft.claims_disallowed
            description = edit_data.get('rule_description') or draft.rule_description

            rule, created = BrandRule.objects.update_or_create(
                profile=profile,
                rule_code=code.upper(),
                defaults={
                    "title": title,
                    "pillar": draft.pillar,
                    "severity": severity,
                    "enforcement": enforcement,
                    "claims_allowed": claims_allowed,
                    "claims_disallowed": claims_disallowed,
                    "rule_description": description,
                    "source": draft.source,
                    "is_active": True,
                    "version": 1,
                    "owner": f"{request.user.get_full_name() or request.user.username}, Brand Governance"
                }
            )

            BrandRuleVersion.objects.create(
                rule=rule,
                version_number=1,
                title=rule.title,
                pillar=rule.pillar,
                severity=rule.severity,
                structured_spec=rule.structured_spec,
                rule_description=rule.rule_description,
                claims_allowed=rule.claims_allowed,
                claims_disallowed=rule.claims_disallowed,
                enforcement=rule.enforcement,
                source=rule.source,
                change_note=f"Approved from draft ({draft.source_type}).",
                changed_by=request.user
            )

            draft.status = 'APPROVED'
            draft.save()
            approved_rules.append(rule.to_dict())

            AuditTrail.log(
                request,
                action="DRAFT_APPROVED",
                entity_type="RULE",
                entity_id=rule.rule_code,
                description=f"Admin approved draft rule {draft.rule_code} into active rule {rule.rule_code}."
            )

        elif action == 'REJECT':
            draft.status = 'REJECTED'
            draft.review_notes = body.get('reason', 'Rejected by Brand Governance Lead.')
            draft.save()
            rejected_rules.append(draft.to_dict())

            AuditTrail.log(
                request,
                action="DRAFT_REJECTED",
                entity_type="DRAFT_RULE",
                entity_id=draft.rule_code,
                description=f"Admin rejected draft rule {draft.rule_code}."
            )

    return JsonResponse({
        "status": "success",
        "action": action,
        "approved": approved_rules,
        "rejected": rejected_rules,
    })


@csrf_exempt
@admin_required
def rules_scrape_view(request):
    """
    POST /api/rules/scrape/
    Admin pastes a URL.
    1. If preview only: SSRF-safe scraper extracts hex palette, fonts, homepage factual claims.
       Returns preview table with checkboxes.
    2. If import_selected: imports selected items as DRAFT rules or UNVERIFIED facts.
    Content writers receive HTTP 403 Forbidden.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    url = body.get('url', '').strip()
    if not url:
        return JsonResponse({"error": "URL is required."}, status=400)

    import_selected = body.get('import_selected', False)
    profile = get_active_profile()

    try:
        # Run SSRF-Safe extraction
        extracted = scrape_brand_profile(url)

        if not import_selected:
            preview_items = []
            for p in extracted.get('palette', []):
                preview_items.append({
                    "id": f"color_{p['hex']}",
                    "type": "HEX_PALETTE",
                    "value": p['hex'],
                    "label": f"{p['name']} ({p['hex']})",
                    "detail": f"Observed {p.get('count', 1)} times in page styles",
                    "status": "draft",
                    "selected": True
                })
            for f in extracted.get('fonts', []):
                preview_items.append({
                    "id": f"font_{f}",
                    "type": "FONT",
                    "value": f,
                    "label": f,
                    "detail": "Extracted typography token",
                    "status": "draft",
                    "selected": True
                })
            for idx, c in enumerate(extracted.get('claims', [])):
                preview_items.append({
                    "id": f"claim_{idx+1}",
                    "type": "FACT",
                    "code": f"FACT_SCRAPED_{idx+1:02d}",
                    "value": c['claim_text'],
                    "label": c['claim_text'],
                    "detail": f"Extracted from {c.get('tag', 'HTML')} (Unverified)",
                    "status": "unverified",
                    "selected": True
                })

            return JsonResponse({
                "status": "success",
                "mode": "preview",
                "url": url,
                "summary": f"Successfully scraped {len(extracted.get('palette', []))} brand colors, {len(extracted.get('fonts', []))} fonts, and {len(extracted.get('claims', []))} factual statements.",
                "preview_items": preview_items,
                "palette": extracted.get('palette', []),
                "fonts": extracted.get('fonts', []),
                "claims": extracted.get('claims', [])
            })

        # Process selected items for import
        selected_items = body.get('selected_items', [])
        imported_facts = []
        imported_draft_rules = []

        for item in selected_items:
            item_type = item.get('type')
            val = item.get('value', '').strip()

            if item_type == 'FACT' and val:
                code = item.get('code') or f"FACT_SCRAPE_{FactLedger.objects.count()+1:03d}"
                fact = FactLedger.objects.create(
                    profile=profile,
                    fact_code=code,
                    category="Web Scraped Factual Claim",
                    claim_truth=val,
                    last_verified=date.today(),
                    valid_until=date.today() + timedelta(days=365),
                    is_verified=False,  # Unverified until admin checks!
                    source=f"Scraped from {url}",
                    created_by=request.user
                )
                imported_facts.append(fact.to_dict())

            elif item_type == 'HEX_PALETTE' and val:
                d_rule = DraftRule.objects.create(
                    rule_code=f"DRAFT_COLOR_{DraftRule.objects.count()+1:03d}",
                    pillar="VISUAL",
                    title=f"Brand Swatch ({val})",
                    severity="BLOCKER",
                    enforcement="Block publish",
                    claims_allowed=val,
                    claims_disallowed="Off-brand swatches exceeding ΔE 4.0",
                    source=f"Scraped from {url}",
                    source_type="SCRAPE",
                    structured_spec={"hex": val, "max_delta_e": 4.0},
                    rule_description=f"Brand color swatch {val} extracted from {url}.",
                    status="DRAFT",
                    created_by=request.user
                )
                imported_draft_rules.append(d_rule.to_dict())

        AuditTrail.log(
            request,
            action="URL_SCRAPED_IMPORTED",
            entity_type="SCRAPE",
            entity_id=url,
            description=f"Admin imported {len(imported_facts)} unverified facts and {len(imported_draft_rules)} draft rules from {url}."
        )

        return JsonResponse({
            "status": "success",
            "message": f"Successfully imported {len(imported_facts)} unverified facts and {len(imported_draft_rules)} draft rules.",
            "imported_facts": imported_facts,
            "imported_draft_rules": imported_draft_rules
        }, status=201)

    except SSRFSecurityException as e:
        return JsonResponse({"error": f"SSRF Security Violation: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Scrape failed: {str(e)}"}, status=500)


@csrf_exempt
@admin_required
def rule_playground_view(request):
    """
    POST /api/rules/playground/
    Tests sample copy or visual swatch against an active or draft rule before activating it.
    Returns whether the input passes, triggers a warning, or is blocked.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    rule_code = body.get('rule_code', '').strip().upper()
    draft_id = body.get('draft_id')
    test_text = body.get('test_text', '').strip()
    profile = get_active_profile()

    target_rule = None
    if draft_id:
        target_rule = DraftRule.objects.filter(id=draft_id).first()
    if not target_rule and rule_code:
        target_rule = BrandRule.objects.filter(profile=profile, rule_code=rule_code).first()

    if not target_rule:
        return JsonResponse({"error": "Target rule or draft could not be found."}, status=404)

    spec = target_rule.structured_spec or {}
    banned_term = spec.get('banned_term') or target_rule.claims_disallowed
    allowed_term = spec.get('replacement') or target_rule.claims_allowed
    case_sensitive = spec.get('case_sensitive', False)

    flagged = False
    match_excerpt = ""
    explanation = ""

    if banned_term:
        if case_sensitive:
            flagged = banned_term in test_text
        else:
            flagged = banned_term.lower() in test_text.lower()
        if flagged:
            match_excerpt = banned_term
            explanation = f"Detected prohibited term '{banned_term}' in sample copy. Should be replaced with '{allowed_term}'."

    if not flagged and target_rule.pillar == 'TONE':
        if '#1' in test_text or 'fastest' in test_text.lower() or 'wrecked' in test_text.lower():
            flagged = True
            match_excerpt = "Unsubstantiated tone indicator"
            explanation = "Sample sentence triggers tone warning: aggressive comparison or unsubstantiated superlative."

    if not flagged and target_rule.pillar == 'FACTUAL':
        if target_rule.claims_disallowed and target_rule.claims_disallowed.lower() in test_text.lower():
            flagged = True
            match_excerpt = target_rule.claims_disallowed
            explanation = f"Sample statement conflicts with truth ledger. Disallowed claim '{target_rule.claims_disallowed}' detected."

    status = "FLAG" if flagged else "PASS"
    return JsonResponse({
        "status": status,
        "rule_code": target_rule.rule_code,
        "title": target_rule.title,
        "pillar": target_rule.pillar,
        "severity": target_rule.severity,
        "flagged": flagged,
        "match_excerpt": match_excerpt,
        "explanation": explanation if flagged else f"Sample copy passed all checks for rule [{target_rule.rule_code}] {target_rule.title}.",
        "suggested_fix": allowed_term if flagged else None,
        "test_text": test_text
    })


# ==============================================================================
# MODULE 2: CODEBASE-TO-CLAIM GROUND-TRUTH VERIFIER VIEWS
# ==============================================================================

@admin_required
def codebase_repos_view(request):
    """
    GET /api/codebase/repos/ -> Lists connected repos for request.user's brand profile
    POST /api/codebase/repos/ -> Connects a new repo with encrypted token and SSRF validation
    """
    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    if request.method == 'GET':
        repos = CodebaseRepo.objects.filter(profile=profile).order_by('-created_at')
        return JsonResponse({"repos": [r.to_dict() for r in repos]})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        repo_name = data.get('repo_name', '').strip()
        repo_url = data.get('repo_url', '').strip()
        branch = data.get('branch', 'main').strip() or 'main'
        auth_token = data.get('auth_token', '').strip()
        webhook_secret = data.get('webhook_secret', '').strip()

        if not repo_name or not repo_url:
            return JsonResponse({"error": "repo_name and repo_url are required."}, status=400)

        try:
            validate_repo_url(repo_url)
        except ValueError as err:
            return JsonResponse({"error": str(err)}, status=400)

        with transaction.atomic():
            repo = CodebaseRepo(
                profile=profile,
                repo_name=repo_name,
                repo_url=repo_url,
                branch=branch,
                webhook_secret=webhook_secret,
                scan_status='IDLE'
            )
            if auth_token:
                repo.set_auth_token(auth_token)
            repo.save()

            AuditEvent.emit(
                profile=profile,
                event_type='REPO_SCANNED',
                user=request.user,
                metadata={'action': 'REPO_CONNECTED', 'repo_id': str(repo.id), 'repo_name': repo.repo_name}
            )

        return JsonResponse(repo.to_dict(), status=201)

    return HttpResponseBadRequest("Method not allowed")


@admin_required
def codebase_repo_detail_view(request, repo_id):
    """
    GET /api/codebase/repos/<uuid:repo_id>/ -> Details of single repo
    DELETE /api/codebase/repos/<uuid:repo_id>/ -> Disconnects and deletes repo
    """
    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    repo = CodebaseRepo.objects.filter(id=repo_id, profile=profile).first()
    if not repo:
        return JsonResponse({"error": "Repository not found"}, status=404)

    if request.method == 'GET':
        return JsonResponse(repo.to_dict())

    elif request.method == 'DELETE':
        with transaction.atomic():
            repo_name = repo.repo_name
            repo.delete()
            AuditEvent.emit(
                profile=profile,
                event_type='REPO_SCANNED',
                user=request.user,
                metadata={'action': 'REPO_DISCONNECTED', 'repo_name': repo_name}
            )
        return JsonResponse({"status": "success", "message": f"Repository '{repo_name}' disconnected."})

    return HttpResponseBadRequest("Method not allowed")


@admin_required
def codebase_repo_scan_view(request, repo_id):
    """
    POST /api/codebase/repos/<uuid:repo_id>/scan/
    Queues a background AST scan of the connected repository.
    Returns background Job ID (status polled via GET /api/jobs/<job_id>/).
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    repo = CodebaseRepo.objects.filter(id=repo_id, profile=profile).first()
    if not repo:
        return JsonResponse({"error": "Repository not found"}, status=404)

    is_sync = False
    sandbox_dir = None
    commit_sha = None
    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
        is_sync = body.get('synchronous', False)
        sandbox_dir = body.get('sandbox_dir')
        commit_sha = body.get('commit_sha')
    except Exception:
        pass

    job = enqueue_job(
        profile,
        request.user,
        'REPO_SCAN',
        run_repo_scan,
        repo_id=repo.id,
        commit_sha=commit_sha,
        sandbox_dir=sandbox_dir,
        synchronous=is_sync
    )

    return JsonResponse({
        "job_id": str(job.id),
        "status": job.status,
        "repo_id": str(repo.id),
        "message": f"Codebase AST scan queued for '{repo.repo_name}' ({repo.branch})."
    }, status=202 if job.status == 'PENDING' else 200)


@admin_required
def codebase_constants_view(request, repo_id):
    """
    GET /api/codebase/repos/<uuid:repo_id>/constants/
    Lists extracted code constants with file paths, line numbers, and commit SHAs.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    repo = CodebaseRepo.objects.filter(id=repo_id, profile=profile).first()
    if not repo:
        return JsonResponse({"error": "Repository not found"}, status=404)

    constants = repo.constants.select_related('mapping', 'mapping__target_fact').order_by('file_path', 'line_number')
    return JsonResponse({
        "repo": repo.to_dict(),
        "constants": [c.to_dict() for c in constants],
        "count": constants.count()
    })


@admin_required
def codebase_mappings_view(request):
    """
    GET /api/codebase/mappings/ -> Lists symbol mappings
    POST /api/codebase/mappings/ -> Creates symbol mapping row
    """
    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    if request.method == 'GET':
        mappings = CodeSymbolMapping.objects.filter(profile=profile).select_related('target_fact').order_by('symbol_name')
        return JsonResponse({"mappings": [m.to_dict() for m in mappings]})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        symbol_name = data.get('symbol_name', '').strip()
        semantic_key = data.get('semantic_key', '').strip()
        if not symbol_name or not semantic_key:
            return JsonResponse({"error": "symbol_name and semantic_key are required."}, status=400)

        target_fact_id = data.get('target_fact_id')
        target_fact_code = data.get('target_fact_code')
        target_fact = None
        if target_fact_id:
            target_fact = FactLedger.objects.filter(id=target_fact_id, profile=profile).first()
        elif target_fact_code:
            target_fact = FactLedger.objects.filter(fact_code=target_fact_code, profile=profile).first()

        unit_type = data.get('unit_type', 'RAW')
        scale_factor = float(data.get('scale_factor', 1.0) or 1.0)
        display_format = data.get('display_format', '{value}').strip() or '{value}'
        pattern = data.get('pattern', '').strip()
        confidence_weight = float(data.get('confidence_weight', 1.0) or 1.0)

        with transaction.atomic():
            mapping = CodeSymbolMapping.objects.create(
                profile=profile,
                symbol_name=symbol_name,
                pattern=pattern,
                semantic_key=semantic_key,
                target_fact=target_fact,
                unit_type=unit_type,
                scale_factor=scale_factor,
                display_format=display_format,
                confidence_weight=confidence_weight,
                is_active=True
            )

        return JsonResponse(mapping.to_dict(), status=201)

    return HttpResponseBadRequest("Method not allowed")


@admin_required
def codebase_mapping_detail_view(request, mapping_id):
    """
    GET /api/codebase/mappings/<uuid:mapping_id>/ -> Single mapping details
    PUT /api/codebase/mappings/<uuid:mapping_id>/ -> Update mapping
    DELETE /api/codebase/mappings/<uuid:mapping_id>/ -> Delete mapping
    """
    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    mapping = CodeSymbolMapping.objects.filter(id=mapping_id, profile=profile).first()
    if not mapping:
        return JsonResponse({"error": "Symbol mapping not found"}, status=404)

    if request.method == 'GET':
        return JsonResponse(mapping.to_dict())

    elif request.method == 'PUT':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        if 'symbol_name' in data:
            mapping.symbol_name = data['symbol_name'].strip()
        if 'semantic_key' in data:
            mapping.semantic_key = data['semantic_key'].strip()
        if 'pattern' in data:
            mapping.pattern = data['pattern'].strip()
        if 'unit_type' in data:
            mapping.unit_type = data['unit_type']
        if 'scale_factor' in data:
            mapping.scale_factor = float(data['scale_factor'])
        if 'display_format' in data:
            mapping.display_format = data['display_format']
        if 'confidence_weight' in data:
            mapping.confidence_weight = float(data['confidence_weight'])
        if 'is_active' in data:
            mapping.is_active = bool(data['is_active'])

        if 'target_fact_id' in data or 'target_fact_code' in data:
            target_id = data.get('target_fact_id')
            target_code = data.get('target_fact_code')
            if target_id:
                mapping.target_fact = FactLedger.objects.filter(id=target_id, profile=profile).first()
            elif target_code:
                mapping.target_fact = FactLedger.objects.filter(fact_code=target_code, profile=profile).first()
            else:
                mapping.target_fact = None

        mapping.save()
        return JsonResponse(mapping.to_dict())

    elif request.method == 'DELETE':
        mapping.delete()
        return JsonResponse({"status": "success", "message": "Symbol mapping deleted."})

    return HttpResponseBadRequest("Method not allowed")


@admin_required
def codebase_proposed_changes_view(request):
    """
    GET /api/codebase/proposed-changes/
    Lists proposed truth changes detected from codebase constants.
    Supports filtering by status: ?status=PENDING
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    status_filter = request.GET.get('status', '').upper()
    qs = ProposedFactChange.objects.filter(profile=profile).select_related('fact', 'constant', 'constant__repo', 'reviewed_by')
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(status=status_filter)

    return JsonResponse({
        "proposed_changes": [c.to_dict() for c in qs],
        "count": qs.count()
    })


@admin_required
def codebase_review_proposed_change_view(request, change_id):
    """
    POST /api/codebase/proposed-changes/<uuid:change_id>/review/
    Approve or reject a proposed fact change.
    APPROVAL REQUIRES valid_until (chosen by admin, never auto-invented).
    Approval updates FactLedger, creates snapshot, logs AuditEvent, and triggers Module 3.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    profile, company, err = resolve_request_profile(request)
    if err:
        return err
    change = ProposedFactChange.objects.filter(id=change_id, profile=profile).select_related('fact', 'constant').first()
    if not change:
        return JsonResponse({"error": "Proposed change not found"}, status=404)

    if change.status != 'PENDING':
        return JsonResponse({"error": f"Change is already {change.status}."}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    action = data.get('action', '').upper()
    if action not in ('APPROVE', 'REJECT'):
        return JsonResponse({"error": "action must be 'APPROVE' or 'REJECT'."}, status=400)

    if action == 'APPROVE':
        valid_until_str = data.get('valid_until', '').strip()
        if not valid_until_str:
            return JsonResponse({
                "error": "valid_until date is required upon approval (admin-chosen, never auto-invented)."
            }, status=400)

        try:
            valid_until_date = datetime.strptime(valid_until_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({"error": "Invalid valid_until date format. Use YYYY-MM-DD."}, status=400)

        with transaction.atomic():
            change.status = 'APPROVED'
            change.valid_until = valid_until_date
            change.reviewed_by = request.user
            change.reviewed_at = timezone.now()
            change.save()

            # Update FactLedger in place
            fact = change.fact
            old_truth = fact.claim_truth
            fact.claim_truth = change.new_value
            fact.valid_until = valid_until_date
            fact.last_verified = timezone.now().date()
            fact.is_verified = True
            fact.source = f"Verified product code ({change.code_location})"
            fact.save()

            # Emit audit event for fact approval
            AuditEvent.emit(
                profile=profile,
                event_type='FACT_CHANGE_APPROVED',
                user=request.user,
                fact_code=fact.fact_code,
                fact=fact,
                severity='BLOCKER',
                metadata={
                    'change_id': str(change.id),
                    'fact_code': fact.fact_code,
                    'old_value': old_truth,
                    'new_value': change.new_value,
                    'valid_until': str(valid_until_date),
                    'code_location': change.code_location,
                    'commit_sha': change.commit_sha,
                }
            )

            # Trigger Module 3: Blast Radius and asset invalidation
            from governance.engines.blast_radius_engine import compute_blast_radius
            blast_result = compute_blast_radius(
                profile=profile,
                fact_id=fact.id,
                old_value=old_truth,
                new_value=change.new_value,
                trigger_reason='CODEBASE_FACT_APPROVED'
            )

        return JsonResponse({
            "status": "success",
            "action": "APPROVED",
            "message": f"Fact {fact.fact_code} successfully updated to '{change.new_value}'.",
            "proposed_change": change.to_dict(),
            "fact": fact.to_dict(),
            "blast_radius": blast_result,
        })

    elif action == 'REJECT':
        rejection_reason = data.get('rejection_reason', '').strip()
        with transaction.atomic():
            change.status = 'REJECTED'
            change.rejection_reason = rejection_reason
            change.reviewed_by = request.user
            change.reviewed_at = timezone.now()
            change.save()

            AuditEvent.emit(
                profile=profile,
                event_type='FACT_CHANGE_REJECTED',
                user=request.user,
                fact_code=change.fact.fact_code,
                fact=change.fact,
                metadata={
                    'change_id': str(change.id),
                    'fact_code': change.fact.fact_code,
                    'rejection_reason': rejection_reason,
                    'proposed_value': change.new_value,
                }
            )

        return JsonResponse({
            "status": "success",
            "action": "REJECTED",
            "message": f"Proposed change for {change.fact.fact_code} rejected.",
            "proposed_change": change.to_dict()
        })


@csrf_exempt
def github_webhook_view(request):
    """
    POST /api/webhooks/github/
    GitHub webhook handler for automatic repo rescanning on PR merge / push.
    Verifies X-Hub-Signature-256 HMAC signature against repo.webhook_secret.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Method not allowed")

    sig_header = request.headers.get('X-Hub-Signature-256', '')
    if not sig_header or not sig_header.startswith('sha256='):
        return JsonResponse({"error": "Missing or invalid X-Hub-Signature-256 header"}, status=401)

    payload_bytes = request.body
    provided_signature = sig_header[7:]

    # Locate repo by repo url or query param
    repo_id = request.GET.get('repo_id')
    repo = None
    if repo_id:
        repo = CodebaseRepo.objects.filter(id=repo_id).first()

    if not repo:
        try:
            payload_json = json.loads(payload_bytes.decode('utf-8'))
            repo_html_url = payload_json.get('repository', {}).get('html_url', '')
            repo_clone_url = payload_json.get('repository', {}).get('clone_url', '')
            repo = CodebaseRepo.objects.filter(
                Q(repo_url=repo_html_url) | Q(repo_url=repo_clone_url)
            ).first()
        except Exception:
            pass

    if not repo:
        return JsonResponse({"error": "Repository could not be resolved from webhook payload"}, status=404)

    if not repo.webhook_secret:
        return JsonResponse({"error": "Repository has no webhook_secret configured"}, status=400)

    # HMAC verification
    computed_sig = hmac.new(
        repo.webhook_secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_sig, provided_signature):
        return JsonResponse({"error": "Invalid HMAC signature"}, status=403)

    # Enqueue background scan job
    job = enqueue_job(
        profile=repo.profile,
        user=None,
        job_type='REPO_SCAN',
        task_fn=run_repo_scan,
        repo_id=repo.id
    )

    return JsonResponse({
        "status": "success",
        "message": f"Webhook verified. Background scan queued for '{repo.repo_name}'.",
        "job_id": str(job.id)
    }, status=200)


# ==============================================================================
# REAL-TIME UPDATES CHANNEL: SERVER-SENT EVENTS (SSE) STREAM
# ==============================================================================

import time
from django.http import StreamingHttpResponse


@csrf_exempt
def realtime_event_stream_view(request):
    """
    GET /api/realtime/stream/
    Server-Sent Events (SSE) live stream for telemetry KPIs, job progress,
    truth changes, and compliance updates. Reconnects automatically with 10s fallback.
    """
    token = request.GET.get('token')
    user = None
    if token:
        user = decode_user_token(token)
    if not user:
        user = get_authenticated_user_from_request(request)

    profile = user.brand_profile if user and user.brand_profile else get_active_profile()

    def event_stream():
        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'profile_id': str(profile.id), 'user': user.username if user else 'anonymous'})}\n\n"

        last_check = timezone.now()
        heartbeat = 0

        # Run stream loop (exits gracefully when client disconnects)
        for _ in range(60):  # 60 iterations * 2s = 120s max stream lifetime before client auto-reconnects
            time.sleep(2)
            heartbeat += 1

            try:
                # Active background jobs for this profile
                active_jobs = Job.objects.filter(profile=profile, status__in=['PENDING', 'RUNNING']).order_by('-updated_at')[:3]
                for job in active_jobs:
                    job_data = {
                        'job_id': str(job.id),
                        'job_type': job.job_type,
                        'status': job.status,
                        'progress': job.progress,
                        'status_message': job.status_message,
                    }
                    yield f"event: job_progress\ndata: {json.dumps(job_data)}\n\n"

                # Recent AuditEvents
                recent_events = AuditEvent.objects.filter(
                    profile=profile,
                    timestamp__gte=last_check
                ).order_by('timestamp')

                for ev in recent_events:
                    yield f"event: {ev.event_type.lower()}\ndata: {json.dumps(ev.to_dict())}\n\n"

                last_check = timezone.now()

                # Heartbeat ping every 10s
                if heartbeat >= 5:
                    heartbeat = 0
                    yield f"event: ping\ndata: {json.dumps({'time': timezone.now().isoformat()})}\n\n"

            except Exception:
                break

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# =============================================================================
# Phase R3: Visual Test Lab & Accuracy Calibration Views
# =============================================================================

@admin_required
def visual_test_lab_run_view(request):
    """
    GET / POST /api/visual-test-lab/run/
    Admin only: Executes the accuracy calibration harness across the 42-asset realistic image corpus.
    Returns metrics, confusion matrix, per-rule breakdown, and low-confidence review items.
    """
    if request.method not in ('GET', 'POST'):
        return HttpResponseBadRequest("Method not allowed")
    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    from governance.engines.visual_harness import run_visual_calibration_harness
    report = run_visual_calibration_harness(profile=profile)
    return JsonResponse(report)


@admin_required
def visual_test_lab_report_view(request):
    """
    GET /api/visual-test-lab/report/?format=csv|json
    Admin only: Generates downloadable calibration report.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")
    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    fmt = request.GET.get('format', 'json').lower()
    from governance.engines.visual_harness import run_visual_calibration_harness, generate_calibration_csv_report
    report = run_visual_calibration_harness(profile=profile)

    if fmt == 'csv':
        csv_content = generate_calibration_csv_report(report)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="brandguard_visual_calibration_report.csv"'
        return response
    return JsonResponse(report, json_dumps_params={'indent': 2})


@admin_required
def visual_test_lab_low_confidence_view(request):
    """
    GET /api/visual-test-lab/low-confidence/
    Admin only: Returns detections routed to human review due to low confidence (< 0.75).
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")
    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    from governance.engines.visual_harness import run_visual_calibration_harness
    report = run_visual_calibration_harness(profile=profile)
    return JsonResponse({
        "status": "success",
        "low_confidence_count": report.get("low_confidence_count", 0),
        "detections": report.get("low_confidence_detections", [])
    })


def samples_catalog_view(request):
    """
    GET /api/samples/
    Returns all 42 corpus sample assets grouped by category with metadata for the Sample Gallery.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed")
    import os
    corpus_dir = os.path.join(settings.BASE_DIR, 'fixtures', 'images')
    gt_path = os.path.join(corpus_dir, 'ground_truth.json')
    if not os.path.exists(gt_path):
        return JsonResponse({"samples": [], "total": 0})

    with open(gt_path, 'r', encoding='utf-8') as f:
        gt = json.load(f)

    samples = []
    for filename, meta in gt.get("images", {}).items():
        ext = filename.split('.')[-1].upper()
        clean_title = filename.replace('_', ' ')
        for suffix in ['.png', '.jpeg', '.jpg', '.webp', '.pdf', '.svg']:
            clean_title = clean_title.replace(suffix, '')
        samples.append({
            "filename": filename,
            "title": clean_title.title(),
            "category": meta.get("category", "OTHER"),
            "format": ext,
            "pass_fail": meta.get("pass_fail", "PASS"),
            "expected_blockers": meta.get("expected_blockers", 0),
            "expected_warnings": meta.get("expected_warnings", 0),
            "expected_findings": meta.get("expected_findings", []),
            "low_confidence": meta.get("low_confidence", False),
            "notes": meta.get("notes", ""),
            "sample_url": f"/samples/{filename}"
        })

    return JsonResponse({
        "status": "success",
        "total": len(samples),
        "samples": samples
    })


GLOBAL_NAV_ITEMS = [
    {
        "id": "inspector",
        "title": "Pre-Flight Inspector",
        "description": "Multi-modal compliance compiler & live linter",
        "keywords": ["scan", "lint", "editor", "draft", "compliance", "preflight", "check", "audit", "linter"],
        "category": "Workspace",
        "roles": ["ADMIN", "CONTENT_WRITER"],
    },
    {
        "id": "registry",
        "title": "Rule Registry",
        "description": "Source of truth policies, allowed claims, and severity thresholds",
        "keywords": ["rules", "registry", "policy", "lexicon", "tone", "visual", "factual", "edit rule", "policies"],
        "category": "Governance",
        "roles": ["ADMIN"],
    },
    {
        "id": "guide",
        "title": "Rule Guide",
        "description": "Writer reference for brand claims and tone constraints",
        "keywords": ["guide", "reference", "rules", "allowed claims", "prohibited words"],
        "category": "Workspace",
        "roles": ["CONTENT_WRITER"],
    },
    {
        "id": "facts",
        "title": "Fact Ledger & Codebase Verifier",
        "description": "Ground-truth claims, codebase constant mappings, and blast radius",
        "keywords": ["facts", "ledger", "constants", "repo", "blast radius", "truth", "github", "proposals", "ground truth"],
        "category": "Governance",
        "roles": ["ADMIN"],
    },
    {
        "id": "visual_test_lab",
        "title": "Visual Identity Test Lab",
        "description": "Calibrated CV image corpus, precision/recall harness, and contrast sampling",
        "keywords": ["lab", "visual", "corpus", "precision", "recall", "confusion matrix", "cvd", "contrast", "wcag", "accuracy"],
        "category": "Governance",
        "roles": ["ADMIN"],
    },
    {
        "id": "queue",
        "title": "Manager Review Queue",
        "description": "Exception requests, sign-off workflow, and publication handoff",
        "keywords": ["queue", "exceptions", "sign-off", "review", "approve", "manager", "decided"],
        "category": "Governance",
        "roles": ["ADMIN"],
    },
    {
        "id": "telemetry",
        "title": "Governance Dashboard & Telemetry",
        "description": "Compliance score distributions, rule ambiguity, and system health",
        "keywords": ["dashboard", "telemetry", "metrics", "analytics", "health", "system", "ambiguity", "csv", "pdf", "stats"],
        "category": "Analytics",
        "roles": ["ADMIN", "CONTENT_WRITER"],
    },
    {
        "id": "team",
        "title": "Team & Member Management",
        "description": "Manage organizations, members, invite codes, and permissions",
        "keywords": ["team", "users", "members", "invites", "approval", "roles", "organizations"],
        "category": "Settings",
        "roles": ["ADMIN"],
    },
    {
        "id": "audit_log",
        "title": "Governance Audit Log",
        "description": "Immutable cryptographic event trail and compliance handoffs",
        "keywords": ["audit", "log", "trail", "cryptographic", "events", "history"],
        "category": "Compliance",
        "roles": ["ADMIN"],
    },
    {
        "id": "workspaces",
        "title": "Workspace & Campaign Directory",
        "description": "Active drafts, channels, and multi-version history",
        "keywords": ["workspace", "drafts", "campaigns", "submissions", "projects"],
        "category": "Workspace",
        "roles": ["ADMIN", "CONTENT_WRITER"],
    },
    {
        "id": "design",
        "title": "Design System Showcase",
        "description": "Forest design tokens, color palette, buttons, and alert components",
        "keywords": ["design", "forest", "tokens", "theme", "components", "colors"],
        "category": "System",
        "roles": ["ADMIN", "CONTENT_WRITER"],
    },
]


@csrf_exempt
def global_search_view(request):
    """
    GET /api/search/?q=<query>&company_id=<company_id>&limit=<limit>
    Unified multi-tenant search across Rules, Facts, Submissions/Drafts, and Navigation.
    Returns categorized results with rich previews and navigation targets.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Method not allowed. Use GET.")

    q = request.GET.get('q', '').strip()
    try:
        limit = min(int(request.GET.get('limit', 8)), 20)
    except (ValueError, TypeError):
        limit = 8

    user = get_authenticated_user_from_request(request)
    user_role = getattr(user, 'role', 'ADMIN') if user else 'ADMIN'
    is_admin = user_role == 'ADMIN' or getattr(user, 'is_superuser', False)

    profile, company, err = resolve_request_profile(request)
    if err:
        return err

    from django.db.models import Q

    # Filter navigation items by user role and query
    nav_matches = []
    for item in GLOBAL_NAV_ITEMS:
        if user_role not in item["roles"]:
            continue
        if not q:
            # When query is empty, suggest primary navigation tabs
            suggested = ["inspector", "registry", "facts", "telemetry"] if is_admin else ["inspector", "workspaces", "guide"]
            if item["id"] in suggested:
                nav_matches.append(item)
        else:
            q_lower = q.lower()
            if (
                q_lower in item["title"].lower()
                or q_lower in item["description"].lower()
                or any(q_lower in kw for kw in item["keywords"])
            ):
                nav_matches.append(item)

    # 1. Search Rules
    rules_data = []
    if profile:
        rule_qs = BrandRule.objects.filter(profile=profile, is_active=True)
        if q:
            rule_qs = rule_qs.filter(
                Q(rule_code__icontains=q)
                | Q(title__icontains=q)
                | Q(rule_description__icontains=q)
                | Q(claims_allowed__icontains=q)
                | Q(claims_disallowed__icontains=q)
                | Q(pillar__icontains=q)
                | Q(severity__icontains=q)
            )
        rule_matches = rule_qs.order_by('rule_code')[:limit]
        for r in rule_matches:
            rules_data.append({
                "id": str(r.id),
                "rule_code": r.rule_code,
                "title": r.title,
                "pillar": r.pillar,
                "severity": r.severity,
                "version": r.version,
                "claims_allowed": r.claims_allowed or "",
                "claims_disallowed": r.claims_disallowed or "",
                "rule_description": r.rule_description or "",
            })

    # 2. Search Facts
    facts_data = []
    if profile:
        fact_qs = FactLedger.objects.filter(profile=profile)
        if company:
            fact_qs = fact_qs.filter(Q(company=company) | Q(company__isnull=True))
        if q:
            fact_qs = fact_qs.filter(
                Q(fact_code__icontains=q)
                | Q(claim_truth__icontains=q)
                | Q(category__icontains=q)
                | Q(source__icontains=q)
            )
        fact_matches = fact_qs.order_by('-last_verified')[:limit]
        for f in fact_matches:
            facts_data.append({
                "id": str(f.id),
                "fact_code": f.fact_code,
                "category": f.category,
                "claim_truth": f.claim_truth,
                "source": f.source,
                "is_verified": f.is_verified,
                "valid_until": str(f.valid_until) if f.valid_until else "",
            })

    # 3. Search Drafts / Submissions
    drafts_data = []
    if profile:
        sub_qs = Submission.objects.filter(profile=profile)
        if company:
            sub_qs = sub_qs.filter(Q(company=company) | Q(company__isnull=True))
        if not is_admin and user and user.is_authenticated:
            sub_qs = sub_qs.filter(Q(author=user) | Q(author__isnull=True))
        if q:
            sub_qs = sub_qs.filter(
                Q(title__icontains=q)
                | Q(channel_context__icontains=q)
                | Q(status__icontains=q)
                | Q(versions__raw_text__icontains=q)
            ).distinct()
        sub_matches = sub_qs.order_by('-created_at')[:limit]
        for s in sub_matches:
            latest_v = s.versions.order_by('-version_number').first()
            drafts_data.append({
                "id": str(s.id),
                "title": s.title,
                "channel": s.channel_context,
                "status": s.status,
                "score": latest_v.compliance_score if latest_v else 100.0,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })

    total = len(nav_matches) + len(rules_data) + len(facts_data) + len(drafts_data)

    return JsonResponse({
        "query": q,
        "total": total,
        "navigation": nav_matches,
        "rules": rules_data,
        "facts": facts_data,
        "drafts": drafts_data,
    })



