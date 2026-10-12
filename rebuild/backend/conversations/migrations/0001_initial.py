import uuid

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("listings", "0004_listing_contact_enabled"),
        ("moderation", "0002_messagingrestriction"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("subject", models.CharField(max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_message_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_sequence", models.PositiveBigIntegerField(default=0)),
                ("initiator", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                               related_name="initiated_conversations", to=settings.AUTH_USER_MODEL)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                               related_name="received_conversations", to=settings.AUTH_USER_MODEL)),
                ("listing", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                             related_name="conversations", to="listings.listing")),
            ],
            options={
                "ordering": ["-last_message_at", "-pk"],
                "constraints": [
                    models.UniqueConstraint(fields=("listing", "initiator"),
                                            name="conversations_listing_initiator_unique"),
                    models.CheckConstraint(condition=~models.Q(initiator=models.F("recipient")),
                                           name="conversations_distinct_parties"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveBigIntegerField()),
                ("body", models.TextField(validators=[django.core.validators.MaxLengthValidator(4000)])),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("client_token", models.UUIDField()),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="messages", to="conversations.conversation")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                            related_name="conversation_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-sequence"],
                "constraints": [
                    models.UniqueConstraint(fields=("conversation", "sequence"),
                                            name="conversations_message_sequence_unique"),
                    models.UniqueConstraint(fields=("conversation", "sender", "client_token"),
                                            name="conversations_message_token_unique"),
                    models.CheckConstraint(condition=models.Q(sequence__gte=1),
                                           name="conversations_message_positive_sequence"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Participant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_read_sequence", models.PositiveBigIntegerField(default=0)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                  related_name="participants", to="conversations.conversation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                          related_name="conversation_participations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("conversation", "user"), name="conversations_participant_unique"),
                ],
            },
        ),
        migrations.CreateModel(
            name="UserBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("blocked", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                             related_name="received_user_blocks", to=settings.AUTH_USER_MODEL)),
                ("blocker", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                             related_name="placed_user_blocks", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("blocker", "blocked"), name="conversations_userblock_unique"),
                    models.CheckConstraint(condition=~models.Q(blocker=models.F("blocked")),
                                           name="conversations_userblock_distinct_users"),
                ],
            },
        ),
    ]
