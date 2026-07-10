from __future__ import annotations

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase

from categories.admin import CategoryAdmin
from categories.models import Category
import categories.models as category_models


class CategoryHierarchySafeguardsV182Tests(TestCase):
    def test_v182_model_marker_is_declared(self):
        self.assertEqual(
            category_models.V182_CATEGORY_HIERARCHY_SAFEGUARDS_MARKER,
            "V182_CATEGORY_HIERARCHY_SAFEGUARDS",
        )

    def test_v182_admin_marker_and_registration_are_declared(self):
        import categories.admin as category_admin

        self.assertEqual(
            category_admin.V182_CATEGORY_ADMIN_SAFEGUARDS_MARKER,
            "V182_CATEGORY_ADMIN_SAFEGUARDS",
        )
        self.assertIn(Category, admin.site._registry)
        self.assertIsInstance(admin.site._registry[Category], CategoryAdmin)

    def test_v182_admin_exposes_safe_hierarchy_fields(self):
        registered_admin = admin.site._registry[Category]

        self.assertEqual(registered_admin.list_display, ("name", "slug", "parent"))
        self.assertEqual(registered_admin.list_filter, ("parent",))
        self.assertEqual(registered_admin.search_fields, ("name", "slug"))
        self.assertEqual(registered_admin.prepopulated_fields, {"slug": ("name",)})

    def test_v182_root_and_child_categories_validate_cleanly(self):
        root = Category.objects.create(name="Vehicles", slug="vehicles")
        child = Category.objects.create(name="Cars", slug="cars", parent=root)

        root.full_clean()
        child.full_clean()

    def test_v182_category_cannot_be_its_own_parent(self):
        category = Category.objects.create(name="Electronics", slug="electronics")
        category.parent = category

        with self.assertRaises(ValidationError) as context:
            category.full_clean()

        self.assertIn("parent", context.exception.message_dict)
        self.assertIn(
            "A category cannot be its own parent.",
            context.exception.message_dict["parent"],
        )

    def test_v182_category_hierarchy_cycle_is_rejected(self):
        root = Category.objects.create(name="Home", slug="home")
        child = Category.objects.create(name="Furniture", slug="furniture", parent=root)
        grandchild = Category.objects.create(
            name="Tables",
            slug="tables",
            parent=child,
        )

        root.parent = grandchild

        with self.assertRaises(ValidationError) as context:
            root.full_clean()

        self.assertIn("parent", context.exception.message_dict)
        self.assertIn(
            "Category hierarchy cannot contain a cycle.",
            context.exception.message_dict["parent"],
        )

    def test_v182_sibling_categories_under_same_parent_validate(self):
        root = Category.objects.create(name="Jobs", slug="jobs")
        first = Category.objects.create(name="IT Jobs", slug="it-jobs", parent=root)
        second = Category.objects.create(
            name="Marketing Jobs",
            slug="marketing-jobs",
            parent=root,
        )

        first.full_clean()
        second.full_clean()
