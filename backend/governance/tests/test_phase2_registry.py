import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from governance.models import BrandProfile, BrandRule, BrandRuleVersion, DraftRule, FactLedger
from governance.auth import generate_user_token

User = get_user_model()


class Phase2RuleRegistryTestCase(TestCase):
    """
    Automated test suite for Phase 2:
    1. Rule CRUD (list, filter, create, update, deactivate)
    2. Versioning & Rollback with snapshot history
    3. Multi-format upload -> DRAFT staging -> Admin approval
    4. SSRF-Safe scraper (rejects private IPs/metadata; preview & import as unverified/draft)
    5. Rule Playground (testing sample text against rules/drafts)
    6. RBAC enforcement (writers get 403 on admin-only actions)
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
            username="admin_phase2",
            email="admin2@novapay.io",
            password="adminpassword123",
            role="ADMIN",
            department="Brand Governance Lead",
            brand_profile=self.profile
        )
        self.admin_token = generate_user_token(self.admin)

        # Content Writer user
        self.writer = User.objects.create_user(
            username="writer_phase2",
            email="writer2@novapay.io",
            password="writerpassword123",
            role="CONTENT_WRITER",
            department="Marketing Ops",
            brand_profile=self.profile
        )
        self.writer_token = generate_user_token(self.writer)

    # -------------------------------------------------------------------------
    # 1. Rule CRUD & RBAC
    # -------------------------------------------------------------------------
    def test_rule_crud_lifecycle(self):
        # Admin creates new rule
        new_rule_payload = {
            "rule_code": "TONE_TEST_01",
            "title": "Clear Financial Clarity",
            "pillar": "TONE",
            "severity": "BLOCKER",
            "enforcement": "Block publish",
            "claims_allowed": "Empowering users with straightforward payments",
            "claims_disallowed": "Get rich quick with guaranteed payouts",
            "banned_term": "guaranteed payouts",
            "replacement": "transparent processing",
            "rule_description": "Never promise guaranteed payouts or get-rich-quick outcomes."
        }
        create_res = self.client.post(
            '/api/rules/',
            data=json.dumps(new_rule_payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(create_res.status_code, 201)
        created_data = create_res.json()["rule"]
        self.assertEqual(created_data["rule_code"], "TONE_TEST_01")
        self.assertEqual(created_data["version"], 1)

        # Verify initial BrandRuleVersion was created
        rule_obj = BrandRule.objects.get(rule_code="TONE_TEST_01")
        v1 = rule_obj.versions.filter(version_number=1).first()
        self.assertIsNotNone(v1)
        self.assertEqual(v1.title, "Clear Financial Clarity")

        # List rules with filters
        list_res = self.client.get('/api/rules/?pillar=TONE&severity=BLOCKER')
        self.assertEqual(list_res.status_code, 200)
        rules = list_res.json()["rules"]
        self.assertTrue(any(r["rule_code"] == "TONE_TEST_01" for r in rules))

        # Admin updates rule -> version increments to 2
        update_payload = {
            "title": "Clear Financial Clarity (Revised)",
            "severity": "WARNING",
            "change_note": "Downgraded severity to WARNING after team review."
        }
        update_res = self.client.put(
            '/api/rules/TONE_TEST_01/',
            data=json.dumps(update_payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(update_res.status_code, 200)
        rule_obj.refresh_from_db()
        self.assertEqual(rule_obj.version, 2)
        self.assertEqual(rule_obj.title, "Clear Financial Clarity (Revised)")
        self.assertEqual(rule_obj.severity, "WARNING")

        # Admin deactivates rule
        delete_res = self.client.delete(
            '/api/rules/TONE_TEST_01/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(delete_res.status_code, 200)
        rule_obj.refresh_from_db()
        self.assertFalse(rule_obj.is_active)

    def test_writer_forbidden_on_rule_mutations(self):
        # Writer cannot create rule
        post_res = self.client.post(
            '/api/rules/',
            data=json.dumps({"rule_code": "HACK_01", "title": "Unauthorized"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(post_res.status_code, 403)

        # Create active rule as admin
        rule = BrandRule.objects.create(
            profile=self.profile,
            rule_code="VOICE_900",
            title="Writer Test Rule",
            pillar="TONE",
            version=1
        )

        # Writer cannot update rule
        put_res = self.client.put(
            f'/api/rules/{rule.rule_code}/',
            data=json.dumps({"title": "Writer Modified"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(put_res.status_code, 403)

        # Writer cannot delete rule
        del_res = self.client.delete(
            f'/api/rules/{rule.rule_code}/',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(del_res.status_code, 403)

    # -------------------------------------------------------------------------
    # 2. Versioning & Rollback
    # -------------------------------------------------------------------------
    def test_version_history_and_rollback(self):
        rule = BrandRule.objects.create(
            profile=self.profile,
            rule_code="FACT_ROLLBACK_01",
            title="Original Spec Title",
            pillar="FACTUAL",
            severity="BLOCKER",
            claims_allowed="FCA registered",
            claims_disallowed="Unlicensed bank",
            version=1,
            is_active=True
        )
        BrandRuleVersion.objects.create(
            rule=rule,
            version_number=1,
            title="Original Spec Title",
            pillar="FACTUAL",
            severity="BLOCKER",
            claims_allowed="FCA registered",
            claims_disallowed="Unlicensed bank",
            change_note="Initial version."
        )

        # Update to v2
        rule.title = "Modified Spec Title"
        rule.severity = "WARNING"
        rule.version = 2
        rule.save()
        BrandRuleVersion.objects.create(
            rule=rule,
            version_number=2,
            title="Modified Spec Title",
            pillar="FACTUAL",
            severity="WARNING",
            claims_allowed="FCA registered",
            claims_disallowed="Unlicensed bank",
            change_note="v2 modification."
        )

        # Fetch versions
        versions_res = self.client.get(f'/api/rules/{rule.rule_code}/versions/')
        self.assertEqual(versions_res.status_code, 200)
        self.assertEqual(len(versions_res.json()["versions"]), 2)

        # Rollback to v1 as admin
        rollback_res = self.client.post(
            f'/api/rules/{rule.rule_code}/rollback/',
            data=json.dumps({"target_version": 1}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(rollback_res.status_code, 200)

        # Verifications
        rule.refresh_from_db()
        self.assertEqual(rule.version, 3, "Rollback increments version to v3")
        self.assertEqual(rule.title, "Original Spec Title", "Values restored from v1")
        self.assertEqual(rule.severity, "BLOCKER", "Severity restored from v1")

        # Writer cannot rollback
        writer_rollback_res = self.client.post(
            f'/api/rules/{rule.rule_code}/rollback/',
            data=json.dumps({"target_version": 2}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.writer_token}'
        )
        self.assertEqual(writer_rollback_res.status_code, 403)

    # -------------------------------------------------------------------------
    # 3. Multi-Format Upload -> Draft Staging -> Admin Approval
    # -------------------------------------------------------------------------
    def test_upload_stages_drafts_and_admin_approves(self):
        upload_content = """# NovaPay Tone Guidelines
Rule: Prohibit Hyperbolic Returns
Code: TONE_UP_01
Severity: BLOCKER
Banned: guaranteed 20% APY
Replacement: competitive variable yield
Disallowed: Any guarantee of exact percentage APY without risk disclosures
Allowed: Clear articulation of variable yield rates with regulatory caveats
Description: Do not state guaranteed annual percentage yields without qualifying disclosures.
"""
        # Upload as admin
        upload_res = self.client.post(
            '/api/rules/upload/',
            data=json.dumps({"rules_text": upload_content, "filename": "policy.md"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(upload_res.status_code, 201)
        res_data = upload_res.json()
        self.assertEqual(res_data["status"], "success")
        self.assertGreater(res_data["count"], 0)

        # CRITICAL SAFETY CHECK: Drafts MUST NOT be created in active BrandRule table!
        self.assertFalse(
            BrandRule.objects.filter(rule_code="TONE_UP_01").exists(),
            "Uploaded rules must NOT be automatically activated!"
        )

        # Drafts MUST be staged in DraftRule table
        draft = DraftRule.objects.filter(rule_code="TONE_UP_01").first()
        self.assertIsNotNone(draft, "Uploaded rule must be staged in DraftRule")
        self.assertEqual(draft.status, "DRAFT")

        # Admin lists drafts
        drafts_res = self.client.get(
            '/api/rules/drafts/',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(drafts_res.status_code, 200)
        draft_codes = [d["rule_code"] for d in drafts_res.json()["drafts"]]
        self.assertIn("TONE_UP_01", draft_codes)

        # Admin approves draft
        approve_res = self.client.post(
            '/api/rules/drafts/approve/',
            data=json.dumps({
                "draft_ids": [str(draft.id)],
                "action": "APPROVE",
                "edits": {
                    str(draft.id): {
                        "title": "Prohibit Hyperbolic Returns (Approved)"
                    }
                }
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(approve_res.status_code, 200)

        # Draft is now APPROVED
        draft.refresh_from_db()
        self.assertEqual(draft.status, "APPROVED")

        # BrandRule is now active
        active_rule = BrandRule.objects.filter(rule_code="TONE_UP_01").first()
        self.assertIsNotNone(active_rule)
        self.assertEqual(active_rule.title, "Prohibit Hyperbolic Returns (Approved)")
        self.assertTrue(active_rule.is_active)
        self.assertEqual(active_rule.version, 1)

    # -------------------------------------------------------------------------
    # 4. SSRF-Safe Scraper Tests
    # -------------------------------------------------------------------------
    def test_ssrf_safety_blocks_private_and_metadata_ips(self):
        # 1. Loopback 127.0.0.1
        res_loopback = self.client.post(
            '/api/rules/scrape/',
            data=json.dumps({"url": "http://127.0.0.1:8000/internal-secrets"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_loopback.status_code, 400)
        self.assertIn("SSRF Security Violation", res_loopback.json()["error"])

        # 2. AWS / Cloud Link-Local Metadata (169.254.169.254)
        res_metadata = self.client.post(
            '/api/rules/scrape/',
            data=json.dumps({"url": "http://169.254.169.254/latest/meta-data/"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_metadata.status_code, 400)
        self.assertIn("SSRF Security Violation", res_metadata.json()["error"])

        # 3. Localhost hostname
        res_localhost = self.client.post(
            '/api/rules/scrape/',
            data=json.dumps({"url": "http://localhost:8080/admin"}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(res_localhost.status_code, 400)
        self.assertIn("SSRF Security Violation", res_localhost.json()["error"])

    @patch('governance.views.scrape_brand_profile')
    def test_scraper_preview_and_import_as_unverified(self, mock_scrape):
        mock_scrape.return_value = {
            "palette": [{"name": "Brand Violet", "hex": "#7B2CBF", "count": 12}],
            "fonts": ["Outfit", "Inter"],
            "claims": [{"claim_text": "Over 10 million transactions processed securely.", "tag": "h2"}]
        }

        # 1. Preview request
        preview_res = self.client.post(
            '/api/rules/scrape/',
            data=json.dumps({"url": "https://example.com/brand", "import_selected": False}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(preview_res.status_code, 200)
        p_data = preview_res.json()
        self.assertEqual(p_data["status"], "success")
        self.assertEqual(p_data["mode"], "preview")
        self.assertIn("preview_items", p_data)

        # Verify items are labeled as draft/unverified
        has_unverified_claim = any(
            item.get("status") == "unverified" for item in p_data["preview_items"]
        )
        self.assertTrue(has_unverified_claim, "Scraped claims must be labeled unverified")

        # 2. Import request
        import_res = self.client.post(
            '/api/rules/scrape/',
            data=json.dumps({
                "url": "https://example.com/brand",
                "import_selected": True,
                "selected_items": [
                    {
                        "type": "FACT",
                        "value": "Over 10 million transactions processed securely.",
                        "code": "FACT_SCRAPED_TEST_01"
                    },
                    {
                        "type": "HEX_PALETTE",
                        "value": "#7B2CBF"
                    }
                ]
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(import_res.status_code, 201)

        # Verify fact was saved as UNVERIFIED (is_verified=False)
        fact = FactLedger.objects.filter(fact_code="FACT_SCRAPED_TEST_01").first()
        self.assertIsNotNone(fact)
        self.assertFalse(fact.is_verified, "Imported scraped facts must be unverified (is_verified=False)")

        # Verify color was saved as DRAFT (DraftRule status='DRAFT')
        draft_color = DraftRule.objects.filter(claims_allowed="#7B2CBF").first()
        self.assertIsNotNone(draft_color)
        self.assertEqual(draft_color.status, "DRAFT", "Imported scraped palette must be DRAFT")

    # -------------------------------------------------------------------------
    # 5. Rule Playground Tests
    # -------------------------------------------------------------------------
    def test_rule_playground_flag_and_pass(self):
        rule = BrandRule.objects.create(
            profile=self.profile,
            rule_code="TONE_PLAY_01",
            title="No Guaranteed Returns",
            pillar="TONE",
            severity="BLOCKER",
            claims_allowed="market-driven yield",
            claims_disallowed="guaranteed returns",
            structured_spec={"banned_term": "guaranteed returns", "replacement": "market-driven yield"}
        )

        # Test prohibited copy -> should FLAG
        flag_res = self.client.post(
            '/api/rules/playground/',
            data=json.dumps({
                "rule_code": "TONE_PLAY_01",
                "test_text": "Invest with NovaPay for guaranteed returns every quarter."
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(flag_res.status_code, 200)
        flag_data = flag_res.json()
        self.assertEqual(flag_data["status"], "FLAG")
        self.assertTrue(flag_data["flagged"])
        self.assertEqual(flag_data["match_excerpt"], "guaranteed returns")
        self.assertEqual(flag_data["suggested_fix"], "market-driven yield")

        # Test compliant copy -> should PASS
        pass_res = self.client.post(
            '/api/rules/playground/',
            data=json.dumps({
                "rule_code": "TONE_PLAY_01",
                "test_text": "Invest with NovaPay for market-driven yield every quarter."
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        self.assertEqual(pass_res.status_code, 200)
        pass_data = pass_res.json()
        self.assertEqual(pass_data["status"], "PASS")
        self.assertFalse(pass_data["flagged"])
