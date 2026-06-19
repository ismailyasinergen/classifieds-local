import json
from functools import lru_cache
from pathlib import Path

from categories.models import Category


ATTRIBUTE_FIELD_PREFIX = "attr__"
SCHEMA_PATH = Path(__file__).resolve().parent / "data" / "category_attribute_schema.json"


def _is_blank(value):
    return value in (None, "", [], {})


@lru_cache(maxsize=1)
def load_attribute_schema():
    if not SCHEMA_PATH.exists():
        return {"version": 1, "categories": [], "global_attributes": []}

    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_schema_categories():
    return load_attribute_schema().get("categories", [])


def get_category_schema_map():
    mapping = {}

    for schema_category in get_schema_categories():
        schema_key = schema_category.get("key", "")

        for slug in schema_category.get("local_category_slugs", []):
            if slug:
                mapping[slug] = schema_key

    return mapping


def get_schema_by_key(schema_key):
    for schema_category in get_schema_categories():
        if schema_category.get("key") == schema_key:
            return schema_category

    return None


def get_schema_key_for_category(category):
    if not category:
        return ""

    mapping = get_category_schema_map()

    current = category
    while current:
        if current.slug in mapping:
            return mapping[current.slug]

        current = current.parent

    return ""


def get_schema_for_category(category):
    return get_schema_by_key(get_schema_key_for_category(category))


def get_category_schema_by_id():
    mapping = {}

    for category in Category.objects.select_related("parent").all():
        schema_key = get_schema_key_for_category(category)

        if schema_key:
            mapping[str(category.pk)] = schema_key

    return mapping


def get_all_attribute_definitions():
    merged = {}

    for schema_category in get_schema_categories():
        schema_key = schema_category.get("key", "")
        local_category_slugs = schema_category.get("local_category_slugs", [])

        for attribute in schema_category.get("attributes", []):
            key = attribute.get("key")

            if not key:
                continue

            item = merged.setdefault(
                key,
                {
                    "key": key,
                    "label": attribute.get("label", key.replace("_", " ").title()),
                    "input_type": attribute.get("input_type", "text"),
                    "required": False,
                    "sample_values": [],
                    "schema_keys": [],
                    "local_category_slugs": [],
                },
            )

            if schema_key and schema_key not in item["schema_keys"]:
                item["schema_keys"].append(schema_key)

            for slug in local_category_slugs:
                if slug and slug not in item["local_category_slugs"]:
                    item["local_category_slugs"].append(slug)

            for value in attribute.get("sample_values", []):
                if value not in item["sample_values"] and len(item["sample_values"]) < 20:
                    item["sample_values"].append(value)

    return sorted(merged.values(), key=lambda item: item["label"].casefold())


def get_attribute_definitions_for_category(category):
    schema_category = get_schema_for_category(category)

    if not schema_category:
        return []

    return [
        attribute
        for attribute in schema_category.get("attributes", [])
        if attribute.get("key")
    ]


def get_known_attribute_keys():
    return {attribute["key"] for attribute in get_all_attribute_definitions()}


def get_attribute_field_name(attribute_key):
    return f"{ATTRIBUTE_FIELD_PREFIX}{attribute_key}"


def get_attribute_key_from_field_name(field_name):
    if not field_name.startswith(ATTRIBUTE_FIELD_PREFIX):
        return ""

    return field_name[len(ATTRIBUTE_FIELD_PREFIX):]


def parse_boolean(value):
    if value in (True, "true", "True", "1", 1, "Evet", "Var", "yes", "Yes"):
        return True

    if value in (False, "false", "False", "0", 0, "Hayır", "Hayir", "Yok", "no", "No"):
        return False

    return None


def format_attribute_value(attribute, value):
    if _is_blank(value):
        return ""

    if attribute.get("input_type") == "boolean":
        parsed = parse_boolean(value)

        if parsed is True:
            return "Yes"

        if parsed is False:
            return "No"

    return str(value)


def prettify_attribute_key(key):
    fallback_labels = {
        "brand": "Brand",
        "model_name": "Model / Series",
        "model_year": "Year",
        "mileage": "Mileage / KM",
        "fuel_type": "Fuel Type",
        "transmission": "Transmission",
        "color": "Color",
        "condition": "Condition",
        "warranty": "Warranty",
        "accepts_exchange": "Accepts Exchange",
    }

    if key in fallback_labels:
        return fallback_labels[key]

    return key.replace("_", " ").title()


def get_display_attributes(listing):
    attributes = listing.attributes or {}
    rows = []
    seen_keys = set()

    schema_attributes = get_attribute_definitions_for_category(listing.category)

    for attribute in schema_attributes:
        key = attribute.get("key")

        if not key or key not in attributes or _is_blank(attributes.get(key)):
            continue

        value = format_attribute_value(attribute, attributes.get(key))

        if value:
            rows.append((attribute.get("label", prettify_attribute_key(key)), value))
            seen_keys.add(key)

    for key, value in attributes.items():
        if key in seen_keys or _is_blank(value):
            continue

        rows.append((prettify_attribute_key(key), value))

    return rows
