import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_securityevent")]
    operations = [
        migrations.CreateModel(
            name="Storefront",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("draft_name", models.CharField(max_length=80)),
                ("draft_intro", models.TextField(blank=True, max_length=2000)),
                ("published_name", models.CharField(blank=True, max_length=80)),
                ("published_intro", models.TextField(blank=True, max_length=2000)),
                ("is_published", models.BooleanField(default=False)),
                ("edit_version", models.PositiveBigIntegerField(default=1)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                    related_name="storefront", to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [
                models.CheckConstraint(condition=models.Q(edit_version__gte=1), name="storefront_version_positive"),
                models.CheckConstraint(condition=models.Q(draft_name__regex=r"\S"), name="storefront_draft_name_present"),
                models.CheckConstraint(condition=models.Q(is_published=False) | (
                    models.Q(published_name__regex=r"\S") & models.Q(published_at__isnull=False)),
                    name="storefront_public_snapshot_present"),
            ]},
        ),
    ]
