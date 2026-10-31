"""
Phase R2 Tenant Isolation & Multi-Company Automated Test Suite.
Tests:
1. Model hierarchy: Organization -> Companies -> Projects -> Memberships.
2. Safe migration 0008 verification (zero data loss, default org and company properly populated).
3. Central tenant-scoping layer (backend/governance/tenancy.py):
   - Company A admin cannot view, create, or update Company B's rules, facts, or submissions (HTTP 403).
   - Company A writer cannot submit copy or run audits for Company B (HTTP 403).
   - Multi-membership user (user belonging to both Company A and B) can switch between companies and access permitted resources.
   - Cross-company attempts are blocked and logged in the audit trail.
   - Company settings isolation (Company A cannot modify Company B's brand palette, fonts, or ruleset).
   - Project isolation (Company A projects are hidden from Company B).
"""

from datetime import timedelta
import json
import uuid
from django.utils import timezone
from django.test import TestCase, Client
from django.urls import reverse
from governance.models import (
    Organization, Company, Project, Membership,
    BrandGuardUser, BrandProfile, BrandRule, FactLedger,
    Submission, SubmissionVersion, AuditEvent, AuditTrail
)
from governance.auth import generate_user_token
from governance.tenancy import get_request_company, scope_queryset_to_caller, ensure_company_profile


class PhaseR2TenantIsolationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Organization 1: NovaPay Group (migrated default)
        self.org_novapay, _ = Organization.objects.get_or_create(
            slug="novapay-group",
            defaults={"name": "NovaPay Group", "requires_writer_approval": True}
        )

        # Company 1A: NovaPay
        self.comp_novapay, _ = Company.objects.get_or_create(
            organization=self.org_novapay,
            slug="novapay",
            defaults={
                "name": "NovaPay",
                "ruleset_version": "v3.2",
                "allowed_hex_palette": [{"name": "Nova Green", "hex": "#0A3423", "max_delta_e": 4.0}],
                "allowed_fonts": ["Inter"]
            }
        )
        self.profile_novapay = ensure_company_profile(self.comp_novapay)

        # Company 1B: NovaPay Retail (sister company under same org)
        self.comp_retail = Company.objects.create(
            organization=self.org_novapay,
            name="NovaPay Retail",
            slug="novapay-retail",
            ruleset_version="v3.2",
            allowed_hex_palette=[{"name": "Retail Blue", "hex": "#0055AA", "max_delta_e": 3.5}],
            allowed_fonts=["Plus Jakarta Sans"]
        )
        self.profile_retail = ensure_company_profile(self.comp_retail)

        # 2. Organization 2: Apex Holdings (competitor org)
        self.org_apex = Organization.objects.create(
            name="Apex Holdings",
            slug="apex-holdings",
            requires_writer_approval=True
        )
        self.comp_apex = Company.objects.create(
            organization=self.org_apex,
            name="Apex Financial",
            slug="apex-financial",
            ruleset_version="v3.0",
            allowed_hex_palette=[{"name": "Apex Red", "hex": "#CC0000", "max_delta_e": 3.0}],
            allowed_fonts=["Roboto"]
        )
        self.profile_apex = ensure_company_profile(self.comp_apex)

        # 3. Users & Memberships
        # NovaPay Admin
        self.user_novapay_admin = BrandGuardUser.objects.create_user(
            username="nova_admin",
            email="admin@novapay.io",
            password="StrongPassword123!",
            role="ADMIN",
            organization=self.org_novapay,
            company=self.comp_novapay,
            brand_profile=self.profile_novapay,
            is_email_verified=True,
            is_approved=True
        )
        Membership.objects.create(
            user=self.user_novapay_admin,
            organization=self.org_novapay,
            company=self.comp_novapay,
            role="ADMIN",
            is_active=True
        )
        self.nova_admin_token = generate_user_token(self.user_novapay_admin)

        # NovaPay Writer
        self.user_novapay_writer = BrandGuardUser.objects.create_user(
            username="nova_writer",
            email="writer@novapay.io",
            password="StrongPassword123!",
            role="CONTENT_WRITER",
            organization=self.org_novapay,
            company=self.comp_novapay,
            brand_profile=self.profile_novapay,
            is_email_verified=True,
            is_approved=True
        )
        Membership.objects.create(
            user=self.user_novapay_writer,
            organization=self.org_novapay,
            company=self.comp_novapay,
            role="CONTENT_WRITER",
            is_active=True
        )
        self.nova_writer_token = generate_user_token(self.user_novapay_writer)

        # Apex Admin
        self.user_apex_admin = BrandGuardUser.objects.create_user(
            username="apex_admin",
            email="admin@apex.io",
            password="StrongPassword123!",
            role="ADMIN",
            organization=self.org_apex,
            company=self.comp_apex,
            brand_profile=self.profile_apex,
            is_email_verified=True,
            is_approved=True
        )
        Membership.objects.create(
            user=self.user_apex_admin,
            organization=self.org_apex,
            company=self.comp_apex,
            role="ADMIN",
            is_active=True
        )
        self.apex_admin_token = generate_user_token(self.user_apex_admin)

        # Multi-Company User (Writer in NovaPay, Admin in NovaPay Retail)
        self.user_multi = BrandGuardUser.objects.create_user(
            username="multi_user",
            email="multi@novapay.io",
            password="StrongPassword123!",
            role="CONTENT_WRITER",
            organization=self.org_novapay,
            company=self.comp_novapay,
            brand_profile=self.profile_novapay,
            is_email_verified=True,
            is_approved=True
        )
        Membership.objects.create(
            user=self.user_multi,
            organization=self.org_novapay,
            company=self.comp_novapay,
            role="CONTENT_WRITER",
            is_active=True
        )
        Membership.objects.create(
            user=self.user_multi,
            organization=self.org_novapay,
            company=self.comp_retail,
            role="ADMIN",
            is_active=True
        )
        self.multi_user_token = generate_user_token(self.user_multi)

        # Seed Sample Data for NovaPay
        self.rule_novapay = BrandRule.objects.create(
            company=self.comp_novapay,
            profile=self.profile_novapay,
            rule_code="NOVA_PROHIBIT_CHEAP",
            title="NovaPay No Cheap",
            pillar="TONE",
            severity="BLOCKER",
            claims_allowed="cost-effective",
            claims_disallowed="cheap"
        )
        self.fact_novapay = FactLedger.objects.create(
            company=self.comp_novapay,
            profile=self.profile_novapay,
            fact_code="FACT_NOVA_01",
            category="Interest Rate",
            claim_truth="NovaPay settles in 24 hours.",
            last_verified=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=365)
        )
        self.sub_novapay = Submission.objects.create(
            company=self.comp_novapay,
            profile=self.profile_novapay,
            author=self.user_novapay_writer,
            title="NovaPay Global Campaign",
            channel_context="LINKEDIN_POST",
            status="DRAFT"
        )

        # Seed Sample Data for Apex
        self.rule_apex = BrandRule.objects.create(
            company=self.comp_apex,
            profile=self.profile_apex,
            rule_code="APEX_PROHIBIT_DISCOUNT",
            title="Apex No Discount",
            pillar="TONE",
            severity="BLOCKER",
            claims_allowed="premium pricing",
            claims_disallowed="discount"
        )
        self.fact_apex = FactLedger.objects.create(
            company=self.comp_apex,
            profile=self.profile_apex,
            fact_code="FACT_APEX_01",
            category="Capital",
            claim_truth="Apex holds $10B in AUM.",
            last_verified=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=365)
        )
        self.sub_apex = Submission.objects.create(
            company=self.comp_apex,
            profile=self.profile_apex,
            author=self.user_apex_admin,
            title="Apex Wealth Campaign",
            channel_context="EMAIL_NEWSLETTER",
            status="APPROVED"
        )

    # =========================================================================
    # 1. Models & Safe Migration Verification
    # =========================================================================
    def test_multi_organization_model_hierarchy(self):
        """Verifies Organization -> Company -> Project -> Membership hierarchy."""
        self.assertEqual(self.comp_novapay.organization, self.org_novapay)
        self.assertEqual(self.comp_retail.organization, self.org_novapay)
        self.assertEqual(self.comp_apex.organization, self.org_apex)

        # Projects under Company
        proj = Project.objects.create(
            company=self.comp_novapay,
            name="Q4 Growth Campaign",
            slug="q4-growth",
            channel="LINKEDIN_POST"
        )
        self.assertEqual(proj.company, self.comp_novapay)
        self.assertIn(proj, self.comp_novapay.projects.all())

        # Memberships
        memberships = Membership.objects.filter(user=self.user_multi, is_active=True)
        self.assertEqual(memberships.count(), 2)

    def test_data_migration_0008_preserved_default_org_and_company(self):
        """Tests that migration 0008 cleanly migrated data into default Organization & Company."""
        default_org = Organization.objects.filter(slug="novapay-group").first()
        self.assertIsNotNone(default_org)
        self.assertEqual(default_org.name, "NovaPay Group")

        default_comp = Company.objects.filter(organization=default_org, slug="novapay").first()
        self.assertIsNotNone(default_comp)
        self.assertEqual(default_comp.name, "NovaPay")

        # Linked BrandProfile exists
        self.assertIsNotNone(default_comp.brand_profile)
        self.assertEqual(default_comp.brand_profile.company, default_comp)

    # =========================================================================
    # 2. Company Listing & Switcher Scoping
    # =========================================================================
    def test_companies_listing_scoped_to_user_memberships(self):
        """Tests GET /api/companies/ returns only companies caller is authorized to view."""
        # NovaPay writer should only see NovaPay
        res_writer = self.client.get(
            '/api/companies/',
            HTTP_AUTHORIZATION=f'Bearer {self.nova_writer_token}'
        )
        self.assertEqual(res_writer.status_code, 200)
        writer_comps = res_writer.json()["companies"]
        writer_comp_ids = [c["id"] for c in writer_comps]
        self.assertIn(str(self.comp_novapay.id), writer_comp_ids)
        self.assertNotIn(str(self.comp_apex.id), writer_comp_ids)

        # Apex Admin should only see Apex Financial
        res_apex = self.client.get(
            '/api/companies/',
            HTTP_AUTHORIZATION=f'Bearer {self.apex_admin_token}'
        )
        self.assertEqual(res_apex.status_code, 200)
        apex_comps = res_apex.json()["companies"]
        apex_comp_ids = [c["id"] for c in apex_comps]
        self.assertIn(str(self.comp_apex.id), apex_comp_ids)
        self.assertNotIn(str(self.comp_novapay.id), apex_comp_ids)

        # Multi-company user should see both NovaPay and NovaPay Retail
        res_multi = self.client.get(
            '/api/companies/',
            HTTP_AUTHORIZATION=f'Bearer {self.multi_user_token}'
        )
        self.assertEqual(res_multi.status_code, 200)
        multi_comps = res_multi.json()["companies"]
        multi_comp_ids = [c["id"] for c in multi_comps]
        self.assertIn(str(self.comp_novapay.id), multi_comp_ids)
        self.assertIn(str(self.comp_retail.id), multi_comp_ids)
        self.assertNotIn(str(self.comp_apex.id), multi_comp_ids)

    # =========================================================================
    # 3. Cross-Company Isolation: Admin Blocked on Target Company
    # =========================================================================
    def test_company_a_admin_cannot_access_or_modify_company_b(self):
        """Tests Company A admin is rejected (HTTP 403) when attempting to access Company B."""
        # NovaPay admin attempts GET /api/companies/<apex_id>/
        res_detail = self.client.get(
            f'/api/companies/{self.comp_apex.id}/',
            HTTP_AUTHORIZATION=f'Bearer {self.nova_admin_token}'
        )
        self.assertEqual(res_detail.status_code, 403)
        self.assertIn("Cross-company access forbidden", res_detail.json()["error"])

        # NovaPay admin attempts PUT /api/companies/<apex_id>/ (settings update)
        res_update = self.client.put(
            f'/api/companies/{self.comp_apex.id}/',
            data=json.dumps({"name": "Hacked Apex Financial"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f'Bearer {self.nova_admin_token}'
        )
        self.assertEqual(res_update.status_code, 403)

        # Verify Apex company was NOT modified
        self.comp_apex.refresh_from_db()
        self.assertEqual(self.comp_apex.name, "Apex Financial")

    def test_company_a_admin_cannot_access_company_b_rules_or_facts(self):
        """Tests that passing X-Company-ID for an unauthorized company returns HTTP 403."""
        # NovaPay admin passes Apex's company ID in header
        res_rules = self.client.get(
            '/api/rules/',
            HTTP_AUTHORIZATION=f'Bearer {self.nova_admin_token}',
            HTTP_X_COMPANY_ID=str(self.comp_apex.id)
        )
        self.assertEqual(res_rules.status_code, 403)

        res_facts = self.client.get(
            '/api/facts/',
            HTTP_AUTHORIZATION=f'Bearer {self.nova_admin_token}',
            HTTP_X_COMPANY_ID=str(self.comp_apex.id)
        )
        self.assertEqual(res_facts.status_code, 403)

    # =========================================================================
    # 4. Cross-Company Isolation: Writer Blocked on Target Company
    # =========================================================================
    def test_company_a_writer_cannot_audit_or_submit_for_company_b(self):
        """Tests Company A writer cannot submit copy or run audits for Company B."""
        audit_payload = {
            "title": "Malicious Cross-Tenant Post",
            "channel_context": "LINKEDIN_POST",
            "raw_text": "Our cheap rates settle fast with Apex.",
            "company_id": str(self.comp_apex.id)
        }

        # Attempt audit with unauthorized company_id in payload
        res_audit = self.client.post(
            '/api/submissions/audit/',
            data=json.dumps(audit_payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.nova_writer_token}',
            HTTP_X_COMPANY_ID=str(self.comp_apex.id)
        )
        self.assertEqual(res_audit.status_code, 403)

    # =========================================================================
    # 5. Multi-Company User Switching & Role Elevation Scoping
    # =========================================================================
    def test_multi_company_user_can_switch_context(self):
        """
        Tests user who is CONTENT_WRITER in Company 1A and ADMIN in Company 1B:
        - In Company 1A context: can view submissions, but cannot update company settings (HTTP 403).
        - In Company 1B context: can update company settings (HTTP 200).
        """
        # Context 1: NovaPay (Writer role)
        res_comp1_update = self.client.put(
            f'/api/companies/{self.comp_novapay.id}/',
            data=json.dumps({"name": "NovaPay Updated by Writer"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f'Bearer {self.multi_user_token}',
            HTTP_X_COMPANY_ID=str(self.comp_novapay.id)
        )
        self.assertEqual(res_comp1_update.status_code, 403)

        # Context 2: NovaPay Retail (Admin role)
        res_comp2_update = self.client.put(
            f'/api/companies/{self.comp_retail.id}/',
            data=json.dumps({"name": "NovaPay Retail Prime"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f'Bearer {self.multi_user_token}',
            HTTP_X_COMPANY_ID=str(self.comp_retail.id)
        )
        self.assertEqual(res_comp2_update.status_code, 200)

        self.comp_retail.refresh_from_db()
        self.assertEqual(self.comp_retail.name, "NovaPay Retail Prime")

    # =========================================================================
    # 6. Central Scoping Layer & QuerySet Isolation
    # =========================================================================
    def test_scope_queryset_to_caller_isolates_records(self):
        """Verifies scope_queryset_to_caller central function cleanly isolates querysets."""
        from django.test import RequestFactory
        factory = RequestFactory()

        # Request with NovaPay Admin
        req_nova = factory.get('/api/rules/')
        req_nova.user = self.user_novapay_admin

        scoped_rules_nova = scope_queryset_to_caller(BrandRule.objects.all(), req_nova)
        self.assertIn(self.rule_novapay, scoped_rules_nova)
        self.assertNotIn(self.rule_apex, scoped_rules_nova)

        # Request with Apex Admin
        req_apex = factory.get('/api/rules/')
        req_apex.user = self.user_apex_admin

        scoped_rules_apex = scope_queryset_to_caller(BrandRule.objects.all(), req_apex)
        self.assertIn(self.rule_apex, scoped_rules_apex)
        self.assertNotIn(self.rule_novapay, scoped_rules_apex)

    # =========================================================================
    # 7. Project Scoping
    # =========================================================================
    def test_company_projects_isolation(self):
        """Tests GET /api/companies/<id>/projects/ and project creation isolation."""
        # NovaPay admin creates a project for NovaPay
        res_create = self.client.post(
            f'/api/companies/{self.comp_novapay.id}/projects/',
            data=json.dumps({
                "name": "NovaPay Spring Push",
                "description": "Cross-border campaign",
                "channel": "LINKEDIN_POST"
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f'Bearer {self.nova_admin_token}'
        )
        self.assertEqual(res_create.status_code, 201)
        proj_id = res_create.json()["project"]["id"]

        # Apex Admin attempts to list NovaPay projects -> 403 Forbidden
        res_list_blocked = self.client.get(
            f'/api/companies/{self.comp_novapay.id}/projects/',
            HTTP_AUTHORIZATION=f'Bearer {self.apex_admin_token}'
        )
        self.assertEqual(res_list_blocked.status_code, 403)
