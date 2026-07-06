from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import models
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import (
    ModerationAppeal,
    ModerationAppealAttachment,
    ModerationNotice,
    UserProfile,
)


class PrivateMediaProtectionTests(TestCase):
    password = "Testpass12345"

    def setUp(self):
        self.owner = self._create_user("private-owner@classifieds.local")
        self.other_user = self._create_user("private-other@classifieds.local")
        self.admin = self._create_user(
            "private-admin@classifieds.local",
            is_staff=True,
            is_superuser=True,
        )

        self.anon_client = Client(HTTP_HOST="localhost")
        self.owner_client = Client(HTTP_HOST="localhost")
        self.other_client = Client(HTTP_HOST="localhost")
        self.admin_client = Client(HTTP_HOST="localhost")

        self.owner_client.force_login(self.owner)
        self.other_client.force_login(self.other_user)
        self.admin_client.force_login(self.admin)

        self.created_media_names = []

    def tearDown(self):
        for name in self.created_media_names:
            path = Path(settings.MEDIA_ROOT) / name
            if path.exists():
                path.unlink()

    def _create_user(self, email, is_staff=False, is_superuser=False):
        User = get_user_model()
        username_field = User.USERNAME_FIELD

        kwargs = {username_field: email}
        if username_field != "email" and any(field.name == "email" for field in User._meta.fields):
            kwargs["email"] = email

        user = User.objects.create_user(password=self.password, **kwargs)
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save(update_fields=["is_staff", "is_superuser"])
        return user

    def _profile_with_private_document(self):
        profile, _created = UserProfile.objects.get_or_create(user=self.owner)
        profile.verification_document.save(
            "private-media-protection-test.jpg",
            ContentFile(b"private verification document test bytes"),
            save=True,
        )
        self.created_media_names.append(profile.verification_document.name)
        return profile

    def _appeal_attachment_with_private_file(self):
        notice = ModerationNotice.objects.create(
            recipient=self.owner,
            title="Private evidence notice",
            body="Private evidence body.",
            notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
        )

        appeal_kwargs = {
            "appellant": self.owner,
            "moderation_notice": notice,
        }

        for field in ModerationAppeal._meta.concrete_fields:
            if field.name in appeal_kwargs:
                continue

            if field.primary_key or getattr(field, "auto_created", False):
                continue

            if field.has_default() or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue

            if field.null or field.blank:
                continue

            if isinstance(field, models.CharField):
                if field.choices:
                    appeal_kwargs[field.name] = field.choices[0][0]
                else:
                    appeal_kwargs[field.name] = "Private evidence appeal"
            elif isinstance(field, models.TextField):
                appeal_kwargs[field.name] = "Private evidence appeal reason."
            elif isinstance(field, models.BooleanField):
                appeal_kwargs[field.name] = False
            elif isinstance(field, models.IntegerField):
                appeal_kwargs[field.name] = 1
            elif isinstance(field, models.DateTimeField):
                appeal_kwargs[field.name] = timezone.now()
            elif isinstance(field, models.DateField):
                appeal_kwargs[field.name] = timezone.localdate()

        appeal = ModerationAppeal.objects.create(**appeal_kwargs)

        attachment = ModerationAppealAttachment.objects.create(
            appeal=appeal,
            original_name="private-evidence.pdf",
            content_type="application/pdf",
            size=32,
        )
        attachment.file.save(
            "private-evidence.pdf",
            ContentFile(b"private appeal evidence test bytes"),
            save=True,
        )
        self.created_media_names.append(attachment.file.name)
        return attachment

    def _direct_media_url(self, file_name):
        return f"{settings.MEDIA_URL.rstrip('/')}/{file_name}"

    def test_private_verification_document_is_not_directly_served_from_media(self):
        profile = self._profile_with_private_document()

        response = self.anon_client.get(
            self._direct_media_url(profile.verification_document.name),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    def test_private_verification_document_download_requires_authorized_user(self):
        profile = self._profile_with_private_document()
        url = reverse(
            "accounts:private_file_download",
            args=[
                "accounts",
                "userprofile",
                profile.pk,
                "verification_document",
            ],
        )

        anonymous_response = self.anon_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(anonymous_response.status_code, 302)

        other_response = self.other_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(other_response.status_code, 404)

        owner_response = self.owner_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response["Cache-Control"], "private, no-store")
        self.assertEqual(owner_response["X-Content-Type-Options"], "nosniff")

        admin_response = self.admin_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(admin_response["Cache-Control"], "private, no-store")
        self.assertEqual(admin_response["X-Content-Type-Options"], "nosniff")

    def test_private_appeal_attachment_is_not_directly_served_from_media(self):
        attachment = self._appeal_attachment_with_private_file()

        response = self.anon_client.get(
            self._direct_media_url(attachment.file.name),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    def test_private_appeal_attachment_download_requires_authorized_user(self):
        attachment = self._appeal_attachment_with_private_file()
        url = reverse("accounts:moderation_appeal_attachment_download", args=[attachment.pk])

        anonymous_response = self.anon_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(anonymous_response.status_code, 302)

        other_response = self.other_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(other_response.status_code, 404)

        owner_response = self.owner_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response["Cache-Control"], "private, no-store")
        self.assertEqual(owner_response["X-Content-Type-Options"], "nosniff")

        admin_response = self.admin_client.get(url, HTTP_HOST="localhost")
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(admin_response["Cache-Control"], "private, no-store")
        self.assertEqual(admin_response["X-Content-Type-Options"], "nosniff")
