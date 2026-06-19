from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


DEMO_USERS = [
    {
        "label": "Admin",
        "username": "admin@classifieds.local",
        "email": "admin@classifieds.local",
        "password": "Testpass12345",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "label": "Seller",
        "username": "demo_seller@classifieds.local",
        "email": "demo_seller@classifieds.local",
        "password": "demo12345",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "label": "Buyer",
        "username": "buyer1@classifieds.local",
        "email": "buyer1@classifieds.local",
        "password": "Testpass12345",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "label": "Appeal deadline seller",
        "username": "appeal_deadline_seller@classifieds.local",
        "email": "appeal_deadline_seller@classifieds.local",
        "password": "Testpass12345",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "label": "Appeal stage seller",
        "username": "appeal_stage_seller@classifieds.local",
        "email": "appeal_stage_seller@classifieds.local",
        "password": "Testpass12345",
        "is_staff": False,
        "is_superuser": False,
    },
]


class Command(BaseCommand):
    help = "Create or reset local demo users with known passwords."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        for data in DEMO_USERS:
            username = data["username"]
            email = data["email"]

            user = (
                User.objects.filter(username__iexact=username).first()
                or User.objects.filter(email__iexact=email).first()
            )

            created = False
            if user is None:
                user = User(username=username)
                created = True

            user.username = username
            user.email = email
            user.is_active = True
            user.is_staff = data["is_staff"]
            user.is_superuser = data["is_superuser"]
            user.set_password(data["password"])
            user.save()

            status = "created" if created else "reset"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{data['label']}: {status} {email} / {data['password']}"
                )
            )
