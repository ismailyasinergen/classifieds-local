from decimal import Decimal

from django.contrib.postgres.search import SearchRank
from django.core.exceptions import ValidationError
from django.db.models import F, Q, QuerySet, Value
from django.db.models.lookups import Regex

from catalog.models import AttributeSchema
from catalog.search import category_scope_ids
from catalog.validation import normalize_attribute_value
from listings.models import Listing
from listings.queries import public_listings

from .expressions import (
    SearchFoldV1, attribute_value_v1, folded_location_v1, folded_title_v1,
    search_query_v1, search_vector_v1,
)
from .parsing import validate_search_spec
from .specs import SearchSpec


def _comparison_value(kind, value):
    if kind in ("integer", "decimal"):
        return Decimal(str(value).strip())
    if kind == "boolean":
        return "true" if value else "false"
    return value


def _candidate_branch(*, schema, spec, aliases):
    branch = Q(
        public_revision__category_id=schema.category_id,
        public_revision__attribute_schema_id=schema.pk,
        public_revision__schema_version=schema.version,
    )
    guarded = set()
    for predicate in spec.attributes:
        rule = schema.definition["fields"].get(predicate.key)
        if (not isinstance(rule, dict) or rule.get("filterable") is False
                or rule.get("type") != predicate.kind
                or rule.get("unit", "").strip() != predicate.unit):
            return None
        alias = aliases[predicate.key]
        if predicate.key not in guarded:
            # CASE rejects missing/null/wrong JSON types before any comparison.
            branch &= Q(**{f"{alias}__isnull": False})
            if predicate.kind in ("integer", "decimal"):
                for bound, operator in (("min", "gte"), ("max", "lte")):
                    if bound in rule:
                        branch &= Q(**{
                            f"{alias}__{operator}": _comparison_value(predicate.kind, rule[bound])})
            if "options" in rule:
                option_rule = {key: value for key, value in rule.items() if key != "options"}
                options = [
                    _comparison_value(predicate.kind, normalize_attribute_value(
                        name="attributes", rule=option_rule, value=value))
                    for value in rule["options"]
                ]
                branch &= Q(**{f"{alias}__in": options})
            guarded.add(predicate.key)
        if predicate.operator == "eq":
            try:
                value = normalize_attribute_value(
                    name="attributes", rule=rule, value=predicate.value)
            except ValidationError:
                # Equality may be allowed by another compatible frozen branch.
                return None
            operator = "exact"
        else:
            # Search endpoints compare values; candidate bounds guard storage.
            value, operator = predicate.value, predicate.operator
        branch &= Q(**{
            f"{alias}__{operator}": _comparison_value(predicate.kind, value)})
    return branch


def _match_attributes(queryset, spec):
    predicates_by_key = {predicate.key: predicate for predicate in spec.attributes}
    aliases = {key: f"_search_attribute_{index}" for index, key in enumerate(predicates_by_key)}
    queryset = queryset.alias(**{
        aliases[key]: attribute_value_v1(key=key, kind=predicate.kind)
        for key, predicate in predicates_by_key.items()
    })
    # Only catalog objects are materialized. Listing rows stay in the queryset.
    schemas = AttributeSchema.objects.in_bulk([ref.id for ref in spec.resolved_schemas])
    branches = Q(pk__in=[])
    for ref in spec.resolved_schemas:
        schema = schemas.get(ref.id)
        if schema is None or (schema.category_id, schema.version) != (ref.category_id, ref.version):
            raise ValidationError({"schemas": "Şema kimliği artık geçerli değil."})
        branch = _candidate_branch(schema=schema, spec=spec, aliases=aliases)
        if branch is not None:
            branches |= branch
    return queryset.filter(branches)


def matching_public_listings(*, spec: SearchSpec, at=None) -> QuerySet[Listing]:
    """Return lazy public membership; callers may narrow it by owner/UUID."""
    spec = validate_search_spec(spec)
    queryset = public_listings(at=at)
    if spec.category_id is not None:
        queryset = queryset.filter(public_revision__category_id__in=category_scope_ids(
            category_id=spec.category_id, scope=spec.category_scope))
    if spec.currency:
        queryset = queryset.filter(public_revision__currency=spec.currency)
    if spec.price_min is not None:
        queryset = queryset.filter(public_revision__price__gte=spec.price_min)
    if spec.price_max is not None:
        queryset = queryset.filter(public_revision__price__lte=spec.price_max)
    if spec.keyword:
        folded_keyword = SearchFoldV1(Value(spec.keyword))
        queryset = queryset.alias(
            _search_document=search_vector_v1("public_revision__"),
            _search_title=folded_title_v1("public_revision__"),
        )
        # Fixed database regex tests the folded query, never a user pattern.
        # The planner can fold this immutable constant; short model tokens use @@.
        eligible_literal = Q(Regex(folded_keyword, Value("[[:alnum:]]{3}")))
        queryset = queryset.filter(
            Q(_search_document=search_query_v1(spec.keyword))
            | (eligible_literal & Q(_search_title__contains=folded_keyword)))
    if spec.location:
        queryset = queryset.alias(_search_location=folded_location_v1("public_revision__")).filter(
            _search_location__contains=SearchFoldV1(Value(spec.location)))
    if spec.attributes:
        queryset = _match_attributes(queryset, spec)
    return queryset


def order_search_results(queryset, *, spec: SearchSpec) -> QuerySet[Listing]:
    """Order matching membership without adding/removing rows."""
    spec = validate_search_spec(spec)
    tie_breakers = ("-first_published_at", "-pk")
    if spec.sort == "price_asc":
        return queryset.order_by(F("public_revision__price").asc(nulls_last=True), *tie_breakers)
    if spec.sort == "price_desc":
        return queryset.order_by(F("public_revision__price").desc(nulls_last=True), *tie_breakers)
    if spec.sort == "relevance":
        return queryset.alias(_search_rank=SearchRank(
            search_vector_v1("public_revision__"), search_query_v1(spec.keyword),
        )).order_by("-_search_rank", *tie_breakers)
    return queryset.order_by(*tie_breakers)
