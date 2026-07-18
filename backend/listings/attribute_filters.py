from urllib.parse import urlencode


ATTRIBUTE_FILTERS_BY_CATEGORY = {
    "cars": [
        {"key": "marka", "label": "Brand", "placeholder": "BMW, Toyota..."},
        {"key": "model", "label": "Model", "placeholder": "520i, Corolla..."},
        {"key": "yil", "label": "Year", "placeholder": "2018"},
        {"key": "km", "label": "Mileage", "placeholder": "150000"},
        {"key": "yakit_tipi", "label": "Fuel", "placeholder": "Diesel, Petrol..."},
        {"key": "vites", "label": "Transmission", "placeholder": "Automatic..."},
    ],
    "motorcycles": [
        {"key": "marka", "label": "Brand", "placeholder": "Honda, Yamaha..."},
        {"key": "model", "label": "Model", "placeholder": "CBR..."},
        {"key": "yil", "label": "Year", "placeholder": "2020"},
        {"key": "km", "label": "Mileage", "placeholder": "25000"},
    ],
    "commercial-vehicles": [
        {"key": "arac_tipi", "label": "Vehicle type", "placeholder": "Panelvan..."},
        {"key": "marka", "label": "Brand", "placeholder": "Ford..."},
        {"key": "model", "label": "Model", "placeholder": "Transit..."},
        {"key": "yil", "label": "Year", "placeholder": "2019"},
        {"key": "km", "label": "Mileage", "placeholder": "120000"},
    ],
    "homes-for-sale": [
        {"key": "oda_sayisi", "label": "Rooms", "placeholder": "2+1"},
        {"key": "m2_brut", "label": "Gross m²", "placeholder": "120"},
        {"key": "m2_net", "label": "Net m²", "placeholder": "95"},
        {"key": "bina_yasi", "label": "Building age", "placeholder": "5"},
        {"key": "bulundugu_kat", "label": "Floor", "placeholder": "3"},
    ],
    "homes-for-rent": [
        {"key": "oda_sayisi", "label": "Rooms", "placeholder": "2+1"},
        {"key": "m2_brut", "label": "Gross m²", "placeholder": "120"},
        {"key": "m2_net", "label": "Net m²", "placeholder": "95"},
        {"key": "bina_yasi", "label": "Building age", "placeholder": "5"},
        {"key": "bulundugu_kat", "label": "Floor", "placeholder": "3"},
    ],
    "land": [
        {"key": "m2", "label": "m²", "placeholder": "500"},
        {"key": "imar_durumu", "label": "Zoning", "placeholder": "Residential..."},
        {"key": "ada_no", "label": "Block no", "placeholder": "123"},
        {"key": "parsel_no", "label": "Parcel no", "placeholder": "45"},
    ],
    "phones": [
        {"key": "marka", "label": "Brand", "placeholder": "Apple, Samsung..."},
        {"key": "model", "label": "Model", "placeholder": "iPhone 14..."},
        {"key": "kapasite", "label": "Capacity", "placeholder": "128 GB"},
        {"key": "renk", "label": "Color", "placeholder": "Black"},
        {"key": "durum", "label": "Condition", "placeholder": "Used..."},
    ],
    "computers": [
        {"key": "marka", "label": "Brand", "placeholder": "Apple, Lenovo..."},
        {"key": "model", "label": "Model", "placeholder": "MacBook Pro..."},
        {"key": "islemci", "label": "CPU", "placeholder": "Intel i7..."},
        {"key": "ram", "label": "RAM", "placeholder": "16 GB"},
        {"key": "ssd", "label": "SSD", "placeholder": "512 GB"},
    ],
    "cameras": [
        {"key": "marka", "label": "Brand", "placeholder": "Canon, Sony..."},
        {"key": "model", "label": "Model", "placeholder": "EOS R6..."},
        {"key": "lens", "label": "Lens", "placeholder": "24-70mm"},
        {"key": "video", "label": "Video", "placeholder": "4K"},
    ],
    "furniture": [
        {"key": "urun_tipi", "label": "Product type", "placeholder": "Sofa set..."},
        {"key": "marka", "label": "Brand", "placeholder": "Bellona..."},
        {"key": "malzeme", "label": "Material", "placeholder": "Wood..."},
        {"key": "renk", "label": "Color", "placeholder": "Gray"},
        {"key": "durum", "label": "Condition", "placeholder": "Used..."},
    ],
    "appliances": [
        {"key": "urun_tipi", "label": "Product type", "placeholder": "Fridge..."},
        {"key": "marka", "label": "Brand", "placeholder": "Bosch..."},
        {"key": "model", "label": "Model", "placeholder": "No Frost..."},
        {"key": "kapasite", "label": "Capacity", "placeholder": "500 lt"},
        {"key": "durum", "label": "Condition", "placeholder": "Used..."},
    ],
}


def normalize_category_slug(category_slug):
    return (category_slug or "").strip()



# FILTER_BEHAVIOR_HARDENING_V75
import re
from decimal import Decimal, InvalidOperation


NUMERIC_ATTRIBUTE_FILTER_KEYS = {
    "m2_brut",
    "m2_net",
    "acik_alan_m2",
    "bina_yasi",
    "bulundugu_kat",
    "kat_sayisi",
    "banyo_sayisi",
    "aidat_tl",
    "yil",
    "km",
    "motor_gucu",
    "motor_hacmi",
    "sehir_ici_100_km_de",
    "sehir_disi_100_km_de",
    "ortalama_100_km_de",
    "kapasite",
}


def _is_numeric_filter_key(key):
    return key in NUMERIC_ATTRIBUTE_FILTER_KEYS


def _with_filter_metadata(spec):
    enriched = dict(spec)
    key = enriched.get("key", "")
    enriched["param"] = "attr_" + key

    if _is_numeric_filter_key(key):
        enriched["filter_type"] = "number"
        enriched["param_min"] = "attr_" + key + "_min"
        enriched["param_max"] = "attr_" + key + "_max"
    else:
        enriched.setdefault("filter_type", "text")
        enriched["param_min"] = ""
        enriched["param_max"] = ""

    return enriched


def _normalize_numeric_text(raw):
    text = str(raw).strip().replace(" ", "")
    if not text:
        return ""

    match = re.search(r"-?\d[\d.,]*", text)
    if not match:
        return ""

    value = match.group(0)

    if "," in value and "." in value:
        decimal_separator = "," if value.rfind(",") > value.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        value = value.replace(thousands_separator, "")
        if decimal_separator == ",":
            value = value.replace(",", ".")
        return value

    if "," in value:
        parts = value.split(",")
        if len(parts) > 1 and len(parts[-1]) == 3 and all(part.isdigit() for part in parts if part):
            return "".join(parts)
        return value.replace(",", ".")

    if "." in value:
        parts = value.split(".")
        if len(parts) > 2:
            return "".join(parts)
        if len(parts) == 2 and len(parts[-1]) == 3 and all(part.isdigit() for part in parts if part):
            return "".join(parts)

    return value


def _parse_numeric_value(raw):
    if raw is None or raw == "":
        return None

    if isinstance(raw, Decimal):
        return raw

    try:
        normalized = _normalize_numeric_text(raw)
        if not normalized:
            return None
        return Decimal(normalized)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _filter_queryset_by_numeric_attribute(queryset, key, minimum=None, maximum=None):
    matching_ids = []

    for pk, attributes in queryset.values_list("pk", "attributes"):
        if not isinstance(attributes, dict):
            continue

        value = _parse_numeric_value(attributes.get(key))
        if value is None:
            continue

        if minimum is not None and value < minimum:
            continue

        if maximum is not None and value > maximum:
            continue

        matching_ids.append(pk)

    if not matching_ids:
        return queryset.none()

    return queryset.filter(pk__in=matching_ids)

def get_attribute_filter_specs(category_slug):
    return [
        _with_filter_metadata(spec)
        for spec in ATTRIBUTE_FILTERS_BY_CATEGORY.get(normalize_category_slug(category_slug), [])
    ]


def get_attribute_filter_specs_by_category():
    result = {}
    for category_slug in ATTRIBUTE_FILTERS_BY_CATEGORY.keys():
        result[category_slug] = [
            {
                **spec,
                "param": spec["param"],
                "param_min": spec["param_min"],
                "param_max": spec["param_max"],
                "filter_type": spec["filter_type"],
            }
            for spec in get_attribute_filter_specs(category_slug)
        ]
    return result



# FILTER_UX_POLISH_V76
def _querystring_without(request, remove_keys):
    query = request.GET.copy()

    remove_key_set = set(remove_keys)
    remove_key_set.add("page")

    for key in list(query.keys()):
        if key in remove_key_set:
            del query[key]

    encoded = query.urlencode()
    if encoded:
        return f"{request.path}?{encoded}"
    return request.path


def _format_category_filter_value(category_slug):
    return (category_slug or "").replace("-", " ").title()


def _format_sort_filter_value(sort_value):
    labels = {
        "price_low": "Price low to high",
        "price_high": "Price high to low",
        # RECENT_PRICE_DROP_SORT_V279
        "recent_price_drop": "Recently reduced",
        "newest": "Newest",
    }
    return labels.get(sort_value, sort_value)


def _format_range_filter_value(minimum, maximum):
    if minimum and maximum:
        return f"Min {minimum} – Max {maximum}"
    if minimum:
        return f"Min {minimum}"
    if maximum:
        return f"Max {maximum}"
    return ""


def _build_active_filter_chips(request, fields):
    chips = []

    all_attribute_keys = [key for key in request.GET.keys() if key.startswith("attr_")]

    def add_chip(label, value, remove_keys, clear_param):
        value = str(value or "").strip()
        if not value:
            return

        chips.append({
            "label": label,
            "value": value,
            "clear_url": _querystring_without(request, remove_keys),
            "clear_param": clear_param,
        })

    category_slug = request.GET.get("category", "").strip()
    add_chip(
        "Category",
        _format_category_filter_value(category_slug),
        ["category", *all_attribute_keys],
        "category",
    )

    add_chip("Search", request.GET.get("q", "").strip(), ["q"], "q")
    add_chip("Location", request.GET.get("location", "").strip(), ["location"], "location")
    add_chip("Min price", request.GET.get("min_price", "").strip() + " TL" if request.GET.get("min_price", "").strip() else "", ["min_price"], "min_price")
    add_chip("Max price", request.GET.get("max_price", "").strip() + " TL" if request.GET.get("max_price", "").strip() else "", ["max_price"], "max_price")

    # PRICE_DROP_PUBLIC_BROWSE_FILTER_V278
    price_drops_value = (
        request.GET
        .get(
            "price_drops",
            "",
        )
        .strip()
    )

    if price_drops_value == "1":
        add_chip(
            "Price",
            "Price drops only",
            ["price_drops"],
            "price_drops",
        )

    sort_value = request.GET.get("sort", "newest").strip() or "newest"
    if sort_value != "newest":
        add_chip("Sort", _format_sort_filter_value(sort_value), ["sort"], "sort")

    for field in fields:
        if field.get("filter_type") == "number":
            range_value = _format_range_filter_value(
                field.get("value_min", ""),
                field.get("value_max", ""),
            )
            if range_value:
                remove_keys = [
                    field.get("param", ""),
                    field.get("param_min", ""),
                    field.get("param_max", ""),
                ]
                remove_keys = [key for key in remove_keys if key]
                add_chip(
                    field.get("label", field.get("key", "Filter")),
                    range_value,
                    remove_keys,
                    ",".join([field.get("param_min", ""), field.get("param_max", "")]).strip(","),
                )
        elif field.get("value"):
            add_chip(
                field.get("label", field.get("key", "Filter")),
                field.get("value", ""),
                [field.get("param", "")],
                field.get("param", ""),
            )

    return chips


def get_attribute_filter_context(request, category_slug):
    fields = []
    for spec in get_attribute_filter_specs(category_slug):
        field = {
            **spec,
            "value": request.GET.get(spec["param"], "").strip(),
            "value_min": request.GET.get(spec["param_min"], "").strip() if spec["param_min"] else "",
            "value_max": request.GET.get(spec["param_max"], "").strip() if spec["param_max"] else "",
        }
        fields.append(field)

    return {
        "attribute_filter_category_slug": normalize_category_slug(category_slug),
        "attribute_filter_fields": fields,
        "attribute_filter_specs_by_category": get_attribute_filter_specs_by_category(),
        "active_filter_chips": _build_active_filter_chips(request, fields),
        "active_filter_clear_all_url": request.path,
    }


def apply_attribute_filters(queryset, request, category_slug):
    for spec in get_attribute_filter_specs(category_slug):
        key = spec["key"]
        value = request.GET.get(spec["param"], "").strip()
        if value:
            queryset = queryset.filter(**{
                f"attributes__{key}__icontains": value,
            })

        if spec.get("filter_type") == "number":
            minimum = _parse_numeric_value(request.GET.get(spec["param_min"], "").strip())
            maximum = _parse_numeric_value(request.GET.get(spec["param_max"], "").strip())

            if minimum is not None or maximum is not None:
                queryset = _filter_queryset_by_numeric_attribute(
                    queryset,
                    key,
                    minimum=minimum,
                    maximum=maximum,
                )

    return queryset


def get_page_querystring(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


# REAL_ESTATE_ATTRIBUTE_FILTERS_V67
REAL_ESTATE_ATTRIBUTE_FILTERS_V67 = [
    {"key": "m2_brut", "label": "m² (Brüt)", "placeholder": "120"},
    {"key": "m2_net", "label": "m² (Net)", "placeholder": "95"},
    {"key": "acik_alan_m2", "label": "Açık Alan m²", "placeholder": "25"},
    {"key": "oda_sayisi", "label": "Oda Sayısı", "placeholder": "3+1"},
    {"key": "bina_yasi", "label": "Bina Yaşı", "placeholder": "5-10 arası"},
    {"key": "bulundugu_kat", "label": "Bulunduğu Kat", "placeholder": "3"},
    {"key": "kat_sayisi", "label": "Kat Sayısı", "placeholder": "8"},
    {"key": "isitma", "label": "Isıtma", "placeholder": "Kombi"},
    {"key": "banyo_sayisi", "label": "Banyo Sayısı", "placeholder": "2"},
    {"key": "mutfak", "label": "Mutfak", "placeholder": "Açık / Kapalı"},
    {"key": "balkon", "label": "Balkon", "placeholder": "Evet / Hayır"},
    {"key": "asansor", "label": "Asansör", "placeholder": "Evet / Hayır"},
    {"key": "otopark", "label": "Otopark", "placeholder": "Açık / Kapalı"},
    {"key": "esyali", "label": "Eşyalı", "placeholder": "Evet / Hayır"},
    {"key": "kullanim_durumu", "label": "Kullanım Durumu", "placeholder": "Boş / Kiracılı"},
    {"key": "site_i_cerisinde", "label": "Site İçerisinde", "placeholder": "Evet / Hayır"},
    {"key": "krediye_uygun", "label": "Krediye Uygun", "placeholder": "Evet / Hayır"},
    {"key": "tapu_durumu", "label": "Tapu Durumu", "placeholder": "Kat Mülkiyetli"},
    {"key": "kimden", "label": "Kimden", "placeholder": "Sahibinden"},
    {"key": "takas", "label": "Takaslı", "placeholder": "Evet / Hayır"},
    {"key": "foto_video", "label": "Fotoğraf / Video", "placeholder": "Fotoğraflı"},
    {"key": "harita", "label": "Harita", "placeholder": "Evet / Hayır"},
]

for _real_estate_slug in ("homes-for-sale", "homes-for-rent"):
    ATTRIBUTE_FILTERS_BY_CATEGORY[_real_estate_slug] = REAL_ESTATE_ATTRIBUTE_FILTERS_V67
