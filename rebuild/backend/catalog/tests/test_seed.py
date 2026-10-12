from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from catalog.models import AttributeSchema, Category
from catalog.validation import validate_attributes


class SeedCatalogTests(TestCase):
    def test_seed_is_idempotent_and_typed(self):
        call_command("seed_catalog", stdout=StringIO())
        first_ids = list(AttributeSchema.objects.values_list("pk", flat=True))
        call_command("seed_catalog", stdout=StringIO())
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(AttributeSchema.objects.count(), 2)
        self.assertEqual(list(AttributeSchema.objects.values_list("pk", flat=True)), first_ids)
        vehicle = AttributeSchema.objects.get(category__slug="automobiles", version=1)
        self.assertEqual(validate_attributes(schema=vehicle, values={"model_year": "2021", "mileage_km": "150000"}),
                         {"model_year": 2021, "mileage_km": 150000})
        property_schema = AttributeSchema.objects.get(category__slug="property", version=1)
        self.assertEqual(validate_attributes(schema=property_schema, values={"area_m2": "90.50", "room_count": "3"}),
                         {"area_m2": "90.5", "room_count": 3})

    def test_seed_preserves_user_categories_and_schemas(self):
        category = Category.objects.create(name="Kullanıcı kategorisi", slug="user-category")
        schema = AttributeSchema.objects.create(category=category, version=1, definition={"fields": {}})
        call_command("seed_catalog", stdout=StringIO())
        category.refresh_from_db()
        schema.refresh_from_db()
        self.assertEqual(category.name, "Kullanıcı kategorisi")
        self.assertEqual(schema.definition, {"fields": {}})
        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(AttributeSchema.objects.count(), 3)

    def test_seed_does_not_overwrite_existing_schema_version(self):
        category = Category.objects.create(name="Emlak", slug="property")
        schema = AttributeSchema.objects.create(category=category, version=1, definition={"fields": {
            "custom": {"type": "string"},
        }})
        call_command("seed_catalog", stdout=StringIO())
        schema.refresh_from_db()
        self.assertEqual(schema.definition, {"fields": {"custom": {"type": "string"}}})
        self.assertEqual(AttributeSchema.objects.filter(category=category, version=1).count(), 1)
