from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from categories.models import Category
from listings.models import Listing


class Command(BaseCommand):
    help = "Seed demo categories and listings for local development."

    def handle(self, *args, **options):
        User = get_user_model()

        seller, _ = User.objects.get_or_create(
            username="demo_seller",
            defaults={
                "email": "seller1@classifieds.local",
            },
        )
        seller.set_password("demo12345")
        seller.save()

        def category(name, slug, parent=None):
            obj, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "parent": parent,
                },
            )
            return obj

        vehicles = category("Vehicles", "vehicles")
        cars = category("Cars", "cars", vehicles)
        motorcycles = category("Motorcycles", "motorcycles", vehicles)
        commercial = category("Commercial Vehicles", "commercial-vehicles", vehicles)

        real_estate = category("Real Estate", "real-estate")
        homes_for_sale = category("Homes for Sale", "homes-for-sale", real_estate)
        homes_for_rent = category("Homes for Rent", "homes-for-rent", real_estate)
        land = category("Land", "land", real_estate)

        electronics = category("Electronics", "electronics")
        phones = category("Phones", "phones", electronics)
        computers = category("Computers", "computers", electronics)
        cameras = category("Cameras", "cameras", electronics)

        home_garden = category("Home & Garden", "home-garden")
        furniture = category("Furniture", "furniture", home_garden)
        appliances = category("Appliances", "appliances", home_garden)

        listings = [
            {
                "title": "2015 Volkswagen Golf",
                "description": "Clean local car. Manual transmission. Good condition.",
                "price": "12500.00",
                "category": cars,
                "location": "Istanbul",
                "is_featured": True,
            },
            {
                "title": "Family SUV",
                "description": "Spacious SUV suitable for families.",
                "price": "22000.00",
                "category": cars,
                "location": "Izmir",
                "is_featured": False,
            },
            {
                "title": "Yamaha MT-07",
                "description": "Well-maintained motorcycle with low mileage.",
                "price": "7800.00",
                "category": motorcycles,
                "location": "Antalya",
                "is_featured": True,
            },
            {
                "title": "Ford Transit Van",
                "description": "Commercial van ready for work.",
                "price": "18500.00",
                "category": commercial,
                "location": "Bursa",
                "is_featured": False,
            },
            {
                "title": "2+1 Apartment for Sale",
                "description": "Bright apartment close to public transport.",
                "price": "185000.00",
                "category": homes_for_sale,
                "location": "Ankara",
                "is_featured": False,
            },
            {
                "title": "Studio Flat for Rent",
                "description": "Central location, suitable for students.",
                "price": "650.00",
                "category": homes_for_rent,
                "location": "Eskisehir",
                "is_featured": False,
            },
            {
                "title": "Small Land Plot",
                "description": "Affordable land plot near main road.",
                "price": "42000.00",
                "category": land,
                "location": "Balikesir",
                "is_featured": False,
            },
            {
                "title": "iPhone 14 Pro",
                "description": "Good condition, original box included.",
                "price": "850.00",
                "category": phones,
                "location": "Istanbul",
                "is_featured": True,
            },
            {
                "title": "Gaming Laptop",
                "description": "RTX graphics card, 16GB RAM, 1TB SSD.",
                "price": "1350.00",
                "category": computers,
                "location": "Bursa",
                "is_featured": False,
            },
            {
                "title": "Canon DSLR Camera",
                "description": "Camera body with kit lens.",
                "price": "500.00",
                "category": cameras,
                "location": "Izmir",
                "is_featured": False,
            },
            {
                "title": "Dining Table Set",
                "description": "Table with six chairs.",
                "price": "300.00",
                "category": furniture,
                "location": "Istanbul",
                "is_featured": False,
            },
            {
                "title": "Washing Machine",
                "description": "Working condition. Buyer collects.",
                "price": "250.00",
                "category": appliances,
                "location": "Ankara",
                "is_featured": False,
            },
        ]

        created_count = 0
        updated_count = 0

        for item in listings:
            listing, created = Listing.objects.update_or_create(
                title=item["title"],
                owner=seller,
                defaults={
                    "description": item["description"],
                    "price": item["price"],
                    "category": item["category"],
                    "location": item["location"],
                    "is_featured": item["is_featured"],
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Created {created_count}, updated {updated_count} listings."
            )
        )