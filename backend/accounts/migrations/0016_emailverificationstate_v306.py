# Generated manually for v306 verified-recipient lifecycle foundation

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_email_verification_states_v306(
    apps,
    schema_editor,
):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")

    User = apps.get_model(
        app_label,
        model_name,
    )

    EmailVerificationState = apps.get_model(
        "accounts",
        "EmailVerificationState",
    )

    states = [
        EmailVerificationState(
            user_id=user.pk,
            email_snapshot=str(
                getattr(user, "email", "")
                or ""
            ).strip(),
        )
        for user in User.objects.all().iterator(
            chunk_size=500
        )
    ]

    if states:
        EmailVerificationState.objects.bulk_create(
            states,
            batch_size=500,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0015_seller_store_branding"),
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailVerificationState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "email_snapshot",
                    models.EmailField(
                        blank=True,
                        default="",
                        max_length=254,
                    ),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "verification_method",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=40,
                    ),
                ),
                (
                    "token_version",
                    models.PositiveBigIntegerField(
                        default=0,
                    ),
                ),
                (
                    "last_requested_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=(
                            django.db.models.deletion.CASCADE
                        ),
                        related_name=(
                            "email_verification_state"
                        ),
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            backfill_email_verification_states_v306,
            migrations.RunPython.noop,
        ),
    ]
