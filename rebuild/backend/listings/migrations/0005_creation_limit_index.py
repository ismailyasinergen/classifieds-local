from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0004_listing_contact_enabled")]

    operations = [
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(fields=["owner", "-created_at", "-id"], name="listing_owner_recent_idx"),
        ),
    ]
