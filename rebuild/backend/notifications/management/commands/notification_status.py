import json
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count
from events.models import EventConsumption
from notifications.consumer import CONSUMER


class Command(BaseCommand):
    help = 'Uygulama içi tüketicinin yalnız aggregate kalıcı durum sayıları.'

    def handle(self, **options):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION READ ONLY')
                cursor.execute("SET LOCAL statement_timeout = '3s'")
                cursor.execute("SET LOCAL lock_timeout = '1s'")
            counts = {status: 0 for status in ['pending', 'retry', 'completed', 'skipped', 'failed']}
            counts.update({row['status']: row['total'] for row in EventConsumption.objects.filter(
                consumer=CONSUMER).values('status').annotate(total=Count('pk'))})
        self.stdout.write(json.dumps(counts))
