#!/usr/bin/env python3
"""Regenerate the ViewCoach Milestone 3.5 patch against commit 35b1664.

Run this from the ViewCoach repository root. By default it creates and validates
an updated patch. Pass --apply to apply the validated patch immediately.
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

EXPECTED_HEAD = "35b16641a4453253ca08b050b9323a537fd49746"
DEFAULT_SOURCE = "viewcoach-personal-evidence-milestone-3.5-current.patch"
DEFAULT_OUTPUT = "viewcoach-personal-evidence-milestone-3.5-head-35b1664.patch"
DASHBOARD_PATH = "templates/core/dashboard.html"


class RegenerationError(RuntimeError):
    pass


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RegenerationError(f"git {' '.join(args)} failed:\n{detail}")
    return result


def diff_section_bounds(patch: str, path: str) -> tuple[int, int]:
    marker = f"diff --git a/{path} b/{path}\n"
    start = patch.find(marker)
    if start == -1:
        raise RegenerationError(f"Could not find the patch section for {path}.")

    next_marker = patch.find("\ndiff --git a/", start + len(marker))
    end = len(patch) if next_marker == -1 else next_marker + 1
    return start, end


def get_diff_section(patch: str, path: str) -> str:
    start, end = diff_section_bounds(patch, path)
    return patch[start:end]


def recalculate_hunk_counts(section: str) -> str:
    """Recalculate line counts after editing lines inside a unified-diff hunk."""
    lines = section.splitlines(keepends=True)
    header_pattern = re.compile(
        r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*?)(\n?)$"
    )

    index = 0
    while index < len(lines):
        match = header_pattern.match(lines[index])
        if match is None:
            index += 1
            continue

        next_hunk = index + 1
        old_count = 0
        new_count = 0
        while next_hunk < len(lines) and not lines[next_hunk].startswith("@@ "):
            line = lines[next_hunk]
            if line.startswith("diff --git "):
                break
            if line.startswith(" "):
                old_count += 1
                new_count += 1
            elif line.startswith("-"):
                old_count += 1
            elif line.startswith("+"):
                new_count += 1
            next_hunk += 1

        old_start, _, new_start, _, suffix, newline = match.groups()
        lines[index] = (
            f"@@ -{old_start},{old_count} +{new_start},{new_count} @@"
            f"{suffix}{newline}"
        )
        index = next_hunk

    return "".join(lines)


def replace_diff_section(patch: str, path: str, replacement: str) -> str:
    start, end = diff_section_bounds(patch, path)
    replacement = recalculate_hunk_counts(replacement).rstrip("\n") + "\n"
    return patch[:start] + replacement + patch[end:]


def build_dashboard_section(repository_root: Path) -> str:
    dashboard_file = repository_root / DASHBOARD_PATH
    original = dashboard_file.read_text(encoding="utf-8")
    updated = original

    facts_anchor = """            <div>\n                <dt>In my library</dt>\n                <dd>{{ question_count }}</dd>\n            </div>\n"""
    facts_replacement = facts_anchor + """            <div>\n                <dt>Evidence records</dt>\n                <dd>{{ evidence_summary.total_count }}</dd>\n            </div>\n"""
    if updated.count(facts_anchor) != 1:
        raise RegenerationError(
            "The current dashboard no longer has the expected 'In my library' block."
        )
    updated = updated.replace(facts_anchor, facts_replacement, 1)

    links_anchor = """            <a href=\"{% url 'goals:list' %}\">Interview goals <span aria-hidden=\"true\">→</span></a>\n"""
    links_replacement = links_anchor + """            <a href=\"{% url 'evidence:list' %}\">Personal evidence <span aria-hidden=\"true\">→</span></a>\n"""
    if updated.count(links_anchor) != 1:
        raise RegenerationError(
            "The current dashboard no longer has the expected Interview goals link."
        )
    updated = updated.replace(links_anchor, links_replacement, 1)

    unified = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{DASHBOARD_PATH}",
            tofile=f"b/{DASHBOARD_PATH}",
        )
    )
    if not unified:
        raise RegenerationError("Dashboard regeneration produced no changes.")

    return f"diff --git a/{DASHBOARD_PATH} b/{DASHBOARD_PATH}\n{unified}"


def repair_multi_roadmap_fixture(patch: str) -> str:
    path = "apps/evidence/tests/conftest.py"
    section = get_diff_section(patch, path)

    old_block = """+@pytest.fixture
+def goal(user, roadmap):
+    return InterviewGoal.objects.create(
+        user=user,
+        title="Backend interview",
+        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
+        role_title="Backend Developer",
+        roadmap=roadmap,
+        is_primary=True,
+    )
"""
    new_block = """+@pytest.fixture
+def goal(user, roadmap):
+    goal = InterviewGoal.objects.create(
+        user=user,
+        title="Backend interview",
+        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
+        role_title="Backend Developer",
+        is_primary=True,
+    )
+    goal.roadmaps.add(roadmap)
+    return goal
"""

    if section.count(old_block) != 1:
        raise RegenerationError(
            "Could not find the stale single-roadmap evidence test fixture."
        )
    section = section.replace(old_block, new_block, 1)
    return replace_diff_section(patch, path, section)


def update_evidence_migration_dependency(patch: str) -> str:
    path = "apps/evidence/migrations/0001_initial.py"
    section = get_diff_section(patch, path)
    old = '+        ("goals", "0001_initial"),\n'
    new = '+        ("goals", "0002_goal_roadmaps_and_creation_token"),\n'
    if section.count(old) != 1:
        raise RegenerationError("Could not find the old goals migration dependency.")
    section = section.replace(old, new, 1)
    return replace_diff_section(patch, path, section)


def enforce_quarter_hour_steps(patch: str) -> str:
    path = "apps/planner/forms.py"
    section = get_diff_section(patch, path)

    anchor = """+    )
+ 
+    def clean(self):
"""
    replacement = """+    )
+ 
+    def clean_time_budget_hours(self):
+        hours = self.cleaned_data["time_budget_hours"]
+        quarter_hours = hours * Decimal("4")
+        if quarter_hours != quarter_hours.to_integral_value():
+            raise forms.ValidationError("Use 15-minute increments.")
+        return hours
+ 
+    def clean(self):
"""
    if section.count(anchor) != 1:
        raise RegenerationError(
            "Could not locate the study-hours form insertion point."
        )
    section = section.replace(anchor, replacement, 1)
    return replace_diff_section(patch, path, section)


def regenerate(repository_root: Path, source: Path, output: Path) -> None:
    patch = source.read_text(encoding="utf-8")

    patch = repair_multi_roadmap_fixture(patch)
    patch = update_evidence_migration_dependency(patch)
    patch = enforce_quarter_hour_steps(patch)
    patch = replace_diff_section(
        patch,
        DASHBOARD_PATH,
        build_dashboard_section(repository_root),
    )

    output.write_text(patch, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate and validate Milestone 3.5 against the current ViewCoach HEAD."
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the regenerated patch after git apply --check succeeds.",
    )
    parser.add_argument(
        "--allow-different-head",
        action="store_true",
        help="Skip the exact-commit guard. Use only after deliberately reviewing drift.",
    )
    args = parser.parse_args()

    root = Path(run_git("rev-parse", "--show-toplevel").stdout.strip())
    head = run_git("rev-parse", "HEAD").stdout.strip()
    branch = run_git("branch", "--show-current").stdout.strip()

    if head != EXPECTED_HEAD and not args.allow_different_head:
        raise RegenerationError(
            "Refusing to regenerate against an unexpected commit.\n"
            f"Expected: {EXPECTED_HEAD}\n"
            f"Actual:   {head}"
        )

    source = (root / args.source).resolve()
    output = (root / args.output).resolve()
    if not source.is_file():
        raise RegenerationError(f"Source patch not found: {source}")
    if source == output:
        raise RegenerationError("Source and output patch paths must be different.")

    if args.apply:
        tracked_changes = run_git("status", "--porcelain", "--untracked-files=no").stdout
        if tracked_changes.strip():
            raise RegenerationError(
                "Tracked files have local changes. Commit or stash them before applying 3.5."
            )

    regenerate(root, source, output)

    check_result = run_git("apply", "--check", "--whitespace=error-all", str(output), check=False)
    if check_result.returncode != 0:
        detail = check_result.stderr.strip() or check_result.stdout.strip()
        raise RegenerationError(
            "The regenerated patch was written, but validation failed:\n"
            f"{detail}"
        )

    print(f"Branch: {branch}")
    print(f"HEAD:   {head}")
    print(f"Created and validated: {output.name}")

    if args.apply:
        run_git("apply", "--whitespace=error-all", str(output))
        print("Patch applied successfully.")
        print("Next: python manage.py migrate")
        print("Then: python -m pytest")
        print("Then: python -m ruff check .")
        print("Then: python manage.py makemigrations --check --dry-run")
    else:
        print(f"Apply with: git apply {output.name}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegenerationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
