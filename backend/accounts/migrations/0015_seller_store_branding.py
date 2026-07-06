# Generated manually for v108 seller store branding

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_seller_store"),
    ]

    operations = [
        migrations.AddField(
            model_name="sellerstore",
            name="logo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="seller_store_logos/",
            ),
        ),
        migrations.AddField(
            model_name="sellerstore",
            name="banner",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="seller_store_banners/",
            ),
        ),
    ]
