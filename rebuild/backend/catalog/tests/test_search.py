from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import TestCase
from catalog.models import AttributeSchema, Category

try:
    from catalog import search
except ImportError:
    search = None


class CatalogSearchTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(search, "The catalog search contract is not implemented.")
        self.category = Category.objects.create(name="Root", slug="root")

    def schema(self, version, fields, category=None):
        return AttributeSchema.objects.create(
            category=category or self.category, version=version, definition={"fields": fields})

    def test_tree_uses_one_snapshot_and_includes_deep_descendants(self):
        ids = [self.category.pk]
        parent = self.category
        for level in range(30):
            parent = Category.objects.create(name=str(level), slug=f"level-{level}", parent=parent)
            ids.append(parent.pk)
        with self.assertNumQueries(1):
            self.assertEqual(search.category_scope_ids(category_id=self.category.pk, scope="tree"), tuple(sorted(ids)))
        self.assertEqual(search.category_scope_ids(category_id=self.category.pk, scope="exact"), (self.category.pk,))

    def test_missing_category_is_empty_and_cycle_terminates(self):
        self.assertEqual(search.category_scope_ids(category_id=9223372036854775807, scope="tree"), ())
        child = Category.objects.create(name="Child", slug="child", parent=self.category)
        Category.objects.filter(pk=self.category.pk).update(parent=child)
        self.assertEqual(search.category_scope_ids(category_id=self.category.pk, scope="tree"),
                         tuple(sorted((self.category.pk, child.pk))))

    def test_scope_ids_reject_bool_oversize_and_unknown_scope(self):
        for category_id, scope in ((True, "exact"), (0, "exact"), (2**10000, "exact"), (1, "other")):
            with self.subTest(scope=scope), self.assertRaises(ValidationError):
                search.category_scope_ids(category_id=category_id, scope=scope)

    def test_source_resolution_retains_exact_identity_and_latest_is_explicit(self):
        old = self.schema(1, {"distance": {"type": "integer"}})
        new = self.schema(2, {"distance": {"type": "integer"}})
        self.assertEqual(search.category_filter_schema(category_id=self.category.pk).pk, new.pk)
        ref = SimpleNamespace(id=old.pk, category_id=self.category.pk, version=1)
        self.assertEqual(search.category_filter_schema(category_id=self.category.pk, schema_ref=ref).pk, old.pk)
        for bad in (SimpleNamespace(id=old.pk, category_id=self.category.pk, version=2),
                    SimpleNamespace(id=True, category_id=self.category.pk, version=1)):
            with self.assertRaises(ValidationError):
                search.category_filter_schema(category_id=self.category.pk, schema_ref=bad)

    def test_compatibility_uses_all_keys_exact_category_type_and_unit(self):
        fields = {"distance": {"type": "integer", "unit": " km "}, "enabled": {"type": "boolean"}}
        source = self.schema(1, fields)
        same = self.schema(2, {"distance": {"type": "integer", "unit": "km", "min": 10},
                               "enabled": {"type": "boolean", "filterable": True}})
        other = Category.objects.create(name="Other", slug="other")
        self.schema(1, fields, category=other)
        self.schema(3, {"distance": {"type": "decimal", "unit": "km"}, "enabled": {"type": "boolean"}})
        self.schema(4, {"distance": {"type": "integer", "unit": "m"}, "enabled": {"type": "boolean"}})
        self.schema(5, {"distance": {"type": "integer", "unit": "km"}})
        self.schema(6, {"distance": {"type": "integer", "unit": "km", "filterable": False},
                        "enabled": {"type": "boolean"}})
        predicates = (SimpleNamespace(key="distance", kind="integer", unit="km"),
                      SimpleNamespace(key="enabled", kind="boolean", unit=""))
        with self.assertNumQueries(1):
            result = search.compatible_attribute_schemas(source_schema=source, predicates=predicates)
        self.assertEqual([schema.pk for schema in result], [source.pk, same.pk])
        source.refresh_from_db()
        self.assertEqual(source.definition, {"fields": fields})

    def test_option_and_domain_changes_do_not_change_identity(self):
        source = self.schema(1, {"area": {"type": "decimal", "min": "1", "options": ["1.00"]}})
        new = self.schema(2, {"area": {"type": "decimal", "min": "5", "options": ["10"]}})
        predicate = SimpleNamespace(key="area", kind="decimal", unit="")
        self.assertEqual([schema.pk for schema in search.compatible_attribute_schemas(
            source_schema=source, predicates=(predicate,))], [source.pk, new.pk])
