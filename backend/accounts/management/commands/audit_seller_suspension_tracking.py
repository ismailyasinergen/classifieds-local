from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.models import UserProfile
from listings.models import Listing


class Command(BaseCommand):
    help = "Audit and optionally repair seller suspension listing tracking."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix-active-suspended-sellers",
            action="store_true",
            help="Hide active listings for sellers who are currently suspended.",
        )
        parser.add_argument(
            "--restore-lifted-sellers",
            action="store_true",
            help="Restore only seller-hidden listings for sellers whose suspension is no longer active.",
        )

    def handle(self, *args, **options):
        fix_active = options["fix_active_suspended_sellers"]
        restore_lifted = options["restore_lifted_sellers"]

        total_warnings = 0
        total_repairs = 0

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("Seller suspension tracking audit"))
        self.stdout.write("=" * 42)

        invalid_seller_hidden = Listing.objects.filter(
            suspended_due_to_seller=True,
        ).exclude(
            status=Listing.Status.SUSPENDED,
        )

        if invalid_seller_hidden.exists():
            total_warnings += invalid_seller_hidden.count()
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("WARNING: seller-hidden flag on non-suspended listings"))
            for listing in invalid_seller_hidden.select_related("owner"):
                self.stdout.write(
                    f"  Listing #{listing.pk}: {listing.title} | owner={listing.owner.username} | status={listing.status}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("OK: no non-suspended listings have seller-hidden flag."))

        unknown_previous_status = Listing.objects.filter(
            status=Listing.Status.SUSPENDED,
            suspended_due_to_seller=True,
        ).exclude(
            status_before_seller_suspension__in=[
                Listing.Status.APPROVED,
                Listing.Status.PENDING,
            ]
        )

        if unknown_previous_status.exists():
            total_warnings += unknown_previous_status.count()
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("WARNING: seller-hidden suspended listings with unknown previous status"))
            for listing in unknown_previous_status.select_related("owner"):
                self.stdout.write(
                    f"  Listing #{listing.pk}: {listing.title} | owner={listing.owner.username} | before={listing.status_before_seller_suspension!r}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("OK: all seller-hidden suspended listings have a known previous status."))

        suspended_profiles = [
            profile
            for profile in UserProfile.objects.select_related("user")
            if profile.is_seller_suspended
        ]

        self.stdout.write("")
        self.stdout.write(f"Currently suspended sellers: {len(suspended_profiles)}")

        for profile in suspended_profiles:
            seller = profile.user
            active_listings = Listing.objects.filter(
                owner=seller,
                status__in=[
                    Listing.Status.APPROVED,
                    Listing.Status.PENDING,
                ],
            )

            if active_listings.exists():
                total_warnings += active_listings.count()
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        f"WARNING: suspended seller still has active listings: {seller.username}"
                    )
                )

                for listing in active_listings:
                    self.stdout.write(
                        f"  Active listing #{listing.pk}: {listing.title} | status={listing.status}"
                    )

                if fix_active:
                    approved_count = active_listings.filter(
                        status=Listing.Status.APPROVED,
                    ).update(
                        status=Listing.Status.SUSPENDED,
                        suspended_due_to_seller=True,
                        status_before_seller_suspension=Listing.Status.APPROVED,
                    )

                    pending_count = Listing.objects.filter(
                        owner=seller,
                        status=Listing.Status.PENDING,
                    ).update(
                        status=Listing.Status.SUSPENDED,
                        suspended_due_to_seller=True,
                        status_before_seller_suspension=Listing.Status.PENDING,
                    )

                    repaired = approved_count + pending_count
                    total_repairs += repaired

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Repaired: hid {repaired} active listing(s) for suspended seller {seller.username}."
                        )
                    )

        lifted_profiles = [
            profile
            for profile in UserProfile.objects.select_related("user")
            if not profile.is_seller_suspended
        ]

        lifted_seller_hidden = Listing.objects.filter(
            owner__in=[profile.user for profile in lifted_profiles],
            status=Listing.Status.SUSPENDED,
            suspended_due_to_seller=True,
        )

        if lifted_seller_hidden.exists():
            total_warnings += lifted_seller_hidden.count()
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: seller-hidden listings exist for sellers who are not currently suspended"
                )
            )

            for listing in lifted_seller_hidden.select_related("owner"):
                self.stdout.write(
                    f"  Listing #{listing.pk}: {listing.title} | owner={listing.owner.username} | before={listing.status_before_seller_suspension}"
                )

            if restore_lifted:
                restored_approved = lifted_seller_hidden.filter(
                    status_before_seller_suspension=Listing.Status.APPROVED,
                ).update(
                    status=Listing.Status.APPROVED,
                    suspended_due_to_seller=False,
                    status_before_seller_suspension="",
                )

                restored_pending = Listing.objects.filter(
                    owner__in=[profile.user for profile in lifted_profiles],
                    status=Listing.Status.SUSPENDED,
                    suspended_due_to_seller=True,
                    status_before_seller_suspension=Listing.Status.PENDING,
                ).update(
                    status=Listing.Status.PENDING,
                    suspended_due_to_seller=False,
                    status_before_seller_suspension="",
                )

                repaired = restored_approved + restored_pending
                total_repairs += repaired

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Repaired: restored {repaired} seller-hidden listing(s) for lifted sellers."
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS("OK: no seller-hidden listings remain for lifted sellers."))

        listing_level_suspended_count = Listing.objects.filter(
            status=Listing.Status.SUSPENDED,
            suspended_due_to_seller=False,
        ).count()

        seller_hidden_count = Listing.objects.filter(
            status=Listing.Status.SUSPENDED,
            suspended_due_to_seller=True,
        ).count()

        self.stdout.write("")
        self.stdout.write("Summary")
        self.stdout.write("-" * 42)
        self.stdout.write(f"Listing-level suspended listings: {listing_level_suspended_count}")
        self.stdout.write(f"Seller-hidden suspended listings: {seller_hidden_count}")
        self.stdout.write(f"Warnings found: {total_warnings}")
        self.stdout.write(f"Repairs performed: {total_repairs}")

        if total_warnings == 0:
            self.stdout.write(self.style.SUCCESS("Audit passed. Tracking is clean."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Audit finished with warnings. Run with repair flags only if the warnings match the intended workflow."
                )
            )
