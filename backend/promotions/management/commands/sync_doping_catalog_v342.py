"""Synchronize the canonical V342 doping product catalog."""

from django.core.management.base import BaseCommand

from promotions.doping_catalog_sync_v342 import (
    sync_doping_catalog_v342,
)


class Command(BaseCommand):
    help = "Create or update the canonical V342 doping catalog."

    def handle(self, *args, **options):
        result = sync_doping_catalog_v342()

        self.stdout.write(
            self.style.SUCCESS(
                "V342 doping catalog synchronized: "
                f"created={result['created']} "
                f"updated={result['updated']} "
                f"unchanged={result['unchanged']} "
                f"deactivated={result['deactivated']} "
                f"total={result['total']}."
            )
        )
