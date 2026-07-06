from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import SellerStore


class Command(BaseCommand):
    help = "Create SellerStore rows for existing sellers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all-users",
            action="store_true",
            help="Create stores for all users, not only users with listings.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without writing to the database.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        if options["all_users"]:
            users = User.objects.all().order_by("id")
        else:
            users = User.objects.filter(listings__isnull=False).distinct().order_by("id")

        created_count = 0
        skipped_count = 0

        for user in users.iterator():
            if SellerStore.objects.filter(owner=user).exists():
                skipped_count += 1
                continue

            created_count += 1

            if options["dry_run"]:
                self.stdout.write(f"Would create store for {user.get_username()}")
                continue

            SellerStore.objects.create(owner=user)
            self.stdout.write(f"Created store for {user.get_username()}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run complete. Would create {created_count} store(s); skipped {skipped_count} existing store(s)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backfill complete. Created {created_count} store(s); skipped {skipped_count} existing store(s)."
                )
            )
