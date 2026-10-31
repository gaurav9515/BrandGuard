import json
from django.test import TestCase, Client
from governance.models import (
    BrandGuardUser, BrandProfile, BrandRule, FactLedger, Submission, SubmissionVersion, Company, Organization
)
from datetime import date


class GlobalSearchTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(name="NovaPay Global", slug="novapay-global")
        self.company = Company.objects.create(organization=self.org, name="NovaPay Core", slug="novapay-core")
        self.profile = BrandProfile.objects.create(org_name="NovaPay Core", company=self.company)

        self.admin = BrandGuardUser.objects.create_user(
            username="admin_search",
            email="admin_search@novapay.io",
            password="StrongPassword123!",
            role="ADMIN",
            organization=self.org,
            company=self.company,
        )

        self.writer = BrandGuardUser.objects.create_user(
            username="writer_search",
            email="writer_search@novapay.io",
            password="StrongPassword123!",
            role="CONTENT_WRITER",
            organization=self.org,
            company=self.company,
        )

        # Create test rule
        self.rule = BrandRule.objects.create(
            profile=self.profile,
            rule_code="FACT_099",
            title="Instant Settlement SLA",
            pillar="FACTUAL",
            severity="BLOCKER",
            claims_allowed="Settles within 2 hours",
            claims_disallowed="Instant real-time settlement",
            rule_description="Real-time claims are strictly prohibited without enterprise tier.",
            is_active=True,
            version=1,
        )

        # Create test fact
        self.fact = FactLedger.objects.create(
            profile=self.profile,
            company=self.company,
            fact_code="FACT_099",
            category="Settlement Policy",
            claim_truth="Standard enterprise rails settle in 2 business hours.",
            last_verified=date.today(),
            valid_until=date(2028, 1, 1),
            is_verified=True,
            source="NovaPay Docs",
        )

        # Create test submission
        self.submission = Submission.objects.create(
            profile=self.profile,
            company=self.company,
            author=self.writer,
            title="Cross-Border Rails Campaign",
            channel_context="LINKEDIN_POST",
            status="IN_REVIEW",
        )
        self.version = SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=1,
            raw_text="Announcing our lightning fast cross-border rails settlement.",
            compliance_score=84.0,
        )

    def test_search_returns_rules_facts_drafts_and_navigation(self):
        response = self.client.get('/api/search/?q=Settlement')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("rules", data)
        self.assertIn("facts", data)
        self.assertIn("drafts", data)
        self.assertIn("navigation", data)

        # Verify Rule match
        rule_codes = [r["rule_code"] for r in data["rules"]]
        self.assertIn("FACT_099", rule_codes)

        # Verify Fact match
        fact_codes = [f["fact_code"] for f in data["facts"]]
        self.assertIn("FACT_099", fact_codes)

    def test_search_by_rule_code(self):
        response = self.client.get('/api/search/?q=FACT_099')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data["rules"]) >= 1)
        self.assertEqual(data["rules"][0]["rule_code"], "FACT_099")
        self.assertEqual(data["rules"][0]["severity"], "BLOCKER")

    def test_search_by_draft_title(self):
        response = self.client.get('/api/search/?q=Cross-Border')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data["drafts"]) >= 1)
        self.assertIn("Cross-Border", data["drafts"][0]["title"])

    def test_search_navigation_query(self):
        response = self.client.get('/api/search/?q=Registry')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        nav_ids = [n["id"] for n in data["navigation"]]
        self.assertIn("registry", nav_ids)

    def test_empty_query_returns_suggestions(self):
        response = self.client.get('/api/search/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data["navigation"]) > 0)
        self.assertTrue(len(data["rules"]) > 0)

