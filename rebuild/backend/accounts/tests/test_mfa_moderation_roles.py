from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from accounts.mfa_policy import requires_mfa
from accounts.models import User
from accounts.tests.mfa_support import MFATestIsolationMixin, authenticate_client


class CaseRoleMFATests(MFATestIsolationMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("case-role@example.test")
        EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)

    def test_new_role_requires_mfa_without_staff(self):
        for codename in ("review_reports", "review_appeals"):
            with self.subTest(role=codename):
                permission = Permission.objects.get(content_type__app_label="moderation", codename=codename)
                self.user.user_permissions.set([permission])
                self.client.logout()
                self.client.force_login(self.user)
                response = self.client.get(reverse("listings:dashboard"))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/accounts/", response["Location"])
                self.assertEqual(self.client.post(reverse("listings:dashboard")).status_code, 403)
                authenticate_client(self.client, self.user)
                self.assertEqual(self.client.get(reverse("listings:dashboard")).status_code, 200)

    def test_revocation_rechecks_current_permissions(self):
        for codename in ("review_reports", "review_appeals"):
            permission = Permission.objects.get(content_type__app_label="moderation", codename=codename)
            group = Group.objects.create(name=codename)
            group.permissions.add(permission)
            self.user.groups.add(group)
            cached = User.objects.get(pk=self.user.pk)
            self.assertTrue(requires_mfa(cached))
            self.assertTrue(cached.has_perm("moderation." + codename))
            group.permissions.clear()
            self.assertFalse(requires_mfa(cached))
