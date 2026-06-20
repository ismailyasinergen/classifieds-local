#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "backend" / "accounts" / "views.py"

TARGET_TESTS = [
    "accounts.tests.test_report_trust_safety_events",
    "accounts.tests.test_trust_safety_flows",
]

PY_COMPILE_FILES = [
    ROOT / "backend" / "accounts" / "views.py",
    ROOT / "backend" / "accounts" / "tests" / "test_report_trust_safety_events.py",
    ROOT / "backend" / "accounts" / "tests" / "test_trust_safety_flows.py",
]


@dataclass(frozen=True)
class CleanupStep:
    key: str
    description: str
    start_marker: str
    end_marker: str
    function_name: str
    commit_message: str
    tag_name: str


STEPS = [
    CleanupStep(
        key="obsolete_initial_user_report_views",
        description=(
            "Remove the obsolete initial seller-report create/list/queue/review/dismiss "
            "views that are shadowed by FINAL_SELLER_REPORT_MODERATION_OVERRIDES_V2 "
            "and the later notice-aware/action-event implementations."
        ),
        start_marker="",
        end_marker="# FINAL_SELLER_REPORT_MODERATION_OVERRIDES_V2",
        function_name="user_report_create",
        commit_message="Remove obsolete initial seller report views",
        tag_name="project-checkpoint-v23-remove-obsolete-initial-user-report-views",
    ),
    CleanupStep(
        key="obsolete_pre_tracking_suspend_action",
        description=(
            "Remove the obsolete seller suspension action from "
            "SELLER_SUSPENSION_SUSPEND_ACTIVE_LISTINGS_V1. The safer "
            "SAFE_SELLER_SUSPENSION_TRACKING_FINAL_V1 implementation remains active."
        ),
        start_marker="# SELLER_SUSPENSION_SUSPEND_ACTIVE_LISTINGS_V1",
        end_marker="# SAFE_SELLER_SUSPENSION_TRACKING_FINAL_V1",
        function_name="user_report_suspend_seller",
        commit_message="Remove obsolete pre tracking seller suspend action",
        tag_name="project-checkpoint-v24-remove-obsolete-pre-tracking-suspend-action",
    ),
    CleanupStep(
        key="obsolete_notice_aware_suspend_action",
        description=(
            "Remove the older notice-aware user_report_suspend_seller definition that is "
            "shadowed by SELLER_SUSPENSION_SUSPEND_ACTIVE_LISTINGS_V1. The final event "
            "wrapper should continue to wrap the later active implementation."
        ),
        start_marker="# FINAL_SELLER_REPORT_NOTICE_ACTIONS_V1",
        end_marker="# SELLER_SUSPENSION_SUSPEND_ACTIVE_LISTINGS_V1",
        function_name="user_report_suspend_seller",
        commit_message="Remove obsolete notice seller suspend action",
        tag_name="project-checkpoint-v20-remove-obsolete-notice-suspend-action",
    ),
    CleanupStep(
        key="obsolete_pre_appeals_dashboard",
        description=(
            "Remove the older trust_safety_dashboard definition before TRUST_SAFETY_AUDIT_UI_V1. "
            "The later TRUST_SAFETY_DASHBOARD_APPEALS_V1 implementation remains active."
        ),
        start_marker="# SELLER_SUSPENSION_SUSPEND_ACTIVE_LISTINGS_V1",
        end_marker="# TRUST_SAFETY_AUDIT_UI_V1",
        function_name="trust_safety_dashboard",
        commit_message="Remove obsolete pre appeals trust safety dashboard",
        tag_name="project-checkpoint-v21-remove-obsolete-pre-appeals-dashboard",
    ),
]


def run_capture(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def run_to_file(cmd: list[str], output_path: Path) -> int:
    with output_path.open("w", encoding="utf-8") as handle:
        process = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
    return process.returncode


def print_tail(path: Path, lines: int = 120) -> None:
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in content[-lines:]:
        print(line)


def git_status_short() -> str:
    return run_capture(["git", "status", "--short"]).stdout.strip()


def require_clean_tree() -> None:
    status = git_status_short()
    if status:
        print("Working tree is not clean. Refusing to apply automated cleanup.")
        print(status)
        raise SystemExit(2)


def git_tag_exists(tag_name: str) -> bool:
    result = run_capture(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag_name}"])
    return result.returncode == 0


def find_marker(lines: list[str], marker: str) -> int:
    for index, line in enumerate(lines):
        if line.strip() == marker:
            return index
    raise RuntimeError(f"marker not found: {marker}")


def find_function_span(
    lines: list[str],
    function_name: str,
    start_index: int,
    end_index: int,
) -> tuple[int, int]:
    def_index = None
    prefix = f"def {function_name}("

    for index in range(start_index, end_index):
        if lines[index].startswith(prefix):
            def_index = index
            break

    if def_index is None:
        raise RuntimeError(
            f"function {function_name} not found between selected markers"
        )

    span_start = def_index
    while span_start > start_index and lines[span_start - 1].startswith("@"):
        span_start -= 1

    span_end = end_index
    for index in range(def_index + 1, end_index):
        line = lines[index]

        if line.startswith("@"):
            lookahead = lines[index + 1 : min(index + 8, end_index)]
            if any(next_line.startswith("def ") for next_line in lookahead):
                span_end = index
                break

        if line.startswith("def ") or line.startswith("class "):
            span_end = index
            break

        if line.startswith("# ") and index > def_index + 1:
            span_end = index
            break

    while span_end > span_start and lines[span_end - 1].strip() == "":
        span_end -= 1

    return span_start, span_end


def collapse_blank_runs(text: str) -> str:
    return re.sub(r"\n{4,}", "\n\n\n", text).rstrip() + "\n"


def apply_step_to_text(text: str, step: CleanupStep) -> str:
    if step.key == "obsolete_initial_user_report_views":
        lines = text.splitlines()
        end_index = find_marker(lines, "# FINAL_SELLER_REPORT_MODERATION_OVERRIDES_V2")

        def_index = None
        for index in range(0, end_index):
            if lines[index].startswith("def user_report_create("):
                def_index = index
                break

        if def_index is None:
            raise RuntimeError("initial user_report_create block not found before FINAL_SELLER_REPORT_MODERATION_OVERRIDES_V2")

        span_start = def_index
        while span_start > 0 and lines[span_start - 1].startswith("@"):
            span_start -= 1

        new_lines = lines[:span_start] + lines[end_index:]
        return collapse_blank_runs("\n".join(new_lines))

    lines = text.splitlines()
    start_marker_index = find_marker(lines, step.start_marker)
    end_marker_index = find_marker(lines, step.end_marker)

    if end_marker_index <= start_marker_index:
        raise RuntimeError(
            f"marker order invalid for {step.key}: {step.start_marker} before {step.end_marker}"
        )

    span_start, span_end = find_function_span(
        lines,
        step.function_name,
        start_marker_index,
        end_marker_index,
    )

    new_lines = lines[:span_start] + lines[span_end:]
    return collapse_blank_runs("\n".join(new_lines))


def duplicate_function_report() -> str:
    lines = VIEWS.read_text(encoding="utf-8", errors="ignore").splitlines()
    seen: dict[str, list[int]] = {}

    for index, line in enumerate(lines, 1):
        if line.startswith("def "):
            name = line.split("def ", 1)[1].split("(", 1)[0].strip()
            seen.setdefault(name, []).append(index)

    duplicates = [
        f"{name}: {positions}"
        for name, positions in sorted(seen.items())
        if len(positions) > 1
    ]

    return "\n".join(duplicates) if duplicates else "No duplicate top-level function names found."


def step_state(step: CleanupStep) -> tuple[str, str]:
    if git_tag_exists(step.tag_name):
        return "done", f"tag exists: {step.tag_name}"

    text = VIEWS.read_text(encoding="utf-8")
    try:
        new_text = apply_step_to_text(text, step)
    except RuntimeError as exc:
        return "not-applicable", str(exc)

    if new_text == text:
        return "not-applicable", "step would not change the file"

    return "pending", step.description


def plan() -> None:
    print("===== accounts cleanup runner plan =====")
    print()
    print("Repository:")
    print(ROOT)
    print()
    print("Current HEAD:")
    print(run_capture(["git", "log", "--oneline", "--decorate", "-1"]).stdout.strip())
    print()
    print("Working tree status:")
    status = git_status_short()
    print(status if status else "clean")
    print()
    print("accounts/views.py size:")
    print(len(VIEWS.read_text(encoding="utf-8").splitlines()), "lines")
    print()
    print("Duplicate function names:")
    print(duplicate_function_report())
    print()
    print("Registered safe cleanup steps:")
    for number, step in enumerate(STEPS, 1):
        state, detail = step_state(step)
        print(f"{number}. {step.key}: {state}")
        print(f"   {detail}")
        print(f"   commit: {step.commit_message}")
        print(f"   tag:    {step.tag_name}")


def run_checks(step: CleanupStep) -> bool:
    outputs: list[Path] = []

    checks = [
        (
            "py_compile",
            [sys.executable, "-m", "py_compile", *[str(path) for path in PY_COMPILE_FILES]],
            80,
        ),
        (
            "target_tests",
            ["docker", "exec", "classifieds_web", "python", "manage.py", "test", *TARGET_TESTS],
            180,
        ),
        (
            "full_tests",
            ["docker", "exec", "classifieds_web", "python", "manage.py", "test"],
            180,
        ),
        (
            "diff_check",
            ["git", "diff", "--check"],
            80,
        ),
    ]

    for name, cmd, tail_lines in checks:
        output_path = ROOT / f".cleanup_runner_{step.key}_{name}.txt"
        outputs.append(output_path)
        print()
        print(f"===== running {name} =====")
        print("$ " + " ".join(cmd))
        status = run_to_file(cmd, output_path)
        print_tail(output_path, tail_lines)

        if status != 0:
            print()
            print(f"{name} failed with status {status}.")
            print(f"Output kept at: {output_path.name}")
            return False

    for output_path in outputs:
        try:
            output_path.unlink()
        except FileNotFoundError:
            pass

    return True


def apply_one(step: CleanupStep, no_commit: bool = False) -> bool:
    state, detail = step_state(step)
    if state != "pending":
        print(f"Skipping {step.key}: {state} - {detail}")
        return False

    require_clean_tree()

    original_text = VIEWS.read_text(encoding="utf-8")
    new_text = apply_step_to_text(original_text, step)

    print()
    print(f"===== applying {step.key} =====")
    print(step.description)

    VIEWS.write_text(new_text, encoding="utf-8")

    checks_ok = run_checks(step)
    if not checks_ok:
        VIEWS.write_text(original_text, encoding="utf-8")
        print()
        print("Restored backend/accounts/views.py because a check failed.")
        return False

    print()
    print("===== git status =====")
    print(git_status_short() or "clean")
    print()
    print("===== git diff --stat =====")
    print(run_capture(["git", "diff", "--stat"]).stdout.strip())

    if no_commit:
        print()
        print("no-commit mode enabled; leaving changes uncommitted.")
        return True

    add_result = run_capture(["git", "add", VIEWS.relative_to(ROOT).as_posix()])
    if add_result.returncode != 0:
        print(add_result.stdout)
        return False

    commit_result = run_capture(["git", "commit", "-m", step.commit_message])
    print(commit_result.stdout)
    if commit_result.returncode != 0:
        return False

    tag_result = run_capture(["git", "tag", step.tag_name])
    print(tag_result.stdout)
    if tag_result.returncode != 0:
        return False

    print()
    print(f"Created checkpoint: {step.tag_name}")
    print(run_capture(["git", "log", "--oneline", "--decorate", "-1"]).stdout.strip())
    return True


def pending_steps() -> list[CleanupStep]:
    result = []
    for step in STEPS:
        state, _detail = step_state(step)
        if state == "pending":
            result.append(step)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Conservative marker-based cleanup runner for backend/accounts/views.py"
    )
    parser.add_argument("--plan", action="store_true", help="Show safe registered cleanup steps.")
    parser.add_argument("--apply-next", action="store_true", help="Apply only the next pending safe cleanup.")
    parser.add_argument("--apply-safe", action="store_true", help="Apply all pending registered safe cleanups, one commit per step.")
    parser.add_argument("--no-commit", action="store_true", help="Apply and test but do not commit or tag.")

    args = parser.parse_args()

    selected_modes = sum([args.plan, args.apply_next, args.apply_safe])
    if selected_modes != 1:
        parser.error("choose exactly one of --plan, --apply-next, or --apply-safe")

    if args.plan:
        plan()
        return 0

    steps = pending_steps()
    if not steps:
        print("No pending registered safe cleanup steps.")
        return 0

    if args.apply_next:
        return 0 if apply_one(steps[0], no_commit=args.no_commit) else 1

    for step in steps:
        ok = apply_one(step, no_commit=args.no_commit)
        if not ok:
            print()
            print("Stopped before applying remaining steps.")
            return 1

    print()
    print("All registered safe cleanup steps completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
