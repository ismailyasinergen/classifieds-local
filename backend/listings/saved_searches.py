# SAVED_SEARCH_FOUNDATION_V77
from django.http import QueryDict
from django.urls import reverse


SAVED_SEARCH_ALLOWED_KEYS = {
    "q",
    "location",
    "min_price",
    "max_price",
    "category",
    "sort",
}


def _clean_value(value):
    return str(value or "").strip()


def clean_saved_search_querydict(data):
    if isinstance(data, QueryDict):
        source = data.copy()
    else:
        source = QueryDict(str(data or ""), mutable=True)

    clean = QueryDict("", mutable=True)

    for key, values in source.lists():
        if key == "page":
            continue

        if key not in SAVED_SEARCH_ALLOWED_KEYS and not key.startswith("attr_"):
            continue

        cleaned_values = []
        for value in values:
            value = _clean_value(value)
            if value:
                cleaned_values.append(value)

        if cleaned_values:
            clean.setlist(key, cleaned_values)

    return clean


def querydict_to_plain_params(querydict):
    params = {}

    for key, values in querydict.lists():
        if not values:
            continue

        if len(values) == 1:
            params[key] = values[0]
        else:
            params[key] = list(values)

    return params


def get_saved_search_context(request):
    querydict = clean_saved_search_querydict(request.GET)
    querystring = querydict.urlencode()

    context = {
        "save_search_querystring": querystring,
        "current_saved_search": None,
    }

    if not querystring or not request.user.is_authenticated:
        return context

    from .models import SavedSearch

    context["current_saved_search"] = (
        SavedSearch.objects
        .filter(user=request.user, path=reverse("listings:listing_list"), querystring=querystring)
        .first()
    )

    return context


def create_saved_search_from_request(request, querystring, name=""):
    from .models import SavedSearch

    querydict = clean_saved_search_querydict(querystring)
    clean_querystring = querydict.urlencode()

    if not clean_querystring:
        return None, False, ""

    path = reverse("listings:listing_list")
    query_params = querydict_to_plain_params(querydict)
    name = _clean_value(name)[:120]

    saved_search = (
        SavedSearch.objects
        .filter(user=request.user, path=path, querystring=clean_querystring)
        .first()
    )

    if saved_search:
        update_fields = ["query_params", "updated_at"]
        saved_search.query_params = query_params

        if name and saved_search.name != name:
            saved_search.name = name
            update_fields.append("name")

        saved_search.save(update_fields=update_fields)
        return saved_search, False, clean_querystring

    saved_search = SavedSearch.objects.create(
        user=request.user,
        name=name,
        path=path,
        query_params=query_params,
        querystring=clean_querystring,
    )
    return saved_search, True, clean_querystring

# SAVED_SEARCH_UX_POLISH_V78
SORT_LABELS_V78 = {
    "newest": "Newest",
    "price_low": "Price low to high",
    "price_high": "Price high to low",
}

ATTRIBUTE_LABELS_V78 = {
    "m2_brut": "Gross m²",
    "m2_net": "Net m²",
    "oda_sayisi": "Rooms",
    "bina_yasi": "Building age",
    "bulundugu_kat": "Floor",
    "kat_sayisi": "Floors",
    "isitma": "Heating",
    "banyo_sayisi": "Bathrooms",
    "balkon": "Balcony",
    "esyali": "Furnished",
    "site_icerisinde": "In complex",
    "krediye_uygun": "Mortgage eligible",
    "tapu_durumu": "Title deed",
    "kimden": "Listed by",
    "marka": "Brand",
    "model": "Model",
    "seri": "Series",
    "yil": "Year",
    "km": "KM",
    "yakit": "Fuel",
    "vites": "Transmission",
    "kasa_tipi": "Body type",
    "motor_gucu": "Engine power",
    "motor_hacmi": "Engine size",
    "cekis": "Drivetrain",
    "renk": "Color",
    "garanti": "Warranty",
    "takas": "Exchange",
    "kapasite": "Capacity",
}


def _format_key_label_v78(key):
    key = str(key or "")
    if key.startswith("attr_"):
        key = key[5:]

    for suffix in ("_min", "_max"):
        if key.endswith(suffix):
            key = key[: -len(suffix)]

    if key in ATTRIBUTE_LABELS_V78:
        return ATTRIBUTE_LABELS_V78[key]

    return key.replace("_", " ").replace("-", " ").title()


def _format_value_v78(value):
    if isinstance(value, list):
        return ", ".join(_format_value_v78(item) for item in value)

    value = _clean_value(value)
    if value.lower() in {"true", "yes", "1"}:
        return "Yes"
    if value.lower() in {"false", "no", "0"}:
        return "No"

    if value and value.islower() and any(character.isalpha() for character in value):
        return value.replace("-", " ").replace("_", " ").title()

    return value


def _append_range_summary_v78(summaries, params, min_key, max_key, label):
    minimum = params.get(min_key)
    maximum = params.get(max_key)

    if not minimum and not maximum:
        return

    if minimum and maximum:
        value = f"{minimum} – {maximum}"
    elif minimum:
        value = f"Min {minimum}"
    else:
        value = f"Max {maximum}"

    summaries.append(
        {
            "label": label,
            "value": value,
            "param": ",".join([min_key, max_key]),
            "kind": "range",
        }
    )


def summarize_saved_search_params(query_params):
    params = query_params or {}
    summaries = []

    category = params.get("category")
    if category:
        summaries.append(
            {
                "label": "Category",
                "value": _format_value_v78(category),
                "param": "category",
                "kind": "category",
            }
        )

    q = params.get("q")
    if q:
        summaries.append(
            {
                "label": "Search",
                "value": _format_value_v78(q),
                "param": "q",
                "kind": "search",
            }
        )

    location = params.get("location")
    if location:
        summaries.append(
            {
                "label": "Location",
                "value": _format_value_v78(location),
                "param": "location",
                "kind": "location",
            }
        )

    _append_range_summary_v78(summaries, params, "min_price", "max_price", "Price")

    sort = params.get("sort")
    if sort and sort != "newest":
        summaries.append(
            {
                "label": "Sort",
                "value": SORT_LABELS_V78.get(sort, _format_value_v78(sort)),
                "param": "sort",
                "kind": "sort",
            }
        )

    handled_attr_keys = set()
    attr_base_names = set()

    for key in params:
        if not key.startswith("attr_"):
            continue

        base = key[5:]
        if base.endswith("_min"):
            base = base[:-4]
        elif base.endswith("_max"):
            base = base[:-4]

        attr_base_names.add(base)

    for base in sorted(attr_base_names):
        min_key = f"attr_{base}_min"
        max_key = f"attr_{base}_max"
        exact_key = f"attr_{base}"
        label = _format_key_label_v78(base)

        if min_key in params or max_key in params:
            _append_range_summary_v78(summaries, params, min_key, max_key, label)
            handled_attr_keys.update({min_key, max_key})
            continue

        if exact_key in params:
            summaries.append(
                {
                    "label": label,
                    "value": _format_value_v78(params.get(exact_key)),
                    "param": exact_key,
                    "kind": "attribute",
                }
            )
            handled_attr_keys.add(exact_key)

    for key, value in sorted(params.items()):
        if key in handled_attr_keys:
            continue
        if key.startswith("attr_"):
            summaries.append(
                {
                    "label": _format_key_label_v78(key),
                    "value": _format_value_v78(value),
                    "param": key,
                    "kind": "attribute",
                }
            )

    return summaries


def saved_search_filter_count(query_params):
    return len(summarize_saved_search_params(query_params))


def saved_search_summary_sentence(query_params):
    summaries = summarize_saved_search_params(query_params)

    if not summaries:
        return "No filters saved."

    return " · ".join(f"{item['label']}: {item['value']}" for item in summaries)
