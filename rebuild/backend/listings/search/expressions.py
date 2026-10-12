"""Version-one SQL semantics.

SearchFoldV1 and the *_v1 factories are migration dependencies: never change
their meaning. A future text normalization/index contract needs new versions.
"""
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Case, DecimalField, Func, TextField, Value, When
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Length
from django.db.models.lookups import Exact, LessThanOrEqual, Regex


class SearchFoldV1(Func):
    arity = 1
    output_field = TextField()
    # NFC uses PostgreSQL's special grammar, not a quoted Func argument.
    # The extra U+0307 source character is deleted by TRANSLATE after NFC.
    template = (
        "LOWER(TRANSLATE(NORMALIZE(%(expressions)s,NFC),"
        "'ÇçĞğİIıiÖöŞşÜü'||CHR(775),'ccggiiiioossuu'))"
    )


def search_vector_v1(prefix=""):
    return (
        SearchVector(SearchFoldV1(prefix + "title"), config="simple", weight="A")
        + SearchVector(SearchFoldV1(prefix + "description"), config="simple", weight="B")
    )


def folded_title_v1(prefix=""):
    return SearchFoldV1(prefix + "title")


def folded_location_v1(prefix=""):
    return SearchFoldV1(prefix + "location")


def search_query_v1(keyword):
    return SearchQuery(SearchFoldV1(Value(keyword)), config="simple", search_type="plain")


class _UnrestrictedNumeric(Func):
    arity = 1
    output_field = DecimalField()
    template = "(%(expressions)s)::numeric"


def attribute_value_v1(*, key, kind, field="public_revision__attributes"):
    """Literal JSON keys; all numeric casts are inside their validating CASE."""
    json_value = KeyTransform(key, field)
    text_value = KeyTextTransform(key, field)
    json_type = Func(json_value, function="jsonb_typeof", output_field=TextField())
    expected_type = {"integer": "number", "decimal": "string",
                     "string": "string", "boolean": "boolean"}[kind]
    guard = Exact(json_type, Value(expected_type))
    output_field = TextField()
    result = text_value
    if kind in ("integer", "decimal"):
        pattern = (r"\A(0|-?[1-9][0-9]*)\Z" if kind == "integer" else
                   r"\A(0|-?[1-9][0-9]*|-?(0|[1-9][0-9]*)\.[0-9]*[1-9])\Z")
        guard &= LessThanOrEqual(Length(text_value), Value(64))
        guard &= Regex(text_value, Value(pattern))
        output_field = DecimalField()
        result = _UnrestrictedNumeric(text_value)
    return Case(When(guard, then=result), default=Value(None), output_field=output_field)
