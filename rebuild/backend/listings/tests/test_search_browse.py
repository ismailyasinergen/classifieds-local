from accounts.tests.mfa_support import authenticate_client
"""Rendered search regression gates against the new PostgreSQL application."""
from copy import deepcopy
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from catalog.models import AttributeSchema, Category
from listings.models import Listing, ListingRevision
from listings.tests.test_drafts import DraftFixtures
from media.models import MediaAsset, RevisionImage


class SearchBrowseTests(DraftFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.at = timezone.now()
        self.parent = Category.objects.create(name="Vasıta", slug="vehicles")
        self.category.parent = self.parent
        self.category.save()
        self.second = Category.objects.create(name="Emlak", slug="property")
        self.second_schema = AttributeSchema.objects.create(
            category=self.second, version=1, definition={"fields": {"rooms": {"type": "integer"}}})

    def live(self, number=1, *, schema=None, image=False, **content):
        schema = schema or self.schema
        listing = Listing.objects.create(id=UUID(int=number), owner=self.owner,
                                         lifecycle="live", first_published_at=self.at)
        values = dict(title="İstanbul BMW X5", description="Sentetik ilan", price="10",
                      currency="EUR", location="Şişli",
                      attributes={"model_year": 2020, "area": "9", "electric": False})
        values.update(content)
        revision = ListingRevision.objects.create(
            listing=listing, status="approved", category_id=schema.category_id,
            attribute_schema=schema, schema_version=schema.version, **values)
        Listing.objects.filter(pk=listing.pk).update(public_revision=revision)
        if image:
            asset = MediaAsset.objects.create(owner=self.owner, state="ready", source_bytes=1,
                                              width=1, height=1, source_mime="image/jpeg", derivative="synthetic/search.jpg")
            RevisionImage.objects.create(revision=revision, asset=asset, position=0)
        return revision

    def params(self, **extra):
        return {"category": self.category.pk, "schema": self.schema.pk,
                "schema_version": self.schema.version, **extra}

    def listing_sql(self, captured):
        return [item["sql"] for item in captured if '"listings_listing"' in item["sql"]
                or '"listings_listingrevision"' in item["sql"]]

    def test_invalid_criteria_are_inline_and_execute_no_listing_sql(self):
        self.live()
        cases = [
            {"currency": "EU"}, {"price_min": "10"}, {"sort": "price_asc"},
            {"q": "!!!"}, {"v": "2"}, {"scope": "tree"},
            {"currency": "EUR", "price_min": "20", "price_max": "10"},
            {"currency": "EUR", "price_min": "NaN"}, {"q": "a\x00b"},
            self.params(**{"a.unknown.eq": "x"}), {"q": "a", "sort": "unknown"},
        ]
        for params in cases:
            with self.subTest(params=params), CaptureQueriesContext(connection) as queries:
                response = self.client.get("/", params)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["search_valid"])
            self.assertIsNone(response.context["page_obj"])
            self.assertContains(response, "Arama ölçütlerini kontrol edin")
            self.assertEqual(self.listing_sql(queries), [])

    def test_duplicate_scalar_is_not_flattened(self):
        response = self.client.get("/?currency=EUR&currency=TRY")
        self.assertFalse(response.context["search_valid"])
        self.assertContains(response, "yalnız bir kez")

    def test_legacy_category_and_missing_positive_id_contract(self):
        self.live()
        for value in ("abc", "-1", "0", "９", "9" * 100, "9223372036854775808"):
            with self.subTest(value=value):
                response = self.client.get("/", {"category": value})
                self.assertTrue(response.context["search_valid"])
                self.assertEqual(response.context["selected_category"], "")
                self.assertEqual(response.context["page_obj"].paginator.count, 1)
        response = self.client.get("/", {"category": "999999"})
        self.assertTrue(response.context["search_valid"])
        self.assertEqual(response.context["selected_category"], "999999")
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertContains(response, "Bu ölçütlerle ilan bulunamadı")

    def test_parent_choice_and_tree_membership(self):
        self.live()
        response = self.client.get("/", {"category": self.parent.pk, "scope": "tree"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "Vasıta")
        self.assertContains(response, "Vasıta › Otomobil")
        self.assertNotContains(response, 'name="a.')
        exact = self.client.get("/", {"category": self.parent.pk})
        self.assertEqual(exact.context["page_obj"].paginator.count, 0)

    def test_unselected_form_has_no_attribute_controls(self):
        response = self.client.get("/")
        self.assertTrue(response.context["search_valid"])
        self.assertNotContains(response, 'name="a.')

    def test_blank_controls_have_exact_hidden_source_and_submit_successfully(self):
        response = self.client.get("/", {"category": self.category.pk})
        self.assertContains(response, 'name="a.model_year.min"')
        self.assertContains(response, 'name="schema"')
        self.assertContains(response, 'name="schema_version"')
        self.assertNotContains(response, 'name="schemas"')
        replay = self.client.get("/", self.params(**{"a.model_year.min": "", "a.electric.eq": ""}))
        self.assertTrue(replay.context["search_valid"])

    def test_category_apply_clears_all_old_identity_and_attributes_preserving_common(self):
        self.live(schema=self.second_schema)
        params = self.params(q="BMW", currency="eur", location="sisli", price_min="0",
                             category=self.second.pk, page="99", category_apply="1",
                             schemas=f"{self.schema.pk}:1", **{"a.model_year.min": "bad"})
        response = self.client.get("/", params)
        self.assertTrue(response.context["search_valid"])
        spec = response.context["search_spec"]
        self.assertEqual((spec.keyword, spec.currency, spec.location), ("BMW", "EUR", "sisli"))
        self.assertEqual(spec.attributes, ())
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertContains(response, 'name="a.rooms.min"')
        self.assertNotContains(response, 'name="a.model_year.')
        invalid = self.client.get("/", {**params, "price_min": "bad"})
        self.assertFalse(invalid.context["search_valid"])

    def test_stale_category_controls_error_without_reinterpretation(self):
        self.live()
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/", self.params(category=self.second.pk, **{"a.model_year.min": "2020"}))
        self.assertFalse(response.context["search_valid"])
        self.assertEqual(self.listing_sql(queries), [])
        self.assertContains(response, "şema")
        self.assertNotContains(response, 'name="a.rooms.min"')
        self.assertContains(response, "Önceki kategori filtreleri")
        self.assertContains(response, "2020")

    def test_entered_errors_are_escaped_and_accessibly_associated(self):
        response = self.client.get("/", {"currency": '<script>alert("x")</script>', "price_min": "1"})
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'id_currency_error')
        self.assertContains(response, 'href="#id_currency"')

    def test_currency_is_syntax_only_with_suggestions(self):
        self.live(currency="CHF")
        response = self.client.get("/", {"currency": " chf "})
        self.assertTrue(response.context["search_valid"])
        self.assertEqual(response.context["search_spec"].currency, "CHF")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "TRY")
        self.assertContains(response, "1000.50")

    def test_numeric_range_has_no_stored_domain_html_min(self):
        response = self.client.get("/", {"category": self.category.pk})
        self.assertNotContains(response, 'min="1900"')
        response = self.client.get("/", self.params(**{"a.model_year.min": "0"}))
        self.assertTrue(response.context["search_valid"])

    def test_false_and_numeric_zero_are_distinct_search_values(self):
        self.live(attributes={"model_year": 2020, "area": "0", "electric": False})
        response = self.client.get("/", self.params(**{"a.area.min": "0", "a.electric.eq": "false"}))
        self.assertTrue(response.context["search_valid"])
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, 'value="false" selected')
        self.assertContains(response, "Hayır")

    def test_options_union_uses_compatible_versions_and_frozen_replay(self):
        fields = deepcopy(self.schema.definition["fields"])
        fields["brand"] = {"type": "string", "options": ["red"], "label": "Marka"}
        source = AttributeSchema.objects.create(category=self.category, version=2, definition={"fields": fields})
        fields = deepcopy(fields)
        fields["brand"]["options"] = ["blue"]
        older = AttributeSchema.objects.create(category=self.category, version=3, definition={"fields": fields})
        self.live(schema=older, attributes={"model_year": 2020, "area": "9", "brand": "blue"})
        params = {"category": self.category.pk, "schema": source.pk, "schema_version": 2, "a.brand.eq": "blue"}
        response = self.client.get("/", params)
        self.assertTrue(response.context["search_valid"])
        self.assertContains(response, 'value="blue" selected')
        self.assertContains(response, 'name="schemas"')
        frozen = self.client.get("/", {**params, "schemas": f"{older.pk}:3"})
        self.assertContains(frozen, 'value="blue" selected')
        self.assertNotContains(frozen, 'value="red"')

    def test_canonical_numeric_equality_reopens_without_range_confusion(self):
        self.live()
        params = self.params(**{"a.area.eq": "9.00"})
        response = self.client.get("/", params)
        self.assertTrue(response.context["search_valid"])
        self.assertContains(response, 'name="a.area.eq"')
        self.assertContains(response, 'value="9"')
        self.assertNotContains(response, 'name="a.area.min"')
        self.assertNotContains(response, 'name="a.area.max"')
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def numeric_option_rows(self, kind):
        category = Category.objects.create(name=f"Sayısal {kind}", slug=f"numeric-options-{kind}")
        options = [0, 10, 20] if kind == "integer" else ["0", "10.5", "20"]
        schema = AttributeSchema.objects.create(category=category, version=1, definition={"fields": {
            "amount": {"type": kind, "options": options, "label": "Ölçü", "unit": "kg"},
        }})
        offset = 100 if kind == "integer" else 200
        rows = [self.live(offset + index, schema=schema, attributes={"amount": value}).listing_id
                for index, value in enumerate(options)]
        return schema, options, rows

    def rendered_search_values(self, response):
        # Every field in this form is rendered by search_filters.html; buttons are separate.
        return {field.name: "" if field.value() is None else field.value()
                for field in response.context["search_form"]}

    def test_option_numeric_ranges_survive_canonical_form_resubmission(self):
        from listings.search.parsing import search_querystring
        for kind in ("integer", "decimal"):
            schema, options, rows = self.numeric_option_rows(kind)
            middle = str(options[1])
            cases = (
                ({"a.amount.min": "0", "a.amount.max": middle}, rows[:2]),
                ({"a.amount.min": middle}, rows[1:]),
                ({"a.amount.max": "0"}, rows[:1]),
            )
            for attributes, expected in cases:
                with self.subTest(kind=kind, attributes=attributes):
                    params = {"category": schema.category_id, "schema": schema.pk,
                              "schema_version": schema.version, **attributes}
                    first = self.client.get("/", params)
                    self.assertTrue(first.context["search_valid"])
                    self.assertEqual({item.pk for item in first.context["page_obj"]}, set(expected))
                    canonical = search_querystring(first.context["search_spec"])
                    reopened = self.client.get(f"/?{canonical}")
                    replay = self.client.get("/", self.rendered_search_values(reopened))
                    self.assertTrue(replay.context["search_valid"])
                    self.assertEqual({item.pk for item in replay.context["page_obj"]}, set(expected))
                    self.assertEqual(replay.context["search_spec"].attributes,
                                     reopened.context["search_spec"].attributes)
                    self.assertEqual(replay.context["search_spec"].resolved_schemas,
                                     reopened.context["search_spec"].resolved_schemas)
                    for name in ("a.amount.min", "a.amount.max"):
                        self.assertContains(reopened, f'name="{name}"')
                    self.assertNotContains(reopened, 'name="a.amount.eq"')

    def test_option_numeric_equality_keeps_the_dropdown_and_replays(self):
        for kind in ("integer", "decimal"):
            with self.subTest(kind=kind):
                schema, options, rows = self.numeric_option_rows(kind)
                params = {"category": schema.category_id, "schema": schema.pk,
                          "schema_version": schema.version}
                ordinary = self.client.get("/", params)
                self.assertContains(ordinary, '<select name="a.amount.eq"')
                self.assertNotContains(ordinary, 'name="a.amount.min"')
                self.assertNotContains(ordinary, 'name="a.amount.max"')
                selected = self.client.get("/", {**params, "a.amount.eq": str(options[1])})
                self.assertContains(selected, '<select name="a.amount.eq"')
                replay = self.client.get("/", self.rendered_search_values(selected))
                self.assertTrue(replay.context["search_valid"])
                self.assertEqual({item.pk for item in replay.context["page_obj"]}, {rows[1]})

    def test_invalid_option_numeric_ranges_retain_values_and_field_errors(self):
        for kind in ("integer", "decimal"):
            schema, options, unused_rows = self.numeric_option_rows(kind)
            cases = (
                ({"a.amount.min": "not-a-number"}, "a.amount.min"),
                ({"a.amount.max": "not-a-number"}, "a.amount.max"),
                ({"a.amount.min": "20", "a.amount.max": "0"}, "a.amount.min"),
                ({"a.amount.eq": str(options[1]), "a.amount.min": "0"}, "a.amount.eq"),
            )
            for attributes, error_field in cases:
                with self.subTest(kind=kind, attributes=attributes), CaptureQueriesContext(connection) as queries:
                    params = {"category": schema.category_id, "schema": schema.pk,
                              "schema_version": schema.version, **attributes}
                    response = self.client.get("/", params)
                    self.assertFalse(response.context["search_valid"])
                    self.assertEqual(self.listing_sql(queries), [])
                    form = response.context["search_form"]
                    for name, value in attributes.items():
                        self.assertIn(name, form.fields)
                        self.assertContains(response, f'name="{name}"')
                        self.assertEqual(form[name].value(), value)
                    self.assertIn(error_field, form.errors)
                    self.assertContains(response, f'href="#id_{error_field}"')
                    self.assertContains(response, 'aria-invalid="true"')
                    replay = self.client.get("/", self.rendered_search_values(response))
                    self.assertFalse(replay.context["search_valid"])

    def test_explicit_false_field_is_not_rendered(self):
        source = AttributeSchema.objects.create(category=self.category, version=2, definition={"fields": {
            "hidden": {"type": "string", "filterable": False},
            "visible": {"type": "boolean"},
        }})
        response = self.client.get("/", {"category": source.category_id})
        self.assertNotContains(response, 'name="a.hidden.')
        self.assertContains(response, 'name="a.visible.eq"')

    def test_canonical_paging_stable_ties_and_frozen_filters_once(self):
        for number in range(1, 26):
            self.live(number, image=True)
        params = self.params(q="  BMW   X5 ", currency="eur", sort="price_asc",
                             **{"a.area.min": "9.00", "a.electric.eq": "false"})
        first = self.client.get("/", params)
        url = first.context["next_url"]
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["q"], ["BMW X5"])
        self.assertEqual(query["currency"], ["EUR"])
        self.assertEqual(query["a.area.min"], ["9"])
        self.assertEqual(query["a.electric.eq"], ["false"])
        self.assertEqual(query["schemas"], [f"{self.schema.pk}:1"])
        self.assertEqual(query["page"], ["2"])
        self.assertNotIn("category_apply", query)
        second = self.client.get(url)
        first_ids = [item.pk.int for item in first.context["page_obj"]]
        second_ids = [item.pk.int for item in second.context["page_obj"]]
        self.assertEqual(first_ids, list(range(25, 13, -1)))
        self.assertEqual(second_ids, list(range(13, 1, -1)))
        self.assertFalse(set(first_ids) & set(second_ids))
        self.assertContains(first, "/fotograflar/")

    def test_bounded_page_fallback(self):
        for number in range(1, 26):
            self.live(number)
        for raw, expected in (("", 1), ("bad", 1), ("1.5", 1), ("0", 3), ("-1", 3),
                              ("99", 3), ("9" * 5000, 3), ("-" + "9" * 5000, 3), ("0002", 2)):
            with self.subTest(raw=raw):
                response = self.client.get("/", {"page": raw})
                self.assertTrue(response.context["search_valid"])
                self.assertEqual(response.context["page_obj"].number, expected)

    def test_query_count_is_bounded_and_rows_are_limited_with_images(self):
        self.live(1, image=True)
        with CaptureQueriesContext(connection) as one:
            self.client.get("/", self.params(**{"a.area.min": "0"}))
        for number in range(2, 26):
            self.live(number, image=True)
        with CaptureQueriesContext(connection) as many:
            response = self.client.get("/", self.params(**{"a.area.min": "0"}))
        self.assertLessEqual(len(many), len(one) + 6)
        sql = self.listing_sql(many)
        self.assertTrue(any("COUNT(" in statement for statement in sql))
        self.assertTrue(any("LIMIT 12" in statement for statement in sql))
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertLessEqual(len(sql), 2)

    def test_owner_and_moderation_keep_shared_pagination(self):
        self.other.user_permissions.add(Permission.objects.get(
            content_type__app_label="listings", codename="review_listingrevision"))
        for number in range(1, 14):
            self.live(number)
        self.client.force_login(self.owner)
        dashboard = self.client.get("/ilanlarim/")
        self.assertContains(dashboard, 'href="?page=2"')
        self.assertTemplateUsed(dashboard, "listings/pagination.html")
        for number in range(1, 14):
            ListingRevision.objects.create(listing_id=UUID(int=number), status="submitted",
                                           category=self.category, attribute_schema=self.schema, schema_version=1)
        authenticate_client(self.client, self.other)
        queue = self.client.get("/inceleme/")
        self.assertContains(queue, 'href="?page=2"')
        self.assertTemplateUsed(queue, "listings/pagination.html")


class SearchFixtureGuardsTests(TestCase):
    def command(self, data):
        import json
        from io import StringIO
        from unittest.mock import patch
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with patch("sys.stdin", StringIO(json.dumps(data))), self.assertRaises(CommandError):
            call_command("search_browser_fixture", stdout=StringIO())

    def test_debug_and_exact_developer_domain_are_required(self):
        from django.contrib.sites.models import Site
        from django.test import override_settings
        from accounts.models import User
        for debug, domain in ((False, "localhost:8089"), (True, "127.0.0.1:8088")):
            with self.subTest(debug=debug, domain=domain), override_settings(DEBUG=debug):
                Site.objects.update_or_create(pk=1, defaults={"domain": domain, "name": "Test"})
                self.command({"run": "0123456789abcdef"})
                self.assertEqual(User.objects.count(), 0)
                self.assertEqual(Listing.objects.count(), 0)

    def test_invalid_or_reused_run_cannot_touch_existing_rows(self):
        from django.contrib.sites.models import Site
        from django.test import override_settings
        from accounts.models import User
        Site.objects.update_or_create(pk=1, defaults={"domain": "localhost:8089", "name": "Test"})
        existing = User.objects.create_user(email="search-0123456789abcdef-owner@browser.example.test", password=None)
        with override_settings(DEBUG=True):
            for data in ({"run": "bad"}, {"run": "0123456789abcdef", "owner": existing.pk},
                         {"run": "0123456789abcdef"}):
                with self.subTest(data=data):
                    self.command(data)
                    self.assertEqual(User.objects.count(), 1)
                    self.assertEqual(Listing.objects.count(), 0)
                    existing.refresh_from_db()
                    self.assertFalse(existing.has_usable_password())
                    self.assertEqual(existing.user_permissions.count(), 0)
