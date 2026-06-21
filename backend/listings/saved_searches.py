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
