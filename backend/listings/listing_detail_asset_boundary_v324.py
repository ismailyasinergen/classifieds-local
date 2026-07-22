"""Read-only listing-detail inline asset boundary audit for v324."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path


V324_MARKER = "LISTING_DETAIL_ASSET_EXTRACTION_GROUNDWORK_V324"
PLANNED_CSS_ASSET_V324 = "listings/listing-detail-v324.css"
PLANNED_JS_ASSET_V324 = "listings/listing-detail-v324.js"
ASSET_AWARE_SOURCE_READER_V325 = (
    "read_listing_detail_contract_source_v325"
)

_STYLE_BLOCK_PATTERN = re.compile(
    r"<style\b[^>]*>(?P<body>.*?)</style>",
    re.IGNORECASE | re.DOTALL,
)
_SCRIPT_BLOCK_PATTERN = re.compile(
    r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(?P<body>.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_TEMPLATE_TOKEN_PATTERN = re.compile(r"\{[{%#]")
_MARKER_PATTERN = re.compile(
    r"\b(?:LISTING|PUBLIC_LISTING|MOBILE_LISTING)_[A-Z0-9_]+_V\d+\b"
)


@dataclass(frozen=True)
class InlineAssetBlockV324:
    kind: str
    index: int
    start_line: int
    end_line: int
    line_count: int
    character_count: int
    contains_template_syntax: bool
    markers: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class InlineEventHandlerV324:
    tag: str
    attribute: str
    line_number: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class InlineStyleAttributeV324:
    tag: str
    line_number: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StaticAssetV324:
    path: str
    kind: str
    character_count: int
    markers: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ListingDetailAssetBoundaryReportV324:
    template_path: str
    style_blocks: tuple[InlineAssetBlockV324, ...]
    script_blocks: tuple[InlineAssetBlockV324, ...]
    inline_event_handlers: tuple[InlineEventHandlerV324, ...]
    inline_style_attributes: tuple[InlineStyleAttributeV324, ...]
    static_assets: tuple[StaticAssetV324, ...]
    source_contract_tests: tuple[str, ...]
    asset_aware_source_tests: tuple[str, ...]
    template_markers: tuple[str, ...]

    @property
    def asset_blocks(self) -> tuple[InlineAssetBlockV324, ...]:
        return self.style_blocks + self.script_blocks

    @property
    def template_dependent_block_count(self) -> int:
        return sum(
            block.contains_template_syntax
            for block in self.asset_blocks
        )

    @property
    def mechanically_extractable(self) -> bool:
        return not self.template_dependent_block_count

    @property
    def blocker_codes(self) -> tuple[str, ...]:
        blockers = []

        if self.template_dependent_block_count:
            blockers.append("template-dependent-asset-blocks")
        if self.inline_event_handlers:
            blockers.append("inline-event-handlers")
        if self.source_contract_tests:
            blockers.append("legacy-source-contract-tests")

        return tuple(blockers)

    @property
    def cutover_ready(self) -> bool:
        return self.mechanically_extractable and not self.blocker_codes

    @property
    def strict_csp_ready(self) -> bool:
        return not (
            self.style_blocks
            or self.script_blocks
            or self.inline_event_handlers
            or self.inline_style_attributes
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "marker": V324_MARKER,
            "template_path": self.template_path,
            "planned_css_asset": PLANNED_CSS_ASSET_V324,
            "planned_js_asset": PLANNED_JS_ASSET_V324,
            "style_blocks": [block.as_dict() for block in self.style_blocks],
            "script_blocks": [block.as_dict() for block in self.script_blocks],
            "inline_event_handlers": [
                handler.as_dict()
                for handler in self.inline_event_handlers
            ],
            "inline_style_attributes": [
                attribute.as_dict()
                for attribute in self.inline_style_attributes
            ],
            "static_assets": [
                asset.as_dict()
                for asset in self.static_assets
            ],
            "source_contract_tests": list(self.source_contract_tests),
            "asset_aware_source_tests": list(
                self.asset_aware_source_tests
            ),
            "template_markers": list(self.template_markers),
            "asset_block_count": len(self.asset_blocks),
            "template_dependent_block_count": (
                self.template_dependent_block_count
            ),
            "mechanically_extractable": self.mechanically_extractable,
            "blocker_codes": list(self.blocker_codes),
            "cutover_ready": self.cutover_ready,
            "strict_csp_ready": self.strict_csp_ready,
            "read_only": True,
        }


class _InlineAttributeParserV324(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.handlers: list[InlineEventHandlerV324] = []
        self.style_attributes: list[InlineStyleAttributeV324] = []

    def handle_starttag(self, tag, attrs):
        line_number, _offset = self.getpos()

        for attribute, _value in attrs:
            normalized = attribute.lower()
            if normalized.startswith("on"):
                self.handlers.append(
                    InlineEventHandlerV324(
                        tag=tag.lower(),
                        attribute=normalized,
                        line_number=line_number,
                    )
                )
            if normalized == "style":
                self.style_attributes.append(
                    InlineStyleAttributeV324(
                        tag=tag.lower(),
                        line_number=line_number,
                    )
                )


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _asset_blocks(
    source: str,
    *,
    kind: str,
    pattern: re.Pattern[str],
) -> tuple[InlineAssetBlockV324, ...]:
    blocks = []

    for index, match in enumerate(pattern.finditer(source), start=1):
        body = match.group("body")
        start_line = _line_number(source, match.start())
        end_line = _line_number(source, match.end() - 1)
        blocks.append(
            InlineAssetBlockV324(
                kind=kind,
                index=index,
                start_line=start_line,
                end_line=end_line,
                line_count=end_line - start_line + 1,
                character_count=len(body),
                contains_template_syntax=bool(
                    _TEMPLATE_TOKEN_PATTERN.search(body)
                ),
                markers=tuple(sorted(set(_MARKER_PATTERN.findall(body)))),
            )
        )

    return tuple(blocks)


def _source_contract_tests(
    backend_dir: Path,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    legacy_matches = []
    asset_aware_matches = []

    for path in sorted(backend_dir.rglob("test*.py")):
        source = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(backend_dir).as_posix()
        if ASSET_AWARE_SOURCE_READER_V325 in source:
            asset_aware_matches.append(relative_path)
            continue
        if "listing_detail.html" not in source:
            continue
        if "read_text" not in source:
            continue

        legacy_matches.append(relative_path)

    return tuple(legacy_matches), tuple(asset_aware_matches)


def _static_assets(backend_dir: Path) -> tuple[StaticAssetV324, ...]:
    assets = []

    for relative_path, kind in (
        (
            f"listings/static/{PLANNED_CSS_ASSET_V324}",
            "css",
        ),
        (
            f"listings/static/{PLANNED_JS_ASSET_V324}",
            "javascript",
        ),
    ):
        path = backend_dir / relative_path
        if not path.is_file():
            continue

        source = path.read_text(encoding="utf-8")
        assets.append(
            StaticAssetV324(
                path=relative_path,
                kind=kind,
                character_count=len(source),
                markers=tuple(
                    sorted(set(_MARKER_PATTERN.findall(source)))
                ),
            )
        )

    return tuple(assets)


def audit_listing_detail_asset_boundary_v324(
    *,
    template_path: Path,
    backend_dir: Path,
) -> ListingDetailAssetBoundaryReportV324:
    template_path = Path(template_path)
    backend_dir = Path(backend_dir)
    source = template_path.read_text(encoding="utf-8")

    attribute_parser = _InlineAttributeParserV324()
    attribute_parser.feed(source)
    source_contract_tests, asset_aware_source_tests = (
        _source_contract_tests(backend_dir)
    )

    return ListingDetailAssetBoundaryReportV324(
        template_path=template_path.relative_to(backend_dir).as_posix(),
        style_blocks=_asset_blocks(
            source,
            kind="style",
            pattern=_STYLE_BLOCK_PATTERN,
        ),
        script_blocks=_asset_blocks(
            source,
            kind="script",
            pattern=_SCRIPT_BLOCK_PATTERN,
        ),
        inline_event_handlers=tuple(attribute_parser.handlers),
        inline_style_attributes=tuple(
            attribute_parser.style_attributes
        ),
        static_assets=_static_assets(backend_dir),
        source_contract_tests=source_contract_tests,
        asset_aware_source_tests=asset_aware_source_tests,
        template_markers=tuple(sorted(set(_MARKER_PATTERN.findall(source)))),
    )
