import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="MessagingRestriction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField(validators=[django.core.validators.MaxLengthValidator(2000)])),
                ("begins_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                           related_name="issued_messaging_restrictions", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                          related_name="messaging_restrictions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "-pk"],
                "permissions": [("restrict_messaging", "Can restrict account messaging")],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(reason__regex=r"\S"),
                                           name="moderation_messaging_reason_not_blank"),
                    models.CheckConstraint(
                        condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=models.F("begins_at")),
                        name="moderation_messaging_valid_interval"),
                ],
            },
        ),
    ]
