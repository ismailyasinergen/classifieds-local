import re
import unicodedata
from dataclasses import replace
from decimal import Decimal
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.http import QueryDict

from catalog.search import MAX_ID, MAX_VERSION, category_filter_schema, compatible_attribute_schemas
from catalog.validation import SUPPORTED_TYPES, normalize_attribute_value

from .specs import AttributePredicate, SchemaRef, SearchSpec

MAX_QUERY_BYTES = 8192
MAX_PARAMS = 64
MAX_PREDICATES = 20
MAX_SCHEMAS = 64
MAX_RAW_ATTRIBUTE = 200
MAX_RAW_NUMBER = 64
MAX_PRICE = Decimal("9999999999999999.99")
NUMBER_RE = re.compile(r"-?[0-9]+(?:\.[0-9]+)?\Z")
KEY_RE = re.compile(r"[a-z][a-z0-9_]*\Z")
SCALARS = ("v", "q", "category", "scope", "location", "currency", "price_min",
           "price_max", "schema", "schema_version", "schemas", "sort", "page")
SPEC_FIELDS = frozenset(SearchSpec.__dataclass_fields__)
REF_FIELDS = {"id", "category_id", "version"}
PREDICATE_FIELDS = {"key", "kind", "unit", "operator", "value"}
OP_ORDER = {"eq": 0, "gte": 1, "lte": 2}


def _error(field, message="Geçerli bir arama değeri girin."):
    raise ValidationError({field: message})


def _integer(value, maximum, field):
    # Compare integers before str(): an attacker-controlled int can be enormous.
    if type(value) is not int or not 1 <= value <= maximum:
        _error(field)
    return value


def _integer_text(value, maximum, field):
    if (not isinstance(value, str) or len(value) > len(str(maximum))
            or not re.fullmatch(r"[0-9]+", value)):
        _error(field)
    return _integer(int(value), maximum, field)


def _ref(value, field):
    if not isinstance(value, SchemaRef):
        _error(field)
    _integer(value.id, MAX_ID, field)
    _integer(value.category_id, MAX_ID, field)
    _integer(value.version, MAX_VERSION, field)
    return value


def _ref_from_dict(value, field):
    if not isinstance(value, dict) or set(value) != REF_FIELDS:
        _error(field)
    return _ref(SchemaRef(**value), field)


def _text(value, field, maximum):
    if (not isinstance(value, str) or len(value) > MAX_QUERY_BYTES
            or "\x00" in value):
        _error(field)
    value = " ".join(unicodedata.normalize("NFC", value).split())
    if len(value) > maximum:
        _error(field)
    return value


def _number_text(value, field):
    if type(value) is int:
        if not -(10**MAX_RAW_NUMBER) < value < 10**MAX_RAW_NUMBER:
            _error(field)
        value = str(value)
    if (not isinstance(value, str) or len(value) > MAX_RAW_NUMBER
            or not NUMBER_RE.fullmatch(value)):
        _error(field, "Nokta ayracıyla sonlu ve sınırlı bir sayı girin.")
    return value


def _price(value, field):
    if value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite():
        _error(field)
    parts = value.as_tuple()
    # Inspect exponent/digit count before fixed formatting or quantization.
    if len(parts.digits) > MAX_RAW_NUMBER or not -2 <= parts.exponent <= 16:
        _error(field)
    if not 0 <= value <= MAX_PRICE:
        _error(field)
    if value == 0:
        return Decimal("0.00")
    return value.quantize(Decimal("0.01"))


def _price_text(value, field, *, json_value=False):
    if value is None or (not json_value and value == ""):
        return None
    value = _number_text(value, field)
    if json_value and not re.fullmatch(r"[0-9]+\.[0-9]{2}", value):
        _error(field, "Fiyat iki ondalık basamaklı metin olmalıdır.")
    return _price(Decimal(value), field)


def _attribute_value(value, kind, field, *, raw=False):
    if raw:
        if not isinstance(value, str) or len(value) > MAX_RAW_ATTRIBUTE:
            _error(field)
        if kind == "boolean":
            if value not in ("true", "false"):
                _error(field, "Doğru veya yanlış seçin.")
            value = value == "true"
        elif kind in ("integer", "decimal"):
            value = _number_text(value, field)
    else:
        if ((kind == "integer" and type(value) is not int)
                or (kind == "decimal" and not isinstance(value, str))
                or (kind == "boolean" and type(value) is not bool)
                or (kind == "string" and not isinstance(value, str))):
            _error(field)
        if kind in ("integer", "decimal"):
            value = _number_text(value, field)
    if isinstance(value, str) and (len(value) > MAX_RAW_ATTRIBUTE or "\x00" in value):
        _error(field)
    # A projected type rule intentionally excludes stored-value min/max/options.
    return normalize_attribute_value(name=field, rule={"type": kind}, value=value)


def _schema_ref(schema):
    return SchemaRef(schema.pk, schema.category_id, schema.version)


def _predicates(attributes, source):
    fields = source.definition["fields"]
    normalized = []
    seen = set()
    by_key = {}
    for predicate in attributes:
        if not isinstance(predicate, AttributePredicate):
            _error("attributes")
        key = predicate.key
        if (not isinstance(key, str) or len(key) > MAX_QUERY_BYTES or not KEY_RE.fullmatch(key)
                or key not in fields):
            _error("attributes", "Bilinmeyen özellik alanı.")
        if not isinstance(predicate.operator, str) or predicate.operator not in OP_ORDER:
            _error("attributes")
        field = f"a.{key}.{ {'eq': 'eq', 'gte': 'min', 'lte': 'max'}[predicate.operator] }"
        rule = fields[key]
        if (not isinstance(predicate.kind, str) or predicate.kind not in SUPPORTED_TYPES
                or rule.get("filterable") is False or predicate.kind != rule["type"]
                or not isinstance(predicate.unit, str)
                or predicate.unit.strip() != rule.get("unit", "").strip()):
            _error(field, "Özellik seçili şemayla eşleşmelidir.")
        if not isinstance(predicate.operator, str) or predicate.operator not in OP_ORDER:
            _error(field)
        if predicate.operator != "eq" and predicate.kind not in ("integer", "decimal"):
            _error(field, "Aralık yalnız sayısal alanlarda kullanılabilir.")
        if (key, predicate.operator) in seen:
            _error(field, "Yinelenen özellik filtresi.")
        seen.add((key, predicate.operator))
        value = _attribute_value(predicate.value, predicate.kind, field)
        normalized.append(replace(predicate, value=value, unit=predicate.unit.strip()))
        by_key.setdefault(key, {})[predicate.operator] = value
    for key, operators in by_key.items():
        if "eq" in operators and len(operators) > 1:
            _error(f"a.{key}.eq", "Eşitlik ve aralık birlikte kullanılamaz.")
        if ("gte" in operators and "lte" in operators
                and Decimal(operators["gte"]) > Decimal(operators["lte"])):
            _error(f"a.{key}.min", "Alt sınır üst sınırdan büyük olamaz.")
    return tuple(sorted(normalized, key=lambda p: (p.key, OP_ORDER[p.operator])))


def validate_search_spec(spec: SearchSpec) -> SearchSpec:
    """Single validation contract for GET, stored JSON, and programmatic specs."""
    if not isinstance(spec, SearchSpec):
        _error("search")
    if type(spec.version) is not int or spec.version != 1:
        _error("v", "Desteklenmeyen arama sürümü.")
    keyword = _text(spec.keyword, "q", 200)
    if keyword and not any(character.isalnum() for character in keyword):
        _error("q", "Arama en az bir harf veya rakam içermelidir.")
    location = _text(spec.location, "location", 160)
    if spec.category_id is not None:
        _integer(spec.category_id, MAX_ID, "category")
    if not isinstance(spec.category_scope, str) or spec.category_scope not in ("exact", "tree"):
        _error("scope")
    if spec.category_scope == "tree" and spec.category_id is None:
        _error("scope", "Kategori seçin.")
    if not isinstance(spec.currency, str) or len(spec.currency) > MAX_QUERY_BYTES:
        _error("currency")
    currency = spec.currency.strip()
    if currency and not re.fullmatch(r"[A-Za-z]{3}", currency):
        _error("currency", "Üç ASCII harfli para birimi kodu girin.")
    currency = currency.upper()
    price_min, price_max = _price(spec.price_min, "price_min"), _price(spec.price_max, "price_max")
    if (price_min is not None or price_max is not None) and not currency:
        _error("currency", "Fiyat filtresi için para birimi seçin.")
    if price_min is not None and price_max is not None and price_min > price_max:
        _error("price_min", "Alt fiyat üst fiyattan büyük olamaz.")
    if not isinstance(spec.sort, str) or spec.sort not in ("newest", "price_asc", "price_desc", "relevance"):
        _error("sort")
    if spec.sort in ("price_asc", "price_desc") and not currency:
        _error("currency", "Fiyat sıralaması için para birimi seçin.")
    if spec.sort == "relevance" and not keyword:
        _error("q", "İlgililik sıralaması için arama metni girin.")
    if not isinstance(spec.attributes, tuple) or len(spec.attributes) > MAX_PREDICATES:
        _error("attributes", "En fazla 20 özellik filtresi kullanılabilir.")
    if not isinstance(spec.resolved_schemas, tuple) or len(spec.resolved_schemas) > MAX_SCHEMAS:
        _error("schemas", "En fazla 64 şema kullanılabilir.")
    if spec.attribute_schema is not None:
        _ref(spec.attribute_schema, "schema")
    for ref in spec.resolved_schemas:
        _ref(ref, "schemas")
    attributes, source_ref, resolved_refs = (), None, ()
    if spec.attributes:
        if spec.category_id is None or spec.category_scope != "exact":
            _error("category", "Özellikler için tek bir kesin kategori seçin.")
        if spec.attribute_schema is None:
            _error("schema", "Özellikler için şema ve sürüm seçin.")
        source = category_filter_schema(category_id=spec.category_id, schema_ref=spec.attribute_schema)
        attributes = _predicates(spec.attributes, source)
        if not spec.resolved_schemas:
            _error("schemas", "Çözümlenmiş şema kimlikleri gereklidir.")
        compatible = compatible_attribute_schemas(source_schema=source, predicates=attributes)
        by_ref = {_schema_ref(schema): schema for schema in compatible}
        if len(set(spec.resolved_schemas)) != len(spec.resolved_schemas):
            _error("schemas", "Yinelenen şema kimliği.")
        if any(ref not in by_ref for ref in spec.resolved_schemas):
            _error("schemas", "Şema kimlikleri kategori, sürüm ve özelliklerle eşleşmelidir.")
        resolved_refs = tuple(sorted(spec.resolved_schemas, key=lambda ref: (ref.id, ref.version)))
        for predicate in attributes:
            if predicate.operator != "eq":
                continue
            valid = False
            for ref in resolved_refs:
                rule = by_ref[ref].definition["fields"][predicate.key]
                try:
                    normalize_attribute_value(name="attributes", rule=rule, value=predicate.value)
                except ValidationError:
                    continue
                valid = True
                break
            if not valid:
                _error(f"a.{predicate.key}.eq", "Değer uyumlu şemaların hiçbirinde geçerli değil.")
        source_ref = spec.attribute_schema
    else:
        # Stored/manual refs still identify real immutable schemas, even when
        # metadata is removed because it has no predicates to narrow results.
        supplied_refs = spec.resolved_schemas
        if spec.attribute_schema is not None:
            supplied_refs = (spec.attribute_schema, *supplied_refs)
        for ref in supplied_refs:
            category_filter_schema(category_id=ref.category_id, schema_ref=ref)
    return replace(spec, keyword=keyword, location=location, currency=currency,
                   price_min=price_min, price_max=price_max, attribute_schema=source_ref,
                   attributes=attributes, resolved_schemas=resolved_refs)


def _query_budget(params):
    if not isinstance(params, QueryDict):
        _error("search")
    count, raw_size = 0, 0
    for key, values in params.lists():
        count += len(values)
        if count > MAX_PARAMS:
            _error("search", "En fazla 64 sorgu parametresi kullanılabilir.")
        for value in values:
            if not isinstance(value, str):
                _error("search")
            # Each pair has "="; only pairs after the first have "&".
            raw_size += len(key) + len(value) + (2 if raw_size else 1)
            if raw_size > MAX_QUERY_BYTES:
                _error("search", "Arama sorgusu en fazla 8 KiB olabilir.")
    if len(params.urlencode().encode("utf-8")) > MAX_QUERY_BYTES:
        _error("search", "Arama sorgusu en fazla 8 KiB olabilir.")


def parse_search_spec(params: QueryDict) -> SearchSpec:
    _query_budget(params)
    for field in SCALARS:
        if field != "category" and len(params.getlist(field)) > 1:
            _error(field, "Bu alan yalnız bir kez gönderilebilir.")
    version = 1 if "v" not in params else _integer_text(params["v"], 1, "v")
    category = params.get("category", "")
    try:
        category_id = _integer_text(category, MAX_ID, "category")
    except ValidationError:
        category_id = None
    raw_attributes = []
    declared_attributes = []
    for key, values in params.lists():
        if not key.startswith("a."):
            continue
        if len(values) != 1:
            _error(key, "Bu alan yalnız bir kez gönderilebilir.")
        match = re.fullmatch(r"a\.([a-z][a-z0-9_]*)\.(eq|min|max)", key)
        if not match:
            _error("attributes", "Bilinmeyen özellik filtresi.")
        if len(values[0]) > MAX_RAW_ATTRIBUTE:
            _error(key)
        declared_attributes.append((key, match[1]))
        if values[0] != "":
            raw_attributes.append((key, match[1], match[2], values[0]))
    if len(raw_attributes) > MAX_PREDICATES:
        _error("attributes", "En fazla 20 özellik filtresi kullanılabilir.")
    source_ref, attributes, resolved = None, (), ()
    scope = params.get("scope", "") or "exact"
    if declared_attributes:
        if category_id is None or scope != "exact":
            _error("category", "Özellikler için tek bir kesin kategori seçin.")
        source_ref = SchemaRef(_integer_text(params.get("schema", ""), MAX_ID, "schema"), category_id,
                               _integer_text(params.get("schema_version", ""), MAX_VERSION, "schema_version"))
        source = category_filter_schema(category_id=category_id, schema_ref=source_ref)
        for field, key in declared_attributes:
            rule = source.definition["fields"].get(key)
            if rule is None or rule.get("filterable") is False:
                _error(field, "Bilinmeyen veya filtrelenemeyen özellik alanı.")
        predicates = []
        for field, key, operator, value in raw_attributes:
            rule = source.definition["fields"].get(key)
            if rule is None or rule.get("filterable") is False:
                _error(field, "Bilinmeyen veya filtrelenemeyen özellik alanı.")
            kind = rule["type"]
            predicates.append(AttributePredicate(key, kind, rule.get("unit", "").strip(),
                                                 {"eq": "eq", "min": "gte", "max": "lte"}[operator],
                                                 _attribute_value(value, kind, field, raw=True)))
        attributes = _predicates(tuple(predicates), source)
        if not attributes:
            source_ref = None
        elif "schemas" in params:
            pairs = params["schemas"].split(",")
            if len(pairs) > MAX_SCHEMAS:
                _error("schemas")
            refs = []
            for pair in pairs:
                parts = pair.split(":")
                if len(parts) != 2:
                    _error("schemas")
                refs.append(SchemaRef(_integer_text(parts[0], MAX_ID, "schemas"), category_id,
                                      _integer_text(parts[1], MAX_VERSION, "schemas")))
            resolved = tuple(refs)
        elif attributes:
            targets = compatible_attribute_schemas(source_schema=source, predicates=attributes)
            if len(targets) > MAX_SCHEMAS:
                _error("schemas", "En fazla 64 şema kullanılabilir.")
            resolved = tuple(_schema_ref(schema) for schema in targets)
    spec = SearchSpec(version, params.get("q", ""), category_id, scope, params.get("location", ""),
                      params.get("currency", ""), _price_text(params.get("price_min", ""), "price_min"),
                      _price_text(params.get("price_max", ""), "price_max"), source_ref, attributes,
                      resolved, params.get("sort", "") or "newest")
    return validate_search_spec(spec)


def search_spec_from_dict(payload: dict) -> SearchSpec:
    if not isinstance(payload, dict) or set(payload) != SPEC_FIELDS:
        _error("search", "Arama nesnesinin bütün ve yalnız tanımlı alanları gereklidir.")
    raw_attributes, raw_refs = payload["attributes"], payload["resolved_schemas"]
    if not isinstance(raw_attributes, list) or len(raw_attributes) > MAX_PREDICATES:
        _error("attributes")
    if not isinstance(raw_refs, list) or len(raw_refs) > MAX_SCHEMAS:
        _error("schemas")
    attributes = []
    for item in raw_attributes:
        if not isinstance(item, dict) or set(item) != PREDICATE_FIELDS:
            _error("attributes")
        attributes.append(AttributePredicate(**item))
    source = None if payload["attribute_schema"] is None else _ref_from_dict(payload["attribute_schema"], "schema")
    refs = tuple(_ref_from_dict(item, "schemas") for item in raw_refs)
    return validate_search_spec(SearchSpec(
        payload["version"], payload["keyword"], payload["category_id"], payload["category_scope"],
        payload["location"], payload["currency"], _price_text(payload["price_min"], "price_min", json_value=True),
        _price_text(payload["price_max"], "price_max", json_value=True), source, tuple(attributes), refs, payload["sort"]))


def search_spec_to_dict(spec: SearchSpec) -> dict:
    spec = validate_search_spec(spec)
    def ref_dict(ref):
        return {"id": ref.id, "category_id": ref.category_id, "version": ref.version}
    return {
        "version": spec.version, "keyword": spec.keyword, "category_id": spec.category_id,
        "category_scope": spec.category_scope, "location": spec.location, "currency": spec.currency,
        "price_min": None if spec.price_min is None else format(spec.price_min, ".2f"),
        "price_max": None if spec.price_max is None else format(spec.price_max, ".2f"),
        "attribute_schema": None if spec.attribute_schema is None else ref_dict(spec.attribute_schema),
        "attributes": [{"key": p.key, "kind": p.kind, "unit": p.unit, "operator": p.operator, "value": p.value}
                       for p in spec.attributes],
        "resolved_schemas": [ref_dict(ref) for ref in spec.resolved_schemas], "sort": spec.sort,
    }


def search_querystring(spec: SearchSpec, *, page: int | None = None) -> str:
    spec = validate_search_spec(spec)
    pairs = []
    if spec.keyword:
        pairs.append(("q", spec.keyword))
    if spec.category_id is not None:
        pairs.append(("category", str(spec.category_id)))
    if spec.category_scope != "exact":
        pairs.append(("scope", spec.category_scope))
    if spec.location:
        pairs.append(("location", spec.location))
    if spec.currency:
        pairs.append(("currency", spec.currency))
    for field in ("price_min", "price_max"):
        value = getattr(spec, field)
        if value is not None:
            pairs.append((field, format(value, ".2f")))
    if spec.attributes:
        pairs.extend((("schema", str(spec.attribute_schema.id)), ("schema_version", str(spec.attribute_schema.version)),
                      ("schemas", ",".join(f"{ref.id}:{ref.version}" for ref in spec.resolved_schemas))))
        for predicate in spec.attributes:
            operator = {"eq": "eq", "gte": "min", "lte": "max"}[predicate.operator]
            value = predicate.value
            if type(value) is bool:
                value = "true" if value else "false"
            pairs.append((f"a.{predicate.key}.{operator}", str(value)))
    if spec.sort != "newest":
        pairs.append(("sort", spec.sort))
    if pairs:
        pairs.insert(0, ("v", "1"))
    if page is not None:
        _integer(page, MAX_ID, "page")
        pairs.append(("page", str(page)))
    query = urlencode(pairs)
    if len(pairs) > MAX_PARAMS or len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        _error("search", "Arama sorgusu bütçeyi aşıyor.")
    return query
