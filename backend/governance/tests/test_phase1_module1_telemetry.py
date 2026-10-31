import json
import math
from datetime import timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse

from governance.models import (
    BrandGuardUser, BrandProfile, BrandRule, FactLedger,
    Submission, SubmissionVersion, AuditFinding, AuditEvent,
    SystemSettings, Job
)
from governance.auth import generate_user_token
from governance.engines.telemetry import (
    diagnose_rule, is_fact_or_accessibility_rule,
    calculate_window_telemetry, generate_telemetry_csv
)


class TestAmbiguityDiagnosisBoundaryValues(TestCase):
    """
    Test deliverable (a): diagnosis logic with boundary values.
    Requirements:
    - Below MIN_TRIGGERS (default 10) show "Not enough data"
    - triggers >= MIN_TRIGGERS:
        override_rate >= 40% -> NEEDS_CLARIFICATION (rule too rigid or poorly written)
        override_rate <= 15% -> TRAINING_GAP (rule is valid, writers keep making mistakes)
        otherwise            -> HEALTHY_GOVERNANCE
    - Facts and accessibility rules cannot be overridden, so their override rate is 0 by design.
      Show them as TRAINING_GAP candidates only, never NEEDS_CLARIFICATION.
    """

    def test_below_min_triggers_boundary(self):
        # Boundary at MIN_TRIGGERS - 1 (e.g. 9 triggers when min is 10)
        res_9 = diagnose_rule(triggers=9, override_rate_pct=50.0, min_triggers=10)
        self.assertEqual(res_9["diagnosis"], "NOT_ENOUGH_DATA")
        self.assertEqual(res_9["diagnosis_label"], "Not enough data")
        self.assertIn("minimum 10 triggers", res_9["hint"])

        res_0 = diagnose_rule(triggers=0, override_rate_pct=0.0, min_triggers=10)
        self.assertEqual(res_0["diagnosis"], "NOT_ENOUGH_DATA")

    def test_exact_min_triggers_boundary(self):
        # Exactly 10 triggers (triggers >= min_triggers)
        res_40 = diagnose_rule(triggers=10, override_rate_pct=40.0, min_triggers=10)
        self.assertEqual(res_40["diagnosis"], "NEEDS_CLARIFICATION")

        res_15 = diagnose_rule(triggers=10, override_rate_pct=15.0, min_triggers=10)
        self.assertEqual(res_15["diagnosis"], "TRAINING_GAP")

        res_healthy = diagnose_rule(triggers=10, override_rate_pct=25.0, min_triggers=10)
        self.assertEqual(res_healthy["diagnosis"], "HEALTHY_GOVERNANCE")

    def test_override_rate_boundaries(self):
        min_trig = 10
        # 39.9% vs 40.0% boundary
        below_40 = diagnose_rule(triggers=20, override_rate_pct=39.9, min_triggers=min_trig)
        self.assertEqual(below_40["diagnosis"], "HEALTHY_GOVERNANCE")

        at_40 = diagnose_rule(triggers=20, override_rate_pct=40.0, min_triggers=min_trig)
        self.assertEqual(at_40["diagnosis"], "NEEDS_CLARIFICATION")

        above_40 = diagnose_rule(triggers=20, override_rate_pct=40.1, min_triggers=min_trig)
        self.assertEqual(above_40["diagnosis"], "NEEDS_CLARIFICATION")

        # 15.0% vs 15.1% boundary
        at_15 = diagnose_rule(triggers=20, override_rate_pct=15.0, min_triggers=min_trig)
        self.assertEqual(at_15["diagnosis"], "TRAINING_GAP")

        above_15 = diagnose_rule(triggers=20, override_rate_pct=15.1, min_triggers=min_trig)
        self.assertEqual(above_15["diagnosis"], "HEALTHY_GOVERNANCE")

        at_zero = diagnose_rule(triggers=20, override_rate_pct=0.0, min_triggers=min_trig)
        self.assertEqual(at_zero["diagnosis"], "TRAINING_GAP")

    def test_facts_and_accessibility_constraint(self):
        # Facts and accessibility rules cannot be overridden.
        # Must always diagnose as TRAINING_GAP when triggers >= min_triggers, NEVER NEEDS_CLARIFICATION.
        min_trig = 10
        res_fact = diagnose_rule(triggers=15, override_rate_pct=0.0, is_fact_or_accessibility=True, min_triggers=min_trig)
        self.assertEqual(res_fact["diagnosis"], "TRAINING_GAP")

        # Even if a hypothetical override_rate were passed as 80%, is_fact_or_accessibility must guard it
        res_fact_guarded = diagnose_rule(triggers=15, override_rate_pct=80.0, is_fact_or_accessibility=True, min_triggers=min_trig)
        self.assertEqual(res_fact_guarded["diagnosis"], "TRAINING_GAP")
        self.assertNotEqual(res_fact_guarded["diagnosis"], "NEEDS_CLARIFICATION")

        # Below min triggers still returns NOT_ENOUGH_DATA
        res_fact_low = diagnose_rule(triggers=5, override_rate_pct=0.0, is_fact_or_accessibility=True, min_triggers=min_trig)
        self.assertEqual(res_fact_low["diagnosis"], "NOT_ENOUGH_DATA")

    def test_rule_classifier(self):
        self.assertTrue(is_fact_or_accessibility_rule("FACT_012"))
        self.assertTrue(is_fact_or_accessibility_rule("VIS_WCAG_2.1"))
        self.assertTrue(is_fact_or_accessibility_rule("RULE_CONTRAST_01"))
        self.assertTrue(is_fact_or_accessibility_rule("GEN_01", pillar="FACTUAL"))
        self.assertTrue(is_fact_or_accessibility_rule("GEN_02", pillar="ACCESSIBILITY"))
        self.assertFalse(is_fact_or_accessibility_rule("VOICE_004", pillar="TONE"))
        self.assertFalse(is_fact_or_accessibility_rule("LEX_001", pillar="VISUAL", title="Brand Casing"))


class TestTelemetryEngineAndFirstPassAggregation(TestCase):
    """
    Tests live telemetry calculation from AuditEvent rows and aggregated queries.
    """

    def setUp(self):
        self.profile = BrandProfile.objects.create(
            org_name="TestOrg",
            allowed_hex_palette=[],
            allowed_fonts=[]
        )
        self.admin = BrandGuardUser.objects.create(
            username="test_admin",
            role="ADMIN",
            brand_profile=self.profile
        )
        self.writer = BrandGuardUser.objects.create(
            username="test_writer",
            role="CONTENT_WRITER",
            brand_profile=self.profile
        )

        self.rule = BrandRule.objects.create(
            profile=self.profile,
            rule_code="TONE_TEST",
            title="Tone Test Rule",
            pillar="TONE",
            severity="WARNING"
        )

        sys_settings = SystemSettings.get_settings()
        sys_settings.min_triggers = 10
        sys_settings.minutes_per_audit = 5
        sys_settings.save()

    def test_first_pass_rate_single_aggregated_query(self):
        now = timezone.now()

        # Submission 1: clean v1 (0 blockers)
        s1 = Submission.objects.create(profile=self.profile, author=self.writer, title="Sub 1", channel_context="LINKEDIN_POST")
        v1_s1 = SubmissionVersion.objects.create(submission=s1, version_number=1, raw_text="Clean text")
        # Add a warning finding (not blocker)
        AuditFinding.objects.create(version=v1_s1, pillar="TONE", severity="WARNING", rule_citation_code="TONE_TEST", status="OPEN")
        AuditEvent.objects.create(profile=self.profile, user=self.writer, event_type="SCAN", submission=s1, submission_version=v1_s1, channel="LINKEDIN_POST", timestamp=now)

        # Submission 2: v1 had an open blocker
        s2 = Submission.objects.create(profile=self.profile, author=self.writer, title="Sub 2", channel_context="LINKEDIN_POST")
        v1_s2 = SubmissionVersion.objects.create(submission=s2, version_number=1, raw_text="Dirty text")
        AuditFinding.objects.create(version=v1_s2, pillar="FACTUAL", severity="BLOCKER", rule_citation_code="FACT_TEST", status="OPEN")
        AuditEvent.objects.create(profile=self.profile, user=self.writer, event_type="SCAN", submission=s2, submission_version=v1_s2, channel="LINKEDIN_POST", timestamp=now)

        # Compute telemetry
        telemetry = calculate_window_telemetry(profile=self.profile, days=30)
        kpis = telemetry["kpis"]

        # Audit volume = 2 distinct submissions
        self.assertEqual(kpis["audit_volume"], 2)

        # First-pass rate: 1 clean out of 2 = 50.0%
        self.assertEqual(kpis["first_pass_rate"], 50.0)

        # Review time saved = 2 audits * 5 min / 60 = 0.2 hrs
        expected_saved = round((2 * 5) / 60.0, 1)
        self.assertEqual(kpis["review_time_saved_hours"], expected_saved)
        self.assertIn("(estimated)", kpis["review_time_saved_label"])

    def test_friction_and_last_triggered_real_timestamp(self):
        now = timezone.now()
        ts_old = now - timedelta(days=2)
        ts_latest = now - timedelta(hours=1)

        # Emit 12 violations for TONE_TEST and 6 approved exceptions
        for i in range(12):
            ts = ts_latest if i == 11 else ts_old
            AuditEvent.objects.create(
                profile=self.profile,
                user=self.writer,
                event_type="RULE_VIOLATED",
                rule_code="TONE_TEST",
                severity="WARNING",
                timestamp=ts
            )

        for _ in range(6):
            AuditEvent.objects.create(
                profile=self.profile,
                user=self.admin,
                event_type="EXCEPTION_APPROVED",
                rule_code="TONE_TEST",
                timestamp=ts_old
            )

        telemetry = calculate_window_telemetry(profile=self.profile, days=30)
        rule_entry = next(r for r in telemetry["rules"] if r["rule_code"] == "TONE_TEST")

        self.assertEqual(rule_entry["triggers"], 12)
        self.assertEqual(rule_entry["overrides"], 6)
        self.assertEqual(rule_entry["override_rate_pct"], 50.0)

        # Friction = (6/12) * ln(12 + 1) = 0.5 * ln(13) = 0.5 * 2.564949 = 1.282
        expected_friction = round(0.5 * math.log(13), 3)
        self.assertEqual(rule_entry["friction_score"], expected_friction)

        # Diagnosis: override_rate >= 40% with triggers >= 10 -> NEEDS_CLARIFICATION
        self.assertEqual(rule_entry["diagnosis"], "NEEDS_CLARIFICATION")

        # last_triggered must match ts_latest exactly
        self.assertIsNotNone(rule_entry["last_triggered"])
        self.assertEqual(rule_entry["last_triggered"], ts_latest.isoformat())


class TestRBACPermissionsAndSecurity(TestCase):
    """
    Test deliverable (d): content writer gets HTTP 403 on all admin endpoints.
    """

    def setUp(self):
        self.client = Client()
        self.profile = BrandProfile.objects.create(
            org_name="NovaPay",
            allowed_hex_palette=[],
            allowed_fonts=[]
        )
        self.admin = BrandGuardUser.objects.create_user(
            username="admin_user",
            password="password123",
            role="ADMIN",
            brand_profile=self.profile
        )
        self.writer = BrandGuardUser.objects.create_user(
            username="writer_user",
            password="password123",
            role="CONTENT_WRITER",
            brand_profile=self.profile
        )

        self.admin_token = generate_user_token(self.admin)
        self.writer_token = generate_user_token(self.writer)

    def test_writer_forbidden_on_admin_telemetry_endpoints(self):
        writer_headers = {'HTTP_AUTHORIZATION': f'Bearer {self.writer_token}'}

        # 1. Main Telemetry Dashboard (Admin only)
        res1 = self.client.get('/api/telemetry/', **writer_headers)
        self.assertEqual(res1.status_code, 403)

        # 2. Telemetry CSV Export (Admin only)
        res2 = self.client.get('/api/telemetry/export-csv/', **writer_headers)
        self.assertEqual(res2.status_code, 403)

        # 3. Telemetry PDF Export (Admin only)
        res3 = self.client.get('/api/telemetry/export-pdf/', **writer_headers)
        self.assertEqual(res3.status_code, 403)

    def test_writer_allowed_on_writer_summary_endpoint(self):
        # Writer accessing writer-facing endpoint
        writer_headers = {'HTTP_AUTHORIZATION': f'Bearer {self.writer_token}'}

        res = self.client.get('/api/telemetry/writer-summary/', **writer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('my_top_rules', data)
        self.assertIn('writer', data)
        # Ensure zero org-wide metrics (no kpis, no org audit volume, etc.)
        self.assertNotIn('kpis', data)
        self.assertNotIn('audit_volume', data)

    def test_admin_allowed_on_all_telemetry_endpoints(self):
        admin_headers = {'HTTP_AUTHORIZATION': f'Bearer {self.admin_token}'}

        # 1. Dashboard
        res1 = self.client.get('/api/telemetry/', **admin_headers)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertIn('kpis', data1)
        self.assertIn('rules', data1)

        # 2. CSV Export
        res2 = self.client.get('/api/telemetry/export-csv/', **admin_headers)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2['Content-Type'], 'text/csv')

        # 3. PDF Export
        res3 = self.client.get('/api/telemetry/export-pdf/', **admin_headers)
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3['Content-Type'], 'application/pdf')


class TestJobStatusEndpoint(TestCase):
    """
    Tests Job model and GET /api/jobs/<job_id>/ status polling.
    """

    def setUp(self):
        self.client = Client()
        self.profile = BrandProfile.objects.create(
            org_name="NovaPay",
            allowed_hex_palette=[],
            allowed_fonts=[]
        )
        self.writer = BrandGuardUser.objects.create_user(
            username="job_writer",
            password="password123",
            role="CONTENT_WRITER",
            brand_profile=self.profile
        )
        self.token = generate_user_token(self.writer)

    def test_poll_job_status(self):
        job = Job.objects.create(
            profile=self.profile,
            user=self.writer,
            job_type="REPO_SCAN",
            status="RUNNING",
            progress=45,
            status_message="Parsing Python AST..."
        )

        headers = {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}
        res = self.client.get(f'/api/jobs/{job.id}/', **headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'RUNNING')
        self.assertEqual(data['progress'], 45)
        self.assertEqual(data['job_type'], 'REPO_SCAN')
        self.assertEqual(data['status_message'], 'Parsing Python AST...')
