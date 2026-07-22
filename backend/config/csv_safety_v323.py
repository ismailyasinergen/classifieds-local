"""Shared spreadsheet-formula neutralization for staff CSV exports."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


CSV_FORMULA_PREFIXES_V323 = ("=", "+", "-", "@", "\t", "\r")
CSV_FORMULA_ESCAPE_PREFIX_V323 = "'"


def csv_safe_cell_v323(value: Any) -> str:
    """Return an idempotent text cell that spreadsheets cannot execute."""

    text = "" if value is None else str(value)

    if text.startswith(CSV_FORMULA_PREFIXES_V323):
        return CSV_FORMULA_ESCAPE_PREFIX_V323 + text

    return text


def csv_safe_row_v323(
    row: Mapping[str, Any] | Iterable[Any],
) -> dict[str, str] | tuple[str, ...]:
    if isinstance(row, Mapping):
        return {
            key: csv_safe_cell_v323(value)
            for key, value in row.items()
        }

    return tuple(csv_safe_cell_v323(value) for value in row)


def write_csv_row_v323(writer: Any, row: Any) -> Any:
    return writer.writerow(csv_safe_row_v323(row))
