from copy import deepcopy
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from catalog.models import AttributeSchema, Category
from catalog.validation import validate_attributes, validate_schema_definition


class AttributeValidationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Otomobil", slug="automobiles")
        self.schema = AttributeSchema.objects.create(category=self.category, version=1, definition={"fields": {
            "model_year": {"type": "integer", "required": True, "min": 1900, "max": 2100},
            "mileage_km": {"type": "integer", "required": True, "min": 0, "max": 5000000},
        }})

    def test_vehicle_numeric_attributes_are_normalized(self):
        result = validate_attributes(schema=self.schema, values={"model_year": "2020", "mileage_km": "150000"})
        self.assertEqual(result, {"model_year": 2020, "mileage_km": 150000})
        self.assertIs(type(result["mileage_km"]), int)

    def test_property_attributes_validate_types(self):
        schema = AttributeSchema.objects.create(category=self.category, version=2, definition={"fields": {
            "area_m2": {"type": "decimal", "required": True, "min": "0.01"},
            "room_count": {"type": "integer", "required": True, "min": 1},
        }})
        self.assertEqual(validate_attributes(schema=schema, values={"area_m2": "82.500", "room_count": "3"}),
                         {"area_m2": "82.5", "room_count": 3})

    def test_invalid_numeric_value_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_attributes(schema=self.schema, values={"model_year": "2020", "mileage_km": "not-a-number"})

    def test_schema_version_is_retained(self):
        validate_attributes(schema=self.schema, values={"model_year": 2020, "mileage_km": 150000})
        self.schema.refresh_from_db()
        self.assertEqual(self.schema.version, 1)

    def test_unknown_or_missing_required_keys_rejected(self):
        for values in ({"model_year": 2020}, {"model_year": 2020, "mileage_km": 1, "extra": "x"},
                       {"model_year": 2020, "mileage_km": None}, []):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                validate_attributes(schema=self.schema, values=values)

    def test_nonfinite_boolean_fractional_and_malformed_numbers_rejected(self):
        for value in (True, False, "NaN", "Infinity", "-Infinity", float("nan"), 1.5, "1.5", [], {}):
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                validate_attributes(schema=self.schema, values={"model_year": 2020, "mileage_km": value})

    def test_numeric_min_max_enforced(self):
        for value in (-1, 5000001):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_attributes(schema=self.schema, values={"model_year": 2020, "mileage_km": value})

    def test_decimal_rejects_nonfinite_and_bool(self):
        schema = AttributeSchema.objects.create(category=self.category, version=2, definition={"fields": {
            "area": {"type": "decimal", "required": True, "min": "1", "max": "100"},
        }})
        for value in ("NaN", "Infinity", True, 0, 101):
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                validate_attributes(schema=schema, values={"area": value})
        self.assertEqual(validate_attributes(schema=schema, values={"area": Decimal("10.00")}), {"area": "10"})

    def test_string_options_and_boolean_types(self):
        schema = AttributeSchema.objects.create(category=self.category, version=2, definition={"fields": {
            "fuel": {"type": "string", "required": True, "options": ["diesel", "electric"]},
            "registered": {"type": "boolean"},
        }})
        self.assertEqual(validate_attributes(schema=schema, values={"fuel": " diesel ", "registered": True}),
                         {"fuel": "diesel", "registered": True})
        for values in ({"fuel": "petrol"}, {"fuel": "diesel", "registered": "true"}, {"fuel": 1}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                validate_attributes(schema=schema, values=values)

    def test_validation_does_not_mutate_schema_or_input(self):
        values = {"model_year": "2020", "mileage_km": "150000"}
        original = deepcopy(self.schema.definition)
        validate_attributes(schema=self.schema, values=values)
        self.assertEqual(self.schema.definition, original)
        self.assertEqual(values["mileage_km"], "150000")

    def test_bulk_create_materializes_and_persists_validated_generator(self):
        schemas = [AttributeSchema(category=self.category, version=version, definition={"fields": {}})
                   for version in (2, 3)]
        created = AttributeSchema.objects.bulk_create(schema for schema in schemas)
        self.assertEqual(len(created), 2)
        self.assertTrue(all(schema.pk is not None for schema in created))
        self.assertEqual(list(AttributeSchema.objects.filter(category=self.category)
                              .order_by("version").values_list("version", flat=True)), [1, 2, 3])

    def test_bulk_create_validates_entire_generator_before_any_insert(self):
        schemas = [
            AttributeSchema(category=self.category, version=2, definition={"fields": {}}),
            AttributeSchema(category=self.category, version=3,
                            definition={"fields": {"invalid": {"type": "unsupported"}}}),
        ]
        with self.assertRaises(ValidationError):
            AttributeSchema.objects.bulk_create(schema for schema in schemas)
        self.assertEqual(AttributeSchema.objects.filter(category=self.category).count(), 1)

    def test_saved_schema_is_immutable(self):
        self.schema.definition = {"fields": {}}
        with self.assertRaises(ValidationError):
            self.schema.save()
        with self.assertRaises(ValidationError):
            AttributeSchema.objects.filter(pk=self.schema.pk).update(version=9)
        with self.assertRaises(ValidationError):
            AttributeSchema.objects.filter(pk=self.schema.pk).delete()

    def test_database_prevents_schema_update_and_delete(self):
        for sql in ("UPDATE catalog_attributeschema SET version = version + 1 WHERE id = %s",
                    "DELETE FROM catalog_attributeschema WHERE id = %s"):
            with self.subTest(sql=sql), self.assertRaises(IntegrityError), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql, [self.schema.pk])

    def test_schema_version_unique_and_positive(self):
        with self.assertRaises((ValidationError, IntegrityError)), transaction.atomic():
            AttributeSchema.objects.create(category=self.category, version=1, definition={"fields": {}})
        with self.assertRaises((ValidationError, IntegrityError)), transaction.atomic():
            AttributeSchema.objects.create(category=self.category, version=0, definition={"fields": {}})

    def test_malformed_schema_definition_rejected(self):
        for fields in ({"x": {"type": "unsupported"}}, {"x": {"type": "integer", "min": "NaN"}},
                       {"x": {"type": "integer", "min": 3, "max": 1}}, {"x": {"type": "string", "options": [1]}}):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                AttributeSchema.objects.create(category=self.category, version=2, definition={"fields": fields})

    def test_unit_and_filterability_metadata_is_preserved(self):
        original_schema = deepcopy(self.schema.definition)
        for version, filterable in ((2, True), (3, False)):
            definition = {"fields": {
                "area_m2": {"type": "decimal", "required": True, "unit": " m² ", "filterable": filterable},
            }}
            before_validation = deepcopy(definition)
            validate_schema_definition(definition)
            schema = AttributeSchema.objects.create(category=self.category, version=version, definition=definition)
            schema.refresh_from_db()
            self.assertEqual(schema.definition, before_validation)
            self.assertEqual(validate_attributes(schema=schema, values={"area_m2": "82.500"}), {"area_m2": "82.5"})
            self.assertEqual(schema.definition, before_validation)
            self.assertEqual(definition, before_validation)
            self.assertIs(schema.definition["fields"]["area_m2"]["filterable"], filterable)
        self.schema.refresh_from_db()
        self.assertEqual(self.schema.version, 1)
        self.assertEqual(self.schema.definition, original_schema)

    def test_malformed_unit_metadata_rejected(self):
        for unit in ("", "   ", None, 1, False, [], {}):
            definition = {"fields": {"area_m2": {"type": "decimal", "unit": unit}}}
            with self.subTest(unit=repr(unit)):
                with self.assertRaises(ValidationError):
                    validate_schema_definition(definition)
                with self.assertRaises(ValidationError):
                    validate_attributes(schema=AttributeSchema(definition=definition), values={"area_m2": "10"})
                with self.assertRaises(ValidationError):
                    AttributeSchema.objects.create(category=self.category, version=2, definition=definition)

    def test_malformed_filterability_metadata_rejected(self):
        for filterable in ("true", "false", 0, 1, None, [], {}):
            definition = {"fields": {"area_m2": {"type": "decimal", "filterable": filterable}}}
            with self.subTest(filterable=repr(filterable)):
                with self.assertRaises(ValidationError):
                    validate_schema_definition(definition)
                with self.assertRaises(ValidationError):
                    validate_attributes(schema=AttributeSchema(definition=definition), values={"area_m2": "10"})
                with self.assertRaises(ValidationError):
                    AttributeSchema.objects.create(category=self.category, version=2, definition=definition)

    def test_invalid_type_declarations_rejected_by_definition_validator(self):
        for kind in ([], {}, None, 1, 1.5, True, "", "unsupported"):
            with self.subTest(kind=repr(kind)), self.assertRaises(ValidationError):
                validate_schema_definition({"fields": {"x": {"type": kind}}})

    def test_invalid_type_declarations_rejected_by_public_validator(self):
        for kind in ([], {}, None, 1, 1.5, True, "", "unsupported"):
            definition = {"fields": {"x": {"type": kind}}}
            with self.subTest(kind=repr(kind)), self.assertRaises(ValidationError):
                validate_attributes(schema=AttributeSchema(definition=definition), values={})

    def test_invalid_type_declarations_rejected_on_schema_create(self):
        for kind in ([], {}, None, 1, 1.5, True, "", "unsupported"):
            definition = {"fields": {"x": {"type": kind}}}
            with self.subTest(kind=repr(kind)), self.assertRaises(ValidationError):
                AttributeSchema.objects.create(category=self.category, version=2, definition=definition)

    def test_category_supports_variable_depth(self):
        parent = self.category
        for index in range(5):
            parent = Category.objects.create(name=f"Level {index}", slug=f"level-{index}", parent=parent)
        self.assertEqual(parent.parent.parent.parent.parent.parent, self.category)
