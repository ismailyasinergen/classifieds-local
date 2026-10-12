"""Search membership and ordering run against the developer PostgreSQL database."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import connection
from django.http import QueryDict
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from catalog.models import AttributeSchema, Category
from listings.models import Listing, ListingRevision
from listings.search.parsing import parse_search_spec
from listings.tests.test_publication import PublicationFixtures
from moderation.models import Restriction


class SearchQueryTests(PublicationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(connection.vendor, "postgresql")
        self.at = timezone.now()
        try:
            self.search = import_module("listings.search.queries")
        except ModuleNotFoundError as exc:
            if exc.name != "listings.search.queries":
                raise
            self.fail("Task B public PostgreSQL search API is not implemented.")

    def spec(self, **params):
        query = QueryDict("", mutable=True)
        query.update({key: str(value) for key, value in params.items()})
        return parse_search_spec(query)

    def attribute_spec(self, source=None, **params):
        source = source or self.schema
        return self.spec(category=source.category_id, schema=source.pk,
                         schema_version=source.version, **params)

    def match(self, spec=None, **params):
        return self.search.matching_public_listings(
            spec=spec if spec is not None else self.spec(**params), at=self.at)

    def ids(self, queryset):
        return set(queryset.values_list("pk", flat=True))

    def live(self, *, schema=None, category=None, attributes=None, **content):
        schema = schema or self.schema
        listing = Listing.objects.create(
            id=content.pop("listing_id", None) or UUID(int=1000 + Listing.objects.count()),
            owner=self.owner, lifecycle="live",
            first_published_at=content.pop("published_at", self.at),
        )
        defaults = {
            "title": "Araba", "description": "Açıklama", "price": Decimal("10"),
            "currency": "EUR", "location": "Berlin",
        }
        defaults.update(content)
        revision = ListingRevision.objects.create(
            listing=listing, status="approved", category=category or schema.category,
            attribute_schema=schema, schema_version=defaults.pop("schema_version", schema.version),
            attributes=attributes if attributes is not None else {
                "model_year": 2020, "area": "9", "electric": False, "brand": "blue",
            }, **defaults,
        )
        Listing.objects.filter(pk=listing.pk).update(public_revision=revision)
        return revision

    def schema_version(self, version, **changes):
        fields = deepcopy(self.schema.definition["fields"])
        fields.update(changes)
        return AttributeSchema.objects.create(
            category=self.category, version=version, definition={"fields": fields})

    def test_empty_search_is_exactly_the_shared_public_membership(self):
        from listings.queries import public_listings
        self.live()
        hidden = self.live()
        Listing.objects.filter(pk=hidden.listing_id).update(lifecycle="paused")
        self.assertEqual(self.ids(self.match()), self.ids(public_listings(at=self.at)))

    def test_later_private_revision_content_never_matches_even_for_owner(self):
        content = dict(self.content, title="Public Cobalt", description="Visible Harbor",
                       price="10", location="Şişli",
                       attributes={"model_year": 2020, "area": "9", "electric": False})
        public = self.approve(self.submit(self.draft(content=content)))
        private = self.edit(
            public, title="Private Nebula", description="Secret Archive", price="999",
            location="Hidden Cove",
            attributes={"model_year": 2030, "area": "100", "electric": True})
        public_spec = self.attribute_spec(**{"a.area.eq": "9"})
        private_spec = self.attribute_spec(**{"a.area.eq": "100"})
        for status in ("draft", "submitted", "rejected"):
            ListingRevision.objects.filter(pk=private.pk).update(status=status)
            for owner_scope in (False, True):
                with self.subTest(status=status, owner_scope=owner_scope):
                    for spec in (self.spec(q="Nebula"), self.spec(q="Archive"),
                                 self.spec(location="Cove"),
                                 self.spec(currency="EUR", price_min="999"), private_spec):
                        results = self.match(spec)
                        if owner_scope:
                            results = results.filter(owner_id=self.owner.pk)
                        self.assertEqual(results.count(), 0)
                        self.assertFalse(results.filter(pk=public.listing_id).exists())
                    for spec in (self.spec(q="Cobalt"), self.spec(q="Harbor"),
                                 self.spec(location="sisli"),
                                 self.spec(currency="EUR", price_max="10"), public_spec):
                        results = self.match(spec)
                        if owner_scope:
                            results = results.filter(owner_id=self.owner.pk)
                        self.assertEqual(self.ids(results), {public.listing_id})

    def test_old_approved_revision_stops_matching_when_public_pointer_changes(self):
        public = self.publish()
        self.assertEqual(self.ids(self.match(q="Araba")), {public.listing_id})
        newer = self.approve(self.submit(self.edit(
            public, title="Replacement Cobalt", description="Modern Harbor", price="100",
            attributes={"model_year": 2021, "area": "100", "electric": True})), expected=public.pk)
        self.assertEqual(self.match(q="Araba").count(), 0)
        self.assertEqual(self.match(self.attribute_spec(**{"a.area.eq": "82.5"})).count(), 0)
        self.assertEqual(self.match(currency="EUR", price_min="1000").count(), 0)
        self.assertEqual(self.ids(self.match(q="Cobalt")), {newer.listing_id})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(**{"a.area.eq": "100"}))), {newer.listing_id})

    def test_lifecycle_and_expiry_use_the_shared_at_boundary(self):
        public = self.live()
        for lifecycle in ("draft", "paused", "closed"):
            Listing.objects.filter(pk=public.listing_id).update(lifecycle=lifecycle)
            self.assertFalse(self.match(q="Araba").exists())
        Listing.objects.filter(pk=public.listing_id).update(lifecycle="live")
        for seconds, expected in ((-1, False), (0, False), (1, True)):
            Listing.objects.filter(pk=public.listing_id).update(
                expires_at=self.at + timedelta(seconds=seconds))
            self.assertEqual(self.match(q="Araba").exists(), expected)
        Listing.objects.filter(pk=public.listing_id).update(expires_at=None)
        self.assertTrue(self.match(q="Araba").exists())

    def test_listing_and_seller_restrictions_hide_owner_narrowed_search(self):
        public = self.live()
        for target in ({"listing": public.listing}, {"seller": self.owner}):
            restriction = Restriction.objects.create(
                actor=self.reviewer, reason="Test", begins_at=self.at, **target)
            self.assertFalse(self.match(q="Araba").filter(owner_id=self.owner.pk).exists())
            Restriction.objects.filter(pk=restriction.pk).update(revoked_at=self.at)
            self.assertTrue(self.match(q="Araba").exists())

    def test_wrong_listing_or_nonapproved_public_pointer_is_hidden(self):
        public = self.live(title="Cobalt")
        other = self.live(title="Harbor")
        Listing.objects.filter(pk=other.listing_id).update(public_revision=public)
        self.assertEqual(self.ids(self.match(q="Cobalt")), {public.listing_id})
        for status in ("draft", "submitted", "rejected", "withdrawn"):
            ListingRevision.objects.filter(pk=public.pk).update(status=status)
            self.assertFalse(self.match(q="Cobalt").exists())

    def test_account_email_is_not_searchable_content(self):
        self.live()
        self.assertFalse(self.match(q="owner@example.test").exists())
        sql, _ = self.match(q="owner").query.sql_with_params()
        self.assertNotIn("accounts_user", sql)
        self.assertNotIn("email", sql)

    def test_category_exact_tree_and_unknown_ids_remain_sql_filters(self):
        child = Category.objects.create(name="Child", slug="search-child", parent=self.category)
        grandchild = Category.objects.create(name="Grandchild", slug="search-grandchild", parent=child)
        child_schema = AttributeSchema.objects.create(
            category=child, version=1, definition=self.schema.definition)
        deep_schema = AttributeSchema.objects.create(
            category=grandchild, version=1, definition=self.schema.definition)
        root, branch, leaf = self.live(), self.live(schema=child_schema), self.live(schema=deep_schema)
        self.assertEqual(self.ids(self.match(category=self.category.pk)), {root.listing_id})
        self.assertEqual(self.ids(self.match(category=self.category.pk, scope="tree")),
                         {root.listing_id, branch.listing_id, leaf.listing_id})
        self.assertFalse(self.match(category=9223372036854775807).exists())

    def test_turkish_istanbul_title_variants_use_the_same_fold(self):
        rows = [self.live(title=value) for value in
                ("İstanbul", "ISTANBUL", "istanbul", "I\u0307stanbul", "i\u0307stanbul")]
        for keyword in ("İstanbul", "ISTANBUL", "istanbul", "I\u0307stanbul", "i\u0307stanbul"):
            with self.subTest(keyword=keyword):
                self.assertEqual(self.ids(self.match(q=keyword)), {row.listing_id for row in rows})
        rows[0].refresh_from_db()
        self.assertEqual(rows[0].title, "İstanbul")

    def test_turkish_dotted_and_dotless_i_and_accents_in_all_document_fields(self):
        for display, queries in (("IŞIK", ("ışık", "isik", "IŞIK")),
                                 ("Şişli", ("sisli", "ŞİŞLİ")),
                                 ("Çeşme", ("cesme", "ÇEŞME"))):
            row = self.live(title="Neutral", description=display, location=display)
            for keyword in queries:
                with self.subTest(display=display, keyword=keyword):
                    self.assertEqual(self.ids(self.match(q=keyword)), {row.listing_id})
                    self.assertEqual(self.ids(self.match(location=keyword)), {row.listing_id})

    def test_plain_full_text_ands_terms_across_weighted_fields(self):
        both = self.live(title="Clio Renault", description="Good")
        across = self.live(title="Renault", description="Clio")
        self.live(title="Renault", description="Other")
        self.live(title="Clio", description="Other")
        self.assertEqual(self.ids(self.match(q='"Renault Clio"')),
                         {both.listing_id, across.listing_id})
        self.assertFalse(self.match(q="Renault Missing").exists())
        sql, params = self.match(q="Renault Clio").query.sql_with_params()
        self.assertIn("@@", sql)
        self.assertIn("plainto_tsquery", sql)
        self.assertIn("simple", params)
        self.assertNotIn("Renault Clio", sql)

    def test_model_tokens_match_without_short_substring_fallback(self):
        bmw = self.live(title="BMW X5")
        audi = self.live(title="Audi Q7")
        peugeot = self.live(title="Peugeot208")
        self.live(title="Peugeot 208")
        self.live(title="PrefixX5Suffix Q70")
        for keyword, expected in (("X5", bmw), ("Q7", audi), ("Peugeot208", peugeot)):
            self.assertEqual(self.ids(self.match(q=keyword)), {expected.listing_id})
        self.assertFalse(self.match(q="X").exists())

    def test_literal_title_fallback_is_distinct_from_full_text(self):
        literal = self.live(title="MicroClioModel")
        self.live(title="Different")
        self.assertEqual(self.ids(self.match(q="cli")), {literal.listing_id})
        self.live(title="prefixa-b-csuffix")
        self.assertFalse(self.match(q="a-b-c").exists())

    def test_fallback_eligibility_uses_the_folded_decomposed_query(self):
        literal = self.live(title="PrefixIsiSuffix")
        for keyword in ("i\u0307si", "I\u0307SI", "isi"):
            self.assertEqual(self.ids(self.match(q=keyword)), {literal.listing_id})

    def test_literal_title_percent_underscore_quotes_and_backslash_are_escaped(self):
        for keyword in ("abc%xyz", "abc_xyz", "abc'xyz", "abc\\xyz"):
            row = self.live(title=f"prefix{keyword}suffix")
            self.live(title="prefixabcWILDCARDxyzsuffix")
            with self.subTest(keyword=keyword):
                self.assertEqual(self.ids(self.match(q=keyword)), {row.listing_id})

    def test_location_contains_is_literal_and_parameterized(self):
        for location in ("100%_", "quote' OR 1=1 --", "back\\slash"):
            row = self.live(location=f"prefix {location} suffix")
            self.live(location="prefix 100AB quote back slash suffix")
            with self.subTest(location=location):
                result = self.match(location=location)
                self.assertEqual(self.ids(result), {row.listing_id})
                sql, params = result.query.sql_with_params()
                self.assertNotIn(location, sql)
                self.assertIn(location, params)
                self.assertNotIn("UPPER(", sql)

    def test_compatible_versions_match_but_type_unit_hidden_and_missing_do_not(self):
        compatible = self.schema_version(2, area={"type": "decimal", "label": "New label"})
        changed_unit = self.schema_version(3, area={"type": "decimal", "unit": "m2"})
        changed_type = self.schema_version(4, area={"type": "integer"})
        hidden = self.schema_version(5, area={"type": "decimal", "filterable": False})
        missing_fields = deepcopy(self.schema.definition["fields"])
        del missing_fields["area"]
        missing = AttributeSchema.objects.create(
            category=self.category, version=6, definition={"fields": missing_fields})
        rows = [self.live(schema=schema) for schema in
                (self.schema, compatible, changed_unit, changed_type, hidden, missing)]
        spec = self.attribute_spec(**{"a.area.eq": "9"})
        self.assertEqual({ref.id for ref in spec.resolved_schemas}, {self.schema.pk, compatible.pk})
        self.assertEqual(self.ids(self.match(spec)), {rows[0].listing_id, rows[1].listing_id})

    def test_exact_schema_category_id_and_version_are_all_required(self):
        good = self.live()
        self.live(schema_version=2)
        other_category = Category.objects.create(name="Other", slug="search-other")
        other_schema = AttributeSchema.objects.create(
            category=other_category, version=1, definition=self.schema.definition)
        self.live(schema=other_schema)
        self.live(schema=self.schema, category=other_category)
        self.live(schema=other_schema, category=self.category)
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(**{"a.area.eq": "9"}))), {good.listing_id})

    def test_frozen_resolved_schema_set_does_not_gain_new_versions(self):
        original = self.live()
        spec = self.attribute_spec(**{"a.area.eq": "9"})
        newer = self.live(schema=self.schema_version(2))
        self.assertEqual(self.ids(self.match(spec)), {original.listing_id})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(**{"a.area.eq": "9"}))), {original.listing_id, newer.listing_id})

    def test_numeric_decimal_ranges_use_numeric_order_for_9_10_100(self):
        rows = {value: self.live(attributes={"area": value}) for value in ("9", "10", "100")}
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(**{"a.area.min": "10", "a.area.max": "99"}))),
            {rows["10"].listing_id})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(**{"a.area.min": "10"}))),
            {rows["10"].listing_id, rows["100"].listing_id})

    def test_decimal_case_rejects_wrong_json_types_and_noncanonical_text_safely(self):
        good = self.live(attributes={"area": "10"})
        invalid = (None, 10, True, {}, [], "", "NaN", "Infinity", "1e1", "01", "1.00",
                   "-0", "10\n", "9" * 65, "' OR 1=1 --")
        for value in invalid:
            self.live(attributes={"area": value})
        self.live(attributes={})
        results = self.match(self.attribute_spec(**{"a.area.min": "-1"}))
        self.assertEqual(self.ids(results), {good.listing_id})
        sql, _ = results.query.sql_with_params()
        self.assertIn("CASE WHEN", sql)
        self.assertIn("jsonb_typeof", sql)
        self.assertIn("numeric", sql.lower())

    def test_integer_case_rejects_string_boolean_fraction_and_missing(self):
        good = self.live(attributes={"model_year": 2020})
        for value in (None, "2020", True, {}, [], 2020.5, 2020.0, "9" * 65):
            self.live(attributes={"model_year": value})
        self.live(attributes={})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(**{"a.model_year.min": "0"}))), {good.listing_id})

    def test_unrestricted_numeric_cast_preserves_more_than_28_digits(self):
        low = "123456789012345678901234567890.123456789012345678901234567891"
        high = "123456789012345678901234567890.123456789012345678901234567892"
        self.live(attributes={"area": low})
        higher = self.live(attributes={"area": high})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(**{"a.area.min": high}))), {higher.listing_id})

    def test_zero_false_null_and_missing_are_distinct(self):
        zero_false = self.live(attributes={"area": "0", "electric": False})
        self.live(attributes={"area": "0", "electric": 0})
        self.live(attributes={"area": 0, "electric": False})
        self.live(attributes={"area": "0", "electric": "false"})
        self.live(attributes={"area": "0", "electric": None})
        self.live(attributes={})
        self.assertEqual(self.ids(self.match(self.attribute_spec(
            **{"a.area.eq": "0", "a.electric.eq": "false"}))), {zero_false.listing_id})

    def test_each_candidate_applies_its_own_stored_numeric_domain(self):
        bounded = self.schema_version(2, area={"type": "decimal", "min": "10", "max": "20"})
        old = self.live(attributes={"area": "9"})
        good = self.live(schema=bounded, attributes={"area": "10"})
        self.live(schema=bounded, attributes={"area": "9"})
        self.live(schema=bounded, attributes={"area": "100"})
        spec = self.attribute_spec(**{"a.area.min": "-1", "a.area.max": "1000"})
        self.assertEqual(self.ids(self.match(spec)), {old.listing_id, good.listing_id})

    def test_candidate_equality_options_are_canonical_and_branch_specific(self):
        category = Category.objects.create(name="Options", slug="search-options")
        source = AttributeSchema.objects.create(category=category, version=1, definition={
            "fields": {"amount": {"type": "decimal", "options": ["1.00", "9"]}}})
        target = AttributeSchema.objects.create(category=category, version=2, definition={
            "fields": {"amount": {"type": "decimal", "options": ["10", "100"]}}})
        one = self.live(schema=source, attributes={"amount": "1"})
        self.live(schema=source, attributes={"amount": "1.00"})
        self.live(schema=source, attributes={"amount": "100"})
        hundred = self.live(schema=target, attributes={"amount": "100"})
        one_spec = self.attribute_spec(source, **{"a.amount.eq": "1.00"})
        self.assertEqual(one_spec.attributes[0].value, "1")
        self.assertEqual(self.ids(self.match(one_spec)), {one.listing_id})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(source, **{"a.amount.eq": "100"}))), {hundred.listing_id})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(source, **{"a.amount.min": "0"}))),
            {one.listing_id, hundred.listing_id})

    def test_string_equality_is_case_sensitive_typed_and_candidate_option_guarded(self):
        source = self.schema_version(2, brand={"type": "string", "options": [" blue "]})
        target = self.schema_version(3, brand={"type": "string", "options": ["green"]})
        green = self.live(schema=target, attributes={"brand": "green"})
        self.live(schema=source, attributes={"brand": "green"})
        self.live(schema=target, attributes={"brand": "GREEN"})
        self.live(schema=target, attributes={"brand": None})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(source, schemas=f"{source.pk}:2,{target.pk}:3",
                                **{"a.brand.eq": " green "}))), {green.listing_id})
        text = self.live(attributes={"brand": "false"})
        self.live(attributes={"brand": False})
        self.assertEqual(self.ids(self.match(
            self.attribute_spec(schemas=f"{self.schema.pk}:1", **{"a.brand.eq": "false"}))),
            {text.listing_id})

    def test_literal_double_underscore_attribute_key_is_not_a_json_path(self):
        schema = self.schema_version(2, drive__mode={"type": "string"})
        direct = self.live(schema=schema, attributes={"drive__mode": "sport"})
        self.live(schema=schema, attributes={"drive": {"mode": "sport"}})
        spec = self.attribute_spec(schema, **{"a.drive__mode.eq": "sport"})
        queryset = self.match(spec)
        self.assertEqual(self.ids(queryset), {direct.listing_id})
        sql, params = queryset.query.sql_with_params()
        self.assertIn("drive__mode", params)
        self.assertNotIn("drive__mode", sql)
        self.assertNotIn("#>", sql)
        self.assertIn(self.category.pk, params)
        self.assertIn(schema.pk, params)

    def test_all_requested_predicates_must_match_inside_one_candidate_branch(self):
        second = self.schema_version(2)
        good = self.live(schema=second, attributes={"area": "10", "electric": False})
        self.live(attributes={"area": "10", "electric": True})
        self.live(schema=second, attributes={"area": "9", "electric": False})
        self.assertEqual(self.ids(self.match(self.attribute_spec(
            **{"a.area.min": "10", "a.electric.eq": "false"}))), {good.listing_id})

    def test_manually_malformed_search_specs_are_rejected_by_both_entrypoints(self):
        base = self.spec()
        for spec in (None, replace(base, version=True), replace(base, category_id=True),
                     replace(base, sort="price_asc"), replace(base, sort="relevance"),
                     replace(base, attributes=[]), replace(base, price_min=Decimal("NaN")),
                     replace(base, keyword=["x"])):
            with self.subTest(spec=spec):
                with self.assertRaises(ValidationError):
                    self.search.matching_public_listings(spec=spec, at=self.at)
                with self.assertRaises(ValidationError):
                    self.search.order_search_results(Listing.objects.all(), spec=spec)

    def test_newest_order_uses_publication_time_and_descending_uuid_ties(self):
        old = self.live(published_at=self.at - timedelta(days=1), listing_id=UUID(int=400))
        newer_low = self.live(listing_id=UUID(int=100))
        newer_high = self.live(listing_id=UUID(int=200))
        spec = self.spec()
        rows = self.search.order_search_results(self.match(spec), spec=spec)
        self.assertEqual(list(rows.values_list("pk", flat=True)),
                         [newer_high.listing_id, newer_low.listing_id, old.listing_id])

    def test_prices_sort_numerically_in_selected_currency_with_nulls_last(self):
        rows = {value: self.live(price=value) for value in ("9", "10", "100")}
        empty = self.live(price=None)
        self.live(price="1", currency="USD")
        for sort, values in (("price_asc", ("9", "10", "100")),
                             ("price_desc", ("100", "10", "9"))):
            spec = self.spec(currency="EUR", sort=sort)
            ordered = self.search.order_search_results(self.match(spec), spec=spec)
            self.assertEqual(list(ordered.values_list("pk", flat=True)),
                             [rows[value].listing_id for value in values] + [empty.listing_id])

    def test_price_ties_use_publication_time_then_uuid(self):
        old = self.live(price="10", published_at=self.at - timedelta(days=1), listing_id=UUID(int=400))
        low = self.live(price="10", listing_id=UUID(int=100))
        high = self.live(price="10", listing_id=UUID(int=200))
        for sort in ("price_asc", "price_desc"):
            spec = self.spec(currency="EUR", sort=sort)
            ordered = self.search.order_search_results(self.match(spec), spec=spec)
            self.assertEqual(list(ordered.values_list("pk", flat=True)),
                             [high.listing_id, low.listing_id, old.listing_id])

    def test_relevance_weights_title_above_description_and_keeps_literal_only(self):
        literal = self.live(title="MicroRenaultModel")
        description = self.live(title="Other", description="Renault")
        title = self.live(title="Renault", description="Other")
        spec = self.spec(q="Renault", sort="relevance")
        ordered = self.search.order_search_results(self.match(spec), spec=spec)
        self.assertEqual(list(ordered.values_list("pk", flat=True)),
                         [title.listing_id, description.listing_id, literal.listing_id])

    def test_every_sort_keeps_exact_membership(self):
        self.live(title="MicroClioModel", price=None)
        self.live(title="Clio", price="9")
        self.live(title="Other", price="1")
        base = self.spec(q="Clio", currency="EUR")
        membership = self.ids(self.match(base))
        for sort in ("newest", "price_asc", "price_desc", "relevance"):
            spec = replace(base, sort=sort)
            self.assertEqual(self.ids(self.search.order_search_results(
                self.match(spec), spec=spec)), membership)

    def test_matching_and_ordering_do_not_evaluate_listing_rows(self):
        self.live()
        spec = self.attribute_spec(**{"a.area.eq": "9"})
        with CaptureQueriesContext(connection) as captured:
            matched = self.match(spec)
            ordered = self.search.order_search_results(matched, spec=spec)
        self.assertIsNone(matched._result_cache)
        self.assertIsNone(ordered._result_cache)
        self.assertTrue(all("listings_listing" not in item["sql"] for item in captured))
        self.assertEqual(ordered.count(), 1)

    def test_related_revision_category_schema_and_images_keep_bounded_loading(self):
        for _ in range(3):
            self.live()
        spec = self.spec()
        ordered = self.search.order_search_results(self.match(spec), spec=spec)
        with self.assertNumQueries(2):
            rows = list(ordered)
            for row in rows:
                self.assertEqual(row.public_revision.category.pk, self.category.pk)
                self.assertEqual(row.public_revision.attribute_schema.pk, self.schema.pk)
                self.assertEqual(list(row.public_revision.images.all()), [])
        self.assertEqual(len(rows), 3)

    def test_actual_database_has_the_three_approved_expression_gin_indexes(self):
        expected = {"search_document_v1_gin", "search_title_v1_trgm", "search_location_v1_trgm"}
        with connection.cursor() as cursor:
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = %s", ["pg_trgm"])
            self.assertEqual(cursor.fetchone(), ("pg_trgm",))
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = %s AND indexname = ANY(%s)",
                ["listings_listingrevision", sorted(expected)])
            indexes = dict(cursor.fetchall())
        self.assertEqual(set(indexes), expected)
        model_indexes = {index.name: index for index in ListingRevision._meta.indexes}
        migration = import_module("listings.migrations.0003_public_search_indexes").Migration
        migration_indexes = {operation.index.name: operation.index
                             for operation in migration.operations if hasattr(operation, "index")}
        for name, definition in indexes.items():
            self.assertEqual(model_indexes[name].deconstruct(), migration_indexes[name].deconstruct())
            self.assertIn("USING gin", definition)
            self.assertIn("normalize(", definition.lower())
            self.assertIn("'ÇçĞğİIıiÖöŞşÜü'::text || chr(775)", definition)
            self.assertIn("'ccggiiiioossuu'::text", definition)
            self.assertTrue(definition.endswith("WHERE ((status)::text = 'approved'::text)"))
        self.assertIn("'simple'::regconfig", indexes["search_document_v1_gin"])
        self.assertIn("setweight", indexes["search_document_v1_gin"])
        self.assertIn("gin_trgm_ops", indexes["search_title_v1_trgm"])
        self.assertIn("gin_trgm_ops", indexes["search_location_v1_trgm"])

    def test_nul_text_is_rejected_by_both_query_apis_before_listing_sql(self):
        base = self.spec()
        attribute_base = self.attribute_spec(**{"a.brand.eq": "Renault"})
        invalid_specs = (
            ("q", replace(base, keyword="Renault\x00", sort="relevance")),
            ("location", replace(base, location="Renault\x00")),
            ("a.brand.eq", replace(attribute_base, attributes=(
                replace(attribute_base.attributes[0], value="Renault\x00"),))),
        )
        for field, spec in invalid_specs:
            calls = (
                ("matching", lambda: self.search.matching_public_listings(spec=spec, at=self.at)),
                ("ordering", lambda: self.search.order_search_results(Listing.objects.all(), spec=spec)),
            )
            for entrypoint, call in calls:
                with self.subTest(field=field, entrypoint=entrypoint):
                    with CaptureQueriesContext(connection) as captured:
                        with self.assertRaises(ValidationError) as error:
                            call()
                    self.assertIn(field, error.exception.message_dict)
                    self.assertNotIn("\x00", str(error.exception))
                    self.assertTrue(all("listings_listing" not in item["sql"] for item in captured))
