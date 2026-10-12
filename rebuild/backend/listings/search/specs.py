from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SchemaRef:
    id: int
    category_id: int
    version: int


@dataclass(frozen=True)
class AttributePredicate:
    key: str
    kind: str
    unit: str
    operator: str
    value: int | str | bool


@dataclass(frozen=True)
class SearchSpec:
    version: int
    keyword: str
    category_id: int | None
    category_scope: str
    location: str
    currency: str
    price_min: Decimal | None
    price_max: Decimal | None
    attribute_schema: SchemaRef | None
    attributes: tuple[AttributePredicate, ...]
    resolved_schemas: tuple[SchemaRef, ...]
    sort: str
