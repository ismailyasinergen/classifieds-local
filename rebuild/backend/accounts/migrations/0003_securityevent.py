from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_user_email_user_accounts_user_email_ci_unique_and_more"),
    ]
    operations = [
        migrations.CreateModel(
            name="SecurityEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("activated", "Etkinleştirme"), ("used", "Başarılı doğrulama"), ("failed", "Başarısız doğrulama"), ("removed", "Cihaz kaldırma"), ("recovery_regenerated", "Kurtarma kodlarını yenileme")], max_length=32)),
                ("method", models.CharField(choices=[("totp", "Doğrulama uygulaması"), ("recovery_codes", "Kurtarma kodu")], max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at", "-pk")},
        ),
    ]
