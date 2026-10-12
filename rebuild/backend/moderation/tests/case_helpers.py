from uuid import uuid4

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Permission

from accounts.models import User
from conversations.services import start_conversation
from listings.tests.test_publication import PublicationFixtures


class CaseFixtures(PublicationFixtures):
    def setUp(self):
        super().setUp()
        self.reporter = self.case_user()
        self.case_reviewer = self.case_user()
        self.appeal_reviewer = self.case_user()
        for user in (self.owner, self.reviewer):
            EmailAddress.objects.get_or_create(
                user=user, email=user.email, defaults={"verified": True, "primary": True})
        self.public = self.publish()
        self.listing = self.public.listing
        self.message = start_conversation(
            actor=self.reporter, listing_id=self.listing.pk,
            body="Sentetik mesaj", client_token=uuid4())
        self.conversation = self.message.conversation

    def case_user(self, **kwargs):
        user = User.objects.create_user(f"case-{uuid4().hex}@example.test", **kwargs)
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        return user

    def grant(self, user, codename):
        permission = Permission.objects.get(content_type__app_label="moderation", codename=codename)
        user.user_permissions.add(permission)
        return permission
