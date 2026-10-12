from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.db import connection
from django.http import QueryDict
from django.test import TestCase
from catalog.models import AttributeSchema, Category

try:
    from listings.search import parsing
    from listings.search.specs import AttributePredicate, SchemaRef, SearchSpec
except ImportError:
    parsing = None


class SearchSpecTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(parsing, "SearchSpec v1 is not implemented.")
        self.category = Category.objects.create(name="Root", slug="root")
        self.fields = {
            "distance": {"type": "integer", "unit": " km ", "min": 10, "max": 100},
            "area": {"type": "decimal", "min": "1", "options": ["1.00", "10.00"]},
            "fuel": {"type": "string", "options": ["diesel", "electric"]},
            "enabled": {"type": "boolean"},
            "engine__size": {"type": "integer"},
            "hidden": {"type": "string", "filterable": False},
        }
        self.schema = self.make_schema(1, self.fields)

    def make_schema(self, version, fields):
        return AttributeSchema.objects.create(category=self.category, version=version, definition={"fields": fields})

    def parse(self, pairs=()):
        return parsing.parse_search_spec(QueryDict(urlencode(pairs)))

    def attribute_pairs(self, *pairs):
        return [("category", str(self.category.pk)), ("schema", str(self.schema.pk)),
                ("schema_version", "1"), *pairs]

    def test_runtime_is_postgresql_and_empty_contract_is_frozen(self):
        self.assertEqual(connection.vendor, "postgresql")
        spec = self.parse()
        self.assertEqual(parsing.search_querystring(spec), "")
        self.assertEqual(parsing.search_spec_to_dict(spec), {
            "version": 1, "keyword": "", "category_id": None, "category_scope": "exact",
            "location": "", "currency": "", "price_min": None, "price_max": None,
            "attribute_schema": None, "attributes": [], "resolved_schemas": [], "sort": "newest"})
        with self.assertRaises(FrozenInstanceError):
            spec.keyword = "changed"
        with self.assertRaises(FrozenInstanceError):
            SchemaRef(1, 1, 1).id = 2
        with self.assertRaises(FrozenInstanceError):
            AttributePredicate("x", "integer", "", "eq", 0).value = 1

    def test_canonical_common_roundtrip_and_page_once(self):
        spec = self.parse([("q", " I\u0307stanbul   BMW X5 "), ("category", f"00{self.category.pk}"),
                           ("scope", "tree"), ("location", " Şişli  merkez "), ("currency", "try"),
                           ("price_min", "0"), ("price_max", "10.00"), ("sort", "price_asc"),
                           ("ignored", "x"), ("page", "99")])
        self.assertEqual(spec.keyword, "İstanbul BMW X5")
        self.assertEqual(spec.location, "Şişli merkez")
        expected = urlencode([("v", "1"), ("q", "İstanbul BMW X5"), ("category", self.category.pk),
                              ("scope", "tree"), ("location", "Şişli merkez"), ("currency", "TRY"),
                              ("price_min", "0.00"), ("price_max", "10.00"), ("sort", "price_asc"), ("page", 2)])
        self.assertEqual(parsing.search_querystring(spec, page=2), expected)
        self.assertEqual(parsing.parse_search_spec(QueryDict(expected)), spec)
        self.assertEqual(parsing.search_spec_from_dict(parsing.search_spec_to_dict(spec)), spec)

    def test_attributes_zero_false_literal_key_and_canonical_decimal(self):
        spec = self.parse(self.attribute_pairs(("a.engine__size.eq", "0"), ("a.enabled.eq", "false"),
                                               ("a.area.eq", "1.00")))
        self.assertEqual(spec.attributes, (
            AttributePredicate("area", "decimal", "", "eq", "1"),
            AttributePredicate("enabled", "boolean", "", "eq", False),
            AttributePredicate("engine__size", "integer", "", "eq", 0)))
        data = parsing.search_spec_to_dict(spec)
        self.assertEqual(data["attribute_schema"], {"id": self.schema.pk, "category_id": self.category.pk, "version": 1})
        self.assertEqual(data["attributes"][0], {"key": "area", "kind": "decimal", "unit": "", "operator": "eq", "value": "1"})
        self.assertEqual(parsing.search_spec_from_dict(data), spec)
        self.assertEqual(parsing.parse_search_spec(QueryDict(parsing.search_querystring(spec))), spec)

    def test_ranges_are_type_bounds_not_stored_value_domain_or_option_members(self):
        spec = self.parse(self.attribute_pairs(("a.distance.min", "0"), ("a.distance.max", "200"),
                                               ("a.area.min", "0.00"), ("a.area.max", "100.5")))
        self.assertEqual([p.value for p in spec.attributes], ["0", "100.5", 0, 200])
        self.assertEqual(parsing.search_spec_from_dict(parsing.search_spec_to_dict(spec)), spec)

    def test_fresh_resolution_freezes_old_and_new_then_replay_never_appends(self):
        new = self.make_schema(2, self.fields)
        spec = self.parse(self.attribute_pairs(("a.distance.eq", "10")))
        self.assertEqual(spec.resolved_schemas, (SchemaRef(self.schema.pk, self.category.pk, 1),
                                                SchemaRef(new.pk, self.category.pk, 2)))
        url, payload = parsing.search_querystring(spec), parsing.search_spec_to_dict(spec)
        later = self.make_schema(3, self.fields)
        self.assertEqual(parsing.parse_search_spec(QueryDict(url)), spec)
        self.assertEqual(parsing.search_spec_from_dict(payload), spec)
        self.assertEqual(len(self.parse(self.attribute_pairs(("a.distance.eq", "10"))).resolved_schemas), 3)
        self.assertNotIn(SchemaRef(later.pk, self.category.pk, 3), spec.resolved_schemas)

    def test_equality_may_be_valid_only_in_later_branch(self):
        changed = {**self.fields, "area": {"type": "decimal", "min": "5", "options": ["20.00"]}}
        new = self.make_schema(2, changed)
        spec = self.parse(self.attribute_pairs(("a.area.eq", "20.00")))
        self.assertEqual(spec.attributes[0].value, "20")
        self.assertEqual([r.id for r in spec.resolved_schemas], [self.schema.pk, new.pk])
        with self.assertRaises(ValidationError):
            self.parse(self.attribute_pairs(("a.area.eq", "30")))

    def test_frozen_incompatible_missing_or_wrong_version_targets_are_rejected(self):
        other = Category.objects.create(name="Other", slug="other")
        foreign = AttributeSchema.objects.create(category=other, version=1, definition={"fields": self.fields})
        wrong = self.make_schema(2, {**self.fields, "distance": {"type": "decimal", "unit": "km"}})
        for refs in (f"{foreign.pk}:1", f"{wrong.pk}:2", f"{self.schema.pk}:2", "9223372036854775807:1",
                     f"{self.schema.pk}:1,{self.schema.pk}:1"):
            with self.subTest(refs=refs), self.assertRaises(ValidationError):
                self.parse(self.attribute_pairs(("a.distance.eq", "10"), ("schemas", refs)))

    def test_schema_metadata_without_predicates_is_discarded(self):
        spec = self.parse(self.attribute_pairs(("schemas", f"{self.schema.pk}:1")))
        self.assertIsNone(spec.attribute_schema)
        self.assertEqual(spec.resolved_schemas, ())
        self.assertNotIn("schema", parsing.search_querystring(spec))
        with self.assertRaises(ValidationError):
            self.parse([("schema", "1"), ("schema", "2")])

    def test_legacy_malformed_category_matrix_and_last_value(self):
        for value in ("", "abc", "-1", "+1", "1.0", "1e2", "١", "0", "9"*20, "9223372036854775808", " 1 "):
            with self.subTest(value=value):
                self.assertIsNone(self.parse([("category", value)]).category_id)
        self.assertEqual(self.parse([("category", "bad"), ("category", str(self.category.pk))]).category_id,
                         self.category.pk)
        self.assertIsNone(self.parse([("category", str(self.category.pk)), ("category", "bad")]).category_id)
        self.assertEqual(self.parse([("category", "9223372036854775807")]).category_id, 9223372036854775807)

    def test_missing_category_and_tree_attributes_are_dependency_errors(self):
        for pairs in ([("a.distance.eq", "10")],
                      self.attribute_pairs(("scope", "tree"), ("a.distance.eq", "10")),
                      [("category", "bad"), ("a.distance.eq", "10")],
                      [("scope", "tree")]):
            with self.subTest(pairs=pairs), self.assertRaises(ValidationError):
                self.parse(pairs)

    def test_unknown_duplicate_hidden_and_conflicting_attributes_are_errors(self):
        for pairs in (("a.missing.eq", "x"), ("a.hidden.eq", "x"), ("a.distance.nope", "10"),
                      ("a.enabled.min", "false"), ("a.", "x")):
            with self.subTest(pairs=pairs), self.assertRaises(ValidationError):
                self.parse(self.attribute_pairs(pairs))
        for pairs in ([("a.distance.eq", "10"), ("a.distance.eq", "10")],
                      [("a.distance.eq", "10"), ("a.distance.min", "0")],
                      [("a.distance.min", "20"), ("a.distance.max", "10")]):
            with self.assertRaises(ValidationError):
                self.parse(self.attribute_pairs(*pairs))

    def test_scalar_duplicates_and_invalid_versions_do_not_broaden(self):
        for field in ("v", "q", "scope", "location", "currency", "price_min", "price_max",
                      "schema", "schema_version", "schemas", "sort", "page"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.parse([(field, "1"), (field, "1")])
        for version in ("", "0", "2", "True", "1.0", "9"*65):
            with self.subTest(version=version), self.assertRaises(ValidationError):
                self.parse([("v", version)])

    def test_prices_require_plain_bounded_finite_decimal_and_currency(self):
        for value in ("NaN", "Infinity", "-Infinity", "1e999999", "1,00", "-1", "0.001", "9"*65,
                      "10000000000000000", "9"*10000):
            with self.subTest(value=value[:30]), self.assertRaises(ValidationError):
                self.parse([("currency", "TRY"), ("price_min", value)])
        for pairs in ([("price_min", "0")], [("sort", "price_desc")],
                      [("currency", "TRY"), ("price_min", "2"), ("price_max", "1")]):
            with self.assertRaises(ValidationError):
                self.parse(pairs)
        self.assertEqual(self.parse([("currency", "TRY"), ("price_max", "9999999999999999.99")]).price_max,
                         Decimal("9999999999999999.99"))

    def test_text_currency_and_sort_validation(self):
        for pairs in ([("q", " %_ !!! ")], [("q", "a"*201)], [("location", "x"*161)],
                      [("currency", "₺")], [("currency", "ıry")], [("sort", "unknown")],
                      [("sort", "relevance")]):
            with self.assertRaises(ValidationError):
                self.parse(pairs)
        self.assertEqual(self.parse([("q", "BMW X5"), ("sort", "relevance")]).sort, "relevance")

    def test_budgets_count_encoded_bytes_repeats_and_raw_values(self):
        for pairs in ([("ignored", "x"*8193)], [("ignored", "x")]*65,
                      self.attribute_pairs(("a.fuel.eq", "x"*201)),
                      self.attribute_pairs(("a.distance.eq", "1"*65)),
                      [("q", "😀"*2000)]):
            with self.assertRaises(ValidationError):
                self.parse(pairs)
        self.assertEqual(self.parse([("ignored", "x")]*64).keyword, "")
        many_fields = {f"field_{n}": {"type": "integer"} for n in range(21)}
        many = self.make_schema(2, many_fields)
        with self.assertRaises(ValidationError):
            self.parse([("category", str(self.category.pk)), ("schema", str(many.pk)),
                        ("schema_version", "2"), *[(f"a.field_{n}.eq", "0") for n in range(21)]])

    def test_resolved_schema_cap_is_error_not_silent_truncation(self):
        for version in range(2, 66):
            self.make_schema(version, self.fields)
        with self.assertRaises(ValidationError):
            self.parse(self.attribute_pairs(("a.distance.eq", "10")))

    def test_programmatic_ids_versions_and_prices_reject_bools_huge_and_bad_types(self):
        base = self.parse()
        for spec in (replace(base, version=True), replace(base, version=2),
                     replace(base, category_id=True), replace(base, category_id=2**10000),
                     replace(base, category_id=-1), replace(base, currency="TRY", price_min=True),
                     replace(base, currency="TRY", price_min=Decimal("1e999999")),
                     replace(base, currency="TRY", price_min=Decimal("NaN")),
                     replace(base, attributes=[]), replace(base, keyword=1)):
            with self.assertRaises(ValidationError):
                parsing.validate_search_spec(spec)

    def test_json_requires_all_exact_fields_and_nested_shapes(self):
        spec = self.parse(self.attribute_pairs(("a.distance.eq", "10")))
        payload = parsing.search_spec_to_dict(spec)
        for field in payload:
            bad = {**payload}
            del bad[field]
            with self.subTest(missing=field), self.assertRaises(ValidationError):
                parsing.search_spec_from_dict(bad)
        for bad in ({**payload, "extra": 1}, {**payload, "version": True}, {**payload, "category_id": True},
                    {**payload, "attribute_schema": {**payload["attribute_schema"], "version": True}},
                    {**payload, "attributes": [{**payload["attributes"][0], "extra": 1}]},
                    {**payload, "attributes": [{**payload["attributes"][0], "value": True}]},
                    {**payload, "resolved_schemas": []},
                    {**payload, "currency": "TRY", "price_min": 1},
                    {**payload, "currency": "TRY", "price_min": "1.0"}):
            with self.assertRaises(ValidationError):
                parsing.search_spec_from_dict(bad)

    def test_json_decimal_and_boolean_values_keep_their_types(self):
        spec = self.parse(self.attribute_pairs(("a.area.eq", "1"), ("a.enabled.eq", "false")))
        payload = parsing.search_spec_to_dict(spec)
        for key, value in (("area", 1), ("area", 1.0), ("enabled", "false"), ("enabled", 0)):
            altered = [{**p, "value": value} if p["key"] == key else p for p in payload["attributes"]]
            with self.assertRaises(ValidationError):
                parsing.search_spec_from_dict({**payload, "attributes": altered})

    def test_errors_are_field_addressable_without_source_values(self):
        secret = "sensitive-invalid-number"
        with self.assertRaises(ValidationError) as caught:
            self.parse([("currency", "TRY"), ("price_min", secret)])
        self.assertIn("price_min", caught.exception.message_dict)
        self.assertNotIn(secret, str(caught.exception))

    def test_blank_unknown_attribute_is_still_an_error_and_known_blank_is_absent(self):
        for pairs in ([("a.missing.eq", "")], self.attribute_pairs(("a.missing.eq", ""))):
            with self.assertRaises(ValidationError):
                self.parse(pairs)
        spec = self.parse(self.attribute_pairs(("a.enabled.eq", ""), ("a.distance.min", "")))
        self.assertEqual(spec.attributes, ())
        self.assertIsNone(spec.attribute_schema)

    def test_malformed_programmatic_predicates_have_validation_errors(self):
        spec = self.parse(self.attribute_pairs(("a.distance.eq", "10")))
        predicate = spec.attributes[0]
        for altered in (replace(predicate, operator=[]), replace(predicate, key=[]),
                        replace(predicate, kind=[]), replace(predicate, unit=[]),
                        replace(predicate, value=True), replace(predicate, value=2**10000)):
            with self.assertRaises(ValidationError):
                parsing.validate_search_spec(replace(spec, attributes=(altered,)))

    def test_programmatic_and_json_source_and_target_bounds_are_checked_before_conversion(self):
        spec = self.parse(self.attribute_pairs(("a.distance.eq", "10")))
        for ref in (SchemaRef(True, self.category.pk, 1), SchemaRef(self.schema.pk, True, 1),
                    SchemaRef(self.schema.pk, self.category.pk, True),
                    SchemaRef(self.schema.pk, self.category.pk, 2147483648),
                    SchemaRef(2**10000, self.category.pk, 1)):
            with self.assertRaises(ValidationError):
                parsing.validate_search_spec(replace(spec, attribute_schema=ref))
            with self.assertRaises(ValidationError):
                parsing.validate_search_spec(replace(spec, resolved_schemas=(ref,)))

    def test_frozen_subset_must_validate_equality_against_that_subset(self):
        newer = self.make_schema(2, {**self.fields, "area": {"type": "decimal", "options": ["20.00"]}})
        pairs = self.attribute_pairs(("a.area.eq", "20"))
        with self.assertRaises(ValidationError):
            self.parse([*pairs, ("schemas", f"{self.schema.pk}:1")])
        spec = self.parse([*pairs, ("schemas", f"{newer.pk}:2")])
        self.assertEqual(spec.resolved_schemas, (SchemaRef(newer.pk, self.category.pk, 2),))

    def test_unused_programmatic_refs_validate_exact_identity_before_discarding(self):
        base = self.parse()
        valid = SchemaRef(self.schema.pk, self.category.pk, 1)
        spec = replace(base, attribute_schema=valid, resolved_schemas=(valid,))
        self.assertIsNone(parsing.validate_search_spec(spec).attribute_schema)
        payload = parsing.search_spec_to_dict(base)
        for field in ("attribute_schema", "resolved_schemas"):
            bad_ref = {"id": self.schema.pk, "category_id": self.category.pk, "version": 2}
            altered = {**payload, field: bad_ref if field == "attribute_schema" else [bad_ref]}
            with self.assertRaises(ValidationError):
                parsing.search_spec_from_dict(altered)
        for ref in (SchemaRef(self.schema.pk, self.category.pk, 2),
                    SchemaRef(9223372036854775807, self.category.pk, 1)):
            with self.assertRaises(ValidationError):
                parsing.validate_search_spec(replace(base, resolved_schemas=(ref,)))

    def test_signed_zero_prices_canonicalize_through_get_and_json_for_both_bounds(self):
        for field in ("price_min", "price_max"):
            for value in ("-0", "-0.0", "-0.00", "0", "0.00"):
                with self.subTest(field=field, value=value):
                    spec = self.parse([("currency", "TRY"), (field, value)])
                    self.assertEqual(str(getattr(spec, field)), "0.00")
                    payload = parsing.search_spec_to_dict(spec)
                    self.assertEqual(payload[field], "0.00")
                    self.assertEqual(parsing.search_spec_from_dict(payload), spec)
                    self.assertEqual(parsing.parse_search_spec(QueryDict(parsing.search_querystring(spec))), spec)

    def test_manual_signed_zero_prices_use_shared_unsigned_two_place_normalization(self):
        base = self.parse([("currency", "TRY")])
        for field in ("price_min", "price_max"):
            for value in ("-0", "-0.0", "-0.00", "0", "0.00"):
                with self.subTest(field=field, value=value):
                    manual = replace(base, **{field: Decimal(value)})
                    spec = parsing.validate_search_spec(manual)
                    self.assertEqual(str(getattr(spec, field)), "0.00")
                    payload = parsing.search_spec_to_dict(manual)
                    self.assertEqual(payload[field], "0.00")
                    self.assertEqual(parsing.search_spec_from_dict(payload), spec)
                    self.assertEqual(parsing.parse_search_spec(QueryDict(parsing.search_querystring(manual))), spec)

    def test_query_byte_limit_is_inclusive_for_single_ascii_pair(self):
        for length in (8191, 8192, 8193):
            params = QueryDict("ignored=" + "x" * (length - len("ignored=")))
            self.assertEqual(len(params.urlencode().encode("utf-8")), length)
            with self.subTest(length=length):
                if length <= 8192:
                    self.assertEqual(parsing.parse_search_spec(params).keyword, "")
                else:
                    with self.assertRaises(ValidationError):
                        parsing.parse_search_spec(params)

    def test_query_byte_limit_counts_repeated_pair_separators_exactly(self):
        prefix = "&".join(["ignored=x"] * 63) + "&ignored="
        for length in (8191, 8192, 8193):
            params = QueryDict(prefix + "x" * (length - len(prefix)))
            self.assertEqual(sum(len(values) for _, values in params.lists()), 64)
            self.assertEqual(len(params.urlencode().encode("utf-8")), length)
            with self.subTest(length=length):
                if length <= 8192:
                    self.assertEqual(parsing.parse_search_spec(params).keyword, "")
                else:
                    with self.assertRaises(ValidationError):
                        parsing.parse_search_spec(params)

    def test_query_byte_limit_checks_utf8_and_percent_encoding_expansion(self):
        for expanded in ("é", "&"):
            params = QueryDict("", mutable=True)
            params["ignored"] = expanded
            overhead = len(params.urlencode().encode("utf-8"))
            for length in (8191, 8192, 8193):
                params["ignored"] = expanded + "x" * (length - overhead)
                self.assertEqual(len(params.urlencode().encode("utf-8")), length)
                with self.subTest(expanded=expanded, length=length):
                    if length <= 8192:
                        self.assertEqual(parsing.parse_search_spec(params).keyword, "")
                    else:
                        with self.assertRaises(ValidationError):
                            parsing.parse_search_spec(params)

    def test_nul_common_text_get_has_field_errors(self):
        for field in ("q", "location"):
            for value in ("\x00Renault", "Re\x00nault", "Renault\x00"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValidationError) as error:
                        self.parse([(field, value)])
                    self.assertIn(field, error.exception.message_dict)
                    self.assertNotIn("\x00", str(error.exception))

    def test_nul_common_text_json_and_manual_have_field_errors(self):
        base = self.parse()
        for field, attribute in (("q", "keyword"), ("location", "location")):
            invalid = replace(base, **{attribute: "Renault\x00"})
            payload = parsing.search_spec_to_dict(base)
            payload[attribute] = "Renault\x00"
            checks = (
                ("json", lambda: parsing.search_spec_from_dict(payload)),
                ("manual", lambda: parsing.validate_search_spec(invalid)),
                ("serialize", lambda: parsing.search_spec_to_dict(invalid)),
                ("querystring", lambda: parsing.search_querystring(invalid)),
            )
            for entrypoint, check in checks:
                with self.subTest(field=field, entrypoint=entrypoint):
                    with self.assertRaises(ValidationError) as error:
                        check()
                    self.assertIn(field, error.exception.message_dict)
                    self.assertNotIn("\x00", str(error.exception))

    def test_nul_free_string_get_json_and_manual_have_attribute_field_errors(self):
        source = self.make_schema(2, {**self.fields, "notes": {"type": "string"}})
        prefix = [("category", str(self.category.pk)), ("schema", str(source.pk)),
                  ("schema_version", "2")]
        base = self.parse(prefix + [("a.notes.eq", "Renault")])
        for value in ("\x00Renault", "Re\x00nault", "Renault\x00"):
            invalid = replace(base, attributes=(replace(base.attributes[0], value=value),))
            payload = parsing.search_spec_to_dict(base)
            payload["attributes"][0]["value"] = value
            checks = (
                ("get", lambda: self.parse(prefix + [("a.notes.eq", value)])),
                ("json", lambda: parsing.search_spec_from_dict(payload)),
                ("manual", lambda: parsing.validate_search_spec(invalid)),
                ("serialize", lambda: parsing.search_spec_to_dict(invalid)),
                ("querystring", lambda: parsing.search_querystring(invalid)),
            )
            for entrypoint, check in checks:
                with self.subTest(value=value, entrypoint=entrypoint):
                    with self.assertRaises(ValidationError) as error:
                        check()
                    self.assertIn("a.notes.eq", error.exception.message_dict)
                    self.assertNotIn("\x00", str(error.exception))

    def test_nul_rejection_preserves_valid_text_zero_false_roundtrips(self):
        source = self.make_schema(2, {**self.fields, "notes": {"type": "string"}})
        spec = self.parse([
            ("category", str(self.category.pk)), ("schema", str(source.pk)),
            ("schema_version", "2"), ("q", " \tI\u0307stanbul   BMW X5\n"),
            ("location", " Şişli\t merkez "), ("currency", "EUR"), ("price_min", "-0.00"),
            ("a.engine__size.eq", "0"), ("a.enabled.eq", "false"),
            ("a.notes.eq", " Renault \t Clio "),
        ])
        self.assertEqual(spec.keyword, "İstanbul BMW X5")
        self.assertEqual(spec.location, "Şişli merkez")
        self.assertEqual(str(spec.price_min), "0.00")
        attributes = {predicate.key: predicate.value for predicate in spec.attributes}
        self.assertIs(attributes["enabled"], False)
        self.assertEqual(attributes["engine__size"], 0)
        self.assertIs(type(attributes["engine__size"]), int)
        self.assertEqual(attributes["notes"], "Renault \t Clio")
        self.assertEqual(parsing.search_spec_from_dict(parsing.search_spec_to_dict(spec)), spec)
        self.assertEqual(parsing.parse_search_spec(QueryDict(parsing.search_querystring(spec))), spec)
