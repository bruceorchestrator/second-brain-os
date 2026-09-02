#!/usr/bin/env python3
"""
state_freshness.py — is memory/STATE.md still the truth?

STATE.md is the command center every session reads first. It goes stale silently: a
decision gets written into memory/daily/ and nobody mirrors it into STATE. This script
turns "did priorities shift?" (a judgment call inside the model) into a predicate that
anything can run — a hook, a skill, a human, CI:

  STALE  <=>  a daily/ file dated after STATE's `Last updated:` contains a `DECISION:` line
         or   STATE is older than --max-age days (default 14)
         or   STATE has no parseable `Last updated: YYYY-MM-DD` header

Convention it depends on: any change of priority / direction / blocker / money is written
in daily/ as a line that starts with `DECISION:` (list marker and **bold** allowed):

    - **DECISION:** media-buying post deferred; acquisition Aug-Sep = LinkedIn proof-first

Same-day rule: a daily dated the same day as STATE counts only if it was modified after
STATE (mtime), so a decision logged after today's STATE bump is still caught, while a
fresh git checkout (equal mtimes) is not a false alarm.

Usage:
    python3 scripts/state_freshness.py            # human-readable, exit 1 if stale
    python3 scripts/state_freshness.py --quiet    # print only when stale (for context.sh)
    python3 scripts/state_freshness.py --json
    python3 scripts/state_freshness.py --root /path/to/repo --max-age 7

Exit codes: 0 fresh · 1 stale · 2 cannot check (no memory/STATE.md)
No dependencies. Works in Claude Code, Cowork (run by a skill), Cursor, CI.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

HEADER_RE = re.compile(r"^Last updated:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
DECISION_RE = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*)?DECISION:")
DAILY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
DEFAULT_MAX_AGE = 14


def find_root(start: Path) -> Path | None:
    """Walk up from `start` until a directory containing memory/STATE.md is found."""
    start = start.resolve()
    for p in (start, *start.parents):
        if (p / "memory" / "STATE.md").is_file():
            return p
    return None


def decisions_in(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if DECISION_RE.match(ln)]


def check(root: Path, today: date | None = None, max_age: int = DEFAULT_MAX_AGE) -> dict:
    """Pure predicate. Returns a dict; `stale` is the verdict, `reasons` say why."""
    today = today or date.today()
    state = root / "memory" / "STATE.md"
    if not state.is_file():
        return {"ok": False, "error": f"{state} not found"}

    text = state.read_text(encoding="utf-8", errors="ignore")
    result: dict = {
        "ok": True,
        "state_file": "memory/STATE.md",
        "state_date": None,
        "age_days": None,
        "max_age": max_age,
        "unmirrored": [],
        "reasons": [],
        "stale": False,
    }

    m = HEADER_RE.search(text)
    state_date: date | None = None
    if m:
        state_date = date.fromisoformat(m.group(1))
        result["state_date"] = state_date.isoformat()
        age = (today - state_date).days
        result["age_days"] = age
        if age > max_age:
            result["reasons"].append(f"STATE.md is {age} days old (limit {max_age})")
    else:
        result["reasons"].append("no `Last updated: YYYY-MM-DD` header in STATE.md")

    state_mtime = state.stat().st_mtime
    daily_dir = root / "memory" / "daily"
    dailies = sorted(daily_dir.glob("*.md")) if daily_dir.is_dir() else []
    for f in dailies:
        dm = DAILY_RE.match(f.name)
        if not dm:
            continue
        try:
            d = date.fromisoformat(dm.group(1))
        except ValueError:
            continue
        if state_date is not None:
            if d < state_date:
                continue
            if d == state_date and f.stat().st_mtime <= state_mtime:
                continue
        for line in decisions_in(f.read_text(encoding="utf-8", errors="ignore")):
            result["unmirrored"].append({"file": f"memory/daily/{f.name}", "line": line})

    if result["unmirrored"]:
        n = len(result["unmirrored"])
        result["reasons"].append(
            f"{n} DECISION line(s) in memory/daily/ after STATE's date are not mirrored"
        )

    result["stale"] = bool(result["reasons"])
    return result


def render(r: dict) -> str:
    if not r.get("ok"):
        return f"state_freshness: cannot check — {r.get('error')}"
    when = r["state_date"] or "?"
    age = r["age_days"] if r["age_days"] is not None else "?"
    if not r["stale"]:
        return f"STATE.md fresh — last updated {when} ({age} d), no unmirrored DECISION lines."
    out = [f"⚠️ STATE.md STALE — last updated {when} ({age} d)."]
    out += [f"  - {reason}" for reason in r["reasons"]]
    for u in r["unmirrored"]:
        out.append(f"  {u['file']}: {u['line'][:160]}")
    out.append(
        "Fix: mirror each DECISION into memory/STATE.md (focus / projects / revenue / "
        "constraints), bump `Last updated:` to today, re-run. Or run /endday."
    )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", help="repo root (default: walk up from cwd to find memory/STATE.md)")
    ap.add_argument("--max-age", type=int, default=DEFAULT_MAX_AGE, help="days before STATE is stale by age")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="print nothing when fresh")
    ap.add_argument("--today", help=argparse.SUPPRESS)  # YYYY-MM-DD, for tests
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    if root is None:
        print("state_freshness: no memory/STATE.md found above cwd (use --root)", file=sys.stderr)
        return 2
    today = date.fromisoformat(args.today) if args.today else None
    r = check(root, today=today, max_age=args.max_age)
    if not r.get("ok"):
        print(render(r), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif r["stale"] or not args.quiet:
        print(render(r))
    return 1 if r["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
