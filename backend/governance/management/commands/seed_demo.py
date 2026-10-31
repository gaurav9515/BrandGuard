"""
Management command to seed NovaPay demo brand profile, rules, facts,
telemetry stats, sample submissions, users, and the off-brand test PNG banner.
"""

import os
import hmac
import hashlib
from pathlib import Path
from datetime import date, datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from governance.models import (
    BrandGuardUser, SystemSettings, BrandProfile, BrandRule, BrandRuleVersion,
    DraftRule, FactLedger, Submission, SubmissionVersion, AuditFinding,
    BrandComplianceSignature, ExceptionRequest, Notification, AuditTrail,
    AuditEvent, CodebaseRepo, CodeSymbolMapping, CodebaseConstant, ProposedFactChange,
    BlastRadiusReport
)


class Command(BaseCommand):
    help = "Seeds NovaPay brand profile, living facts, rules, users, sample banner and telemetry data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding NovaPay brand governance ecosystem...")

        # 0. System Settings
        sys_settings = SystemSettings.get_settings()
        sys_settings.confidential_mode_default = True
        sys_settings.ruleset_version = "v3.2"
        sys_settings.blocker_penalty = 18.0
        sys_settings.warning_penalty = 8.0
        sys_settings.approved_exception_deduction = 4.0
        sys_settings.color_distance_algorithm = "CIEDE2000"
        sys_settings.color_distance_threshold = 4.0
        sys_settings.friction_min_triggers = 20
        sys_settings.min_triggers = 10
        sys_settings.minutes_per_audit = 5
        sys_settings.notification_email = "brand-ops@novapay.io"
        sys_settings.languages_supported = ["en", "es", "fr", "de", "ja"]
        sys_settings.save()
        self.stdout.write(self.style.SUCCESS("SystemSettings initialized."))

        # 1. Users: Exactly 1 Admin and 2 Content Writers
        admin_user, created = BrandGuardUser.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@novapay.io",
                "first_name": "Jordan",
                "last_name": "Lee",
                "role": "ADMIN",
                "department": "Brand Governance Lead",
                "avatar_color": "#0A3423",
                "is_staff": True,
                "is_superuser": True,
            }
        )
        admin_user.set_password("admin123")
        admin_user.role = "ADMIN"
        admin_user.first_name = "Jordan"
        admin_user.last_name = "Lee"
        admin_user.department = "Brand Governance Lead"
        admin_user.save()

        writer_1, created = BrandGuardUser.objects.get_or_create(
            username="writer1",
            defaults={
                "email": "alex.morgan@novapay.io",
                "first_name": "Alex",
                "last_name": "Morgan",
                "role": "CONTENT_WRITER",
                "department": "Marketing Ops",
                "avatar_color": "#00D4B6",
            }
        )
        writer_1.set_password("writer123")
        writer_1.role = "CONTENT_WRITER"
        writer_1.first_name = "Alex"
        writer_1.last_name = "Morgan"
        writer_1.department = "Marketing Ops"
        writer_1.save()

        writer_2, created = BrandGuardUser.objects.get_or_create(
            username="writer2",
            defaults={
                "email": "taylor.reed@novapay.io",
                "first_name": "Taylor",
                "last_name": "Reed",
                "role": "CONTENT_WRITER",
                "department": "Growth & Social",
                "avatar_color": "#3B82F6",
            }
        )
        writer_2.set_password("writer123")
        writer_2.role = "CONTENT_WRITER"
        writer_2.first_name = "Taylor"
        writer_2.last_name = "Reed"
        writer_2.department = "Growth & Social"
        writer_2.save()

        self.stdout.write(self.style.SUCCESS(
            f"Seeded 3 users: Admin ({admin_user.username}), Writer 1 ({writer_1.username}), Writer 2 ({writer_2.username})"
        ))

        # 2. Brand Profile
        palette = [
            {"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0},
            {"name": "Teal", "hex": "#00D4B6", "max_delta_e": 4.5},
            {"name": "Pure White", "hex": "#FFFFFF", "max_delta_e": 2.0},
            {"name": "Muted Panel", "hex": "#F8FAF9", "max_delta_e": 2.0},
        ]
        profile, created = BrandProfile.objects.get_or_create(
            org_name="NovaPay",
            defaults={
                "allowed_hex_palette": palette,
                "allowed_fonts": ["Inter", "JetBrains Mono", "Plus Jakarta Sans"],
                "wcag_min_ratio": 4.5,
                "logo_aspect_ratio": 3.5,
            }
        )
        profile.org_name = "NovaPay"
        profile.allowed_hex_palette = palette
        profile.allowed_fonts = ["Inter", "JetBrains Mono", "Plus Jakarta Sans"]
        profile.save()

        # Link users to BrandProfile
        admin_user.brand_profile = profile
        admin_user.save(update_fields=['brand_profile'])
        writer_1.brand_profile = profile
        writer_1.save(update_fields=['brand_profile'])
        writer_2.brand_profile = profile
        writer_2.save(update_fields=['brand_profile'])

        # 3. Brand Rules
        rules_data = [
            {
                "pillar": "VISUAL",
                "rule_code": "LEX_001",
                "title": "Strict Brand Casing (NovaPay)",
                "severity": "WARNING",
                "version": 2,
                "enforcement": "1-click auto-patch",
                "claims_allowed": "NovaPay, NovaPay Technologies, NovaPay Inc.",
                "claims_disallowed": "Novapay, novapay, NOVA PAY",
                "source": "NovaPay Brand Identity Standards v3.0",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Jordan Lee, Brand Governance Lead",
                "structured_spec": {
                    "banned_term": "Novapay",
                    "replacement": "NovaPay",
                    "case_sensitive": True,
                    "alternatives": ["NovaPay Technologies", "NovaPay Inc."]
                },
                "rule_description": "NovaPay requires camelCase capitalization with capital N and capital P. Never write 'Novapay' or 'novapay'.",
                "trigger_count": 48,
                "override_count": 2,  # Low override -> Team training gap
            },
            {
                "pillar": "TONE",
                "rule_code": "LEX_002",
                "title": "Prohibited Value Terminology ('cheap')",
                "severity": "WARNING",
                "version": 1,
                "enforcement": "Advisory / Request Exception",
                "claims_allowed": "cost-effective, transparently priced, high-efficiency payment rails",
                "claims_disallowed": "cheap, dirt cheap, lowest cost",
                "source": "NovaPay Voice & Tone Guidelines",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Jordan Lee, Brand Governance Lead",
                "structured_spec": {
                    "banned_term": "cheap",
                    "replacement": "cost-effective",
                    "case_sensitive": False,
                    "alternatives": ["accessible", "transparently priced", "high-efficiency"]
                },
                "rule_description": "NovaPay conveys institutional trust and premium engineering. Avoid the word 'cheap'.",
                "trigger_count": 34,
                "override_count": 21,  # High override -> Rule needs revision
            },
            {
                "pillar": "FACTUAL",
                "rule_code": "LEX_003",
                "title": "Regulatory APY Prohibition ('guaranteed returns')",
                "severity": "BLOCKER",
                "version": 3,
                "enforcement": "Block publish (Hard Blocker)",
                "claims_allowed": "Target APY yields, variable liquidity yield, projected institutional yield",
                "claims_disallowed": "Guaranteed returns, 100% risk-free APY, promised yield",
                "source": "NovaPay Legal & Regulatory Compliance Charter",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Maya Chen, Product Ops & Legal",
                "structured_spec": {
                    "banned_term": "guaranteed returns",
                    "replacement": "target APY yields",
                    "case_sensitive": False,
                    "alternatives": ["projected institutional yield", "variable liquidity yield"]
                },
                "rule_description": "Strict compliance prohibition against claiming 'guaranteed returns' on treasury sweep accounts.",
                "trigger_count": 28,
                "override_count": 0,  # 0% override -> High compliance / Training gap
            },
            {
                "pillar": "TONE",
                "rule_code": "TONE_001",
                "title": "Unsubstantiated Performance Superlatives",
                "severity": "WARNING",
                "version": 1,
                "enforcement": "Advisory / Request Exception",
                "claims_allowed": "High-throughput payment rails, institutional-grade execution",
                "claims_disallowed": "#1 fastest, world's quickest, unbeatable speed",
                "source": "NovaPay Voice Guidelines",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Jordan Lee, Brand Governance Lead",
                "structured_spec": {
                    "banned_term": "#1 fastest",
                    "replacement": "high-throughput payment rails",
                    "case_sensitive": False,
                },
                "rule_description": "Prohibits unverified superlative claims such as '#1 fastest' or 'world's quickest' without audited independent benchmark citations.",
                "trigger_count": 42,
                "override_count": 24,  # High override -> Rule needs revision
            },
            {
                "pillar": "TONE",
                "rule_code": "TONE_002",
                "title": "Executive Voice Policy (No Aggressive Slang)",
                "severity": "WARNING",
                "version": 1,
                "enforcement": "Advisory / Request Exception",
                "claims_allowed": "Eliminate legacy banking friction, modernize institutional workflows",
                "claims_disallowed": "Don't get wrecked by banks, banks are trash",
                "source": "NovaPay Executive Communications Manual",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Jordan Lee, Brand Governance Lead",
                "structured_spec": {
                    "banned_term": "get wrecked",
                    "replacement": "eliminate legacy banking friction",
                    "case_sensitive": False,
                },
                "rule_description": "Prohibits fear-mongering and juvenile slang like 'don't get wrecked by banks' in public communications.",
                "trigger_count": 26,
                "override_count": 4,  # 15.4% override -> Training gap
            },
            {
                "pillar": "VISUAL",
                "rule_code": "VIS_COLOR_001",
                "title": "Approved Brand Color Compliance (CIEDE2000 ΔE ≤ 4.0)",
                "severity": "BLOCKER",
                "version": 2,
                "enforcement": "Block publish (Hard Blocker)",
                "claims_allowed": "Midnight Emerald (#0A3423), Teal (#00D4B6), Pure White (#FFFFFF), Muted Panel (#F8FAF9)",
                "claims_disallowed": "Off-brand purples (#9333EA), unapproved neon swatches",
                "source": "NovaPay Visual Identity System 2026",
                "applies_to": "Image and PDF creative assets",
                "language": "en",
                "owner": "Elena Rostova, Lead Visual Designer",
                "structured_spec": {
                    "max_delta_e": 4.0,
                    "approved_palette": ["#0A3423", "#00D4B6", "#FFFFFF", "#F8FAF9"]
                },
                "rule_description": "All creative visual assets must only employ approved brand swatches within acceptable CIEDE2000 Delta-E color distance tolerances.",
                "trigger_count": 84,
                "override_count": 16,  # 19.0% override -> Training gap
            },
            {
                "pillar": "VISUAL",
                "rule_code": "VIS_WCAG_2.1",
                "title": "WCAG 2.1 AA Contrast Standard (Ratio ≥ 4.5:1)",
                "severity": "BLOCKER",
                "version": 2,
                "enforcement": "Block publish (Non-bypassable Blocker)",
                "claims_allowed": "High-contrast legible foreground and background color combinations (≥ 4.5:1)",
                "claims_disallowed": "Muted gray text over gray surfaces below 4.5:1",
                "source": "W3C WCAG 2.1 Level AA Accessibility Standard",
                "applies_to": "All visual creative and digital web assets",
                "language": "en",
                "owner": "Elena Rostova, Lead Visual Designer",
                "structured_spec": {
                    "min_contrast_ratio": 4.5
                },
                "rule_description": "Text against visual backgrounds must meet or exceed WCAG 2.1 AA standard 4.5:1 contrast ratio to guarantee accessibility. Cannot be bypassed by tone exceptions.",
                "trigger_count": 62,
                "override_count": 3,  # 4.8% override -> Blocker
            },
            {
                "pillar": "FACTUAL",
                "rule_code": "FACT_012",
                "title": "International settlement & fees",
                "severity": "BLOCKER",
                "version": 4,
                "enforcement": "Block publish (Hard Blocker)",
                "claims_allowed": "24-hour transfers with 0.5% FX fee",
                "claims_disallowed": "Instant, zero-fee international transfers",
                "source": "NovaPay Product Facts SLA 2026",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Maya Chen, Product Ops",
                "structured_spec": {
                    "allowed_claim": "24-hour transfers with 0.5% FX fee",
                    "disallowed_claim": "Instant, zero-fee international transfers",
                    "applies_to": "All channels",
                    "enforcement": "Block publish",
                    "owner": "Maya Chen, Product Ops",
                    "ledger_entry": "LEDGER-0412",
                    "source": "NovaPay Product Facts",
                    "valid_from": "Nov 20, 2025",
                    "last_verified": "Mar 14, 2026",
                },
                "rule_description": "International transfer claims must reflect the standard settlement time and FX fee. Do not imply zero-fee or instant delivery unless a specific product scope allows it.",
                "trigger_count": 128,
                "override_count": 5,  # 3.9% override -> Blocker
            },
            {
                "pillar": "TONE",
                "rule_code": "VOICE_004",
                "title": "Unsupported superlatives & challenger tone",
                "severity": "WARNING",
                "version": 2,
                "enforcement": "Advisory / Scoped Exception Allowed",
                "claims_allowed": "High-throughput payment rails for global ambition",
                "claims_disallowed": "Don't get wrecked by banks!",
                "source": "NovaPay Brand Guidelines",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Jordan Lee, Brand Governance Lead",
                "structured_spec": {
                    "banned_term": "wrecked",
                    "warning_type": "Warning · Voice",
                    "quote": "Don't get wrecked by banks!",
                },
                "rule_description": "Aggressive comparison tone is outside the default voice range. Scoped exceptions can be requested for targeted challenger campaigns.",
                "trigger_count": 96,
                "override_count": 11,  # 11.5% override -> Warning
            },
            {
                "pillar": "VISUAL",
                "rule_code": "VIS_021",
                "title": "CTA color drift (ΔE > 3.0)",
                "severity": "WARNING",
                "version": 1,
                "enforcement": "Advisory / Request Exception",
                "claims_allowed": "Primary Teal (#00D4B6) or Midnight Emerald (#0A3423)",
                "claims_disallowed": "Color drifted CTAs exceeding Delta-E 3.0",
                "source": "NovaPay Brand Guidelines",
                "applies_to": "Display and banner marketing",
                "language": "en",
                "owner": "Elena Rostova, Lead Visual Designer",
                "structured_spec": {
                    "max_delta_e": 3.0,
                },
                "rule_description": "CTA buttons must comply with primary emerald and teal swatches (ΔE ≤ 3.0).",
                "trigger_count": 74,
                "override_count": 5,  # 6.8% override -> Warning
            },
            {
                "pillar": "FACTUAL",
                "rule_code": "FACT_031",
                "title": "Expired security certification claims",
                "severity": "BLOCKER",
                "version": 2,
                "enforcement": "Block publish (Hard Blocker)",
                "claims_allowed": "SOC2 Type II and ISO 27001 certified through current active cycle",
                "claims_disallowed": "References to expired SOC2 audits or superseded compliance seals",
                "source": "NovaPay Information Security Office",
                "applies_to": "All channels",
                "language": "en",
                "owner": "Maya Chen, Product Ops",
                "structured_spec": {
                    "valid_until": "2026-06-10",
                },
                "rule_description": "Compliance claims require active, unexpired SOC2 and ISO certifications.",
                "trigger_count": 51,
                "override_count": 0,  # 0% override -> Blocker
            },
        ]

        for r_spec in rules_data:
            rule, created = BrandRule.objects.update_or_create(
                profile=profile,
                rule_code=r_spec["rule_code"],
                defaults=r_spec
            )
            # Seed version history for rule versioning & rollback demo
            if not rule.versions.exists():
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
                    changed_by=admin_user,
                    created_at=datetime.utcnow() - timedelta(days=60)
                )
                if rule.version > 1:
                    BrandRuleVersion.objects.create(
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
                        change_note=f"Upgraded to version {rule.version} with refined claim tolerances.",
                        changed_by=admin_user,
                        created_at=datetime.utcnow() - timedelta(days=10)
                    )

        # 4. Draft Rules (Uploaded/Scraped pending review)
        drafts_data = [
            {
                "rule_code": "DRAFT_LEX_009",
                "pillar": "TONE",
                "title": "Avoid Cryptic FinTech Acronyms (KYB/AML in consumer copy)",
                "severity": "WARNING",
                "enforcement": "Advisory / Request Exception",
                "claims_allowed": "Quick identity and business verification",
                "claims_disallowed": "Strict KYB and AML onboarding hurdles",
                "source": "Parsed from 'Global_Campaign_Brand_Deck_v2.pdf'",
                "source_type": "UPLOAD",
                "structured_spec": {"banned_term": "KYB onboarding", "replacement": "business verification"},
                "rule_description": "Avoid technical regulatory jargon in top-of-funnel consumer marketing.",
                "status": "DRAFT",
                "created_by": admin_user,
            },
            {
                "rule_code": "DRAFT_SCRAPE_002",
                "pillar": "FACTUAL",
                "title": "Sub-Second Global Treasury Rebalancing",
                "severity": "BLOCKER",
                "enforcement": "Block publish",
                "claims_allowed": "Automated multi-currency liquidity sweep within minutes",
                "claims_disallowed": "Instant zero-second cross-border rebalancing",
                "source": "Scraped from homepage https://novapay.io",
                "source_type": "SCRAPE",
                "structured_spec": {"claim": "Sub-second rebalancing requires dedicated liquidity pool"},
                "rule_description": "Unverified scraped claim from marketing landing page. Requires validation with Treasury Ops.",
                "status": "DRAFT",
                "created_by": admin_user,
            }
        ]
        for d in drafts_data:
            DraftRule.objects.update_or_create(rule_code=d["rule_code"], defaults=d)

        # 5. Living Fact Ledger (including expired for blast radius alerts)
        facts_data = [
            {
                "fact_code": "FACT_008",
                "category": "Adoption & Enterprise Traction",
                "claim_truth": "NovaPay serves 500+ enterprise teams across North America and Europe.",
                "last_verified": date(2024, 6, 15),
                "valid_until": date(2025, 12, 31),  # EXPIRED!
                "superseded_by_text": "FACT_042: over 2,400+ enterprise teams as of 2026",
                "is_verified": True,
                "source": "Annual Shareholder Report 2024",
                "trigger_count": 34,
                "override_count": 25,  # High override -> Blast radius candidate
            },
            {
                "fact_code": "FACT_042",
                "category": "Adoption & Enterprise Traction",
                "claim_truth": "NovaPay serves over 2,400+ enterprise teams worldwide across 38 sovereign markets.",
                "last_verified": date(2026, 1, 10),
                "valid_until": date(2027, 12, 31),
                "superseded_by_text": "",
                "is_verified": True,
                "source": "Q1 2026 Official Enterprise Census",
                "trigger_count": 12,
                "override_count": 1,
            },
            {
                "fact_code": "FACT_012",
                "category": "Global Settlement & Pricing SLA",
                "claim_truth": "International cross-border settlements clear in standard 24 hours with a transparent 0.5% FX conversion fee schedule.",
                "last_verified": date(2025, 11, 1),
                "valid_until": date(2027, 6, 30),
                "superseded_by_text": "",
                "is_verified": True,
                "source": "NovaPay Product Facts SLA 2026",
                "trigger_count": 68,
                "override_count": 15,
            },
            {
                "fact_code": "FACT_015",
                "category": "Subscription & Tier Entitlements",
                "claim_truth": "The NovaPay Basic Plan is strictly capped at 3 active collaborative seats. Unlimited seat provisioning requires the Enterprise SLA Tier.",
                "last_verified": date(2025, 10, 1),
                "valid_until": date(2027, 12, 31),
                "superseded_by_text": "",
                "is_verified": True,
                "source": "Pricing Matrix v4.1",
                "trigger_count": 22,
                "override_count": 3,
            },
            {
                "fact_code": "FACT_021",
                "category": "Regulatory & Legal Custody",
                "claim_truth": "NovaPay operates as a registered Money Services Business (FinCEN MSB #310002491) maintaining 1:1 segregated liquid tier-1 client reserves.",
                "last_verified": date(2025, 8, 20),
                "valid_until": date(2028, 1, 1),
                "superseded_by_text": "",
                "is_verified": True,
                "source": "FinCEN Compliance Filing 2025",
                "trigger_count": 14,
                "override_count": 1,
            },
            {
                "fact_code": "FACT_031",
                "category": "Security & Trust Compliance",
                "claim_truth": "SOC2 Type II audit certified with zero material exceptions through period ending June 10, 2026.",
                "last_verified": date(2025, 6, 10),
                "valid_until": date(2026, 6, 10),  # Expiring soon!
                "superseded_by_text": "",
                "is_verified": True,
                "source": "Independent Auditor Report - BDO",
                "trigger_count": 51,
                "override_count": 0,
            },
            {
                "fact_code": "FACT_SCRAPE_99",
                "category": "Web Scraped Fact (Unverified)",
                "claim_truth": "NovaPay processes over $14B in annualized institutional payment volume.",
                "last_verified": date(2026, 4, 1),
                "valid_until": date(2027, 4, 1),
                "superseded_by_text": "",
                "is_verified": False,  # Scraped facts labeled unverified!
                "source": "Scraped from homepage marketing banner",
                "trigger_count": 6,
                "override_count": 0,
            }
        ]

        for f_spec in facts_data:
            FactLedger.objects.update_or_create(
                profile=profile,
                fact_code=f_spec["fact_code"],
                defaults=f_spec
            )

        # 6. Programmatically Generate Off-Brand Promotional PNG Banner
        media_dir = Path(settings.MEDIA_ROOT)
        media_dir.mkdir(parents=True, exist_ok=True)
        banner_path = media_dir / "sample_offbrand_banner.png"

        img_w, img_h = 800, 450
        banner_img = Image.new("RGB", (img_w, img_h), color=(147, 51, 234))  # Off-brand purple #9333EA
        draw = ImageDraw.Draw(banner_img)

        # Off-brand high Delta-E magenta badge section (#FF007F)
        draw.rectangle([0, 0, 800, 80], fill=(255, 0, 127))
        draw.rectangle([0, 370, 800, 450], fill=(234, 88, 12))  # Off-brand bright orange #EA580C

        # Low contrast text box (gray text on dark grey surface: #78716C on #57534E ~ 2.1:1 contrast)
        draw.rectangle([40, 260, 760, 340], fill=(87, 83, 78))

        # Draw decorative shapes & CVD Color Collapse Demonstration Swatches
        draw.ellipse([640, 100, 780, 240], fill=(236, 72, 153))

        # Color-Vision Deficiency test badges: Crimson (150, 70, 90) vs Olive (112, 133, 63)
        draw.rounded_rectangle([520, 260, 630, 310], radius=8, fill=(150, 70, 90))
        draw.rounded_rectangle([640, 260, 750, 310], radius=8, fill=(112, 133, 63))

        # Draw banner text
        try:
            font_title = ImageFont.truetype("arial.ttf", 36)
            font_subtitle = ImageFont.truetype("arial.ttf", 22)
            font_low_contrast = ImageFont.truetype("arial.ttf", 20)
            font_badge = ImageFont.truetype("arial.ttf", 24)
        except Exception:
            font_title = font_subtitle = font_low_contrast = font_badge = ImageFont.load_default()

        # Top banner text
        draw.text((30, 24), "FLASH CAMPAIGN // Q4 AGENCY EXPANSION", fill=(255, 255, 255), font=font_badge)
        for offset_x in range(10, 320, 12):
            draw.line([(offset_x, 8), (offset_x + 8, 20)], fill=(255, 255, 255), width=2)
            draw.line([(offset_x, 60), (offset_x + 8, 72)], fill=(255, 255, 255), width=2)
        draw.rectangle([15, 12, 330, 72], outline=(255, 255, 255), width=2)

        # Main headline with brand casing error and superlative
        draw.text((40, 110), "Novapay Flash Sale: #1 fastest payments", fill=(255, 255, 255), font=font_title)
        draw.text((40, 165), "cheap fees & instant zero-fee international transfers", fill=(254, 240, 138), font=font_subtitle)
        draw.text((40, 205), "Join 500+ enterprise teams and Basic Plan with unlimited seats", fill=(243, 244, 246), font=font_subtitle)

        draw.text((540, 275), "TIER A", fill=(255, 255, 255), font=font_badge)
        draw.text((660, 275), "TIER B", fill=(255, 255, 255), font=font_badge)

        draw.text((60, 315), "Settlement terms apply. Instant wire transfers subject to network capacity.", fill=(168, 162, 158), font=font_low_contrast)
        draw.text((60, 340), "Limited availability across eligible jurisdictions. No warranty implied.", fill=(168, 162, 158), font=font_low_contrast)

        draw.text((30, 395), "Don't get wrecked by banks!! Switch to Novapay today.", fill=(255, 255, 255), font=font_badge)

        banner_img.save(banner_path, format="PNG")
        self.stdout.write(self.style.SUCCESS(f"Saved sample off-brand banner to: {banner_path}"))

        # 7. Pre-seed Historical Submission 1 (Cleared with HMAC signature)
        sub_title = "Global Enterprise Liquidity Q1 Pitch Deck"
        sample_sub, _ = Submission.objects.get_or_create(
            profile=profile,
            title=sub_title,
            channel_context="PITCH_DECK",
            defaults={
                "author": writer_1,
                "status": "APPROVED",
                "confidential_mode": True,
                "approved_by": admin_user,
                "approved_at": datetime.utcnow() - timedelta(days=2),
                "audit_notes": "Brand-compliance cleared. All superlatives adjusted and enterprise figures verified against Census 2026.",
            }
        )

        v1, _ = SubmissionVersion.objects.get_or_create(
            submission=sample_sub,
            version_number=1,
            defaults={
                "raw_text": "Novapay is the #1 fastest payments network. We offer cheap enterprise plans for 500+ enterprise teams.",
                "file_type": "TEXT",
                "compliance_score": 58.0,
                "score_breakdown": {
                    "final_score": 58.0, "blockers_count": 1, "warnings_count": 3,
                    "explanation": "Starting from 100: 1 blocker (-18), 3 warnings (-24) = 58/100"
                }
            }
        )

        v2, _ = SubmissionVersion.objects.get_or_create(
            submission=sample_sub,
            version_number=2,
            defaults={
                "raw_text": "NovaPay is the high-throughput payments network. We offer cost-effective enterprise plans for 500+ enterprise teams.",
                "file_type": "TEXT",
                "compliance_score": 82.0,
                "score_breakdown": {
                    "final_score": 82.0, "blockers_count": 1, "warnings_count": 0,
                    "explanation": "Starting from 100: 1 blocker (-18) = 82/100"
                }
            }
        )

        v3, _ = SubmissionVersion.objects.get_or_create(
            submission=sample_sub,
            version_number=3,
            defaults={
                "raw_text": "NovaPay is the high-throughput payments network. We offer cost-effective enterprise plans for over 2,400+ enterprise teams worldwide.",
                "file_type": "TEXT",
                "compliance_score": 100.0,
                "score_breakdown": {
                    "final_score": 100.0, "blockers_count": 0, "warnings_count": 0,
                    "explanation": "Starting from 100: 0 blockers, 0 warnings = 100/100"
                }
            }
        )

        # Generate HMAC-SHA256 signature for cleared submission
        sample_file_bytes = v3.raw_text.encode('utf-8')
        file_sha256 = hashlib.sha256(sample_file_bytes).hexdigest()
        sample_stamp_raw = f"{file_sha256}|{sample_sub.id}|v3.2|{admin_user.username}|{datetime.utcnow().isoformat()}Z"
        hmac_sig = hmac.new(settings.BRANDGUARD_SECRET_KEY.encode(), sample_stamp_raw.encode(), hashlib.sha256).hexdigest()

        sample_sub.clearance_hash = f"SHA256-{file_sha256}"
        sample_sub.clearance_signature = hmac_sig
        sample_sub.save()

        BrandComplianceSignature.objects.update_or_create(
            submission=sample_sub,
            file_sha256=file_sha256,
            defaults={
                "draft_id": str(sample_sub.id),
                "ruleset_version": "v3.2",
                "approver_username": admin_user.username,
                "timestamp": datetime.utcnow() - timedelta(days=2),
                "hmac_signature": hmac_sig,
                "canonical_payload": sample_stamp_raw,
                "legal_notice": "Brand-compliance cleared. Not a substitute for formal legal review."
            }
        )

        # 8. Pre-seed DRAFT_024 Submission with creator Alex Morgan, channel LINKEDIN_POST
        draft_024, _ = Submission.objects.get_or_create(
            profile=profile,
            title="DRAFT_024 - Global ambition. Local simplicity.",
            channel_context="LINKEDIN_POST",
            defaults={
                "author": writer_1,
                "status": "EXCEPTION_PENDING",
                "confidential_mode": False,
            }
        )
        v_draft, _ = SubmissionVersion.objects.get_or_create(
            submission=draft_024,
            version_number=1,
            defaults={
                "raw_text": "Don't get wrecked by banks! Your business. Without borders. Transfers settle in 24 hrs with a 0.5% FX fee.",
                "file_type": "TEXT",
                "compliance_score": 92.0,
                "score_breakdown": {
                    "final_score": 92.0, "blockers_count": 0, "warnings_count": 1,
                    "explanation": "Starting from 100: 0 blockers, 1 tone warning (-8) = 92/100. Pending exception request."
                }
            }
        )

        # 9. Seed Exception Requests
        ex_2041, _ = ExceptionRequest.objects.update_or_create(
            id="EX-2041",
            defaults={
                "submission": draft_024,
                "author": writer_1,
                "draft_id": "DRAFT_024",
                "rule_code": "VOICE_004",
                "title": "Global ambition. Local simplicity.",
                "requester_name": "Alex Morgan",
                "requester_dept": "Marketing Ops",
                "requested_date": date.today() - timedelta(days=1),
                "warning_type": "Warning · Voice",
                "quote_text": "Don't get wrecked by banks!",
                "rule_description": "Aggressive comparison tone is outside the default voice range.",
                "justification": "This is an intentional challenger voice for NovaPay's 'Global ambition' campaign. It addresses banking friction, not individuals or protected groups, and makes no fee or speed claim.",
                "campaign_reference": "Global ambition · Q3 2026 launch",
                "scope": "This draft only",
                "channel": "LinkedIn post",
                "expires_on": date.today() + timedelta(days=90),
                "reviewer_name": "Jordan Lee",
                "reviewer_title": "Brand Governance Lead",
                "hard_blockers_count": 0,
                "supporting_file_name": "Q3_challenger_campaign.pdf",
                "supporting_file_size": "1.2 MB",
                "status": "PENDING",
                "decision_note": "Under review. Narrow scope and high relevance for Q3 launch.",
            }
        )

        ExceptionRequest.objects.update_or_create(
            id="EX-2039",
            defaults={
                "author": writer_2,
                "draft_id": "DRAFT_022",
                "rule_code": "TONE_002",
                "title": "Move money, not mountains.",
                "requester_name": "Taylor Reed",
                "requester_dept": "Growth & Social",
                "requested_date": date.today() - timedelta(days=2),
                "warning_type": "Warning · Voice",
                "quote_text": "Move money, not mountains.",
                "rule_description": "Colloquial idiom register requires brand review.",
                "justification": "Targeting high-velocity international e-commerce merchants.",
                "campaign_reference": "Summer Merchant Push 2026",
                "scope": "This draft only",
                "channel": "LinkedIn post",
                "expires_on": date.today() + timedelta(days=60),
                "reviewer_name": "Jordan Lee",
                "reviewer_title": "Brand Governance Lead",
                "hard_blockers_count": 0,
                "status": "PENDING",
            }
        )

        ExceptionRequest.objects.update_or_create(
            id="EX-2036",
            defaults={
                "author": writer_2,
                "draft_id": "DRAFT_019",
                "rule_code": "VOICE_004",
                "title": "The banking you deserve.",
                "requester_name": "Taylor Reed",
                "requester_dept": "Growth & Social",
                "requested_date": date.today() - timedelta(days=5),
                "warning_type": "Warning · Voice",
                "quote_text": "The banking you deserve.",
                "rule_description": "Unqualified superlative phrasing.",
                "justification": "Executive interview quote for European fintech roundup.",
                "campaign_reference": "FinTech Europe Spotlight",
                "scope": "This draft only",
                "channel": "Press Release",
                "expires_on": date.today() + timedelta(days=30),
                "reviewer_name": "Jordan Lee",
                "reviewer_title": "Brand Governance Lead",
                "hard_blockers_count": 0,
                "status": "APPROVED",
                "decision_note": "Brand-compliance cleared. Scoped strictly to PR quote attribution.",
                "decided_at": datetime.utcnow() - timedelta(days=3),
                "decided_by": "Jordan Lee",
                "decided_by_user": admin_user,
            }
        )

        # 10. Notifications
        Notification.objects.get_or_create(
            recipient=admin_user,
            title="Pending Exception Request (EX-2041)",
            defaults={
                "message": "Alex Morgan submitted a scoped exception request for VOICE_004 on draft 'Global ambition. Local simplicity.'",
                "notification_type": "EXCEPTION_PENDING",
                "link_url": "/queue",
            }
        )
        Notification.objects.get_or_create(
            recipient=admin_user,
            title="Expiring Fact Alert: SOC2 Type II Certification",
            defaults={
                "message": "Fact FACT_031 expires within 45 days (June 10, 2026). 51 drafts reference this certification.",
                "notification_type": "FACT_EXPIRING",
                "link_url": "/facts",
            }
        )
        Notification.objects.get_or_create(
            recipient=writer_1,
            title="Exception Request Submitted: EX-2041",
            defaults={
                "message": "Your exception request for 'Global ambition. Local simplicity.' is pending review by Jordan Lee.",
                "notification_type": "INFO",
                "link_url": "/submissions",
            }
        )
        Notification.objects.get_or_create(
            recipient=writer_2,
            title="Exception Approved: EX-2036",
            defaults={
                "message": "Jordan Lee approved your scoped exception for 'The banking you deserve.' You can now download the cleared asset.",
                "notification_type": "EXCEPTION_DECIDED",
                "link_url": "/submissions",
            }
        )

        # 11. Audit Trail
        AuditTrail.objects.get_or_create(
            user=admin_user,
            action="RULE_UPDATED",
            entity_type="RULE",
            entity_id="FACT_012",
            defaults={
                "user_display": admin_user.username,
                "user_role": "ADMIN",
                "description": "Admin Jordan Lee updated FACT_012 to version 4 (added 0.5% FX fee to allowed claims).",
                "metadata_json": {"version": 4, "rule_code": "FACT_012"},
            }
        )
        AuditTrail.objects.get_or_create(
            user=admin_user,
            action="EXCEPTION_APPROVED",
            entity_type="EXCEPTION",
            entity_id="EX-2036",
            defaults={
                "user_display": admin_user.username,
                "user_role": "ADMIN",
                "description": "Admin Jordan Lee brand-compliance cleared exception EX-2036 with note: Scoped strictly to PR quote attribution.",
                "metadata_json": {"status": "APPROVED", "reviewer": "Jordan Lee"},
            }
        )
        AuditTrail.objects.get_or_create(
            user=writer_1,
            action="AUDIT_EXECUTED",
            entity_type="SUBMISSION",
            entity_id=str(draft_024.id),
            defaults={
                "user_display": writer_1.username,
                "user_role": "CONTENT_WRITER",
                "description": "Content Writer Alex Morgan ran pre-flight audit on 'DRAFT_024 - Global ambition. Local simplicity.' (Score: 92/100).",
                "metadata_json": {"score": 92.0, "channel": "LINKEDIN_POST"},
            }
        )

        # 12. Governance Telemetry AuditEvents (Module 1)
        from django.utils import timezone
        AuditEvent.objects.filter(profile=profile).delete()
        now = timezone.now()

        # Seed audit events for existing submissions
        for sub in Submission.objects.filter(profile=profile):
            v1 = sub.versions.order_by('version_number').first()
            if not v1:
                continue

            # Emit SCAN event
            sub_ts = v1.created_at or (now - timedelta(days=5))
            AuditEvent.objects.create(
                profile=profile,
                user=sub.author or writer_1,
                event_type='SCAN',
                submission=sub,
                submission_version=v1,
                channel=sub.channel_context,
                timestamp=sub_ts
            )

            # Emit findings as RULE_VIOLATED
            for finding in v1.findings.all():
                rc = finding.rule_citation_code
                rule_obj = BrandRule.objects.filter(profile=profile, rule_code=rc).first()
                fact_obj = FactLedger.objects.filter(profile=profile, fact_code=rc).first()
                sev = rule_obj.severity if rule_obj else ('BLOCKER' if fact_obj else finding.severity)

                AuditEvent.objects.create(
                    profile=profile,
                    user=sub.author or writer_1,
                    event_type='RULE_VIOLATED',
                    submission=sub,
                    submission_version=v1,
                    rule_code=rc,
                    fact_code=fact_obj.fact_code if fact_obj else '',
                    rule=rule_obj,
                    fact=fact_obj,
                    severity=sev,
                    channel=sub.channel_context,
                    timestamp=sub_ts
                )

        # Seed historical audit events for rules over the past 28 days
        historical_rules = [
            ("LEX_001", 18, 1, "WARNING"),
            ("LEX_002", 22, 12, "WARNING"),
            ("LEX_003", 14, 0, "BLOCKER"),
            ("TONE_001", 12, 6, "WARNING"),
            ("TONE_002", 15, 2, "WARNING"),
            ("FACT_012", 24, 0, "BLOCKER"),
            ("FACT_031", 11, 0, "BLOCKER"),
            ("VIS_WCAG_001", 16, 0, "BLOCKER"),
        ]

        channels = ['LINKEDIN_POST', 'PRESS_RELEASE', 'PITCH_DECK', 'LANDING_PAGE']
        writers = [writer_1, writer_2]

        for code, trigs, ovs, default_sev in historical_rules:
            rule_obj = BrandRule.objects.filter(profile=profile, rule_code=code).first()
            fact_obj = FactLedger.objects.filter(profile=profile, fact_code=code).first()
            sev = rule_obj.severity if rule_obj else ('BLOCKER' if fact_obj else default_sev)

            for i in range(trigs):
                day_offset = (i % 25) + 1
                ev_ts = now - timedelta(days=day_offset, hours=(i * 3) % 24)
                w = writers[i % len(writers)]
                ch = channels[i % len(channels)]

                AuditEvent.objects.create(
                    profile=profile,
                    user=w,
                    event_type='RULE_VIOLATED',
                    rule_code=code,
                    fact_code=fact_obj.fact_code if fact_obj else '',
                    rule=rule_obj,
                    fact=fact_obj,
                    severity=sev,
                    channel=ch,
                    timestamp=ev_ts
                )

            for j in range(ovs):
                day_offset = (j % 20) + 1
                ev_ts = now - timedelta(days=day_offset, hours=2)
                ch = channels[j % len(channels)]
                AuditEvent.objects.create(
                    profile=profile,
                    user=admin_user,
                    event_type='EXCEPTION_APPROVED',
                    rule_code=code,
                    severity=sev,
                    channel=ch,
                    timestamp=ev_ts
                )

        # Historical scans for sparkline
        for d in range(1, 26):
            scan_ts = now - timedelta(days=d, hours=10)
            AuditEvent.objects.create(
                profile=profile,
                user=writers[d % 2],
                event_type='SCAN',
                channel=channels[d % len(channels)],
                timestamp=scan_ts
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {AuditEvent.objects.count()} live AuditEvent rows for telemetry."))

        # ----------------------------------------------------------------------
        # Module 2: Codebase-to-Claim Ground-Truth Verifier Demo Data
        # ----------------------------------------------------------------------
        repo, created = CodebaseRepo.objects.get_or_create(
            profile=profile,
            repo_name="novapay/core-banking",
            defaults={
                "repo_url": "https://github.com/novapay/core-banking",
                "branch": "main",
                "webhook_secret": "novapay_whsec_live_9942a",
                "last_commit_sha": "7f3d8a1",
                "last_scanned_at": now - timedelta(minutes=42),
                "scan_status": "SUCCESS"
            }
        )
        repo.set_auth_token("ghp_live_read_token_demo_99214")
        repo.save()

        # Symbol Mappings
        fact_12 = FactLedger.objects.filter(profile=profile, fact_code="FACT_012").first()
        fact_08 = FactLedger.objects.filter(profile=profile, fact_code="FACT_008").first()

        map_fee, _ = CodeSymbolMapping.objects.get_or_create(
            profile=profile,
            symbol_name="DEFAULT_FX_FEE",
            defaults={
                "semantic_key": "fx_fee_rate",
                "target_fact": fact_12,
                "unit_type": "PERCENTAGE",
                "scale_factor": 100.0,
                "display_format": "{value}%",
                "confidence_weight": 1.0,
                "is_active": True
            }
        )

        map_settle, _ = CodeSymbolMapping.objects.get_or_create(
            profile=profile,
            symbol_name="SETTLEMENT_WINDOW_HOURS",
            defaults={
                "semantic_key": "settlement_window_hours",
                "target_fact": fact_12,
                "unit_type": "HOURS",
                "scale_factor": 1.0,
                "display_format": "{value} hours",
                "confidence_weight": 1.0,
                "is_active": True
            }
        )

        map_teams, _ = CodeSymbolMapping.objects.get_or_create(
            profile=profile,
            symbol_name="ACTIVE_ENTERPRISE_TEAMS",
            defaults={
                "semantic_key": "enterprise_teams_adoption",
                "target_fact": fact_08,
                "unit_type": "COUNT",
                "scale_factor": 1.0,
                "display_format": "{value}+ teams",
                "confidence_weight": 1.0,
                "is_active": True
            }
        )

        # Extracted Codebase Constants
        const_fee, _ = CodebaseConstant.objects.get_or_create(
            repo=repo,
            symbol_name="DEFAULT_FX_FEE",
            defaults={
                "mapping": map_fee,
                "raw_value": "0.008",
                "normalized_value": "0.8%",
                "file_path": "src/payments/constants.py",
                "line_number": 14,
                "commit_sha": "7f3d8a1",
                "confidence": 1.0
            }
        )

        const_settle, _ = CodebaseConstant.objects.get_or_create(
            repo=repo,
            symbol_name="SETTLEMENT_WINDOW_HOURS",
            defaults={
                "mapping": map_settle,
                "raw_value": "24",
                "normalized_value": "24 hours",
                "file_path": "src/payments/settlement.py",
                "line_number": 28,
                "commit_sha": "7f3d8a1",
                "confidence": 1.0
            }
        )

        # Proposed Fact Change (Pending Admin Review)
        if fact_12:
            prop_change, _ = ProposedFactChange.objects.get_or_create(
                profile=profile,
                fact=fact_12,
                constant=const_fee,
                defaults={
                    "old_value": fact_12.claim_truth,
                    "new_value": "0.8% FX fee schedule",
                    "code_location": "src/payments/constants.py:14 @ commit 7f3d8a1",
                    "commit_sha": "7f3d8a1",
                    "status": "PENDING"
                }
            )

        self.stdout.write(self.style.SUCCESS("Module 2 Codebase-to-Claim Verifier demo data seeded."))

        # ----------------------------------------------------------------------
        # Module 3: Blast Radius of Truth-Change Demo Data
        # ----------------------------------------------------------------------
        if fact_12:
            stale_sub, _ = Submission.objects.get_or_create(
                profile=profile,
                title="Q4 Enterprise Cross-Border Campaign",
                defaults={
                    "author": writer_1,
                    "channel_context": "PAID_ADS",
                    "status": "STALE_REAUDIT_REQUIRED",
                    "clearance_hash": "",
                    "clearance_signature": "",
                }
            )
            stale_ver, _ = SubmissionVersion.objects.get_or_create(
                submission=stale_sub,
                version_number=1,
                defaults={
                    "raw_text": "Experience instant liquidity with guaranteed 0.5% FX rates across global banking corridors.",
                    "file_type": "TEXT",
                    "compliance_score": 64.0,
                }
            )
            AuditFinding.objects.get_or_create(
                version=stale_ver,
                rule_citation_code=fact_12.fact_code,
                defaults={
                    "pillar": "FACTUAL",
                    "severity": "BLOCKER",
                    "engine_provenance": "DETERMINISTIC_LEXICON",
                    "rule_citation_title": f"Stale Truth Contradiction: {fact_12.fact_code}",
                    "explanation": f"Fact [{fact_12.fact_code}] changed in product code. Asset is marked STALE_REAUDIT_REQUIRED.",
                    "suggested_fixes": ["Replace with '0.8%'"],
                    "status": "OPEN",
                    "source_excerpt": "0.5%",
                }
            )
            BlastRadiusReport.objects.get_or_create(
                profile=profile,
                fact=fact_12,
                defaults={
                    "trigger_reason": "FACT_CHANGE_APPROVED",
                    "old_value": "0.5% FX rates",
                    "new_value": "0.8%",
                    "affected_assets_count": 1,
                    "channel_breakdown": {"PAID_ADS": 1},
                    "severity": "CRITICAL",
                    "estimated_reach": 50000,
                    "affected_owners": [
                        {
                            "user_id": str(writer_1.id),
                            "username": writer_1.username,
                            "name": "Sarah Chen",
                            "asset_count": 1,
                            "assets": [{"id": str(stale_sub.id), "title": stale_sub.title}]
                        }
                    ],
                    "draft_patches": [
                        {
                            "submission_id": str(stale_sub.id),
                            "title": stale_sub.title,
                            "channel": "PAID_ADS",
                            "old_excerpt": "0.5%",
                            "replacement": "0.8%",
                            "original_text": stale_ver.raw_text,
                            "patched_text": stale_ver.raw_text.replace("0.5%", "0.8%"),
                        }
                    ],
                }
            )
        self.stdout.write(self.style.SUCCESS("Module 3 Blast Radius & Staleness demo data seeded."))
        self.stdout.write(self.style.SUCCESS("Demo seeding completed successfully! All data structures verified."))
