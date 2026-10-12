from collections import defaultdict

from django.core.exceptions import ValidationError

from .models import AttributeSchema, Category
from .validation import SUPPORTED_TYPES

MAX_ID = 9223372036854775807
MAX_VERSION = 2147483647


def _positive(value, maximum, field):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValidationError({field: "Geçerli bir pozitif kimlik veya sürüm girin."})


def category_scope_ids(*, category_id: int, scope: str) -> tuple[int, ...]:
    """Resolve one catalog snapshot; descendants have no fixed depth limit."""
    _positive(category_id, MAX_ID, "category")
    if scope not in ("exact", "tree"):
        raise ValidationError({"scope": "Geçerli bir kategori kapsamı seçin."})
    snapshot = tuple(Category.objects.values_list("pk", "parent_id"))
    children = defaultdict(list)
    ids = set()
    for node_id, parent_id in snapshot:
        ids.add(node_id)
        children[parent_id].append(node_id)
    if category_id not in ids:
        return ()
    if scope == "exact":
        return (category_id,)
    visited = set()
    pending = [category_id]
    while pending:
        node_id = pending.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        pending.extend(children[node_id])
    return tuple(sorted(visited))


def category_filter_schema(*, category_id: int, schema_ref=None) -> AttributeSchema:
    _positive(category_id, MAX_ID, "category")
    schemas = AttributeSchema.objects.filter(category_id=category_id)
    if schema_ref is None:
        schema = schemas.order_by("-version", "-pk").first()
    else:
        for name, maximum in (("id", MAX_ID), ("category_id", MAX_ID), ("version", MAX_VERSION)):
            _positive(getattr(schema_ref, name, None), maximum, "schema")
        if schema_ref.category_id != category_id:
            raise ValidationError({"schema": "Şema seçili kategoriyle eşleşmelidir."})
        schema = schemas.filter(pk=schema_ref.id, version=schema_ref.version).first()
    if schema is None:
        raise ValidationError({"schema": "Seçili kategori için geçerli bir şema bulunamadı."})
    return schema


def _eligible(rule):
    return (isinstance(rule, dict) and rule.get("type") in SUPPORTED_TYPES
            and rule.get("filterable") is not False)


def compatible_attribute_schemas(*, source_schema, predicates) -> tuple[AttributeSchema, ...]:
    """Identity is exact category/key/type/unit, independent of domain/options."""
    _positive(source_schema.pk, MAX_ID, "schema")
    _positive(source_schema.category_id, MAX_ID, "category")
    _positive(source_schema.version, MAX_VERSION, "schema_version")
    predicates = tuple(predicates)
    source_fields = source_schema.definition["fields"]
    for predicate in predicates:
        rule = source_fields.get(predicate.key)
        if (not _eligible(rule) or rule["type"] != predicate.kind
                or rule.get("unit", "").strip() != predicate.unit):
            raise ValidationError({"attributes": "Özellik seçili şemayla eşleşmelidir."})
    compatible = []
    for schema in AttributeSchema.objects.filter(category_id=source_schema.category_id).order_by("pk", "version"):
        fields = schema.definition["fields"]
        if all(_eligible(fields.get(predicate.key))
               and fields[predicate.key]["type"] == predicate.kind
               and fields[predicate.key].get("unit", "").strip() == predicate.unit
               for predicate in predicates):
            compatible.append(schema)
    return tuple(compatible)
