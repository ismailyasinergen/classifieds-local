from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path


MARKER = "REMAINING_LISTING_VIEW_EXTRACTION_AUDIT_V144"
DEFAULT_TARGET = Path("backend/listings/views.py")
EXTRACTED_V141_CANDIDATES = ("apply_listing_filters", "_create_moderation_notice")
VIEW_SIDE_EFFECT_NAMES = {
    "render",
    "redirect",
    "messages",
    "Paginator",
    "reverse",
    "get_object_or_404",
}


@dataclass(frozen=True)
class FunctionAudit:
    name: str
    lineno: int
    end_lineno: int
    line_count: int
    first_arg: str
    is_private: bool
    is_request_first: bool
    uses_request_name: bool
    uses_view_side_effect_name: bool
    category: str
    risk: str
    reason: str


@dataclass(frozen=True)
class ListingViewAudit:
    target_path: str
    exists: bool
    total_lines: int
    top_level_function_count: int
    top_level_class_count: int
    view_like_function_count: int
    helper_candidate_count: int
    low_risk_candidate_count: int
    medium_risk_candidate_count: int
    extracted_v141_candidates_missing_count: int
    extracted_v141_candidates_still_present: tuple[str, ...]
    candidates: tuple[FunctionAudit, ...]
    all_functions: tuple[FunctionAudit, ...]

    @property
    def next_candidate(self) -> FunctionAudit | None:
        low_risk = [candidate for candidate in self.candidates if candidate.risk == "low"]
        if low_risk:
            return sorted(low_risk, key=lambda item: (item.line_count, item.name))[0]

        medium_risk = [candidate for candidate in self.candidates if candidate.risk == "medium"]
        if medium_risk:
            return sorted(medium_risk, key=lambda item: (item.line_count, item.name))[0]

        return None


def resolve_project_path(root: str | Path, relative_path: str | Path = DEFAULT_TARGET) -> Path:
    root_path = Path(root).resolve()
    relative = Path(relative_path)

    candidates = [root_path / relative]
    if relative.parts and relative.parts[0] == "backend":
        candidates.append(root_path / Path(*relative.parts[1:]))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def _first_arg_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if not node.args.args:
        return ""
    return node.args.args[0].arg


def _load_names(node: ast.AST) -> set[str]:
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }


def classify_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionAudit:
    first_arg = _first_arg_name(node)
    load_names = _load_names(node)
    line_count = int(node.end_lineno or node.lineno) - node.lineno + 1

    is_request_first = first_arg == "request"
    uses_request_name = "request" in load_names
    uses_view_side_effect_name = bool(load_names & VIEW_SIDE_EFFECT_NAMES)
    is_private = node.name.startswith("_")

    if is_request_first:
        category = "function_view"
        risk = "view"
        reason = "request-first function is treated as an active view"
    elif uses_request_name or uses_view_side_effect_name:
        category = "view_adjacent_helper"
        risk = "medium"
        reason = "non-request-first helper but uses request or view side-effect names"
    elif is_private and line_count <= 80:
        category = "private_helper"
        risk = "low"
        reason = "private non-view helper under 80 lines"
    elif line_count <= 80:
        category = "non_view_helper"
        risk = "low"
        reason = "non-view helper under 80 lines"
    elif line_count <= 160:
        category = "larger_non_view_helper"
        risk = "medium"
        reason = "non-view helper between 81 and 160 lines"
    else:
        category = "large_non_view_helper"
        risk = "high"
        reason = "non-view helper over 160 lines"

    return FunctionAudit(
        name=node.name,
        lineno=node.lineno,
        end_lineno=int(node.end_lineno or node.lineno),
        line_count=line_count,
        first_arg=first_arg,
        is_private=is_private,
        is_request_first=is_request_first,
        uses_request_name=uses_request_name,
        uses_view_side_effect_name=uses_view_side_effect_name,
        category=category,
        risk=risk,
        reason=reason,
    )


def build_report(root: str | Path = ".", target: str | Path = DEFAULT_TARGET) -> ListingViewAudit:
    target_path = resolve_project_path(root, target)
    exists = target_path.exists()

    if not exists:
        return ListingViewAudit(
            target_path=str(target_path),
            exists=False,
            total_lines=0,
            top_level_function_count=0,
            top_level_class_count=0,
            view_like_function_count=0,
            helper_candidate_count=0,
            low_risk_candidate_count=0,
            medium_risk_candidate_count=0,
            extracted_v141_candidates_missing_count=0,
            extracted_v141_candidates_still_present=(),
            candidates=(),
            all_functions=(),
        )

    source = target_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(target_path))
    total_lines = len(source.splitlines())

    function_nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    class_nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)]

    all_functions = tuple(classify_function(node) for node in function_nodes)
    top_level_names = {function.name for function in all_functions}

    extracted_still_present = tuple(
        name for name in EXTRACTED_V141_CANDIDATES if name in top_level_names
    )

    candidates = tuple(
        function
        for function in all_functions
        if function.risk in {"low", "medium"}
        and function.name not in EXTRACTED_V141_CANDIDATES
    )

    return ListingViewAudit(
        target_path=str(target_path),
        exists=True,
        total_lines=total_lines,
        top_level_function_count=len(function_nodes),
        top_level_class_count=len(class_nodes),
        view_like_function_count=sum(1 for function in all_functions if function.risk == "view"),
        helper_candidate_count=len(candidates),
        low_risk_candidate_count=sum(1 for function in candidates if function.risk == "low"),
        medium_risk_candidate_count=sum(1 for function in candidates if function.risk == "medium"),
        extracted_v141_candidates_missing_count=len(EXTRACTED_V141_CANDIDATES) - len(extracted_still_present),
        extracted_v141_candidates_still_present=extracted_still_present,
        candidates=candidates,
        all_functions=all_functions,
    )


def render_markdown_report(report: ListingViewAudit) -> str:
    lines: list[str] = [
        "# v144 Remaining Listing View Extraction Audit",
        "",
        f"Marker: `{MARKER}`",
        "",
        "## Target",
        "",
        f"- Path: `{report.target_path}`",
        f"- Exists: `{report.exists}`",
        f"- Total lines: `{report.total_lines}`",
        f"- Top-level functions: `{report.top_level_function_count}`",
        f"- Top-level classes: `{report.top_level_class_count}`",
        f"- View-like functions: `{report.view_like_function_count}`",
        f"- Helper candidates: `{report.helper_candidate_count}`",
        f"- Low-risk candidates: `{report.low_risk_candidate_count}`",
        f"- Medium-risk candidates: `{report.medium_risk_candidate_count}`",
        "",
        "## v141 candidate exhaustion check",
        "",
        f"- Extracted v141 candidates expected missing: `{', '.join(EXTRACTED_V141_CANDIDATES)}`",
        f"- Extracted v141 candidates missing count: `{report.extracted_v141_candidates_missing_count}`",
        f"- Extracted v141 candidates still present: `{', '.join(report.extracted_v141_candidates_still_present) or 'none'}`",
        "",
        "## Recommended next candidate",
        "",
    ]

    next_candidate = report.next_candidate
    if next_candidate is None:
        lines.extend([
            "No low/medium-risk helper candidate is currently recommended by the v144 audit.",
            "",
        ])
    else:
        lines.extend([
            f"- Name: `{next_candidate.name}`",
            f"- Lines: `{next_candidate.line_count}`",
            f"- Risk: `{next_candidate.risk}`",
            f"- Category: `{next_candidate.category}`",
            f"- Reason: {next_candidate.reason}",
            "",
        ])

    lines.extend([
        "## Remaining candidates",
        "",
    ])

    if not report.candidates:
        lines.append("No remaining helper candidates found.")
    else:
        lines.append("| Name | Lines | Risk | Category | First arg | Reason |")
        lines.append("|---|---:|---|---|---|---|")
        for candidate in sorted(report.candidates, key=lambda item: (item.risk != "low", item.line_count, item.name)):
            lines.append(
                f"| `{candidate.name}` | {candidate.line_count} | {candidate.risk} | "
                f"{candidate.category} | `{candidate.first_arg}` | {candidate.reason} |"
            )

    lines.extend([
        "",
        "## v144 rules",
        "",
        "- Do not re-extract `apply_listing_filters`; it was completed in v142.",
        "- Do not re-extract `_create_moderation_notice`; it was completed in v143.",
        "- Prefer low-risk non-view helpers before any request-first function view.",
        "- Do not change behavior in this audit checkpoint.",
        "- Use the audit result to choose the next extraction checkpoint.",
        "",
    ])

    return "\n".join(lines)


def write_markdown_report(report: ListingViewAudit, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown_report(report), encoding="utf-8")
    return output


def print_summary(report: ListingViewAudit) -> None:
    print(f"===== {MARKER} SUMMARY =====")
    print(f"Target: {report.target_path}")
    print(f"Exists: {report.exists}")
    print(f"Total lines: {report.total_lines}")
    print(f"Top-level functions: {report.top_level_function_count}")
    print(f"Top-level classes: {report.top_level_class_count}")
    print(f"View-like functions: {report.view_like_function_count}")
    print(f"Helper candidates: {report.helper_candidate_count}")
    print(f"Low-risk candidates: {report.low_risk_candidate_count}")
    print(f"Medium-risk candidates: {report.medium_risk_candidate_count}")
    print(f"Extracted v141 candidates still present: {', '.join(report.extracted_v141_candidates_still_present) or 'none'}")

    next_candidate = report.next_candidate
    if next_candidate is None:
        print("Recommended next candidate: none")
    else:
        print(
            "Recommended next candidate: "
            f"{next_candidate.name} ({next_candidate.line_count} lines, "
            f"{next_candidate.risk}, {next_candidate.category})"
        )

    if report.candidates:
        print()
        print("Top remaining candidates:")
        for candidate in sorted(report.candidates, key=lambda item: (item.risk != "low", item.line_count, item.name))[:10]:
            print(f"  - {candidate.name}: {candidate.line_count} lines, {candidate.risk}, {candidate.category}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit remaining listing view extraction candidates for v144.")
    parser.add_argument("--root", default=".", help="Repository root or Docker backend mount root.")
    parser.add_argument(
        "--write-report",
        default=None,
        help="Optional markdown report output path.",
    )
    args = parser.parse_args(argv)

    report = build_report(root=args.root)
    print_summary(report)

    if not report.exists:
        print("FAIL: target views.py file does not exist.")
        return 1

    if report.extracted_v141_candidates_still_present:
        print("FAIL: one or more v141 extracted candidates are still top-level functions in views.py.")
        return 1

    if args.write_report:
        output = write_markdown_report(report, args.write_report)
        print(f"Wrote report: {output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
