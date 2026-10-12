"""HTTP boundary regressions: removing the MFA gate exposes privileged activity."""
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from accounts.models import User


class PasswordOnlyBoundaryTests(TestCase):
    def user(self, name, **roles):
        user = User.objects.create_user(email=f"mfa-red-{name}@example.invalid",
                                        password="Synthetic-MFA-test-password-57", **roles)
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        return user

    def test_staff_password_session_cannot_enter_admin(self):
        self.client.force_login(self.user("staff", is_staff=True))
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/", response["Location"])

    def test_direct_reviewer_password_session_cannot_enter_moderation(self):
        user = self.user("direct")
        user.user_permissions.add(Permission.objects.get(codename="review_listingrevision"))
        self.client.force_login(user)
        response = self.client.get(reverse("moderation:queue"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/", response["Location"])

    def test_group_reviewer_password_post_is_rejected_before_view(self):
        user = self.user("group")
        group = Group.objects.create(name="mfa-red-reviewers")
        group.permissions.add(Permission.objects.get(codename="review_listingrevision"))
        user.groups.add(group)
        self.client.force_login(user)
        response = self.client.post(reverse("moderation:review", args=[999999]),
                                    {"action": "approve"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("no-store", response.get("Cache-Control", ""))

    def test_admin_login_post_enters_allauth_without_password_authentication(self):
        self.user("admin-login", is_staff=True)
        response = self.client.post("/admin/login/", {
            "username": "mfa-red-admin-login@example.invalid",
            "password": "Synthetic-MFA-test-password-57", "next": "/admin/"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_regular_seller_uses_own_dashboard_without_mfa(self):
        self.client.force_login(self.user("seller"))
        self.assertEqual(self.client.get(reverse("listings:dashboard")).status_code, 200)

    def test_authentication_cache_is_shared(self):
        from config import settings as product_settings
        self.assertEqual(product_settings.CACHES["default"]["BACKEND"],
                         "django.core.cache.backends.redis.RedisCache")

    def test_password_only_staff_cannot_mutate_account_management(self):
        self.client.force_login(self.user("account", is_staff=True))
        response = self.client.post(reverse("account_change_password"), {
            "oldpassword": "Synthetic-MFA-test-password-57",
            "password1": "Synthetic-new-password-58", "password2": "Synthetic-new-password-58"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("account_reauthentication_state", self.client.session)

    def test_security_overview_is_reachable_while_staff_remediates(self):
        self.client.force_login(self.user("overview", is_staff=True))
        response = self.client.get("/accounts/security/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Güvenlik")
        self.assertIn("no-store", response.get("Cache-Control", ""))

    def test_staff_public_browse_and_health_remain_reachable(self):
        self.client.force_login(self.user("public", is_staff=True))
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/health/").status_code, 200)


import json
import time
from types import SimpleNamespace
from unittest.mock import patch

from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal import auth as totp_auth
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret
from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, SimpleTestCase, TransactionTestCase, override_settings
from redis.exceptions import ConnectionError as RedisConnectionError

from accounts.mfa_adapter import ClassifiedsMFAAdapter, MFAStorageError
from accounts.mfa_policy import (
    PROOF_SESSION_KEY, has_mfa_proof, primary_factor, requires_mfa,
)
from accounts.models import SecurityEvent
from . import mfa_support
from .mfa_support import MFATestIsolationMixin, PASSWORD, add_factors, totp_code


class RealMFAFlowTests(MFATestIsolationMixin, TransactionTestCase):
    def user(self, name, **roles):
        user = User.objects.create_user(email=f"mfa-flow-{name}@example.invalid",
                                        password=PASSWORD, **roles)
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        return user

    def enroll(self, user):
        response = self.client.post(reverse("account_login"), {"login": user.email, "password": PASSWORD})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("mfa_activate_totp"))
        self.assertEqual(response.status_code, 200)
        secret = self.client.session["mfa.totp.secret"]
        response = self.client.post(reverse("mfa_activate_totp"), {"code": totp_code(secret)})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(primary_factor(user) is not None)
        return secret

    def request_for(self, user, session=None):
        request = RequestFactory().get("/")
        request.user = user
        request.session = self.client.session if session is None else session
        return request

    def test_real_enrollment_creates_encrypted_primary_and_bound_proof(self):
        user = self.user("pairing", is_staff=True)
        secret = self.enroll(user)
        primary = primary_factor(user)
        self.assertFalse(secret in json.dumps(primary.data), "Stored primary must not contain clear seed.")
        recovery = Authenticator.objects.get(user=user, type=Authenticator.Type.RECOVERY_CODES)
        self.assertTrue(recovery.data["seed"].startswith("classifieds-mfa:v1:"))
        self.assertTrue(has_mfa_proof(self.request_for(user)))
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertEqual(SecurityEvent.objects.filter(actor=user, action="activated").count(), 2)

    def test_password_then_wrong_missing_and_valid_second_factor(self):
        user = self.user("login", is_staff=True)
        secret = self.enroll(user)
        self.client.logout()
        response = self.client.post(reverse("account_login"), {
            "login": user.email, "password": PASSWORD, "next": "/admin/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("mfa_authenticate"))
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("mfa_authenticate"), {"code": ""})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("mfa_authenticate"), {"code": "not-a-valid-code"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Doğrulama başarısız" in response.content.decode())
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("mfa_authenticate"), {"code": totp_code(secret)})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertTrue(has_mfa_proof(self.request_for(user)))
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertEqual(SecurityEvent.objects.filter(actor=user, action="failed").count(), 1)

    def test_optional_seller_enrollment_requires_second_factor_at_login(self):
        user = self.user("optional")
        secret = self.enroll(user)
        self.client.logout()
        response = self.client.post(reverse("account_login"), {"login": user.email, "password": PASSWORD})
        self.assertEqual(response["Location"], reverse("mfa_authenticate"))
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("mfa_authenticate"), {"code": totp_code(secret)})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse("listings:dashboard")).status_code, 200)

    def test_existing_password_session_reauthenticates_not_login_stage(self):
        user = self.user("existing", is_staff=True)
        primary = add_factors(user)
        secret = ClassifiedsMFAAdapter().decrypt(primary.data["secret"])
        self.client.force_login(user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("mfa_reauthenticate")))
        response = self.client.post(reverse("mfa_reauthenticate"), {"code": totp_code(secret), "next": "/admin/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_totp_replay_cannot_issue_a_new_session_proof(self):
        user = self.user("replay", is_staff=True)
        primary = add_factors(user)
        secret = ClassifiedsMFAAdapter().decrypt(primary.data["secret"])
        self.client.force_login(user)
        code = totp_code(secret)
        self.assertEqual(self.client.post(reverse("mfa_reauthenticate"), {"code": code}).status_code, 302)
        second = Client()
        second.force_login(user)
        response = second.post(reverse("mfa_reauthenticate"), {"code": code})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(PROOF_SESSION_KEY, second.session)
        self.assertEqual(second.get("/admin/").status_code, 302)

    def test_recovery_codes_show_once_and_download_never_exposes_codes(self):
        user = self.user("show-once", is_staff=True)
        self.enroll(user)
        recovery = Authenticator.objects.get(user=user, type=Authenticator.Type.RECOVERY_CODES).wrap()
        codes = recovery.get_unused_codes()
        self.assertEqual(len(codes), 10)
        self.assertTrue(all(len(code) == 8 and code.isdigit() for code in codes))
        first = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(first.status_code, 200)
        self.assertTrue(all(code.encode() in first.content for code in codes), "First view must display synthetic codes.")
        second = self.client.get(reverse("mfa_view_recovery_codes"))
        self.assertEqual(second.status_code, 200)
        self.assertFalse(any(code.encode() in second.content for code in codes), "Codes must never be displayed again.")
        download = self.client.get(reverse("mfa_download_recovery_codes"))
        self.assertEqual(download.status_code, 403)
        self.assertFalse(any(code.encode() in download.content for code in codes), "Download must not expose codes.")
        for response in (first, second, download):
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response["Referrer-Policy"], "same-origin")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_recovery_success_then_replay_fails_and_regeneration_invalidates_old(self):
        user = self.user("recover", is_staff=True)
        self.enroll(user)
        old = Authenticator.objects.get(user=user, type=Authenticator.Type.RECOVERY_CODES).wrap().get_unused_codes()
        self.client.logout()
        self.client.post(reverse("account_login"), {"login": user.email, "password": PASSWORD})
        self.assertEqual(self.client.post(reverse("mfa_authenticate"), {"code": old[0]}).status_code, 302)
        self.assertTrue(has_mfa_proof(self.request_for(user)))
        second = Client()
        second.force_login(user)
        self.assertEqual(second.post(reverse("mfa_reauthenticate"), {"code": old[0]}).status_code, 200)
        self.assertNotIn(PROOF_SESSION_KEY, second.session)
        response = self.client.post(reverse("mfa_generate_recovery_codes"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(has_mfa_proof(self.request_for(user)))
        self.assertEqual(SecurityEvent.objects.filter(actor=user, action="recovery_regenerated").count(), 1)
        self.assertEqual(second.post(reverse("mfa_reauthenticate"), {"code": old[1]}).status_code, 200)
        self.assertNotIn(PROOF_SESSION_KEY, second.session)

    def test_recent_recovery_allows_replacement_but_blocks_privilege_until_new_pairing(self):
        user = self.user("replace", is_staff=True)
        self.enroll(user)
        old_primary_id = primary_factor(user).pk
        recovery = Authenticator.objects.get(user=user, type=Authenticator.Type.RECOVERY_CODES).wrap().get_unused_codes()[0]
        self.client.logout()
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse("mfa_reauthenticate"), {"code": recovery}).status_code, 302)
        self.assertEqual(self.client.post(reverse("mfa_deactivate_totp")).status_code, 302)
        self.assertIsNone(primary_factor(user))
        self.assertNotIn(PROOF_SESSION_KEY, self.client.session)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.assertEqual(self.client.post(reverse("listings:create"), {"category": 1}).status_code, 403)
        response = self.client.get(reverse("mfa_activate_totp"))
        self.assertEqual(response.status_code, 200)
        secret = self.client.session["mfa.totp.secret"]
        response = self.client.post(reverse("mfa_activate_totp"), {"code": totp_code(secret)})
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(primary_factor(user).pk, old_primary_id)
        self.assertTrue(has_mfa_proof(self.request_for(user)))
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_sensitive_management_rejects_expired_mfa_even_after_fresh_password(self):
        user = self.user("stale", is_staff=True)
        self.enroll(user)
        session = self.client.session
        session[PROOF_SESSION_KEY] = {**session[PROOF_SESSION_KEY], "verified_at": time.time() - 301}
        session["account_authentication_methods"] = [{"method": "password", "at": time.time()}]
        session.save()
        primary_id = primary_factor(user).pk
        recovery_id = Authenticator.objects.get(user=user, type="recovery_codes").pk
        for name in ("mfa_deactivate_totp", "mfa_generate_recovery_codes"):
            response = self.client.post(reverse(name), {"test_original_body": "must-not-be-stored"})
            self.assertEqual(response.status_code, 403)
            self.assertNotIn("account_reauthentication_state", self.client.session)
        self.assertEqual(primary_factor(user).pk, primary_id)
        self.assertEqual(Authenticator.objects.get(user=user, type="recovery_codes").pk, recovery_id)

    def test_fresh_pairing_proof_and_stale_stock_record_never_suspend_post(self):
        user = self.user("stock-replay", is_staff=True)
        self.enroll(user)
        session = self.client.session
        session["account_authentication_methods"] = [{"method": "password", "at": time.time() - 301}]
        session.save()
        self.assertTrue(has_mfa_proof(self.request_for(user), max_age=300))
        primary_id = primary_factor(user).pk
        recovery_id = Authenticator.objects.get(user=user, type="recovery_codes").pk
        for name in ("mfa_deactivate_totp", "mfa_generate_recovery_codes"):
            response = self.client.post(reverse(name), {"test_original_body": "must-not-be-stored"})
            self.assertEqual(response.status_code, 403)
            self.assertNotIn("account_reauthentication_state", self.client.session)
        self.assertEqual(primary_factor(user).pk, primary_id)
        self.assertEqual(Authenticator.objects.get(user=user, type="recovery_codes").pk, recovery_id)

    def test_missing_proof_cannot_mutate_privileged_listing_or_private_media(self):
        user = self.user("missing", is_staff=True)
        add_factors(user)
        self.client.force_login(user)
        response = self.client.post(reverse("listings:create"), {"category": 1})
        self.assertEqual(response.status_code, 403)
        response = self.client.get("/private-media/999999/original/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("mfa_reauthenticate")))

    def test_no_email_row_and_changed_current_email_block_pairing(self):
        user = self.user("unverified", is_staff=True)
        EmailAddress.objects.filter(user=user).delete()
        self.client.force_login(user)
        response = self.client.get(reverse("mfa_activate_totp"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("accounts:verify_email")))
        self.assertNotIn("mfa.totp.secret", self.client.session)
        EmailAddress.objects.create(user=user, email="old-address@example.invalid", verified=True)
        self.assertEqual(self.client.post(reverse("mfa_activate_totp"), {"code": "invalid"}).status_code, 403)
        self.assertIsNone(primary_factor(user))

    def test_email_remediation_only_sends_for_current_address_without_auto_verification(self):
        user = self.user("email-remediation", is_staff=True)
        EmailAddress.objects.filter(user=user).update(verified=False)
        self.client.force_login(user)
        response = self.client.post(reverse("accounts:verify_email"), {"email": "attacker@example.invalid"})
        self.assertEqual(response.status_code, 302)
        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].to == [user.email], "Verification must target only synthetic owner's current email.")
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertFalse(EmailAddress.objects.filter(email="attacker@example.invalid").exists())

    def test_hostile_next_parameters_do_not_redirect_outside_origin(self):
        user = self.user("hostile", is_staff=True)
        self.enroll(user)
        response = self.client.get(reverse("accounts:security"), {"next": "https://evil.invalid/steal"})
        self.assertFalse(b"evil.invalid" in response.content)
        self.client.logout()
        self.client.post(reverse("account_login"), {
            "login": user.email, "password": PASSWORD, "next": "//evil.invalid/steal"})
        recovery = Authenticator.objects.get(user=user, type="recovery_codes").wrap().get_unused_codes()[0]
        response = self.client.post(reverse("mfa_authenticate"), {"code": recovery, "next": "//evil.invalid/steal"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse("evil.invalid" in response["Location"])

    def test_expected_security_cache_outage_is_private_503_without_proof(self):
        user = self.user("outage", is_staff=True)
        add_factors(user)
        self.client.force_login(user)
        with patch("allauth.core.ratelimit.consume", side_effect=RedisConnectionError("synthetic transport detail")):
            response = self.client.post(reverse("mfa_reauthenticate"), {"code": "not-a-valid-code"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertFalse(b"synthetic transport detail" in response.content)
        self.assertNotIn(PROOF_SESSION_KEY, self.client.session)

    def test_tampered_storage_fails_generically_without_proof(self):
        user = self.user("tampered", is_staff=True)
        primary = add_factors(user)
        primary.data = {"secret": "unrecognized-format"}
        primary.save(update_fields=["data"])
        self.client.force_login(user)
        response = self.client.post(reverse("mfa_reauthenticate"), {"code": "not-a-valid-code"})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(b"unrecognized-format" in response.content)
        self.assertNotIn(PROOF_SESSION_KEY, self.client.session)

    def test_mfa_failures_observe_normal_retry_limit(self):
        user = self.user("retry", is_staff=True)
        add_factors(user)
        self.client.force_login(user)
        for _ in range(5):
            response = self.client.post(reverse("mfa_reauthenticate"), {"code": "not-a-valid-code"})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(SecurityEvent.objects.filter(actor=user, action="failed").count(), 5)
        response = self.client.post(reverse("mfa_reauthenticate"), {"code": "not-a-valid-code"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SecurityEvent.objects.filter(actor=user, action="failed").count(), 5)
        self.assertNotIn(PROOF_SESSION_KEY, self.client.session)
        for _ in range(5):
            self.client.post(reverse("mfa_reauthenticate"), {"code": "not-a-valid-code"})
        limited = self.client.post(reverse("mfa_reauthenticate"), {"code": "not-a-valid-code"})
        self.assertEqual(limited.status_code, 429)
        self.assertTrue("Çok fazla deneme".encode() in limited.content)

    def test_security_and_mfa_forms_are_turkish_with_labels_and_csrf(self):
        user = self.user("ui", is_staff=True)
        self.enroll(user)
        for name, heading in (
            ("accounts:security", "Güvenlik"), ("mfa_reauthenticate", "İki adımlı doğrulamayı yenile"),
            ("mfa_deactivate_totp", "Cihazı değiştir"), ("mfa_generate_recovery_codes", "Kurtarma kodlarını yenile"),
        ):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(heading.encode() in response.content)
            self.assertIn("no-store", response["Cache-Control"])
            if name == "mfa_reauthenticate":
                self.assertTrue(b'for="id_code"' in response.content)
                self.assertTrue(b'csrfmiddlewaretoken' in response.content)

    def test_csrf_blocks_unsafe_security_operations(self):
        user = self.user("csrf", is_staff=True)
        add_factors(user)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(user)
        self.assertEqual(csrf.post(reverse("mfa_reauthenticate"), {"code": "invalid"}).status_code, 403)
        self.assertEqual(csrf.post(reverse("mfa_deactivate_totp")).status_code, 403)
        self.assertIsNotNone(primary_factor(user))

    def test_authenticated_admin_login_post_still_uses_allauth_and_cannot_switch_user(self):
        user = self.user("admin-owner", is_staff=True)
        self.enroll(user)
        other = self.user("admin-other", is_staff=True)
        response = self.client.post("/admin/login/", {
            "username": other.email, "password": PASSWORD, "next": "/admin/"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("account_login")))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_email_remediation_resend_uses_normal_shared_rate_limit(self):
        from django.core import mail
        user = self.user("email-resend", is_staff=True)
        EmailAddress.objects.filter(user=user).update(verified=False)
        self.client.force_login(user)
        first = self.client.post(reverse("accounts:verify_email"))
        self.assertEqual(first.status_code, 302)
        second = self.client.post(reverse("accounts:verify_email"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(second.status_code, 200)
        self.assertTrue("Biraz bekleyip tekrar deneyin".encode() in second.content)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)

    def test_totp_previous_and_future_periods_cannot_create_proof(self):
        from allauth.mfa.totp.internal.auth import format_hotp_value, hotp_value
        user = self.user("tolerance", is_staff=True)
        primary = add_factors(user)
        secret = ClassifiedsMFAAdapter().decrypt(primary.data["secret"])
        self.client.force_login(user)
        counter = int(time.time()) // 30
        for offset in (-1, 1):
            code = format_hotp_value(hotp_value(secret, counter + offset))
            response = self.client.post(reverse("mfa_reauthenticate"), {"code": code})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(PROOF_SESSION_KEY, self.client.session)

    def test_valid_totp_cache_add_transport_failure_cannot_create_proof(self):
        user = self.user("replay-cache-outage", is_staff=True)
        primary = add_factors(user)
        secret = ClassifiedsMFAAdapter().decrypt(primary.data["secret"])
        self.client.force_login(user)
        clock = SimpleNamespace(time=lambda: 1_700_000_010 + 29.999)
        helper_time, verifier_time = mfa_support.time, totp_auth.time
        mark_code_used = TOTP._mark_code_used
        # Bind only these modules' clocks; real HOTP comparison must reach the cache.
        with patch.object(mfa_support, "time", clock), patch.object(totp_auth, "time", clock), \
                patch.object(TOTP, "_mark_code_used",
                             side_effect=RedisConnectionError("synthetic transport detail")) as mark:
            response = self.client.post(reverse("mfa_reauthenticate"), {"code": totp_code(secret)})
            self.assertEqual(mark.call_count, 1)
        self.assertIs(mfa_support.time, helper_time)
        self.assertIs(totp_auth.time, verifier_time)
        self.assertIs(TOTP._mark_code_used, mark_code_used)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(PROOF_SESSION_KEY, self.client.session)
        self.assertEqual(SecurityEvent.objects.filter(actor=user, action="used").count(), 0)
        self.assertFalse(b"synthetic transport detail" in response.content)

    def test_totp_expiring_between_generation_and_validation_never_reaches_cache(self):
        self.assertEqual(settings.MFA_TOTP_PERIOD, 30)
        self.assertEqual(settings.MFA_TOTP_TOLERANCE, 0)
        user = self.user("expired-before-cache", is_staff=True)
        # Fixed synthetic seed avoids a chance collision between adjacent HOTP values.
        with patch.object(mfa_support, "generate_totp_secret", return_value="A" * 32):
            primary = add_factors(user)
        secret = ClassifiedsMFAAdapter().decrypt(primary.data["secret"])
        self.client.force_login(user)
        helper_time, verifier_time = mfa_support.time, totp_auth.time
        mark_code_used = TOTP._mark_code_used
        with patch.object(mfa_support, "time", SimpleNamespace(time=lambda: 1_700_000_010 + 29.999)), \
                patch.object(totp_auth, "time", SimpleNamespace(time=lambda: 1_700_000_010 + 30.001)), \
                patch.object(TOTP, "_mark_code_used",
                             side_effect=RedisConnectionError("synthetic transport detail")) as mark:
            response = self.client.post(reverse("mfa_reauthenticate"), {"code": totp_code(secret)})
            self.assertEqual(mark.call_count, 0)
        self.assertIs(mfa_support.time, helper_time)
        self.assertIs(totp_auth.time, verifier_time)
        self.assertIs(TOTP._mark_code_used, mark_code_used)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn(PROOF_SESSION_KEY, self.client.session)
        self.assertFalse(has_mfa_proof(self.request_for(user)))
        self.assertEqual(SecurityEvent.objects.filter(actor=user, action="used").count(), 0)
        self.assertFalse(b"synthetic transport detail" in response.content)


class CurrentStateProofTests(MFATestIsolationMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email="mfa-proof-owner@example.invalid", password=PASSWORD)
        EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)
        self.primary = add_factors(self.user)
        self.client.force_login(self.user)
        code = Authenticator.objects.get(user=self.user, type="recovery_codes").wrap().get_unused_codes()[0]
        self.assertEqual(self.client.post(reverse("mfa_reauthenticate"), {"code": code}).status_code, 302)

    def request(self, user=None, proof=None):
        request = RequestFactory().get("/")
        request.user = self.user if user is None else user
        request.session = {PROOF_SESSION_KEY: self.client.session[PROOF_SESSION_KEY] if proof is None else proof}
        return request

    def test_marker_is_bound_to_authenticated_user_and_current_primary(self):
        self.assertTrue(has_mfa_proof(self.request()))
        self.assertFalse(has_mfa_proof(self.request(AnonymousUser())))
        foreign = User.objects.create_user(email="mfa-proof-foreign@example.invalid")
        add_factors(foreign)
        self.assertFalse(has_mfa_proof(self.request(foreign)))
        self.primary.delete()
        self.assertFalse(has_mfa_proof(self.request()))
        add_factors(self.user)
        self.assertFalse(has_mfa_proof(self.request()))

    def test_malformed_future_and_expired_markers_are_rejected(self):
        original = self.client.session[PROOF_SESSION_KEY]
        bad = [True, "yes", [], {}, {**original, "verified_at": "now"},
               {**original, "verified_at": True}, {**original, "verified_at": float("nan")},
               {**original, "verified_at": float("inf")}, {**original, "verified_at": time.time() + 60},
               {**original, "verified_at": time.time() - 28801}, {**original, "method": "password"},
               {**original, "method": []}, {**original, "method": {}},
               {**original, "user_id": str(self.user.pk)}, {**original, "primary_id": True},
               {**original, "unexpected": 1}]
        for proof in bad:
            self.assertFalse(has_mfa_proof(self.request(proof=proof)), "Malformed/stale proof must fail closed.")

    def test_stock_password_or_mfa_authentication_records_never_grant_own_proof(self):
        request = self.request()
        request.session = {"account_authentication_methods": [
            {"method": "password", "at": time.time()},
            {"method": "mfa", "at": time.time(), "id": self.primary.pk, "type": "totp"},
        ]}
        self.assertFalse(has_mfa_proof(request))

    def test_current_role_matrix_and_revocation_ignore_user_permission_cache(self):
        permission = Permission.objects.get(codename="review_listingrevision")
        self.assertFalse(requires_mfa(self.user))
        self.user.user_permissions.add(permission)
        self.assertTrue(self.user.has_perm("listings.review_listingrevision"))
        self.assertTrue(requires_mfa(self.user))
        self.user.user_permissions.clear()
        self.assertFalse(requires_mfa(self.user))
        group = Group.objects.create(name="mfa-current-reviewers")
        group.permissions.add(permission)
        self.user.groups.add(group)
        self.assertTrue(requires_mfa(self.user))
        group.permissions.clear()
        self.assertFalse(requires_mfa(self.user))
        User.objects.filter(pk=self.user.pk).update(is_staff=True)
        self.assertTrue(requires_mfa(self.user))
        User.objects.filter(pk=self.user.pk).update(is_staff=False, is_superuser=True)
        self.assertTrue(requires_mfa(self.user))
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertFalse(requires_mfa(self.user))
        self.assertFalse(has_mfa_proof(self.request()))

    def test_role_grant_existing_session_immediately_requires_proof(self):
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("listings:dashboard")).status_code, 200)
        permission = Permission.objects.get(codename="review_listingrevision")
        self.user.user_permissions.add(permission)
        response = self.client.get(reverse("listings:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("mfa_reauthenticate")))

    def test_revoked_group_reviewer_cannot_review_after_valid_mfa(self):
        group = Group.objects.create(name="mfa-revoked-reviewers")
        group.permissions.add(Permission.objects.get(codename="review_listingrevision"))
        self.user.groups.add(group)
        self.assertEqual(self.client.get(reverse("moderation:queue")).status_code, 200)
        self.user.groups.clear()
        self.assertEqual(self.client.get(reverse("moderation:queue")).status_code, 403)

    def test_unverified_or_inactive_accounts_do_not_gain_privileged_access(self):
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        User.objects.filter(pk=self.user.pk).update(is_staff=True)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("accounts:verify_email")))
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.assertEqual(self.client.post(reverse("mfa_reauthenticate"), {"code": "invalid"}).status_code, 302)


class EncryptionContractTests(SimpleTestCase):
    @override_settings(SECRET_KEY="synthetic-current-key-57", SECRET_KEY_FALLBACKS=[])
    def test_authenticated_ciphertext_roundtrip_is_randomized(self):
        adapter = ClassifiedsMFAAdapter()
        first = adapter.encrypt("SYNTHETIC-SECRET-ONLY")
        second = adapter.encrypt("SYNTHETIC-SECRET-ONLY")
        self.assertTrue(first != second, "Ciphertext must be randomized.")
        self.assertFalse("SYNTHETIC-SECRET-ONLY" in first)
        self.assertTrue(adapter.decrypt(first) == "SYNTHETIC-SECRET-ONLY")

    def test_fallback_key_can_decrypt_but_new_writes_use_current_key(self):
        adapter = ClassifiedsMFAAdapter()
        with override_settings(SECRET_KEY="synthetic-old-key", SECRET_KEY_FALLBACKS=[]):
            old = adapter.encrypt("SYNTHETIC-SECRET-ONLY")
        with override_settings(SECRET_KEY="synthetic-new-key", SECRET_KEY_FALLBACKS=["synthetic-old-key"]):
            self.assertTrue(adapter.decrypt(old) == "SYNTHETIC-SECRET-ONLY")
            new = adapter.encrypt("SYNTHETIC-SECRET-ONLY")
        with override_settings(SECRET_KEY="synthetic-old-key", SECRET_KEY_FALLBACKS=[]):
            with self.assertRaises(MFAStorageError):
                adapter.decrypt(new)

    @override_settings(SECRET_KEY="synthetic-current-key-57", SECRET_KEY_FALLBACKS=[])
    def test_plaintext_unknown_version_wrong_key_and_tamper_fail_generically(self):
        adapter = ClassifiedsMFAAdapter()
        valid = adapter.encrypt("SYNTHETIC-SECRET-ONLY")
        for value in ("SYNTHETIC-SECRET-ONLY", "classifieds-mfa:v2:unknown", valid[:-8] + "tampered", None):
            with self.assertRaisesMessage(MFAStorageError, "Doğrulama şu anda kullanılamıyor."):
                adapter.decrypt(value)
        with override_settings(SECRET_KEY="synthetic-wrong-key"):
            with self.assertRaises(MFAStorageError):
                adapter.decrypt(valid)


class AuditAdminTests(TestCase):
    def test_raw_authenticator_admin_is_absent_and_event_admin_is_read_only(self):
        self.assertFalse(admin.site.is_registered(Authenticator))
        event_admin = admin.site._registry[SecurityEvent]
        request = RequestFactory().get("/")
        request.user = User(email="synthetic-admin@example.invalid", is_staff=True, is_superuser=True)
        self.assertFalse(event_admin.has_add_permission(request))
        self.assertFalse(event_admin.has_change_permission(request))
        self.assertFalse(event_admin.has_delete_permission(request))
        self.assertEqual(event_admin.get_actions(request), {})

    def test_audit_contains_only_actor_action_method_time_and_cannot_be_edited(self):
        user = User.objects.create_user(email="mfa-audit@example.invalid")
        event = SecurityEvent.objects.create(actor=user, action="used", method="totp")
        self.assertEqual({field.name for field in SecurityEvent._meta.fields},
                         {"id", "actor", "action", "method", "created_at"})
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()
        user.delete()
        event.refresh_from_db()
        self.assertIsNone(event.actor_id)

class PrivilegedMutationBoundaryTests(MFATestIsolationMixin, TestCase):
    def test_missing_mfa_cannot_approve_a_real_submitted_revision(self):
        from listings.tests.test_publication import PublicationFixtures
        fixture = PublicationFixtures()
        fixture.setUp()
        revision = fixture.submit()
        EmailAddress.objects.create(user=fixture.reviewer, email=fixture.reviewer.email,
                                    verified=True, primary=True)
        self.client.force_login(fixture.reviewer)
        from events.models import OutboxEvent
        from moderation.models import ModerationDecision
        before_events = OutboxEvent.objects.count()
        response = self.client.post(reverse("moderation:review", args=[revision.pk]), {
            "action": "approve", "reason": "Synthetic decision must not execute",
        })
        self.assertEqual(response.status_code, 403)
        revision.refresh_from_db()
        revision.listing.refresh_from_db()
        self.assertEqual(revision.status, "submitted")
        self.assertIsNone(revision.listing.public_revision_id)
        self.assertFalse(ModerationDecision.objects.filter(revision=revision).exists())
        self.assertEqual(OutboxEvent.objects.count(), before_events)
