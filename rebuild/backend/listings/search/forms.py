"""Presentation adapter; the shared parser remains the sole criteria validator."""
import re

from django import forms
from django.core.exceptions import ValidationError

from catalog.models import Category
from catalog.search import MAX_ID, MAX_VERSION, category_filter_schema, compatible_attribute_schemas
from catalog.validation import SUPPORTED_TYPES, normalize_attribute_value

from .parsing import parse_search_spec
from .specs import SchemaRef


COMMON_FIELDS = ("q", "category", "scope", "location", "currency", "price_min", "price_max", "sort")


def category_apply_params(params):
    result = params.copy()
    if result.get("category_apply") == "1":
        for key in tuple(result):
            if key.startswith("a.") or key in ("schema", "schema_version", "schemas", "page"):
                result.pop(key)
    result.pop("category_apply", None)
    return result


def positive_id(raw, maximum=MAX_ID):
    if isinstance(raw, str) and len(raw) <= len(str(maximum)) and re.fullmatch(r"[0-9]+", raw):
        value = int(raw)
        if 0 < value <= maximum:
            return value
    return None


def bounded_page(raw):
    """Classify huge numeric spellings before int; None means the last page."""
    if not isinstance(raw, str):
        return 1
    raw = raw.strip()
    if not re.fullmatch(r"[+-]?[0-9]+", raw):
        return 1
    negative = raw.startswith("-")
    digits = raw.lstrip("+-").lstrip("0") or "0"
    if negative or len(digits) > 19:
        return None
    number = int(digits)
    return number if number > 0 else None


class SearchForm(forms.Form):
    q = forms.CharField(label="Anahtar kelime", required=False, strip=False)
    category = forms.CharField(label="Kategori", required=False, strip=False)
    scope = forms.CharField(label="Kategori kapsamı", required=False, strip=False)
    location = forms.CharField(label="Konum", required=False, strip=False,
                               help_text="Şehir veya semt.")
    currency = forms.CharField(label="Para birimi", required=False, strip=False,
                               help_text="Üç harfli kod; örneğin TRY, EUR veya USD.",
                               widget=forms.TextInput(attrs={"list": "search-currencies", "autocomplete": "off"}))
    price_min = forms.CharField(label="En az fiyat", required=False, strip=False,
                                help_text="Ondalık için nokta kullanın: 1000.50",
                                widget=forms.TextInput(attrs={"inputmode": "decimal"}))
    price_max = forms.CharField(label="En çok fiyat", required=False, strip=False,
                                widget=forms.TextInput(attrs={"inputmode": "decimal"}))
    sort = forms.CharField(label="Sıralama", required=False, strip=False)

    def __init__(self, params):
        self.params = category_apply_params(params)
        self.spec = None
        self.parse_error = None
        try:
            self.spec = parse_search_spec(self.params)
        except ValidationError as error:
            self.parse_error = error
        data = self.params.copy()
        # Valid fields use canonical display values; errors retain the raw inputs.
        if self.spec is not None:
            spec = self.spec
            for name, value in (
                ("q", spec.keyword), ("category", str(spec.category_id) if spec.category_id else ""),
                ("scope", spec.category_scope), ("location", spec.location), ("currency", spec.currency),
                ("price_min", "" if spec.price_min is None else format(spec.price_min, ".2f")),
                ("price_max", "" if spec.price_max is None else format(spec.price_max, ".2f")),
                ("sort", spec.sort),
            ):
                data[name] = value
            for predicate in spec.attributes:
                operator = {"eq": "eq", "gte": "min", "lte": "max"}[predicate.operator]
                value = predicate.value
                data[f"a.{predicate.key}.{operator}"] = (
                    "true" if value is True else "false" if value is False else str(value))
        super().__init__(data=data, label_suffix="")
        self.attribute_names = []
        self.categories = tuple(Category.objects.all())
        by_id = {item.pk: item for item in self.categories}
        choices = []
        for item in self.categories:
            labels, visited, node = [], set(), item
            while node is not None and node.pk not in visited:
                visited.add(node.pk)
                labels.append(node.name)
                node = by_id.get(node.parent_id)
            choices.append((str(item.pk), " › ".join(reversed(labels))))
        selected = data.get("category", "")
        if positive_id(selected) and int(selected) not in by_id:
            choices.append((selected, "Kategori bulunamadı"))
        self.select("category", [("", "Tüm kategoriler"), *sorted(choices, key=lambda pair: pair[1])])
        self.select("scope", [("exact", "Yalnız bu kategori"), ("tree", "Alt kategoriler dahil")])
        self.select("sort", [("newest", "En yeni ilanlar"), ("price_asc", "Fiyat: düşükten yükseğe"),
                             ("price_desc", "Fiyat: yüksekten düşüğe"), ("relevance", "İlgililik")])
        self.add_attributes(data)
        self.previous_attributes = [
            (key[2:].rsplit(".", 1)[0].replace("_", " ").capitalize(), value)
            for key, value in self.params.items()
            if self.parse_error is not None and re.fullmatch(r"a\.[a-z][a-z0-9_]*\.(eq|min|max)", key)
            and key not in self.fields and value
        ]

    def select(self, name, choices):
        raw = self.data.get(name, "")
        if raw and raw not in {value for value, label in choices}:
            choices = [*choices, (raw, raw)]
        self.fields[name].widget = forms.Select(choices=choices)

    def add_attributes(self, data):
        category_id = positive_id(data.get("category", ""))
        if category_id is None or (data.get("scope", "") or "exact") != "exact":
            return
        source_ref = self.spec.attribute_schema if self.spec is not None else None
        if source_ref is None and ("schema" in data or "schema_version" in data):
            schema_id = positive_id(data.get("schema", ""))
            version = positive_id(data.get("schema_version", ""), MAX_VERSION)
            if schema_id is None or version is None:
                return
            source_ref = SchemaRef(schema_id, category_id, version)
        try:
            source = category_filter_schema(category_id=category_id, schema_ref=source_ref)
        except ValidationError:
            # A parent/missing category has no controls; stale identity never falls back to latest.
            return
        targets = compatible_attribute_schemas(source_schema=source, predicates=())
        if self.spec is not None and self.spec.resolved_schemas:
            frozen = {(ref.id, ref.version) for ref in self.spec.resolved_schemas}
            targets = tuple(item for item in targets if (item.pk, item.version) in frozen)
        eligible = [(key, rule) for key, rule in source.definition["fields"].items()
                    if rule["type"] in SUPPORTED_TYPES and rule.get("filterable") is not False]
        if not eligible:
            return
        for name, value in (("schema", source.pk), ("schema_version", source.version)):
            self.fields[name] = forms.CharField(required=False, widget=forms.HiddenInput)
            data[name] = str(value)
        if self.spec is not None and self.spec.resolved_schemas:
            self.fields["schemas"] = forms.CharField(required=False, widget=forms.HiddenInput)
            data["schemas"] = ",".join(f"{ref.id}:{ref.version}" for ref in self.spec.resolved_schemas)
        for key, rule in eligible:
            kind = rule["type"]
            active_range = kind in ("integer", "decimal") and any(
                data.get(f"a.{key}.{operator}") for operator in ("min", "max"))
            label = rule.get("label", key.replace("_", " ").capitalize())
            unit = rule.get("unit", "").strip()
            options = {}
            if rule.get("options"):
                for target in targets:
                    candidate = target.definition["fields"].get(key, {})
                    if (candidate.get("type") != kind or candidate.get("filterable") is False
                            or candidate.get("unit", "").strip() != unit):
                        continue
                    for option in candidate.get("options", ()):
                        normalized = normalize_attribute_value(name=key, rule=candidate, value=option)
                        options[str(normalized)] = str(option)
            if kind == "boolean":
                self.attribute_field(f"a.{key}.eq", label, unit,
                                     [("", "Tümü"), ("true", "Evet"), ("false", "Hayır")])
            elif rule.get("options") and not active_range:
                self.attribute_field(f"a.{key}.eq", label, unit, [("", "Tümü"), *options.items()])
            elif kind in ("integer", "decimal"):
                help_text = " · ".join(part for part in (unit, "Ondalık için nokta kullanın: 1000.50"
                                                       if kind == "decimal" else "") if part)
                operators = (("eq", "tam değer"),) if data.get(f"a.{key}.eq") else ()
                if active_range or not operators:
                    operators += (("min", "en az"), ("max", "en çok"))
                for operator, suffix in operators:
                    self.attribute_field(f"a.{key}.{operator}", f"{label} — {suffix}", help_text,
                                         inputmode="numeric" if kind == "integer" else "decimal")
            else:
                self.attribute_field(f"a.{key}.eq", label, " · ".join(filter(None, (unit, "Tam eşleşme"))))

    def attribute_field(self, name, label, help_text, choices=None, inputmode=None):
        field = forms.CharField(label=label, help_text=help_text, required=False, strip=False)
        if choices is not None:
            raw = self.data.get(name, "")
            if raw and raw not in {value for value, text in choices}:
                choices = [*choices, (raw, raw)]
            field.widget = forms.Select(choices=choices)
        elif inputmode:
            field.widget.attrs["inputmode"] = inputmode
        self.fields[name] = field
        self.attribute_names.append(name)

    def clean(self):
        values = super().clean()
        if self.parse_error is not None:
            self.add_search_error(self.parse_error)
        return values

    def add_search_error(self, error):
        if hasattr(error, "error_dict"):
            for name, errors in error.error_dict.items():
                for item in errors:
                    self.add_error(name if name in self.fields else None, item)
        else:
            self.add_error(None, error)

    def prepare_accessibility(self):
        for name, field in self.fields.items():
            if field.widget.is_hidden:
                continue
            bound = self[name]
            described = []
            if field.help_text:
                described.append(f"{bound.auto_id}_helptext")
            if bound.errors:
                field.widget.attrs["aria-invalid"] = "true"
                described.append(f"{bound.auto_id}_error")
            if described:
                field.widget.attrs["aria-describedby"] = " ".join(described)

    @property
    def common_fields(self):
        return [self[name] for name in COMMON_FIELDS]

    @property
    def attribute_fields(self):
        return [self[name] for name in self.attribute_names]
