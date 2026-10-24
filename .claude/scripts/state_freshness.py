#!/usr/bin/env python3
"""
state_freshness.py - is memory/STATE.md still the truth?

STATE.md is the page every session plans from. It goes stale silently: a decision lands in
memory/daily/ and nobody carries it into STATE. This script turns "did priorities shift?"
into a predicate that a hook, a skill, a human or CI can run:

  NEEDS REVIEW <=> a tracked DECISION line has no review receipt yet
              or   STATE.md is older than --max-age days (default 14)
              or   STATE.md has no parseable `Last updated: YYYY-MM-DD` line

Convention: any change of priority, direction, blocker or money is written in a daily file
as a line that starts with `DECISION:` (a list marker and **bold** are allowed):

    - **DECISION:** Postgres over SQLite: team accounts need concurrent writes

Review receipts instead of file dates: an explicit acknowledgement stores
SHA-256(daily file name + DECISION line) in memory/state-receipts.json. Editing an
unrelated line of a daily file does not re-open reviewed decisions; a new or changed
DECISION line does. This detects pending review, not whether STATE says the right thing:
a person or the model still compares the facts.

Usage:
    python3 .claude/scripts/state_freshness.py              # human-readable, exit 1 if stale
    python3 .claude/scripts/state_freshness.py --quiet      # print only when stale
    python3 .claude/scripts/state_freshness.py --json
    python3 .claude/scripts/state_freshness.py --begin-review --json   # before editing STATE
    python3 .claude/scripts/state_freshness.py --acknowledge ID [ID ...]

Exit codes: 0 fresh, 1 stale, 2 cannot check (no memory/STATE.md, broken receipts).
Standard library only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

try:  # POSIX file locking; on Windows the acknowledgement simply runs unlocked
    import fcntl
except ImportError:  # pragma: no cover - platform dependent
    fcntl = None

HEADER_RE = re.compile(r"^Last updated:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
DECISION_RE = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*)?DECISION:")
DAILY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
DEFAULT_MAX_AGE = 14
RECEIPTS = "memory/state-receipts.json"


def find_root(start: Path) -> Path | None:
    """Walk up from `start` to the first directory that contains memory/STATE.md."""
    start = start.resolve()
    for p in (start, *start.parents):
        if (p / "memory" / "STATE.md").is_file():
            return p
    return None


def decisions_in(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if DECISION_RE.match(ln)]


def read_receipts(root: Path) -> dict:
    path = root / RECEIPTS
    if not path.exists():
        return {"version": 1, "reviewed": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("reviewed"), list):
        raise ValueError("invalid receipt schema")
    if not all(isinstance(x, str) and re.fullmatch(r"[a-f0-9]{64}", x) for x in data["reviewed"]):
        raise ValueError("invalid decision receipt IDs")
    if "tracking_since" in data:
        date.fromisoformat(data["tracking_since"])
    return data


def decision_records(root: Path):
    """Yield (day, record) for every DECISION line in memory/daily/YYYY-MM-DD*.md."""
    daily = root / "memory" / "daily"
    if not daily.is_dir():
        return
    for f in sorted(daily.glob("*.md")):
        match = DAILY_RE.match(f.name)
        if not match:
            continue
        try:
            day = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        filename = f"memory/daily/{f.name}"
        for line in decisions_in(f.read_text(encoding="utf-8", errors="ignore")):
            decision_id = hashlib.sha256(f"{filename}\n{line}".encode()).hexdigest()
            yield day, {"file": filename, "line": line, "id": decision_id}


def check(root: Path, today: date | None = None, max_age: int = DEFAULT_MAX_AGE) -> dict:
    """Pure predicate. `stale` is the verdict, `reasons` say why."""
    today = today or date.today()
    state = root / "memory" / "STATE.md"
    if not state.is_file():
        return {"ok": False, "error": f"{state} not found"}

    text = state.read_text(encoding="utf-8", errors="ignore")
    try:
        receipts = read_receipts(root)
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "error": f"invalid {RECEIPTS}: {exc}"}
    reviewed = set(receipts["reviewed"])
    pending: list[dict] = []
    result: dict = {
        "ok": True,
        "state_file": "memory/STATE.md",
        "state_date": None,
        "age_days": None,
        "max_age": max_age,
        "pending_decisions": pending,
        "reasons": [],
        "stale": False,
    }

    m = HEADER_RE.search(text)
    state_date: date | None = None
    if m:
        try:
            state_date = date.fromisoformat(m.group(1))
        except ValueError:
            return {"ok": False, "error": "invalid `Last updated:` date in STATE.md"}
        result["state_date"] = state_date.isoformat()
        age = (today - state_date).days
        result["age_days"] = age
        if age > max_age:
            result["reasons"].append(f"STATE.md is {age} days old (limit {max_age})")
    else:
        result["reasons"].append("no `Last updated: YYYY-MM-DD` line in STATE.md")

    cutoff = date.fromisoformat(receipts["tracking_since"]) if receipts.get("tracking_since") else state_date
    for day, record in decision_records(root):
        if (cutoff is None or day >= cutoff) and record["id"] not in reviewed:
            pending.append(record)

    if pending:
        result["reasons"].append(
            f"{len(pending)} DECISION line(s) need an explicit review against STATE.md"
        )

    result["stale"] = bool(result["reasons"])
    return result


def acknowledge(root: Path, ids: list[str], today: date | None = None) -> None:
    """Record only the IDs the caller actually reviewed. Never touches STATE.md itself.

    Called with an empty list (--begin-review) it pins `tracking_since` before STATE is
    edited, so bumping STATE's date afterwards cannot hide a pending decision."""
    memory = root / "memory"
    with (memory / ".state-receipts.lock").open("a") as lock:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        result = check(root, today=today)
        if not result["ok"]:
            raise ValueError(result["error"])
        if result["state_date"] is None:
            raise ValueError("STATE.md needs a valid `Last updated:` date before decisions can be acknowledged")
        receipts = read_receipts(root)
        records = {record["id"]: day for day, record in decision_records(root)}
        known = set(records) | set(receipts["reviewed"])
        if not set(ids) <= known:
            raise ValueError("unknown decision ID; read the current --json output first")
        cutoff = receipts.get("tracking_since", result["state_date"])
        receipts["tracking_since"] = min([cutoff] + [records[i].isoformat() for i in ids if i in records])
        receipts["reviewed"] = sorted(set(receipts["reviewed"]) | set(ids))
        with tempfile.NamedTemporaryFile(mode="w", dir=memory, prefix=".state-receipts-",
                                         delete=False, encoding="utf-8") as f:
            temp = Path(f.name)
            json.dump(receipts, f, indent=2)
            f.write("\n")
        try:
            os.replace(temp, memory / "state-receipts.json")
        finally:
            if temp.exists():
                temp.unlink()


def render(r: dict) -> str:
    if not r.get("ok"):
        return f"state_freshness: cannot check - {r.get('error')}"
    when = r["state_date"] or "?"
    age = r["age_days"] if r["age_days"] is not None else "?"
    if not r["stale"]:
        return f"STATE.md fresh - last updated {when} ({age} d), no DECISION lines waiting for review."
    out = [f"STATE.md NEEDS REVIEW - last updated {when} ({age} d)."]
    out += [f"  - {reason}" for reason in r["reasons"]]
    for d in r["pending_decisions"]:
        out.append(f"  {d['file']}: {d['line'][:160]} [id={d['id']}]")
    out.append(
        "Compare each line with STATE.md and change only missing or contradicting facts. Then record "
        "what you reviewed: .claude/scripts/state_freshness.py --acknowledge ID ... "
        "Never rewrite STATE just to clear this warning."
    )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Is memory/STATE.md still current?")
    ap.add_argument("--root", help="project root (default: walk up from cwd to memory/STATE.md)")
    ap.add_argument("--max-age", type=int, default=DEFAULT_MAX_AGE, help="days before STATE is stale by age")
    action = ap.add_mutually_exclusive_group()
    action.add_argument("--begin-review", action="store_true",
                        help="pin the review cutoff before editing STATE; acknowledges nothing")
    action.add_argument("--acknowledge", nargs="+", metavar="ID",
                        help="record reviewed decision IDs (does not edit STATE)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="print nothing when fresh")
    ap.add_argument("--today", help=argparse.SUPPRESS)  # YYYY-MM-DD, for tests
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    if root is None:
        print("state_freshness: no memory/STATE.md found above the current directory (use --root)", file=sys.stderr)
        return 2
    today = date.fromisoformat(args.today) if args.today else None
    if args.acknowledge or args.begin_review:
        try:
            acknowledge(root, args.acknowledge or [], today=today)
        except (OSError, ValueError, TypeError) as exc:
            print(f"state_freshness: cannot acknowledge - {exc}", file=sys.stderr)
            return 2
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
