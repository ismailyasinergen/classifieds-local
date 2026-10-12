from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0003_public_search_indexes")]
    operations = [
        migrations.AddField(
            model_name="listing", name="contact_enabled", field=models.BooleanField(default=True, db_default=True)),
    ]
