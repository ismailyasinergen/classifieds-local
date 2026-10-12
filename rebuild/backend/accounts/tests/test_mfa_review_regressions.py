"""Reproduce independent review A1/A2 using synthetic HTTP and PostgreSQL.

Only booleans, status codes and test names may appear in assertion diagnostics.
Factor secrets and recovery values remain in the temporary test process.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urljoin, urlsplit
from unittest.mock import patch

from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from django.db import close_old_connections, connection
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from accounts.mfa_middleware import remediation, safe_return_path
from accounts.models import User
from .mfa_support import MFATestIsolationMixin, authenticate_client


class ReturnPathReviewTests(MFATestIsolationMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email="review-a1@example.invalid", is_staff=True)
        authenticate_client(self.client, self.user)
        self.request = RequestFactory().get("/accounts/security/")
        self.candidates = (
            "http://testserver//outside.example.invalid/continue",
            "http://testserver/\\outside.example.invalid/continue",
            "http://testserver///outside.example.invalid/continue",
        )

    def test_transformed_return_path_never_becomes_external_authority(self):
        for candidate in self.candidates:
            result = safe_return_path(self.request, candidate)
            self.assertEqual(result, reverse("accounts:security"))

    def test_real_mfa_security_overview_does_not_render_external_continue_link(self):
        for candidate in self.candidates:
            response = self.client.get(reverse("accounts:security"), {"next": candidate})
            self.assertEqual(response.status_code, 200)
            target = response.context["return_path"]
            self.assertEqual(urlsplit(urljoin("http://testserver/", target.replace("\\", "/"))).netloc, "testserver")
            self.assertNotContains(response, 'href="//outside.example.invalid')

    def test_admin_and_remediation_use_the_revalidated_final_path(self):
        for candidate in self.candidates:
            response = Client().get("/admin/login/", {"next": candidate})
            self.assertEqual(response.status_code, 302)
            target = parse_qs(urlsplit(response["Location"]).query)["next"][0]
            self.assertEqual(target, reverse("accounts:security"))
            response = remediation(self.request, "accounts:security", next_path=candidate)
            self.assertEqual(parse_qs(urlsplit(response["Location"]).query)["next"][0], reverse("accounts:security"))

    def test_ordinary_local_query_return_is_preserved(self):
        expected = "/ilanlarim/?page=2&sort=newest"
        for candidate in (expected, "http://testserver" + expected):
            self.assertEqual(safe_return_path(self.request, candidate), expected)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RecoveryDisplayReviewTests(MFATestIsolationMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(connection.vendor, "postgresql")
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        self.user = User.objects.create_user(email="review-a2@example.invalid", is_staff=True)
        self.first = Client()
        self.second = Client()
        authenticate_client(self.first, self.user)
        authenticate_client(self.second, self.user)
        self.factor = Authenticator.objects.get(user=self.user, type=Authenticator.Type.RECOVERY_CODES)
        self.code = self.factor.wrap().get_unused_codes()[0]
        self.assertFalse(self.factor.wrap().did_view)

    def _race(self, second_action):
        first_paused = threading.Event()
        release_first = threading.Event()
        second_started = threading.Event()
        second_marked = threading.Event()
        second_pid = []
        original_mark = RecoveryCodes.mark_as_viewed
        original_factor_pk = self.factor.pk

        def pause_first_view(wrapper):
            if wrapper.instance.pk == original_factor_pk:
                if threading.current_thread().name.endswith("_0"):
                    first_paused.set()
                    if not release_first.wait(10):
                        raise AssertionError("Controlled display synchronization expired.")
                else:
                    second_marked.set()
            return original_mark(wrapper)

        def run_first():
            close_old_connections()
            try:
                response = self.first.get(reverse("mfa_view_recovery_codes"))
                return response.status_code, self.code.encode() in response.content
            finally:
                connection.close()

        def run_second():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    second_pid.append(cursor.fetchone()[0])
                second_started.set()
                return second_action()
            finally:
                connection.close()

        with patch.object(RecoveryCodes, "mark_as_viewed", pause_first_view):
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="mfa_review") as pool:
                first = pool.submit(run_first)
                try:
                    self.assertTrue(first_paused.wait(5), "First public display must reach the controlled write boundary.")
                    second = pool.submit(run_second)
                    self.assertTrue(second_started.wait(5))
                    # Wait for an actual completion/write or PostgreSQL blocker,
                    # not an arbitrary sleep that might miss an overlap.
                    deadline = time.monotonic() + 5
                    observed = False
                    while time.monotonic() < deadline:
                        if second.done() or second_marked.is_set():
                            observed = True
                            break
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT cardinality(pg_blocking_pids(%s))", [second_pid[0]])
                            if cursor.fetchone()[0] > 0:
                                observed = True
                                break
                        time.sleep(0.01)
                    self.assertTrue(observed, "The competing operation must complete or actually wait on a database lock.")
                finally:
                    release_first.set()
                return first.result(timeout=10), second.result(timeout=10)

    def test_two_concurrent_first_displays_reveal_the_codes_only_once(self):
        def second():
            response = self.second.get(reverse("mfa_view_recovery_codes"))
            return response.status_code, self.code.encode() in response.content
        first, second_result = self._race(second)
        self.assertEqual(first[0], 200)
        self.assertEqual(second_result[0], 200)
        self.assertEqual(int(first[1]) + int(second_result[1]), 1, "Only one concurrent display may reveal codes.")

    def test_display_and_first_download_share_the_show_once_transition(self):
        def second():
            response = self.second.get(reverse("mfa_download_recovery_codes"))
            return response.status_code, self.code.encode() in response.content
        first, second_result = self._race(second)
        self.assertEqual(first[0], 200)
        self.assertIn(second_result[0], (200, 403))
        self.assertEqual(int(first[1]) + int(second_result[1]), 1, "Display and download must not both reveal the first set.")

    def test_view_write_cannot_restore_a_concurrently_consumed_recovery_code(self):
        def consume():
            factor = Authenticator.objects.get(pk=self.factor.pk)
            return factor.wrap().validate_code(self.code)
        first, used = self._race(consume)
        self.assertEqual(first[0], 200)
        self.assertTrue(used)
        current = Authenticator.objects.get(pk=self.factor.pk).wrap()
        self.assertFalse(current.validate_code(self.code), "A consumed recovery code must not be restored by a stale first-view write.")

    def test_missing_proof_cannot_mark_recovery_values_as_viewed(self):
        client = Client()
        client.force_login(self.user)
        for name in ("mfa_view_recovery_codes", "mfa_download_recovery_codes"):
            response = client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertFalse(Authenticator.objects.get(pk=self.factor.pk).wrap().did_view)
            self.assertFalse(self.code.encode() in response.content)
