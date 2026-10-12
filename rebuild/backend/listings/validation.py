import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator
from catalog.validation import normalize_attribute_value, validate_schema_definition

CONTENT_FIELDS = ("title", "description", "price", "currency", "location", "attributes")
TEXT_LIMITS = {"title": 200, "description": 20000, "location": 160}


def validate_partial_attributes(*, schema, values):
    validate_schema_definition(schema.definition)
    if not isinstance(values, dict):
        raise ValidationError({"attributes": "Özellikler sözlük olmalıdır."})
    fields = schema.definition["fields"]
    if set(values) - set(fields):
        raise ValidationError({"attributes": "Bilinmeyen özellik alanı."})
    return {
        name: normalize_attribute_value(name=name, rule=fields[name], value=value)
        for name, value in values.items()
    }


def normalize_draft_content(*, schema, content):
    """Validate only provided keys; omitted keys retain current/default values."""
    if not isinstance(content, dict):
        raise ValidationError("İçerik sözlük olmalıdır.")
    if set(content) - set(CONTENT_FIELDS):
        raise ValidationError("Bilinmeyen veya korunan içerik alanı.")
    result = {}
    for name, value in content.items():
        if name in TEXT_LIMITS:
            if not isinstance(value, str):
                raise ValidationError({name: "Metin girin."})
            value = value.strip()
            if len(value) > TEXT_LIMITS[name]:
                raise ValidationError({name: f"En fazla {TEXT_LIMITS[name]} karakter girin."})
        elif name == "currency":
            if not isinstance(value, str):
                raise ValidationError({name: "Para birimi metin olmalıdır."})
            value = value.strip().upper()
            if value and not re.fullmatch(r"[A-Z]{3}", value):
                raise ValidationError({name: "Üç harfli para birimi kodu girin."})
        elif name == "price" and value is not None:
            if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
                raise ValidationError({name: "Geçerli bir fiyat girin."})
            try:
                value = Decimal(str(value).strip())
            except (InvalidOperation, ValueError):
                raise ValidationError({name: "Geçerli bir fiyat girin."})
            if not value.is_finite() or value < 0:
                raise ValidationError({name: "Sonlu, negatif olmayan fiyat girin."})
            try:
                DecimalValidator(max_digits=18, decimal_places=2)(value)
            except ValidationError as exc:
                raise ValidationError({name: exc.messages})
        elif name == "attributes":
            value = validate_partial_attributes(schema=schema, values=value)
        result[name] = value
    return result
