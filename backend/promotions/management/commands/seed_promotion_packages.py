from django.core.management.base import BaseCommand

from promotions.models import PromotionPackage


class Command(BaseCommand):
    help = "Create demo promotion packages."

    def handle(self, *args, **options):
        packages = [
            {
                "name": "Featured 7 days",
                "package_type": PromotionPackage.PackageType.FEATURED,
                "duration_days": 7,
                "price": "199.00",
                "priority": 50,
            },
            {
                "name": "Featured 30 days",
                "package_type": PromotionPackage.PackageType.FEATURED,
                "duration_days": 30,
                "price": "499.00",
                "priority": 75,
            },
            {
                "name": "Top Listing 7 days",
                "package_type": PromotionPackage.PackageType.TOP,
                "duration_days": 7,
                "price": "299.00",
                "priority": 100,
            },
            {
                "name": "Top Listing 30 days",
                "package_type": PromotionPackage.PackageType.TOP,
                "duration_days": 30,
                "price": "799.00",
                "priority": 150,
            },
        ]

        for package_data in packages:
            PromotionPackage.objects.update_or_create(
                name=package_data["name"],
                defaults=package_data,
            )

        self.stdout.write(self.style.SUCCESS("Promotion packages seeded."))
