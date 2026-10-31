import json
from datetime import timedelta
from django.test import TestCase, Client
from django.utils import timezone
from governance.models import (
    BrandGuardUser, Organization, Company, InviteToken,
    EmailVerificationToken, PasswordResetToken, LoginAttemptLog
)
from governance.auth import generate_user_token


class PhaseR1AuthRegistrationTests(TestCase):
    """
    Test suite for Phase R1:
    1. Role cannot be chosen by the client (server sets role based on route/invite)
    2. Admin registration creates a brand new Organization
    3. Invite-only writer registration (no invite / expired invite / maxed invite = 400)
    4. Admin login strictly rejects writers with a neutral error
    5. Email verification requirement before login
    6. Waiting for admin approval workflow
    7. Rate limiting and account lockout after repeated failures
    8. Password reset flow with zero email discovery leaks
    9. Password strength enforcement (min 12 chars, mixed case, numbers/symbols)
    """

    def setUp(self):
        self.client = Client()
        # Create or retrieve base test organization and company
        self.org, _ = Organization.objects.get_or_create(
            slug="novapay-group",
            defaults={
                "name": "NovaPay Group",
                "requires_writer_approval": True
            }
        )
        self.company, _ = Company.objects.get_or_create(
            organization=self.org,
            slug="novapay",
            defaults={"name": "NovaPay"}
        )
        self.admin = BrandGuardUser.objects.create_user(
            username="admin_user",
            email="admin@novapay.io",
            password="StrongPassword123!",
            role="ADMIN",
            organization=self.org,
            is_email_verified=True,
            is_approved=True
        )
        self.admin_token = generate_user_token(self.admin)
        self.admin_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}

        # Create approved writer
        self.writer = BrandGuardUser.objects.create_user(
            username="writer_user",
            email="writer@novapay.io",
            password="StrongPassword123!",
            role="CONTENT_WRITER",
            organization=self.org,
            is_email_verified=True,
            is_approved=True
        )

        # Clear login attempt logs for clean tests
        LoginAttemptLog.objects.all().delete()

    def test_client_cannot_choose_role_on_writer_registration(self):
        """
        SECURITY REQUIREMENT: Client-supplied role is completely ignored.
        Attacker passes role="ADMIN" to /api/auth/register/writer/, but server forces CONTENT_WRITER.
        """
        invite = InviteToken.objects.create(
            code=InviteToken.generate_code(),
            organization=self.org,
            created_by=self.admin,
            role="CONTENT_WRITER",
            max_uses=1,
            expires_at=timezone.now() + timedelta(days=7),
            is_active=True
        )

        payload = {
            "invite_code": invite.code,
            "name": "Malicious Attacker",
            "email": "attacker@novapay.io",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
            "terms_accepted": True,
            "role": "ADMIN"  # Malicious payload trying to escalate privilege
        }

        resp = self.client.post(
            "/api/auth/register/writer/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        user = BrandGuardUser.objects.get(email="attacker@novapay.io")
        self.assertEqual(user.role, "CONTENT_WRITER", "Server must force CONTENT_WRITER and discard client role!")
        self.assertFalse(user.is_admin_user)

    def test_client_cannot_choose_role_on_admin_registration(self):
        """
        SECURITY REQUIREMENT: Admin registration endpoint always forces role='ADMIN'.
        """
        payload = {
            "org_name": "Acme Holdings",
            "name": "Jane Owner",
            "email": "jane@acme.com",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
            "terms_accepted": True,
            "role": "CONTENT_WRITER"  # Client specifies writer, but endpoint forces ADMIN
        }

        resp = self.client.post(
            "/api/auth/register/admin/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        user = BrandGuardUser.objects.get(email="jane@acme.com")
        self.assertEqual(user.role, "ADMIN")
        self.assertTrue(user.is_admin_user)
        self.assertTrue(user.is_approved)

    def test_admin_registration_creates_brand_new_organization(self):
        """
        Admin registration must create a NEW Organization and default Company.
        Can never add an admin to an existing organization.
        """
        initial_org_count = Organization.objects.count()
        payload = {
            "org_name": "Vertex Capital",
            "name": "Sam Chief",
            "email": "sam@vertex.com",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
            "terms_accepted": True
        }

        resp = self.client.post(
            "/api/auth/register/admin/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()

        self.assertEqual(Organization.objects.count(), initial_org_count + 1)
        new_org = Organization.objects.get(id=data["org_id"])
        self.assertEqual(new_org.name, "Vertex Capital")

        user = BrandGuardUser.objects.get(email="sam@vertex.com")
        self.assertEqual(user.organization, new_org)
        self.assertTrue(Company.objects.filter(organization=new_org, name="Vertex Capital").exists())

    def test_writer_registration_fails_without_invite_code(self):
        """
        Writer registration must fail with 400 when invite code is omitted or invalid.
        """
        payload = {
            "name": "Bob Writer",
            "email": "bob@novapay.io",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
            "terms_accepted": True
        }
        resp = self.client.post(
            "/api/auth/register/writer/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("invite code is required", resp.json()["error"])

        # Invalid code
        payload["invite_code"] = "non_existent_code"
        resp2 = self.client.post(
            "/api/auth/register/writer/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("Invalid invite code", resp2.json()["error"])

    def test_writer_registration_fails_with_expired_or_exhausted_invite(self):
        """
        Invite codes must enforce 7-day expiration and maximum uses.
        """
        # Expired invite
        expired_invite = InviteToken.objects.create(
            code=InviteToken.generate_code(),
            organization=self.org,
            created_by=self.admin,
            role="CONTENT_WRITER",
            max_uses=1,
            expires_at=timezone.now() - timedelta(hours=1),
            is_active=True
        )

        payload = {
            "invite_code": expired_invite.code,
            "name": "Late Writer",
            "email": "late@novapay.io",
            "password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!",
            "terms_accepted": True
        }
        resp = self.client.post("/api/auth/register/writer/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("expired", resp.json()["error"].lower())

        # Single-use exhausted invite
        single_invite = InviteToken.objects.create(
            code=InviteToken.generate_code(),
            organization=self.org,
            created_by=self.admin,
            role="CONTENT_WRITER",
            max_uses=1,
            expires_at=timezone.now() + timedelta(days=7),
            is_active=True
        )

        # First use succeeds
        payload["invite_code"] = single_invite.code
        payload["email"] = "first@novapay.io"
        resp1 = self.client.post("/api/auth/register/writer/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp1.status_code, 201)

        # Second use fails
        payload["email"] = "second@novapay.io"
        resp2 = self.client.post("/api/auth/register/writer/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("maximum number of uses", resp2.json()["error"])

    def test_admin_login_rejects_writer_with_neutral_error(self):
        """
        A) /admin/login: for ADMIN only. If a writer logs in here, show a neutral error.
        Do NOT disclose whether the account exists or that the role is writer.
        """
        # Writer credentials passed to admin login endpoint
        resp = self.client.post(
            "/api/auth/login/admin/",
            data=json.dumps({
                "username": self.writer.username,
                "password": "StrongPassword123!"
            }),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertIn("Invalid credentials or unauthorized portal access.", data["error"])
        # Ensure token is not returned
        self.assertNotIn("token", data)

    def test_email_verification_flow_enforcement(self):
        """
        Users cannot log in until email has been verified via single-use token.
        """
        # Register new admin
        resp = self.client.post(
            "/api/auth/register/admin/",
            data=json.dumps({
                "org_name": "Sec Corp",
                "name": "Sec Lead",
                "email": "lead@seccorp.io",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "terms_accepted": True
            }),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        ver_token = resp.json()["verification_token"]

        # Attempt login before verifying email -> HTTP 403
        login_resp = self.client.post(
            "/api/auth/login/",
            data=json.dumps({
                "username": "lead@seccorp.io",
                "password": "StrongPassword123!",
                "portal": "ADMIN"
            }),
            content_type="application/json"
        )
        self.assertEqual(login_resp.status_code, 403)
        self.assertTrue(login_resp.json().get("needs_email_verification"))

        # Verify email
        verify_resp = self.client.post(
            "/api/auth/verify-email/",
            data=json.dumps({"token": ver_token}),
            content_type="application/json"
        )
        self.assertEqual(verify_resp.status_code, 200)

        # Login now succeeds
        login_resp2 = self.client.post(
            "/api/auth/login/",
            data=json.dumps({
                "username": "lead@seccorp.io",
                "password": "StrongPassword123!",
                "portal": "ADMIN"
            }),
            content_type="application/json"
        )
        self.assertEqual(login_resp2.status_code, 200)
        self.assertIn("token", login_resp2.json())

    def test_writer_approval_workflow(self):
        """
        G) Writers see "Waiting for admin approval" if the org requires approval.
        Admin can approve pending writers.
        """
        invite = InviteToken.objects.create(
            code=InviteToken.generate_code(),
            organization=self.org,
            created_by=self.admin,
            role="CONTENT_WRITER",
            max_uses=1,
            expires_at=timezone.now() + timedelta(days=7),
            is_active=True
        )

        # Register writer under org requiring approval
        resp = self.client.post(
            "/api/auth/register/writer/",
            data=json.dumps({
                "invite_code": invite.code,
                "name": "Pending Writer",
                "email": "pending@novapay.io",
                "password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
                "terms_accepted": True
            }),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        ver_token = resp.json()["verification_token"]

        # Verify email
        self.client.post("/api/auth/verify-email/", data=json.dumps({"token": ver_token}), content_type="application/json")

        # Try to log in -> blocked with "Waiting for admin approval"
        login_resp = self.client.post(
            "/api/auth/login/",
            data=json.dumps({
                "username": "pending@novapay.io",
                "password": "StrongPassword123!",
                "portal": "WRITER"
            }),
            content_type="application/json"
        )
        self.assertEqual(login_resp.status_code, 403)
        self.assertTrue(login_resp.json().get("needs_approval"))
        self.assertIn("Waiting for admin approval", login_resp.json()["error"])

        # Admin lists pending members
        pending_list_resp = self.client.get("/api/members/pending/", **self.admin_headers)
        self.assertEqual(pending_list_resp.status_code, 200)
        pending_users = pending_list_resp.json()["pending_members"]
        pending_user = next(u for u in pending_users if u["email"] == "pending@novapay.io")

        # Admin approves the writer
        approve_resp = self.client.post(f"/api/members/{pending_user['id']}/approve/", **self.admin_headers)
        self.assertEqual(approve_resp.status_code, 200)

        # Writer can now log in successfully
        login_resp2 = self.client.post(
            "/api/auth/login/",
            data=json.dumps({
                "username": "pending@novapay.io",
                "password": "StrongPassword123!",
                "portal": "WRITER"
            }),
            content_type="application/json"
        )
        self.assertEqual(login_resp2.status_code, 200)
        self.assertIn("token", login_resp2.json())

    def test_rate_limiting_and_account_lockout(self):
        """
        Repeated failed login attempts trigger account lockout after 5 failures
        and rate-limiting returns HTTP 429.
        """
        user = BrandGuardUser.objects.create_user(
            username="lockout_target",
            email="lockout@novapay.io",
            password="StrongPassword123!",
            role="CONTENT_WRITER",
            organization=self.org,
            is_email_verified=True,
            is_approved=True
        )

        # Fail 5 times
        for _ in range(5):
            self.client.post(
                "/api/auth/login/",
                data=json.dumps({"username": "lockout_target", "password": "WrongPassword!"}),
                content_type="application/json"
            )

        # Account is now locked -> returns 423 or 429
        locked_resp = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"username": "lockout_target", "password": "StrongPassword123!"}),
            content_type="application/json"
        )
        self.assertIn(locked_resp.status_code, (423, 429))
        self.assertTrue(
            locked_resp.json().get("locked") or locked_resp.json().get("rate_limited")
        )

    def test_password_reset_flow_with_zero_email_leaks(self):
        """
        Password reset instructions return generic response for both existing and non-existing emails.
        """
        # Non-existing email
        resp1 = self.client.post(
            "/api/auth/password-reset/request/",
            data=json.dumps({"email": "ghost@nonexistent.com"}),
            content_type="application/json"
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("password reset instructions have been dispatched", resp1.json()["message"])

        # Existing user
        resp2 = self.client.post(
            "/api/auth/password-reset/request/",
            data=json.dumps({"email": self.writer.email}),
            content_type="application/json"
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("password reset instructions have been dispatched", resp2.json()["message"])
        reset_token = resp2.json().get("reset_token")
        self.assertIsNotNone(reset_token)

        # Confirm password reset
        confirm_resp = self.client.post(
            "/api/auth/password-reset/confirm/",
            data=json.dumps({
                "token": reset_token,
                "password": "NewStrongPassword2026!",
                "confirm_password": "NewStrongPassword2026!"
            }),
            content_type="application/json"
        )
        self.assertEqual(confirm_resp.status_code, 200)

        # Login with old password fails
        old_login = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"username": self.writer.username, "password": "StrongPassword123!"}),
            content_type="application/json"
        )
        self.assertEqual(old_login.status_code, 401)

        # Login with new password succeeds
        new_login = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"username": self.writer.username, "password": "NewStrongPassword2026!"}),
            content_type="application/json"
        )
        self.assertEqual(new_login.status_code, 200)

    def test_password_strength_enforcement(self):
        """
        Password must be at least 12 characters and include uppercase, lowercase, numbers/symbols.
        """
        invite = InviteToken.objects.create(
            code=InviteToken.generate_code(),
            organization=self.org,
            created_by=self.admin,
            role="CONTENT_WRITER",
            max_uses=1,
            expires_at=timezone.now() + timedelta(days=7),
            is_active=True
        )

        # Under 12 characters
        resp_short = self.client.post(
            "/api/auth/register/writer/",
            data=json.dumps({
                "invite_code": invite.code,
                "name": "Short Pass",
                "email": "short@novapay.io",
                "password": "Short1!",
                "confirm_password": "Short1!",
                "terms_accepted": True
            }),
            content_type="application/json"
        )
        self.assertEqual(resp_short.status_code, 400)
        self.assertIn("at least 12 characters", resp_short.json()["error"])

        # No digits or symbols
        resp_no_digits = self.client.post(
            "/api/auth/register/writer/",
            data=json.dumps({
                "invite_code": invite.code,
                "name": "No Digits",
                "email": "nodigits@novapay.io",
                "password": "AllLettersNoNumbersOrPunctuation",
                "confirm_password": "AllLettersNoNumbersOrPunctuation",
                "terms_accepted": True
            }),
            content_type="application/json"
        )
        self.assertEqual(resp_no_digits.status_code, 400)
        self.assertIn("numeric or special characters", resp_no_digits.json()["error"])

