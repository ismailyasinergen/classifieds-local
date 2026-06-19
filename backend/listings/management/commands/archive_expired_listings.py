from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models import Listing


class Command(BaseCommand):
    help = "Archive approved listings whose expiry date has passed."

    def handle(self, *args, **options):
        queryset = Listing.objects.filter(
            status=Listing.Status.APPROVED,
            expires_at__isnull=False,
            expires_at__lte=timezone.now(),
        )

        count = queryset.update(status=Listing.Status.ARCHIVED)

        self.stdout.write(
            self.style.SUCCESS(f"Archived {count} expired listing(s).")
        )
