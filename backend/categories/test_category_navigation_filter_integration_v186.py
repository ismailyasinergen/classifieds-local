from __future__ import annotations

from decimal import Decimal
from io import StringIO

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import timezone
from django.utils.text import slugify

from categories.models import Category
from categories.navigation_v186 import (
    V186_CATEGORY_NAVIGATION_FILTER_MARKER,
    build_category_filter_url_v186,
    build_category_navigation_context_v186,
    filter_queryset_by_category_slug_v186,
    get_category_descendant_ids_v186,
    get_category_descendant_slugs_v186,
)


class CategoryNavigationFilterIntegrationV186Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())
        cls.user = get_user_model().objects.create_user(
            username="v186-filter-user",
            email="v186-filter-user@example.com",
            password="test-password",
        )

    def _listing_kwargs(self, category: Category, title: str) -> dict[str, object]:
        Listing = apps.get_model("listings", "Listing")
        user_model = get_user_model()
        kwargs: dict[str, object] = {}

        for field in Listing._meta.fields:
            if field.primary_key or getattr(field, "auto_created", False):
                continue

            if field.default is not NOT_PROVIDED:
                continue

            if isinstance(field, models.ForeignKey):
                remote_model = field.remote_field.model

                if remote_model is Category:
                    kwargs[field.name] = category
                elif remote_model is user_model:
                    kwargs[field.name] = self.user
                elif field.name in {"seller", "user", "owner", "created_by"}:
                    kwargs[field.name] = self.user
                elif not field.null:
                    raise AssertionError(
                        f"V186 test helper does not know how to populate required FK `{field.name}`."
                    )
                continue

            if field.null or field.blank:
                continue

            if field.choices:
                kwargs[field.name] = field.choices[0][0]
            elif isinstance(field, models.SlugField):
                kwargs[field.name] = slugify(title)
            elif isinstance(field, (models.CharField, models.TextField)):
                if field.name == "title":
                    kwargs[field.name] = title
                elif field.name == "description":
                    kwargs[field.name] = f"{title} description"
                elif field.name == "location":
                    kwargs[field.name] = "Berlin"
                else:
                    kwargs[field.name] = f"{title} {field.name}"[: field.max_length or 255]
            elif isinstance(field, models.DecimalField):
                kwargs[field.name] = Decimal("100.00")
            elif isinstance(field, (models.IntegerField, models.PositiveIntegerField, models.PositiveSmallIntegerField)):
                kwargs[field.name] = 1
            elif isinstance(field, models.BooleanField):
                kwargs[field.name] = False
            elif isinstance(field, models.DateTimeField):
                kwargs[field.name] = timezone.now()
            elif isinstance(field, models.DateField):
                kwargs[field.name] = timezone.localdate()
            elif isinstance(field, models.FileField):
                kwargs[field.name] = "v186-placeholder.txt"
            else:
                raise AssertionError(
                    f"V186 test helper does not know how to populate required field `{field.name}`."
                )

        if "title" not in kwargs:
            kwargs["title"] = title

        return kwargs

    def _create_listing(self, category: Category, title: str):
        Listing = apps.get_model("listings", "Listing")
        return Listing.objects.create(**self._listing_kwargs(category, title))

    def test_v186_descendant_helpers_include_root_child_and_grandchild(self):
        vehicles = Category.objects.get(slug="vehicles")

        descendant_slugs = get_category_descendant_slugs_v186(vehicles)

        self.assertIn("vehicles", descendant_slugs)
        self.assertIn("vehicles-cars", descendant_slugs)
        self.assertIn("vehicles-cars-sedans", descendant_slugs)
        self.assertIn("vehicles-commercial-trucks", descendant_slugs)
        self.assertNotIn("electronics", descendant_slugs)

    def test_v186_listing_queryset_filter_includes_descendants(self):
        Listing = apps.get_model("listings", "Listing")

        vehicles = Category.objects.get(slug="vehicles")
        cars = Category.objects.get(slug="vehicles-cars")
        sedans = Category.objects.get(slug="vehicles-cars-sedans")
        electronics = Category.objects.get(slug="electronics")

        vehicle_listing = self._create_listing(vehicles, "Vehicle root listing")
        car_listing = self._create_listing(cars, "Car child listing")
        sedan_listing = self._create_listing(sedans, "Sedan grandchild listing")
        electronics_listing = self._create_listing(electronics, "Electronics listing")

        filtered_queryset, selected_category, category_ids = filter_queryset_by_category_slug_v186(
            Listing.objects.all(),
            "vehicles",
        )

        self.assertEqual(selected_category, vehicles)
        self.assertEqual(set(category_ids), set(get_category_descendant_ids_v186(vehicles)))
        self.assertIn(vehicle_listing.pk, set(filtered_queryset.values_list("pk", flat=True)))
        self.assertIn(car_listing.pk, set(filtered_queryset.values_list("pk", flat=True)))
        self.assertIn(sedan_listing.pk, set(filtered_queryset.values_list("pk", flat=True)))
        self.assertNotIn(electronics_listing.pk, set(filtered_queryset.values_list("pk", flat=True)))

    def test_v186_invalid_category_slug_leaves_queryset_unfiltered(self):
        Listing = apps.get_model("listings", "Listing")
        furniture = Category.objects.get(slug="home-garden-furniture")

        listing = self._create_listing(furniture, "Furniture listing")

        filtered_queryset, selected_category, category_ids = filter_queryset_by_category_slug_v186(
            Listing.objects.all(),
            "missing-category-slug",
        )

        self.assertIsNone(selected_category)
        self.assertEqual(category_ids, tuple())
        self.assertIn(listing.pk, set(filtered_queryset.values_list("pk", flat=True)))

    def test_v186_navigation_context_marks_selected_and_active_branch(self):
        context = build_category_navigation_context_v186(
            "vehicles-cars-sedans",
            query_params={"q": "hybrid", "page": "5"},
            path="/listings/",
        )

        self.assertEqual(context["marker"], V186_CATEGORY_NAVIGATION_FILTER_MARKER)
        self.assertEqual(context["root_count"], 10)
        self.assertEqual(context["selected_category"].slug, "vehicles-cars-sedans")
        self.assertEqual(
            set(context["active_slugs"]),
            {"vehicles", "vehicles-cars", "vehicles-cars-sedans"},
        )

        vehicles_node = next(root for root in context["roots"] if root.slug == "vehicles")
        cars_node = next(child for child in vehicles_node.children if child.slug == "vehicles-cars")
        sedan_node = next(child for child in cars_node.children if child.slug == "vehicles-cars-sedans")

        self.assertTrue(vehicles_node.is_active_branch)
        self.assertTrue(cars_node.is_active_branch)
        self.assertTrue(sedan_node.is_active_branch)
        self.assertTrue(sedan_node.is_selected)
        self.assertIn("q=hybrid", sedan_node.url)
        self.assertNotIn("page=5", sedan_node.url)

    def test_v186_category_filter_url_preserves_query_but_drops_page(self):
        url = build_category_filter_url_v186(
            "/listings/",
            {"q": "desk", "sort": "newest", "page": "4"},
            "home-garden-furniture",
        )

        self.assertEqual(url, "/listings/?q=desk&sort=newest&category=home-garden-furniture")

        clear_url = build_category_filter_url_v186(
            "/listings/",
            {"q": "desk", "category": "home-garden-furniture", "page": "4"},
            None,
        )

        self.assertEqual(clear_url, "/listings/?q=desk")

    def test_v186_template_partial_renders_navigation_marker(self):
        context = build_category_navigation_context_v186(
            "services-home-repairs",
            query_params={"q": "repair"},
            path="/listings/",
        )

        html = render_to_string("categories/_category_navigation_v186.html", context)

        self.assertIn("V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION", html)
        self.assertIn("Services", html)
        self.assertIn("Home Services", html)
        self.assertIn("Repairs", html)
        self.assertIn("is-selected", html)

    def test_v186_template_tag_can_build_navigation_from_request_context(self):
        template = Template(
            "{% load category_navigation_v186 %}"
            "{% category_navigation_context_v186 'pets-dogs' as category_nav %}"
            "{{ category_nav.marker }}|{{ category_nav.selected_category.slug }}|{{ category_nav.root_count }}"
        )

        rendered = template.render(Context({}))

        self.assertIn("V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION|pets-dogs|10", rendered)
