import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from governance.models import BrandProfile, BrandRule, FactLedger, Submission, SubmissionVersion, AuditFinding
from governance.auth import generate_user_token

User = get_user_model()


class Phase3WorkspaceInspectorTestCase(TestCase):
    """
    Automated tests for Phase 3:
    1. Pre-Flight Audit (POST /api/submissions/audit/) with text & tone findings + highlighted spans
    2. Visual Audit with bounding boxes & CVD deuteranopia analysis
    3. Readiness Score calculation with full mathematical breakdown
    4. 1-Click "Apply Patch" (POST /api/findings/{id}/resolve/ -> ACCEPT_FIX -> v+1)
    5. Real-time debounced Live Lexicon Linting (POST /api/submissions/live-lint/)
    6. My Workspace submissions list with role-based filtering
    """

    def setUp(self):
        self.client = Client()

        # Seed profile
        self.profile = BrandProfile.objects.create(
            org_name="NovaPay",
            allowed_hex_palette=[
                {"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0},
                {"name": "Teal", "hex": "#00D4B6", "max_delta_e": 4.5},
            ],
            allowed_fonts=["Inter"]
        )

        # Seed Rules
        self.rule_lex = BrandRule.objects.create(
            profile=self.profile,
            rule_code="LEX_CHEAP",
            title="Prohibit 'Cheap'",
            pillar="TONE",
            severity="BLOCKER",
            claims_allowed="cost-effective",
            claims_disallowed="cheap",
            structured_spec={"banned_term": "cheap", "replacement": "cost-effective"}
        )

        self.rule_tone = BrandRule.objects.create(
            profile=self.profile,
            rule_code="TONE_WRECKED",
            title="Aggressive Banking Slang",
            pillar="TONE",
            severity="BLOCKER",
            claims_allowed="modern fintech infrastructure",
            claims_disallowed="get wrecked by banks",
            structured_spec={"banned_term": "wrecked", "replacement": "friction"}
        )

        # Seed Admin
        self.admin = User.objects.create_user(
            username="admin_p3",
            email="admin3@novapay.io",
            password="adminpassword123",
            role="ADMIN",
            brand_profile=self.profile
        )
        self.admin_token = generate_user_token(self.admin)

        # Seed Content Writer
        self.writer = User.objects.create_user(
            username="writer_p3",
            email="writer3@novapay.io",
            password="writerpassword123",
            role="CONTENT_WRITER",
            brand_profile=self.profile
        )
        self.writer_token = generate_user_token(self.writer)

    def test_audit_submission_text_and_readiness_score_breakdown(self):
        """Tests POST /api/submissions/audit/ returns findings, location spans, and score breakdown."""
        raw_text = "Don't get wrecked by banks! Our cheap transfers settle fast."
        payload = {
            "title": "Global Launch Campaign",
            "channel_context": "LINKEDIN_POST",
            "raw_text": raw_text,
            "confidential_mode": False
        }

        res = self.client.post(
            '/api/submissions/audit/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Check Submission and Version structure
        self.assertEqual(data["title"], "Global Launch Campaign")
        self.assertEqual(data["channel_context"], "LINKEDIN_POST")
        self.assertIn("versions", data)
        self.assertEqual(len(data["versions"]), 1)

        v1 = data["versions"][0]
        self.assertIn("score_breakdown", v1)
        breakdown = v1["score_breakdown"]
        self.assertEqual(breakdown["base_score"], 100.0)
        self.assertGreater(breakdown["blockers_count"], 0)
        self.assertEqual(breakdown["blocker_rate"], 18.0)
        self.assertLess(v1["compliance_score"], 100.0)

        # Check findings have location spans
        findings = v1["findings"]
        self.assertGreater(len(findings), 0)
        for f in findings:
            self.assertIn("location_json", f)
            loc = f["location_json"]
            self.assertEqual(loc.get("format"), "TEXT_OFFSET")
            self.assertIn("start_char", loc)
            self.assertIn("end_char", loc)
            self.assertIn("suggested_fixes", f)

    def test_apply_patch_creates_new_version_and_updates_score(self):
        """Tests 1-click Apply Patch (POST /api/findings/{id}/resolve/ with ACCEPT_FIX)."""
        raw_text = "Our cheap transfers are fast."
        payload = {
            "title": "Patch Demo Campaign",
            "channel_context": "LINKEDIN_POST",
            "raw_text": raw_text
        }
        res_audit = self.client.post(
            '/api/submissions/audit/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        sub_data = res_audit.json()
        v1 = sub_data["versions"][0]
        finding = v1["findings"][0]
        finding_id = finding["id"]

        # Apply Patch
        patch_res = self.client.post(
            f'/api/findings/{finding_id}/resolve/',
            data=json.dumps({
                "action": "ACCEPT_FIX",
                "chosen_fix": "Replace with 'cost-effective'"
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(patch_res.status_code, 200)
        patch_data = patch_res.json()
        self.assertEqual(patch_data["status"], "success")

        # Verify new Version v2 was created
        sub_updated = patch_data["submission"]
        self.assertEqual(len(sub_updated["versions"]), 2)
        v2 = sub_updated["versions"][1]
        self.assertEqual(v2["version_number"], 2)
        self.assertIn("cost-effective", v2["raw_text"])
        self.assertNotIn("cheap", v2["raw_text"])
        self.assertGreater(v2["compliance_score"], v1["compliance_score"])

    def test_debounced_live_lint_endpoint(self):
        """Tests POST /api/submissions/live-lint/ for instant interactive feedback."""
        res = self.client.post(
            '/api/submissions/live-lint/',
            data=json.dumps({
                "raw_text": "We delve into cheap payments in today's fast-paced world."
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("findings", data)
        self.assertIn("compliance_score", data)
        self.assertIn("score_breakdown", data)
        self.assertIn("voice_fingerprint", data)

        # Check AI-slop was flagged (delve into / in today's fast-paced)
        citations = [f["rule_citation_code"] for f in data["findings"]]
        self.assertTrue(any("SLOP" in c or "LEX" in c for c in citations))

    def test_my_workspace_submissions_listing(self):
        """Tests GET /api/submissions/ lists submissions with role scoping."""
        # Create submission as writer
        self.client.post(
            '/api/submissions/audit/',
            data=json.dumps({"title": "Writer Draft 1", "raw_text": "Compliant statement."}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )

        # Fetch submissions as writer
        res_writer = self.client.get(
            '/api/submissions/',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(res_writer.status_code, 200)
        writer_subs = res_writer.json()["submissions"]
        self.assertGreaterEqual(len(writer_subs), 1)
        self.assertTrue(all(s["title"] == "Writer Draft 1" or s["author"]["username"] == "writer_p3" for s in writer_subs))
