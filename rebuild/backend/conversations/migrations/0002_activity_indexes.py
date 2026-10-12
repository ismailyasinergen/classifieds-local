from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("conversations", "0001_initial")]

    operations = [
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["initiator", "-created_at", "-id"], name="contact_actor_recent_idx"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["sender", "-created_at", "-id"], name="message_actor_recent_idx"),
        ),
    ]
