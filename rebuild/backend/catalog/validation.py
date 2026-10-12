import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from .models import AttributeSchema

SUPPORTED_TYPES = {"integer", "decimal", "string", "boolean"}


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValidationError({name: "Geçerli bir sayı girin."})
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValidationError({name: "Geçerli bir sayı girin."})
    if not number.is_finite():
        raise ValidationError({name: "Sonlu bir sayı girin."})
    return number


def normalize_attribute_value(*, name: str, rule: dict, value):
    """Normalize one present value; reusable for partial drafts without schema mutation."""
    kind = rule["type"]
    if kind in {"integer", "decimal"}:
        number = _number(value, name)
        if kind == "integer" and number != number.to_integral_value():
            raise ValidationError({name: "Tam sayı girin."})
        if "min" in rule and number < _number(rule["min"], name):
            raise ValidationError({name: "Değer izin verilen alt sınırdan küçük."})
        if "max" in rule and number > _number(rule["max"], name):
            raise ValidationError({name: "Değer izin verilen üst sınırdan büyük."})
        if kind == "integer":
            result = int(number)
        else:
            # Fixed notation preserves exact Decimal precision without context rounding.
            result = format(number, "f")
            if "." in result:
                result = result.rstrip("0").rstrip(".")
            if number == 0:
                result = "0"
    elif kind == "string":
        if not isinstance(value, str):
            raise ValidationError({name: "Metin girin."})
        result = value.strip()
        if rule.get("required") and not result:
            raise ValidationError({name: "Bu alan zorunludur."})
    elif kind == "boolean":
        if not isinstance(value, bool):
            raise ValidationError({name: "Doğru veya yanlış değeri girin."})
        result = value
    else:
        raise ValidationError({name: "Bilinmeyen alan türü."})
    if "options" in rule:
        option_rule = {key: val for key, val in rule.items() if key != "options"}
        options = [normalize_attribute_value(name=name, rule=option_rule, value=option) for option in rule["options"]]
        if result not in options:
            raise ValidationError({name: "İzin verilen seçeneklerden birini seçin."})
    return result


def validate_schema_definition(definition):
    if not isinstance(definition, dict) or set(definition) != {"fields"} or not isinstance(definition["fields"], dict):
        raise ValidationError({"definition": "Şema fields sözlüğünü içermelidir."})
    for name, rule in definition["fields"].items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValidationError({"definition": "Geçersiz alan adı."})
        if not isinstance(rule, dict) or not isinstance(rule.get("type"), str) or rule["type"] not in SUPPORTED_TYPES:
            raise ValidationError({"definition": "Geçersiz alan türü."})
        if set(rule) - {"type", "required", "min", "max", "options", "label", "unit", "filterable"}:
            raise ValidationError({"definition": "Bilinmeyen alan kuralı."})
        if "required" in rule and not isinstance(rule["required"], bool):
            raise ValidationError({"definition": "required doğru veya yanlış olmalıdır."})
        if "label" in rule and not isinstance(rule["label"], str):
            raise ValidationError({"definition": "label metin olmalıdır."})
        if "unit" in rule and (not isinstance(rule["unit"], str) or not rule["unit"].strip()):
            raise ValidationError({"definition": "unit boş olmayan metin olmalıdır."})
        if "filterable" in rule and not isinstance(rule["filterable"], bool):
            raise ValidationError({"definition": "filterable doğru veya yanlış olmalıdır."})
        for bound in ("min", "max"):
            if bound in rule:
                if rule["type"] not in {"integer", "decimal"}:
                    raise ValidationError({"definition": "Sınırlar yalnız sayısal alanlarda kullanılabilir."})
                _number(rule[bound], name)
        if "min" in rule and "max" in rule and _number(rule["min"], name) > _number(rule["max"], name):
            raise ValidationError({"definition": "Alt sınır üst sınırdan büyük olamaz."})
        if "options" in rule:
            if not isinstance(rule["options"], list) or not rule["options"]:
                raise ValidationError({"definition": "options boş olmayan liste olmalıdır."})
            option_rule = {key: val for key, val in rule.items() if key != "options"}
            for option in rule["options"]:
                normalize_attribute_value(name=name, rule=option_rule, value=option)


def validate_attributes(*, schema: "AttributeSchema", values: dict) -> dict:
    """Strict submission validation; returns integer/canonical Decimal-string JSON values."""
    validate_schema_definition(schema.definition)
    if not isinstance(values, dict):
        raise ValidationError("Özellikler sözlük olmalıdır.")
    fields = schema.definition["fields"]
    if set(values) - set(fields):
        raise ValidationError("Bilinmeyen özellik alanı.")
    normalized = {}
    errors = {}
    for name, rule in fields.items():
        if name not in values:
            if rule.get("required"):
                errors[name] = ["Bu alan zorunludur."]
            continue
        try:
            normalized[name] = normalize_attribute_value(name=name, rule=rule, value=values[name])
        except ValidationError as exc:
            errors.update(exc.message_dict)
    if errors:
        raise ValidationError(errors)
    return normalized
