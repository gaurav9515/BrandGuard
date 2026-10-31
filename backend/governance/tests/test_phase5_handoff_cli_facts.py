import json
import subprocess
import sys
from pathlib import Path
from datetime import date, timedelta
from PIL import Image

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings
from governance.models import (
    BrandProfile, BrandRule, FactLedger, Submission, SubmissionVersion,
    AuditFinding, BrandComplianceSignature, Notification, AuditTrail
)
from governance.auth import generate_user_token
from governance.crypto_sign import (
    sign_hmac_sha256, verify_hmac_sha256,
    sign_ed25519, verify_ed25519, get_ed25519_keys,
    build_canonical_payload, embed_clearance_in_png,
    extract_metadata_from_file, verify_asset_clearance,
    compute_file_sha256, LEGAL_NOTICE
)

User = get_user_model()


class Phase5HandoffCliFactsTestCase(TestCase):
    """
    Automated tests for Phase 5:
    1. HMAC-SHA256 & Ed25519 signing, verification, and tamper detection.
    2. PNG & ISO XMP metadata embedding and extraction.
    3. brandguard_cli.py verify command execution.
    4. Telemetry dashboard with Friction Score (minimum trigger count filter).
    5. Fact Ledger with expiry status alerts, blast radius, and bulk re-audit.
    """

    def setUp(self):
        self.client = Client()

        # Seed profile
        self.profile = BrandProfile.objects.create(
            org_name="NovaPay",
            allowed_hex_palette=[{"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0}],
            allowed_fonts=["Inter"]
        )

        # Admin user
        self.admin = User.objects.create_user(
            username="admin_p5",
            email="admin5@novapay.io",
            password="adminpassword123",
            role="ADMIN",
            brand_profile=self.profile
        )
        self.admin_token = generate_user_token(self.admin)

        # Content Writer user
        self.writer = User.objects.create_user(
            username="writer_p5",
            email="writer5@novapay.io",
            password="writerpassword123",
            role="CONTENT_WRITER",
            brand_profile=self.profile
        )
        self.writer_token = generate_user_token(self.writer)

        # Create temporary test image
        self.test_img_path = Path(settings.MEDIA_ROOT) / "test_p5_banner.png"
        self.test_img_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new('RGB', (200, 100), color='#0A3423')
        img.save(self.test_img_path, format="PNG")

        self.signed_img_path = Path(settings.MEDIA_ROOT) / "signed_p5_banner.png"

    def tearDown(self):
        for p in [self.test_img_path, self.signed_img_path]:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

    def test_hmac_and_ed25519_cryptographic_signatures(self):
        """Verifies HMAC-SHA256 and Ed25519 signatures, payload validation, and tamper detection."""
        file_hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        draft_id = "DRAFT_TEST_01"
        ruleset_ver = "v3.2"
        approver = "Jordan Lee"
        ts_iso = "2026-10-25T05:00:00Z"

        payload = build_canonical_payload(file_hash, draft_id, ruleset_ver, approver, ts_iso)

        # HMAC-SHA256
        hmac_sig = sign_hmac_sha256(payload)
        self.assertTrue(verify_hmac_sha256(payload, hmac_sig))
        self.assertFalse(verify_hmac_sha256(payload + "_tampered", hmac_sig))

        # Ed25519
        _, _, ed25519_pub = get_ed25519_keys()
        ed25519_sig = sign_ed25519(payload)
        self.assertTrue(verify_ed25519(payload, ed25519_sig, ed25519_pub))
        self.assertFalse(verify_ed25519(payload + "_tampered", ed25519_sig, ed25519_pub))

    def test_png_metadata_and_xmp_embedding(self):
        """Embeds HMAC, Ed25519, and XMP metadata in PNG, then extracts and verifies."""
        file_hash = compute_file_sha256(self.test_img_path)
        draft_id = "DRAFT_TEST_02"
        ruleset_ver = "v3.2"
        approver = "Jordan Lee"
        ts_iso = "2026-10-25T05:00:00Z"

        payload = build_canonical_payload(file_hash, draft_id, ruleset_ver, approver, ts_iso)
        hmac_sig = sign_hmac_sha256(payload)
        _, _, ed25519_pub = get_ed25519_keys()
        ed25519_sig = sign_ed25519(payload)
        clearance_hash = f"SHA256-{hmac_sig[:32]}"

        embed_clearance_in_png(
            source_path=self.test_img_path,
            out_path=self.signed_img_path,
            clearance_hash=clearance_hash,
            hmac_sig=hmac_sig,
            ed25519_sig=ed25519_sig,
            ed25519_pub=ed25519_pub,
            canonical_payload=payload,
            draft_id=draft_id,
            ruleset_version=ruleset_ver,
            approver=approver,
            timestamp_iso=ts_iso
        )

        self.assertTrue(self.signed_img_path.exists())

        # Verify extraction
        extracted = extract_metadata_from_file(self.signed_img_path)
        self.assertEqual(extracted["clearance_hash"], clearance_hash)
        self.assertEqual(extracted["hmac_signature"], hmac_sig)
        self.assertEqual(extracted["ed25519_signature"], ed25519_sig)
        self.assertTrue(extracted["has_xmp"])
        self.assertEqual(extracted["legal_notice"], LEGAL_NOTICE)

        # Full clearance verification
        ver_res = verify_asset_clearance(self.signed_img_path)
        self.assertTrue(ver_res["verified"])
        self.assertEqual(ver_res["status"], "PASS")
        self.assertEqual(ver_res["compliance_status"], "BRAND_COMPLIANCE_CLEARED")

    def test_brandguard_cli_verify_command(self):
        """Executes brandguard_cli.py verify command via subprocess to ensure CLI works end-to-end."""
        file_hash = compute_file_sha256(self.test_img_path)
        payload = build_canonical_payload(file_hash, "CLI_DRAFT", "v3.2", "Jordan Lee", "2026-10-25T05:00:00Z")
        hmac_sig = sign_hmac_sha256(payload)
        _, _, ed25519_pub = get_ed25519_keys()
        ed25519_sig = sign_ed25519(payload)

        embed_clearance_in_png(
            source_path=self.test_img_path,
            out_path=self.signed_img_path,
            clearance_hash=f"SHA256-{hmac_sig[:32]}",
            hmac_sig=hmac_sig,
            ed25519_sig=ed25519_sig,
            ed25519_pub=ed25519_pub,
            canonical_payload=payload,
            draft_id="CLI_DRAFT",
            ruleset_version="v3.2",
            approver="Jordan Lee",
            timestamp_iso="2026-10-25T05:00:00Z"
        )

        cli_path = Path(__file__).resolve().parent.parent.parent / "brandguard_cli.py"

        # 1. Verify signed file -> exit code 0
        cmd_pass = [sys.executable, str(cli_path), "verify", str(self.signed_img_path)]
        res_pass = subprocess.run(cmd_pass, capture_output=True, text=True)
        self.assertEqual(res_pass.returncode, 0, f"CLI verify failed: {res_pass.stderr}")
        self.assertIn("BRAND-COMPLIANCE CLEARED", res_pass.stdout)

        # 2. Verify unsigned file -> exit code 1
        cmd_fail = [sys.executable, str(cli_path), "verify", str(self.test_img_path)]
        res_fail = subprocess.run(cmd_fail, capture_output=True, text=True)
        self.assertEqual(res_fail.returncode, 1)
        self.assertIn("VERIFICATION FAILED", res_fail.stdout)

    def test_telemetry_friction_score_and_min_triggers(self):
        """Tests telemetry endpoint with Friction Score calculation and minimum trigger count filter."""
        from governance.models import AuditEvent, BrandRule
        rule_high = BrandRule.objects.create(profile=self.profile, rule_code="P5_HIGH", title="High Triggers", pillar="TONE", severity="WARNING")
        rule_low = BrandRule.objects.create(profile=self.profile, rule_code="P5_LOW", title="Low Triggers", pillar="TONE", severity="WARNING")

        for _ in range(55):
            AuditEvent.objects.create(profile=self.profile, user=self.writer, event_type="RULE_VIOLATED", rule_code="P5_HIGH", severity="WARNING")
        for _ in range(10):
            AuditEvent.objects.create(profile=self.profile, user=self.writer, event_type="RULE_VIOLATED", rule_code="P5_LOW", severity="WARNING")

        headers = {'HTTP_AUTHORIZATION': f'Bearer {self.admin_token}'}

        # Test with min_triggers=5
        res_5 = self.client.get('/api/telemetry/?min_triggers=5', **headers)
        self.assertEqual(res_5.status_code, 200)
        data_5 = res_5.json()
        self.assertEqual(data_5["min_triggers"], 5)
        self.assertIn("friction_leaderboard", data_5)
        self.assertIn("overall_friction_index", data_5)

        # Test with min_triggers=50 (should filter out low-trigger rules)
        res_50 = self.client.get('/api/telemetry/?min_triggers=50', **headers)
        self.assertEqual(res_50.status_code, 200)
        data_50 = res_50.json()
        self.assertEqual(data_50["min_triggers"], 50)
        for item in data_50["friction_leaderboard"]:
            self.assertGreaterEqual(item["findings"], 50)
            self.assertIn("friction_score", item)
            self.assertIn("friction_level", item)

    def test_fact_ledger_blast_radius_and_bulk_re_audit(self):
        """Tests Fact Ledger listing, blast radius calculation, and bulk re-audit execution."""
        today_d = date.today()

        # Create expired fact
        fact = FactLedger.objects.create(
            profile=self.profile,
            fact_code="FACT_TEST_APY",
            category="Interest Rate",
            claim_truth="Guaranteed 4.8% floating APY on treasury deposits.",
            last_verified=today_d - timedelta(days=60),
            valid_until=today_d - timedelta(days=5),  # Expired
            superseded_by_text="Adjusted to 4.2% floating APY."
        )

        # Create submission citing this fact
        sub = Submission.objects.create(
            profile=self.profile,
            author=self.writer,
            title="Q3 High Yield Campaign Banner",
            channel_context="LINKEDIN_POST",
            status="APPROVED"
        )
        ver = SubmissionVersion.objects.create(
            submission=sub,
            version_number=1,
            raw_text="Earn guaranteed 4.8% floating APY on enterprise treasury deposits with NovaPay.",
            compliance_score=94.0
        )

        # 1. Check GET /api/facts/
        res_facts = self.client.get('/api/facts/')
        self.assertEqual(res_facts.status_code, 200)
        facts_data = res_facts.json()
        self.assertGreaterEqual(facts_data["expired_count"], 1)

        # 2. Check blast radius
        res_blast = self.client.get(
            f'/api/facts/{fact.id}/blast-radius/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_blast.status_code, 200)
        blast_data = res_blast.json()
        self.assertGreaterEqual(blast_data["blast_radius_count"], 1)
        self.assertEqual(blast_data["affected_submissions"][0]["title"], sub.title)

        # 3. Execute bulk re-audit
        res_audit = self.client.post(
            f'/api/facts/{fact.id}/bulk-re-audit/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_audit.status_code, 200)
        audit_data = res_audit.json()
        self.assertGreaterEqual(audit_data["flagged_count"], 1)

        # Verify submission status transitioned to STALE_REAUDIT_REQUIRED
        sub.refresh_from_db()
        self.assertEqual(sub.status, "STALE_REAUDIT_REQUIRED")

        # Verify writer received notification
        notif = Notification.objects.filter(recipient=self.writer, notification_type="FACT_EXPIRING").first()
        self.assertIsNotNone(notif)
        self.assertIn("FACT_TEST_APY", notif.message)
