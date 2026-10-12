from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import AttributeSchema, Category


class Command(BaseCommand):
    help = "Seed the independent development catalog without deleting data."

    @transaction.atomic
    def handle(self, *args, **options):
        vehicles, _ = Category.objects.update_or_create(slug="vehicles", defaults={"name": "Vasıta", "parent": None})
        automobiles, _ = Category.objects.update_or_create(slug="automobiles", defaults={"name": "Otomobil", "parent": vehicles})
        property_category, _ = Category.objects.update_or_create(slug="property", defaults={"name": "Emlak", "parent": None})
        definitions = [
            (automobiles, {"fields": {
                "model_year": {"type": "integer", "required": True, "min": 1900, "max": 2100, "label": "Model yılı"},
                "mileage_km": {"type": "integer", "required": True, "min": 0, "max": 5000000, "label": "Kilometre"},
            }}),
            (property_category, {"fields": {
                "area_m2": {"type": "decimal", "required": True, "min": "0.01", "max": "100000000", "label": "Alan (m²)"},
                "room_count": {"type": "integer", "required": True, "min": 1, "max": 1000, "label": "Oda sayısı"},
            }}),
        ]
        for category, definition in definitions:
            AttributeSchema.objects.get_or_create(category=category, version=1, defaults={"definition": definition})
        self.stdout.write(self.style.SUCCESS("Geliştirme kategorileri hazır; mevcut şemalar korundu."))
