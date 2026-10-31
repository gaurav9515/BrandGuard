"""
Test Suite for Module 2: Codebase-to-Claim Ground-Truth Verifier.
Validates:
1. SSRF and Path Traversal URL validation
2. Encrypted Token storage & non-exposure
3. AST Python & Config constants extraction (parse-only, never executes code)
4. Admin-editable mapping table & unit normalization
5. ProposedFactChange creation (never auto-overwrites facts)
6. Admin approval workflow (requires admin-chosen valid_until)
7. Audit-time conflict citation (hard blocker citing code location for admin, "Verified against product code" for writer)
8. Role-based security (Content Writers get HTTP 403 on all admin repo endpoints)
9. HMAC-SHA256 GitHub webhook verification
10. Async job status tracking via /api/jobs/<job_id>/
"""

import os
import hmac
import json
import hashlib
import tempfile
from datetime import date, timedelta
from django.test import TestCase, Client
from django.utils import timezone
from governance.models import (
    BrandGuardUser, BrandProfile, FactLedger, BrandRule,
    CodebaseRepo, CodeSymbolMapping, CodebaseConstant,
    ProposedFactChange, AuditEvent, Job
)
from governance.auth import generate_user_token
from governance.engines.codebase_extractor import (
    validate_repo_url, ASTConstantExtractor, ConfigConstantExtractor,
    scan_directory, run_repo_scan
)


class Module2CodebaseVerifierTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Organization Profile
        self.profile = BrandProfile.objects.create(
            org_name="NovaPay Financial",
            allowed_hex_palette=[{"name": "Nova Green", "hex": "#0A3423", "max_delta_e": 4.0}]
        )

        # 2. Create Admin and Writer Users
        self.admin = BrandGuardUser.objects.create_user(
            username='admin_lead',
            email='admin@novapay.io',
            password='Password123!',
            role='ADMIN',
            brand_profile=self.profile
        )
        self.writer = BrandGuardUser.objects.create_user(
            username='writer_jordan',
            email='writer@novapay.io',
            password='Password123!',
            role='CONTENT_WRITER',
            brand_profile=self.profile
        )

        self.admin_token = generate_user_token(self.admin)
        self.writer_token = generate_user_token(self.writer)

        # 3. Seed FactLedger fact (FACT_012: 0.5% FX Fee)
        self.fact_012 = FactLedger.objects.create(
            profile=self.profile,
            fact_code="FACT_012",
            category="Pricing & Fees",
            claim_truth="transparent 24-hour global transfers with low 0.5% FX rates",
            last_verified=date.today() - timedelta(days=30),
            valid_until=date.today() + timedelta(days=180),
            is_verified=True,
            source="NovaPay Product Fact Ledger"
        )

        # 4. Seed CodebaseRepo
        self.repo = CodebaseRepo.objects.create(
            profile=self.profile,
            repo_name="novapay/core-banking",
            repo_url="https://github.com/novapay/core-banking",
            branch="main",
            webhook_secret="super_secret_webhook_key_123"
        )
        self.repo.set_auth_token("ghp_test_secret_read_only_token_abc")
        self.repo.save()

        # 5. Seed CodeSymbolMapping for FACT_012
        self.mapping = CodeSymbolMapping.objects.create(
            profile=self.profile,
            symbol_name="DEFAULT_FX_FEE",
            semantic_key="fx_fee_rate",
            target_fact=self.fact_012,
            unit_type="PERCENTAGE",
            scale_factor=100.0,
            display_format="{value}%",
            confidence_weight=1.0,
            is_active=True
        )

    # --------------------------------------------------------------------------
    # 1. SSRF & URL Validation
    # --------------------------------------------------------------------------
    def test_ssrf_and_url_validation(self):
        # Localhost / loopback must be rejected
        with self.assertRaises(ValueError):
            validate_repo_url("http://127.0.0.1:8000/repo.git")
        with self.assertRaises(ValueError):
            validate_repo_url("http://localhost/repo")
        with self.assertRaises(ValueError):
            validate_repo_url("file:///etc/passwd")

        # Valid GitHub HTTPS and SSH URLs must pass
        self.assertTrue(validate_repo_url("https://github.com/novapay/core-banking"))
        self.assertTrue(validate_repo_url("https://gitlab.com/novapay/billing.git"))
        self.assertTrue(validate_repo_url("git@github.com:novapay/core-banking.git"))

    # --------------------------------------------------------------------------
    # 2. Encrypted Token Storage & Masking
    # --------------------------------------------------------------------------
    def test_encrypted_token_storage_and_masking(self):
        self.repo.refresh_from_db()
        raw_token_bytes = bytes(self.repo.auth_token_encrypted)
        # Stored token must NOT match raw plaintext
        self.assertNotEqual(raw_token_bytes, b"ghp_test_secret_read_only_token_abc")
        # Decryption method returns original token
        self.assertEqual(self.repo.get_auth_token(), "ghp_test_secret_read_only_token_abc")

        # API serialization must NEVER expose the token string
        d = self.repo.to_dict()
        self.assertTrue(d['has_token'])
        self.assertNotIn('auth_token', d)
        self.assertNotIn('token', d)

    # --------------------------------------------------------------------------
    # 3. AST Python & Config Constant Extraction (Parse Only)
    # --------------------------------------------------------------------------
    def test_ast_python_extraction_without_execution(self):
        py_code = """
# Payment constants configuration
DEFAULT_FX_FEE = 0.008
SETTLEMENT_HOURS: int = 24
CROSS_BORDER_RAILS = ["SWIFT", "SEPA", "FEDNOW"]

class PaymentConfig:
    MAX_DAILY_TRANSFER = 250000

CONFIG_DICT = {
    'FEE_TIER_PREMIUM': 0.002,
}
"""
        extracted = ASTConstantExtractor.parse_python_source(py_code, "src/payments/constants.py")
        by_name = {x['symbol_name']: x for x in extracted}

        self.assertIn('DEFAULT_FX_FEE', by_name)
        self.assertEqual(by_name['DEFAULT_FX_FEE']['raw_value'], '0.008')
        self.assertEqual(by_name['DEFAULT_FX_FEE']['file_path'], 'src/payments/constants.py')

        self.assertIn('SETTLEMENT_HOURS', by_name)
        self.assertEqual(by_name['SETTLEMENT_HOURS']['raw_value'], '24')

        self.assertIn('MAX_DAILY_TRANSFER', by_name)
        self.assertEqual(by_name['MAX_DAILY_TRANSFER']['raw_value'], '250000')

        self.assertIn('FEE_TIER_PREMIUM', by_name)
        self.assertEqual(by_name['FEE_TIER_PREMIUM']['raw_value'], '0.002')

    def test_config_extraction_env_yaml_json_toml(self):
        env_content = "DEFAULT_FX_FEE=0.008\nAPI_PORT=8080\n"
        env_items = ConfigConstantExtractor.parse_env_file(env_content, ".env.example")
        self.assertEqual(len(env_items), 2)
        self.assertEqual(env_items[0]['symbol_name'], 'DEFAULT_FX_FEE')
        self.assertEqual(env_items[0]['raw_value'], '0.008')

        json_content = json.dumps({"DEFAULT_FX_FEE": "0.008", "ACTIVE_GATEWAY": "STRIPE"})
        json_items = ConfigConstantExtractor.parse_json_file(json_content, "config.json")
        self.assertEqual(len(json_items), 2)

    # --------------------------------------------------------------------------
    # 4. Admin-Editable Mapping Table & Unit Scaling
    # --------------------------------------------------------------------------
    def test_mapping_table_unit_normalization(self):
        # 0.008 * 100.0 with {value}% format -> "0.8%"
        self.assertEqual(self.mapping.normalize_value("0.008"), "0.8%")
        # 0.005 * 100.0 -> "0.5%"
        self.assertEqual(self.mapping.normalize_value("0.005"), "0.5%")

        # Test hours mapping
        hours_mapping = CodeSymbolMapping.objects.create(
            profile=self.profile,
            symbol_name="SETTLEMENT_HOURS",
            semantic_key="settlement_window",
            unit_type="HOURS",
            scale_factor=1.0,
            display_format="{value} hours"
        )
        self.assertEqual(hours_mapping.normalize_value("24"), "24 hours")

    # --------------------------------------------------------------------------
    # 5. Repo Scan & Proposed Fact Change Creation (Never Overwrites Directly)
    # --------------------------------------------------------------------------
    def test_repo_scan_creates_proposed_fact_change(self):
        # Create a sandbox directory with fixture code having DEFAULT_FX_FEE = 0.008 (updated from 0.005)
        with tempfile.TemporaryDirectory() as temp_dir:
            src_dir = os.path.join(temp_dir, "src", "payments")
            os.makedirs(src_dir, exist_ok=True)
            constants_file = os.path.join(src_dir, "constants.py")
            with open(constants_file, "w") as f:
                f.write("# Updated product fee\nDEFAULT_FX_FEE = 0.008\n")

            # Run scan synchronously
            res = run_repo_scan(
                repo_id=self.repo.id,
                commit_sha="c0ffee1234567890",
                sandbox_dir=temp_dir
            )

            self.assertEqual(res['constants_extracted'], 1)
            self.assertEqual(res['proposed_changes_count'], 1)

            # Check that CodebaseConstant was recorded
            const = CodebaseConstant.objects.filter(repo=self.repo, symbol_name="DEFAULT_FX_FEE").first()
            self.assertIsNotNone(const)
            self.assertEqual(const.raw_value, "0.008")
            self.assertEqual(const.normalized_value, "0.8%")
            self.assertEqual(const.commit_sha, "c0ffee1234567890")

            # CRITICAL RULE: FactLedger must NOT be overwritten directly!
            self.fact_012.refresh_from_db()
            self.assertIn("0.5%", self.fact_012.claim_truth)
            self.assertNotIn("0.8%", self.fact_012.claim_truth)

            # ProposedFactChange must be created in PENDING status
            proposed = ProposedFactChange.objects.filter(profile=self.profile, fact=self.fact_012).first()
            self.assertIsNotNone(proposed)
            self.assertEqual(proposed.status, 'PENDING')
            self.assertEqual(proposed.new_value, '0.8%')
            self.assertIn('0.5%', proposed.old_value)
            self.assertIn('constants.py', proposed.code_location)

            # AuditEvent emitted
            self.assertTrue(AuditEvent.objects.filter(profile=self.profile, event_type='FACT_CHANGE_PROPOSED').exists())

    # --------------------------------------------------------------------------
    # 6. Admin Approval Workflow (Requires Admin-Chosen valid_until)
    # --------------------------------------------------------------------------
    def test_admin_approve_proposed_fact_change(self):
        # Setup pending change
        const = CodebaseConstant.objects.create(
            repo=self.repo,
            mapping=self.mapping,
            symbol_name="DEFAULT_FX_FEE",
            raw_value="0.008",
            normalized_value="0.8%",
            file_path="src/payments/constants.py",
            line_number=14,
            commit_sha="c0ffee123"
        )
        change = ProposedFactChange.objects.create(
            profile=self.profile,
            fact=self.fact_012,
            constant=const,
            old_value=self.fact_012.claim_truth,
            new_value="0.8%",
            code_location="src/payments/constants.py:14 @ commit c0ffee1",
            commit_sha="c0ffee123",
            status='PENDING'
        )

        # 1. Missing valid_until must fail
        res_fail = self.client.post(
            f'/api/codebase/proposed-changes/{change.id}/review/',
            data=json.dumps({"action": "APPROVE"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_fail.status_code, 400)
        self.assertIn("valid_until date is required", res_fail.json()['error'])

        # 2. Valid approval with admin-chosen valid_until
        target_valid_until = "2027-12-31"
        res = self.client.post(
            f'/api/codebase/proposed-changes/{change.id}/review/',
            data=json.dumps({
                "action": "APPROVE",
                "valid_until": target_valid_until
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res.status_code, 200)

        # Proposed change marked APPROVED
        change.refresh_from_db()
        self.assertEqual(change.status, 'APPROVED')
        self.assertEqual(str(change.valid_until), target_valid_until)

        # FactLedger now updated to new value with admin-chosen date
        self.fact_012.refresh_from_db()
        self.assertEqual(self.fact_012.claim_truth, "0.8%")
        self.assertEqual(str(self.fact_012.valid_until), target_valid_until)
        self.assertTrue(self.fact_012.is_verified)

        # AuditEvent emitted
        self.assertTrue(AuditEvent.objects.filter(profile=self.profile, event_type='FACT_CHANGE_APPROVED').exists())

    # --------------------------------------------------------------------------
    # 7. Audit-Time Conflict Citation (Hard Blocker + Dual View for Admin/Writer)
    # --------------------------------------------------------------------------
    def test_audit_claim_conflict_against_code_constant(self):
        # Setup constant with new fee 0.8%
        CodebaseConstant.objects.create(
            repo=self.repo,
            mapping=self.mapping,
            symbol_name="DEFAULT_FX_FEE",
            raw_value="0.008",
            normalized_value="0.8%",
            file_path="src/payments/constants.py",
            line_number=14,
            commit_sha="abc1234567"
        )

        # Draft marketing text claiming old 0.5% fee
        marketing_copy = "Enjoy lightning fast cross-border payments with a 0.5% FX fee."

        # Audit as Admin
        res_admin = self.client.post(
            '/api/submissions/audit/',
            data=json.dumps({
                "title": "Summer Campaign",
                "channel_context": "LINKEDIN_POST",
                "raw_text": marketing_copy
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_admin.status_code, 200)
        data_admin = res_admin.json()
        findings = data_admin['versions'][0]['findings']

        # Find the conflict finding
        conflict_finding = next((f for f in findings if f.get('rule_citation_code') == 'FACT_012'), None)
        self.assertIsNotNone(conflict_finding)
        self.assertEqual(conflict_finding['severity'], 'BLOCKER')

        # Admin sees exact code location in explanation
        self.assertIn("src/payments/constants.py:14", conflict_finding['explanation'])
        self.assertIn("commit abc1234", conflict_finding['explanation'])

        # Verify location_json code_verification metadata
        code_ver = conflict_finding['location_json']['code_verification']
        self.assertTrue(code_ver['is_code_verified'])
        self.assertEqual(code_ver['normalized_value'], '0.8%')
        self.assertEqual(code_ver['file_path'], 'src/payments/constants.py')

    # --------------------------------------------------------------------------
    # 8. Role-Based Access Control: Writers get HTTP 403 on Admin Repo Endpoints
    # --------------------------------------------------------------------------
    def test_writers_forbidden_on_all_repo_endpoints(self):
        # 1. Repo list
        r1 = self.client.get('/api/codebase/repos/', HTTP_AUTHORIZATION=f'Bearer {self.writer_token}')
        self.assertEqual(r1.status_code, 403)

        # 2. Connect repo
        r2 = self.client.post(
            '/api/codebase/repos/',
            data=json.dumps({"repo_name": "test", "repo_url": "https://github.com/org/repo"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(r2.status_code, 403)

        # 3. Trigger repo scan
        r3 = self.client.post(
            f'/api/codebase/repos/{self.repo.id}/scan/',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(r3.status_code, 403)

        # 4. Symbol mappings list & create
        r4 = self.client.get('/api/codebase/mappings/', HTTP_AUTHORIZATION=f'Bearer {self.writer_token}')
        self.assertEqual(r4.status_code, 403)
        r5 = self.client.post(
            '/api/codebase/mappings/',
            data=json.dumps({"symbol_name": "TEST", "semantic_key": "test"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(r5.status_code, 403)

        # 5. Proposed changes list & review
        r6 = self.client.get('/api/codebase/proposed-changes/', HTTP_AUTHORIZATION=f'Bearer {self.writer_token}')
        self.assertEqual(r6.status_code, 403)

    # --------------------------------------------------------------------------
    # 9. GitHub Webhook HMAC-SHA256 Verification
    # --------------------------------------------------------------------------
    def test_github_webhook_hmac_verification(self):
        payload = json.dumps({
            "ref": "refs/heads/main",
            "repository": {
                "html_url": "https://github.com/novapay/core-banking"
            }
        }).encode('utf-8')

        # 1. Valid HMAC signature
        valid_sig = hmac.new(b"super_secret_webhook_key_123", payload, hashlib.sha256).hexdigest()
        res_valid = self.client.post(
            f'/api/webhooks/github/?repo_id={self.repo.id}',
            data=payload,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=f'sha256={valid_sig}'
        )
        self.assertEqual(res_valid.status_code, 200)
        self.assertEqual(res_valid.json()['status'], 'success')
        self.assertIn('job_id', res_valid.json())

        # 2. Invalid / Tampered HMAC signature
        res_invalid = self.client.post(
            f'/api/webhooks/github/?repo_id={self.repo.id}',
            data=payload,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=bad_signature_1234567890'
        )
        self.assertEqual(res_invalid.status_code, 403)

    # --------------------------------------------------------------------------
    # 10. Async Job Status Tracking via GET /api/jobs/<job_id>/
    # --------------------------------------------------------------------------
    def test_job_status_tracking(self):
        job = Job.objects.create(
            profile=self.profile,
            user=self.admin,
            job_type='REPO_SCAN',
            status='RUNNING',
            progress=45,
            status_message='Scanning repository files...'
        )

        res = self.client.get(
            f'/api/jobs/{job.id}/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'RUNNING')
        self.assertEqual(data['progress'], 45)
        self.assertEqual(data['status_message'], 'Scanning repository files...')

