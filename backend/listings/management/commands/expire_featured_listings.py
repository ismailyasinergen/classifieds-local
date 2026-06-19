from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models import Listing


class Command(BaseCommand):
    help = "Remove featured placement from listings whose featured date has expired."

    def handle(self, *args, **options):
        queryset = Listing.objects.filter(
            is_featured=True,
            featured_until__isnull=False,
            featured_until__lte=timezone.now(),
        )

        count = queryset.update(
            is_featured=False,
            featured_priority=0,
            featured_until=None,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Expired featured placement for {count} listing(s).")
        )
