import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('events', '0002_publicationboundary_eventconsumption'), ('listings', '0006_favorite'),
                    ('notifications', '0001_initial'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='savedsearch', name='notification_boundary', field=models.PositiveBigIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='savedsearch', name='notification_error', field=models.CharField(blank=True, max_length=40)),
        migrations.AddField(model_name='savedsearch', name='notifications_enabled', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='savedsearch', name='notifications_enabled_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(name='NotificationDelivery', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('channel', models.CharField(default='in_app', editable=False, max_length=12)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('read_at', models.DateTimeField(blank=True, null=True)),
            ('archived_at', models.DateTimeField(blank=True, null=True)),
            ('event', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='events.outboxevent')),
            ('listing', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='listings.listing')),
            ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-created_at', '-pk']}),
        migrations.CreateModel(name='NotificationMatch', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('boundary', models.PositiveBigIntegerField()),
            ('delivery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='notifications.notificationdelivery')),
            ('search', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='notifications.savedsearch')),
        ]),
        migrations.AddIndex(model_name='notificationdelivery', index=models.Index(fields=['recipient', '-created_at', '-id'], name='notification_recipient_recent')),
        migrations.AddConstraint(model_name='notificationdelivery', constraint=models.UniqueConstraint(fields=('event', 'recipient', 'channel'), name='notification_event_recipient_channel')),
        migrations.AddConstraint(model_name='notificationdelivery', constraint=models.CheckConstraint(condition=models.Q(channel='in_app'), name='notification_in_app_only')),
        migrations.AddConstraint(model_name='notificationmatch', constraint=models.UniqueConstraint(fields=('delivery', 'search', 'boundary'), name='notification_match_unique')),
    ]
