"""
Test Suite for Module 3: Dependency-Graph Blast Radius & Staleness Engine.
Validates:
1. Fact change approval triggers Blast Radius computation & marks assets STALE
2. Cryptographic compliance signature revocation (is_revoked=True, revoked_at, revocation_reason)
3. Blast radius channel breakdown, severity weighting (CRITICAL/HIGH/MEDIUM), and audience reach
4. Asset owner notification dispatch
5. Deterministic draft patch generation (diff preview)
6. 1-click batch patch application (POST /api/facts/<id>/apply-patches/) creating new versions
7. Writer finding patch resolution (clearing STALE_REAUDIT_REQUIRED)
8. Role-based security (Writers receive HTTP 403 on admin blast-radius endpoints)
9. Cross-tenant isolation (Org B assets excluded from Org A blast radius)
10. Async job tracking via /api/jobs/<job_id>/
"""

import json
from datetime import date, timedelta
from django.test import TestCase, Client
from django.utils import timezone
from governance.models import (
    BrandGuardUser, BrandProfile, FactLedger, Submission, SubmissionVersion,
    AuditFinding, BrandComplianceSignature, BlastRadiusReport,
    AuditEvent, Notification, CodebaseRepo, CodeSymbolMapping,
    CodebaseConstant, ProposedFactChange, Job
)
from governance.auth import generate_user_token
from governance.engines.blast_radius_engine import compute_blast_radius, apply_batch_patches


class Module3BlastRadiusTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Organization A Profile
        self.profile_a = BrandProfile.objects.create(
            org_name="NovaPay Financial",
            allowed_hex_palette=[{"name": "Nova Green", "hex": "#0A3423", "max_delta_e": 4.0}]
        )

        # 2. Organization B Profile (Cross-tenant check)
        self.profile_b = BrandProfile.objects.create(
            org_name="Apex Global",
            allowed_hex_palette=[{"name": "Apex Blue", "hex": "#003366", "max_delta_e": 4.0}]
        )

        # 3. Users
        self.admin = BrandGuardUser.objects.create_user(
            username='admin_lead',
            email='admin@novapay.io',
            password='Password123!',
            role='ADMIN',
            brand_profile=self.profile_a
        )
        self.writer = BrandGuardUser.objects.create_user(
            username='writer_jordan',
            email='writer@novapay.io',
            password='Password123!',
            role='CONTENT_WRITER',
            brand_profile=self.profile_a
        )
        self.admin_b = BrandGuardUser.objects.create_user(
            username='admin_apex',
            email='admin@apex.io',
            password='Password123!',
            role='ADMIN',
            brand_profile=self.profile_b
        )

        self.admin_token = generate_user_token(self.admin)
        self.writer_token = generate_user_token(self.writer)
        self.admin_b_token = generate_user_token(self.admin_b)

        # 4. Verified Fact in Org A
        self.fact_012 = FactLedger.objects.create(
            profile=self.profile_a,
            fact_code="FACT_012",
            category="Pricing & Fees",
            claim_truth="transparent 24-hour global transfers with low 0.5% FX rates",
            last_verified=date.today() - timedelta(days=30),
            valid_until=date.today() + timedelta(days=180),
            is_verified=True,
            source="NovaPay Product Fact Ledger"
        )

        # 5. Asset 1: Paid Ad (Approved, with cryptographic signature)
        self.sub_paid_ad = Submission.objects.create(
            profile=self.profile_a,
            author=self.writer,
            title="Q3 Paid Search Ad - Global Transfers",
            channel_context="PAID_ADS",
            status="APPROVED",
            clearance_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90",
            clearance_signature="sig_test_clearance_token_xyz",
            approved_by=self.admin,
            approved_at=timezone.now() - timedelta(days=2)
        )
        self.ver_ad = SubmissionVersion.objects.create(
            submission=self.sub_paid_ad,
            version_number=1,
            raw_text="Experience frictionless transfers with low 0.5% FX rates guaranteed worldwide.",
            file_type="TEXT",
            compliance_score=94.0
        )
        self.sig_ad = BrandComplianceSignature.objects.create(
            submission=self.sub_paid_ad,
            file_sha256="a1b2c3d4e5f60718293a4b5c6d7e8f90",
            draft_id=str(self.sub_paid_ad.id),
            ruleset_version="v1.0",
            approver_username=self.admin.username,
            timestamp=timezone.now(),
            hmac_signature="sig_test_hex_value_123456",
            is_revoked=False
        )

        # 6. Asset 2: Landing Page (In Review)
        self.sub_landing = Submission.objects.create(
            profile=self.profile_a,
            author=self.writer,
            title="Business Banking Landing Page",
            channel_context="LANDING_PAGE",
            status="IN_REVIEW"
        )
        self.ver_landing = SubmissionVersion.objects.create(
            submission=self.sub_landing,
            version_number=1,
            raw_text="NovaPay Business Banking offers enterprise routing and 0.5% FX transaction rates.",
            file_type="TEXT",
            compliance_score=88.0
        )

        # 7. Asset 3: Organic LinkedIn Post (Approved)
        self.sub_social = Submission.objects.create(
            profile=self.profile_a,
            author=self.writer,
            title="Founder Update on LinkedIn",
            channel_context="LINKEDIN_POST",
            status="APPROVED",
            clearance_hash="c3d4e5f6a1b2",
            clearance_signature="sig_social_token_abc"
        )
        self.ver_social = SubmissionVersion.objects.create(
            submission=self.sub_social,
            version_number=1,
            raw_text="We are thrilled to announce 24-hour transfers with competitive 0.5% rates across LATAM.",
            file_type="TEXT",
            compliance_score=98.0
        )
        self.sig_social = BrandComplianceSignature.objects.create(
            submission=self.sub_social,
            file_sha256="c3d4e5f6a1b2",
            draft_id=str(self.sub_social.id),
            ruleset_version="v1.0",
            approver_username=self.admin.username,
            timestamp=timezone.now(),
            hmac_signature="sig_social_hex_456789",
            is_revoked=False
        )

        # 8. Unrelated Asset in Org B
        self.sub_org_b = Submission.objects.create(
            profile=self.profile_b,
            author=self.admin_b,
            title="Apex Blue Card Promo",
            channel_context="PAID_ADS",
            status="APPROVED",
            clearance_hash="apex_hash_123",
            clearance_signature="apex_sig_456"
        )
        self.ver_b = SubmissionVersion.objects.create(
            submission=self.sub_org_b,
            version_number=1,
            raw_text="Enjoy 0.5% cashback on all travel expenses with Apex Blue.",
            file_type="TEXT",
            compliance_score=100.0
        )

    # --------------------------------------------------------------------------
    # 1. Direct Engine Computation: Invalidation & Signature Revocation
    # --------------------------------------------------------------------------
    def test_compute_blast_radius_invalidates_assets_and_revokes_signatures(self):
        result = compute_blast_radius(
            profile=self.profile_a,
            fact_id=self.fact_012.id,
            old_value="low 0.5% FX rates",
            new_value="0.8%",
            trigger_reason="MANUAL_SCAN"
        )

        self.assertEqual(result['affected_assets_count'], 3)
        self.assertEqual(result['severity'], 'CRITICAL')  # Contains PAID_ADS
        self.assertGreaterEqual(result['estimated_reach'], 70000)  # 50k (paid) + 15k (landing) + 5k (linkedin)

        # Verify asset statuses transitioned to STALE_REAUDIT_REQUIRED
        self.sub_paid_ad.refresh_from_db()
        self.sub_landing.refresh_from_db()
        self.sub_social.refresh_from_db()

        self.assertEqual(self.sub_paid_ad.status, 'STALE_REAUDIT_REQUIRED')
        self.assertEqual(self.sub_landing.status, 'STALE_REAUDIT_REQUIRED')
        self.assertEqual(self.sub_social.status, 'STALE_REAUDIT_REQUIRED')

        # Clearance tokens cleared on submission
        self.assertEqual(self.sub_paid_ad.clearance_hash, '')
        self.assertEqual(self.sub_paid_ad.clearance_signature, '')

        # Cryptographic signatures marked REVOKED
        self.sig_ad.refresh_from_db()
        self.sig_social.refresh_from_db()
        self.assertTrue(self.sig_ad.is_revoked)
        self.assertIsNotNone(self.sig_ad.revoked_at)
        self.assertIn("Truth changed for FACT_012", self.sig_ad.revocation_reason)
        self.assertTrue(self.sig_social.is_revoked)

        # In-app notifications created for writer
        notifications = Notification.objects.filter(recipient=self.writer)
        self.assertTrue(notifications.exists())
        self.assertTrue(any("FACT_012" in n.title for n in notifications))

        # BlastRadiusReport recorded in DB
        report = BlastRadiusReport.objects.filter(profile=self.profile_a, fact=self.fact_012).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.affected_assets_count, 3)
        self.assertEqual(report.severity, 'CRITICAL')
        self.assertIn('PAID_ADS', report.channel_breakdown)

        # Audit events emitted
        self.assertTrue(AuditEvent.objects.filter(profile=self.profile_a, event_type='BLAST_RADIUS_COMPUTED').exists())
        self.assertTrue(AuditEvent.objects.filter(profile=self.profile_a, event_type='ASSET_MARKED_STALE').exists())

    # --------------------------------------------------------------------------
    # 2. Codebase Approval Workflow triggers Module 3 Blast Radius
    # --------------------------------------------------------------------------
    def test_codebase_approval_triggers_blast_radius(self):
        repo = CodebaseRepo.objects.create(
            profile=self.profile_a,
            repo_name="novapay/backend",
            repo_url="https://github.com/novapay/backend",
            branch="main"
        )
        mapping = CodeSymbolMapping.objects.create(
            profile=self.profile_a,
            symbol_name="DEFAULT_FX_FEE",
            semantic_key="fx_fee_rate",
            target_fact=self.fact_012,
            unit_type="PERCENTAGE"
        )
        const = CodebaseConstant.objects.create(
            repo=repo,
            mapping=mapping,
            symbol_name="DEFAULT_FX_FEE",
            raw_value="0.008",
            normalized_value="0.8%",
            file_path="src/payments/constants.py",
            line_number=14,
            commit_sha="a98b76c"
        )
        change = ProposedFactChange.objects.create(
            profile=self.profile_a,
            fact=self.fact_012,
            constant=const,
            old_value=self.fact_012.claim_truth,
            new_value="0.8%",
            code_location="src/payments/constants.py:14 @ commit a98b76c",
            commit_sha="a98b76c",
            status='PENDING'
        )

        # Admin approves the proposed change
        res = self.client.post(
            f'/api/codebase/proposed-changes/{change.id}/review/',
            data=json.dumps({
                "action": "APPROVE",
                "valid_until": "2027-12-31"
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("blast_radius", data)
        self.assertEqual(data["blast_radius"]["affected_assets_count"], 3)
        self.assertEqual(data["blast_radius"]["severity"], "CRITICAL")

        # Confirm all 3 assets in profile A are now STALE_REAUDIT_REQUIRED
        self.sub_paid_ad.refresh_from_db()
        self.assertEqual(self.sub_paid_ad.status, 'STALE_REAUDIT_REQUIRED')

    # --------------------------------------------------------------------------
    # 3. Draft Patches and 1-Click Batch Patch Application (apply-patches)
    # --------------------------------------------------------------------------
    def test_batch_patch_application_creates_new_versions_and_reaudits(self):
        # 1. Compute blast radius first
        compute_blast_radius(
            profile=self.profile_a,
            fact_id=self.fact_012.id,
            old_value="low 0.5% FX rates",
            new_value="0.8%",
            trigger_reason="MANUAL_SCAN"
        )

        # Update fact claim_truth to 0.8%
        self.fact_012.claim_truth = "0.8%"
        self.fact_012.save()

        # 2. Call batch apply patches endpoint for all stale submissions
        res = self.client.post(
            f'/api/facts/{self.fact_012.id}/apply-patches/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["patched_count"], 3)

        # 3. Inspect updated submissions: version 2 created with patched copy
        self.sub_paid_ad.refresh_from_db()
        v2_ad = self.sub_paid_ad.versions.order_by('-version_number').first()
        self.assertEqual(v2_ad.version_number, 2)
        self.assertIn("0.8%", v2_ad.raw_text)
        self.assertNotIn("0.5%", v2_ad.raw_text)
        self.assertEqual(self.sub_paid_ad.status, 'IN_REVIEW')

        # FIX_ACCEPTED and SCAN events emitted
        self.assertTrue(AuditEvent.objects.filter(profile=self.profile_a, event_type='FIX_ACCEPTED').exists())
        self.assertTrue(AuditEvent.objects.filter(profile=self.profile_a, event_type='SCAN').exists())

    # --------------------------------------------------------------------------
    # 4. Selective Batch Patching (specific submission_ids)
    # --------------------------------------------------------------------------
    def test_selective_batch_patch_application(self):
        compute_blast_radius(
            profile=self.profile_a,
            fact_id=self.fact_012.id,
            old_value="low 0.5% FX rates",
            new_value="0.8%"
        )
        self.fact_012.claim_truth = "0.8%"
        self.fact_012.save()

        # Patch only sub_paid_ad
        res = self.client.post(
            f'/api/facts/{self.fact_012.id}/apply-patches/',
            data=json.dumps({"submission_ids": [str(self.sub_paid_ad.id)]}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["patched_count"], 1)

        # sub_paid_ad has v2
        self.sub_paid_ad.refresh_from_db()
        self.assertEqual(self.sub_paid_ad.versions.count(), 2)

        # sub_social remains STALE_REAUDIT_REQUIRED with only v1
        self.sub_social.refresh_from_db()
        self.assertEqual(self.sub_social.status, 'STALE_REAUDIT_REQUIRED')
        self.assertEqual(self.sub_social.versions.count(), 1)

    # --------------------------------------------------------------------------
    # 5. Writer Single-Asset Patch Resolution (/api/findings/<id>/resolve/)
    # --------------------------------------------------------------------------
    def test_writer_resolves_stale_finding_clears_stale_status(self):
        compute_blast_radius(
            profile=self.profile_a,
            fact_id=self.fact_012.id,
            old_value="low 0.5% FX rates",
            new_value="0.8%"
        )
        self.fact_012.claim_truth = "0.8%"
        self.fact_012.save()

        self.sub_landing.refresh_from_db()
        self.assertEqual(self.sub_landing.status, 'STALE_REAUDIT_REQUIRED')

        # Find the stale finding on landing page
        latest_ver = self.sub_landing.versions.first()
        stale_finding = latest_ver.findings.filter(rule_citation_code=self.fact_012.fact_code).first()
        self.assertIsNotNone(stale_finding)

        # Writer accepts patch
        res = self.client.post(
            f'/api/findings/{stale_finding.id}/resolve/',
            data=json.dumps({
                "action": "ACCEPT_FIX",
                "chosen_fix": "Replace with '0.8%'"
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(res.status_code, 200)

        # Asset should transition to IN_REVIEW with v2 created
        self.sub_landing.refresh_from_db()
        self.assertEqual(self.sub_landing.status, 'IN_REVIEW')
        v2 = self.sub_landing.versions.order_by('-version_number').first()
        self.assertEqual(v2.version_number, 2)
        self.assertIn("0.8%", v2.raw_text)

    # --------------------------------------------------------------------------
    # 6. Role-Based Permissions: Content Writers Forbidden (HTTP 403)
    # --------------------------------------------------------------------------
    def test_writer_forbidden_on_admin_blast_radius_endpoints(self):
        # 1. GET blast radius
        res_get = self.client.get(
            f'/api/facts/{self.fact_012.id}/blast-radius/',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(res_get.status_code, 403)
        self.assertIn("Admin privileges required", res_get.json().get('detail', ''))

        # 2. POST blast radius
        res_post = self.client.post(
            f'/api/facts/{self.fact_012.id}/blast-radius/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(res_post.status_code, 403)

        # 3. POST apply patches
        res_apply = self.client.post(
            f'/api/facts/{self.fact_012.id}/apply-patches/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(res_apply.status_code, 403)

    # --------------------------------------------------------------------------
    # 7. Cross-Tenant Isolation: Org B Assets Untouched
    # --------------------------------------------------------------------------
    def test_cross_tenant_isolation(self):
        compute_blast_radius(
            profile=self.profile_a,
            fact_id=self.fact_012.id,
            old_value="0.5%",
            new_value="0.8%"
        )

        # Org B submission mentioning 0.5% must remain APPROVED with untouched signature
        self.sub_org_b.refresh_from_db()
        self.assertEqual(self.sub_org_b.status, 'APPROVED')
        self.assertEqual(self.sub_org_b.clearance_hash, 'apex_hash_123')

        # Admin B requesting blast radius for fact_012 gets 404 (fact belongs to Org A)
        res_cross = self.client.get(
            f'/api/facts/{self.fact_012.id}/blast-radius/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_b_token}'
        )
        self.assertEqual(res_cross.status_code, 404)

    # --------------------------------------------------------------------------
    # 8. Async Job Runner via /api/jobs/<job_id>/
    # --------------------------------------------------------------------------
    def test_async_blast_radius_job_execution(self):
        res = self.client.post(
            f'/api/facts/{self.fact_012.id}/blast-radius/',
            data=json.dumps({"run_async": True}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res.status_code, 202)
        job_id = res.json()["job_id"]

        # Poll job status
        res_job = self.client.get(
            f'/api/jobs/{job_id}/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_job.status_code, 200)
        job_data = res_job.json()
        self.assertEqual(job_data["status"], "SUCCESS")
        self.assertEqual(job_data["progress"], 100)
        self.assertIn("affected_assets_count", job_data["result"])
        self.assertEqual(job_data["result"]["affected_assets_count"], 3)
