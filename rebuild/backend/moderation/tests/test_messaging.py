from datetime import timedelta

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from conversations.policies import require_can_start
from conversations.tests.helpers import ConversationFixtures
from moderation.messaging import messaging_restrictions, restrict_messaging, revoke_messaging_restriction
from moderation.models import MessagingRestriction
from moderation.policies import visible_listings


class MessagingRestrictionTests(ConversationFixtures, TestCase):
    def permit(self):
        permission = Permission.objects.get(content_type__app_label="moderation", codename="restrict_messaging")
        self.buyer.user_permissions.add(permission)
        return permission

    def test_exact_begin_end_and_any_revocation(self):
        at = timezone.now()
        restriction = MessagingRestriction.objects.create(
            user=self.seller, actor=self.outsider, reason="Private",
            begins_at=at, ends_at=at + timedelta(seconds=1))
        self.assertFalse(messaging_restrictions(at=at - timedelta(microseconds=1)).exists())
        self.assertTrue(messaging_restrictions(at=at).filter(pk=restriction.pk).exists())
        self.assertFalse(messaging_restrictions(at=restriction.ends_at).exists())
        self.listing.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            require_can_start(actor=self.buyer, listing=self.listing, at=at)
        require_can_start(actor=self.buyer, listing=self.listing, at=restriction.ends_at)
        restriction.revoked_at = at + timedelta(days=1)
        restriction.save()
        self.assertFalse(messaging_restrictions(at=at).exists())
        require_can_start(actor=self.buyer, listing=self.listing, at=at)

    def test_staff_alone_denied_explicit_permission_and_fresh_revocation(self):
        self.buyer.is_staff = True
        self.buyer.save()
        with self.assertRaises(PermissionDenied):
            restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason="Valid")
        permission = self.permit()
        # Populate caller permission cache; mutation must use a fresh User.
        self.assertTrue(User.objects.get(pk=self.buyer.pk).has_perm("moderation.restrict_messaging"))
        cached = User.objects.get(pk=self.buyer.pk)
        self.assertTrue(cached.has_perm("moderation.restrict_messaging"))
        restriction = restrict_messaging(actor=cached, user_id=self.seller.pk, reason="  Gerekçe  ")
        self.assertEqual(restriction.reason, "Gerekçe")
        self.assertEqual(restriction.actor_id, self.buyer.pk)
        self.assertTrue(messaging_restrictions().filter(pk=restriction.pk).exists())
        self.buyer.user_permissions.remove(permission)
        for call in [
            lambda: restrict_messaging(actor=cached, user_id=self.seller.pk, reason="Valid"),
            lambda: revoke_messaging_restriction(actor=cached, restriction_id=restriction.pk),
        ]:
            with self.assertRaises(PermissionDenied):
                call()

    def test_reason_and_aware_interval_validation_atomic(self):
        self.permit()
        for reason in ["", "  ", "x" * 2001, None]:
            with self.assertRaises(ValidationError):
                restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason=reason)
        for ends_at in [timezone.now() - timedelta(seconds=1), timezone.now().replace(tzinfo=None), "later"]:
            with self.assertRaises(ValidationError):
                restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason="Valid", ends_at=ends_at)
        self.assertEqual(MessagingRestriction.objects.count(), 0)
        restriction = restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason="x" * 2000)
        self.assertEqual(len(restriction.reason), 2000)

    def test_revoke_idempotence_and_public_visibility_independence(self):
        self.permit()
        restriction = restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason="Private")
        self.assertTrue(visible_listings().filter(pk=self.listing.pk).exists())
        first = revoke_messaging_restriction(actor=self.buyer, restriction_id=restriction.pk)
        second = revoke_messaging_restriction(actor=self.buyer, restriction_id=restriction.pk)
        self.assertEqual(first.revoked_at, second.revoked_at)
        self.assertFalse(messaging_restrictions().exists())

    def test_inactive_stale_actor_and_missing_target_are_denied(self):
        self.permit()
        with self.assertRaises(User.DoesNotExist):
            restrict_messaging(actor=self.buyer, user_id=999999, reason="Valid")
        User.objects.filter(pk=self.buyer.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason="Valid")

    def test_database_interval_and_nonblank_reason_constraints(self):
        for values in [
            dict(reason="   "),
            dict(reason="Valid", ends_at=timezone.now() - timedelta(days=1)),
        ]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                MessagingRestriction.objects.create(user=self.seller, actor=self.outsider, **values)
