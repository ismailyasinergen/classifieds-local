import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('events', '0001_initial')]
    operations = [
        migrations.CreateModel(name='PublicationBoundary', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('value', models.PositiveBigIntegerField(default=0)),
        ]),
        migrations.CreateModel(name='EventConsumption', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('consumer', models.CharField(max_length=40)),
            ('status', models.CharField(db_index=True, default='pending', max_length=12)),
            ('recipient_cursor', models.PositiveBigIntegerField(default=0)),
            ('attempts', models.PositiveSmallIntegerField(default=0)),
            ('next_attempt_at', models.DateTimeField(blank=True, null=True)),
            ('reason', models.CharField(blank=True, max_length=40)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('event', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consumptions', to='events.outboxevent')),
        ], options={'constraints': [models.UniqueConstraint(fields=('event', 'consumer'), name='events_consumer_event_unique')]}),
    ]
