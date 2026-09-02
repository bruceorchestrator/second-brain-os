#!/usr/bin/env python3
"""
Pre-commit staleness check — enforces the "single source of truth" map
in AGENTS.md.

Hard-blocks 3 patterns where body of a current-state file changed but the
header/date marker is stale (older than today):

  1. memory/STATE.md             — `Last updated: YYYY-MM-DD` near top
  2. memory/projects/*.md         — `## Current State as of YYYY-MM-DD` section
  3. agent-os/agents/*/PROJECT_MAP.md — `Last updated: YYYY-MM-DD`

Warn-only:
  - agent-os/agents/*/STATUS.md  — event log; historical dated sections OK
  - missing headers              — flagged but never block

Bypass (intentional):
  STALENESS_SKIP=1 git commit ...     # surgical, keeps PII check active
  git commit --no-verify              # nuclear, skips all hooks
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

if os.environ.get("STALENESS_SKIP") == "1":
    sys.exit(0)

REPO = Path(
    subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
)
TODAY = date.today().isoformat()
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def staged_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
        cwd=REPO, text=True,
    )
    return [l for l in out.splitlines() if l]


def staged_content(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f":{path}"], cwd=REPO, text=True, errors="ignore"
    )


def diff_changes(path: str) -> list[tuple[str, int, str]]:
    """[(sign, new_lineno, content), ...] — only +/- lines."""
    out = subprocess.check_output(
        ["git", "diff", "--cached", "-U0", "--", path], cwd=REPO, text=True,
    )
    result: list[tuple[str, int, str]] = []
    new_lineno = 0
    for line in out.splitlines():
        m = HUNK_RE.match(line)
        if m:
            new_lineno = int(m.group(1)) - 1
            continue
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            new_lineno += 1
            result.append(("+", new_lineno, line[1:]))
        elif line.startswith("-"):
            result.append(("-", new_lineno, line[1:]))
        elif line.startswith(" "):
            new_lineno += 1
    return result


def header_date(content: str, header_re: re.Pattern) -> str | None:
    m = header_re.search(content)
    if not m:
        return None
    d = DATE_RE.search(m.group(0))
    return d.group(1) if d else None


def body_changed(
    path: str,
    exclude_re: re.Pattern,
    line_filter=lambda ln: True,
) -> bool:
    for sign, lineno, content in diff_changes(path):
        if exclude_re.search(content):
            continue
        if not line_filter(lineno):
            continue
        if content.strip() == "":
            continue
        return True
    return False


errors: list[str] = []
warnings: list[str] = []


def check_simple_header(path: str, hard_block: bool) -> None:
    """For files with `Last updated: YYYY-MM-DD` near top."""
    content = staged_content(path)
    header_re = re.compile(r"^Last updated: \d{4}-\d{2}-\d{2}", re.MULTILINE)
    file_date = header_date(content, header_re)
    if file_date is None:
        warnings.append(f"{path}: no `Last updated:` header found")
        return
    if file_date >= TODAY:
        return
    if not body_changed(path, exclude_re=re.compile(r"^Last updated:")):
        return
    msg = (
        f"{path}: body changed but `Last updated: {file_date}` "
        f"is older than today ({TODAY})"
    )
    (errors if hard_block else warnings).append(msg)


def check_client_current_state(path: str) -> None:
    """memory/projects/*.md — only enforce on current-state region."""
    content = staged_content(path)
    lines = content.splitlines()
    cs_start = cs_end = None
    cs_date = None
    for i, line in enumerate(lines, 1):
        m = re.match(r"^## Current State as of (\d{4}-\d{2}-\d{2})", line)
        if m:
            cs_start = i
            cs_date = m.group(1)
            continue
        if cs_start and line.startswith("## "):
            cs_end = i - 1
            break
    if cs_start and cs_end is None:
        cs_end = len(lines)
    if cs_date is None:
        return  # no current-state header → not enforced
    if cs_date >= TODAY:
        return
    in_region = lambda ln: cs_start < ln <= cs_end
    excl = re.compile(r"^## Current State as of")
    if body_changed(path, exclude_re=excl, line_filter=in_region):
        errors.append(
            f"{path}: current-state region changed but "
            f"`## Current State as of {cs_date}` is older than today ({TODAY})"
        )


DECISION_RE = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*)?DECISION:", re.MULTILINE)


def check_decision_coupling(staged: list[str]) -> None:
    """Warn-only: a `DECISION:` line in a staged daily must travel with memory/STATE.md.

    The convention (see AGENTS.md § Session start): any change of priority / direction /
    blocker / money is logged in daily/ as a line starting with `DECISION:`. STATE.md is
    the mirror. A commit that carries the decision but not the mirror is how STATE rots —
    the same predicate that `scripts/state_freshness.py` checks at session start."""
    dailies = [p for p in staged if re.match(r"^memory/daily/[^/]+\.md$", p)]
    hits = [p for p in dailies if DECISION_RE.search(staged_content(p))]
    if hits and "memory/STATE.md" not in staged:
        warnings.append(
            f"{', '.join(hits)}: has a DECISION: line but memory/STATE.md is not in this "
            "commit — mirror the decision into STATE.md (or run /endday) so STATE stays true"
        )


_staged = staged_files()
for path in _staged:
    if path == "memory/STATE.md":
        check_simple_header(path, hard_block=True)
    elif re.match(r"^agent-os/agents/[^/]+/PROJECT_MAP\.md$", path):
        check_simple_header(path, hard_block=True)
    elif re.match(r"^agent-os/agents/[^/]+/STATUS\.md$", path):
        check_simple_header(path, hard_block=False)
    elif re.match(r"^memory/projects/[^/]+\.md$", path):
        check_client_current_state(path)
check_decision_coupling(_staged)


if warnings:
    print()
    print("⚠️  Staleness warnings (won't block):")
    for w in warnings:
        print(f"    {w}")

if errors:
    print()
    print("\U0001f6d1 BLOCKED — staleness check failed:")
    for e in errors:
        print(f"    {e}")
    print()
    print("Per AGENTS.md single-source-of-truth map: when body of a current-state")
    print(f"file changes, the header date must be bumped to today ({TODAY}) in the")
    print("same commit. Header and body drift if updated separately.")
    print()
    print("Fix: update the header date and `git add` the file again.")
    print("Bypass (only if intentionally preserving an old date):")
    print("    STALENESS_SKIP=1 git commit ...")
    print()
    sys.exit(1)

sys.exit(0)
