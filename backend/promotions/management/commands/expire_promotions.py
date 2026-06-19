from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models import Listing
from promotions.models import ListingPromotion


class Command(BaseCommand):
    help = "Expire old promotion records and clear expired listing promotion fields."

    def handle(self, *args, **options):
        now = timezone.now()

        expired_promotions = ListingPromotion.objects.filter(
            status=ListingPromotion.Status.ACTIVE,
            ends_at__isnull=False,
            ends_at__lte=now,
        )

        promotion_count = expired_promotions.update(
            status=ListingPromotion.Status.EXPIRED,
        )

        top_count = Listing.objects.filter(
            top_listing_until__isnull=False,
            top_listing_until__lte=now,
        ).update(
            top_listing_priority=0,
            top_listing_until=None,
        )

        featured_count = Listing.objects.filter(
            is_featured=True,
            featured_until__isnull=False,
            featured_until__lte=now,
        ).update(
            is_featured=False,
            featured_priority=0,
            featured_until=None,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {promotion_count} promotion(s), "
                f"cleared {top_count} top listing(s), "
                f"cleared {featured_count} featured listing(s)."
            )
        )
