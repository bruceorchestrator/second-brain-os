#!/usr/bin/env python3
"""Stop tripwire: keep memory/STATE.md from going stale without anyone noticing.

Two modes, both wired in .claude/settings.json:

  --record  PostToolUse (Edit|Write). Notes when this session writes a file under
            memory/outputs/ or edits memory/STATE.md. Silent, always exits 0.
  --check   Stop. Before Claude ends its turn, nudges (exit 2 + stderr, which keeps Claude
            working on the message) when:
              1. STATE.md needs review by the freshness predicate in
                 .claude/scripts/state_freshness.py: a DECISION line nobody reviewed yet,
                 or STATE older than 14 days, or no `Last updated:` date; or
              2. this session wrote a report under memory/outputs/ and never touched
                 STATE.md (the report has the new facts, STATE keeps the old ones).

Why a per-session ledger: "dirty in git" or "modified in the last few hours" both lie when
several sessions share one checkout, because every session gets nudged for the others'
files. The ledger records only what this session's own Edit/Write calls did.

Loop safety: Claude Code sets `stop_hook_active` when the turn is already continuing because
of a Stop hook; the check then exits 0. Each reason fires at most once per session.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

OUTPUTS = "memory/outputs/"
STATE = "memory/STATE.md"


def project_root(start: str | None) -> Path | None:
    """The directory that holds memory/STATE.md: $CLAUDE_PROJECT_DIR, else walk up from start."""
    candidates = []
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        candidates.append(Path(os.environ["CLAUDE_PROJECT_DIR"]))
    here = Path(start or os.getcwd()).resolve()
    candidates.extend([here, *here.parents])
    for candidate in candidates:
        if (candidate / STATE).is_file():
            return candidate.resolve()
    return None


def _safe(session_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:80] or "default"


def ledger_path(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"claude-os-writes-{_safe(session_id)}"


def session_writes(session_id: str) -> list[str]:
    try:
        lines = ledger_path(session_id).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return list(dict.fromkeys(ln.strip() for ln in lines if ln.strip()))


def record(payload: dict) -> int:
    """PostToolUse recorder. Must never fail or slow down an edit."""
    try:
        raw = (payload.get("tool_input") or {}).get("file_path")
        root = project_root(payload.get("cwd"))
        if not raw or root is None:
            return 0
        path = Path(raw)
        if not path.is_absolute():
            path = Path(payload.get("cwd") or os.getcwd()) / path
        rel = path.resolve().relative_to(root).as_posix()
        if rel.startswith(OUTPUTS) or rel == STATE:
            with ledger_path(str(payload.get("session_id", "default"))).open("a", encoding="utf-8") as fh:
                fh.write(rel + "\n")
    except Exception:
        pass
    return 0


def _first_time(name: str, session_id: str) -> bool:
    """True the first time `name` fires in this session; a marker file remembers it."""
    marker = Path(tempfile.gettempdir()) / f"claude-os-nudged-{name}-{_safe(session_id)}"
    if marker.exists():
        return False
    try:
        marker.touch()
    except OSError:
        pass
    return True


def freshness_report(root: Path) -> str:
    """Rendered freshness verdict when STATE needs review, '' when fresh."""
    scripts = Path(__file__).resolve().parent.parent / "scripts"
    sys.path.insert(0, str(scripts))
    sys.dont_write_bytecode = True  # no __pycache__ (it stores this machine's absolute path)
    try:
        import state_freshness as sf
    except ImportError:
        return ""  # predicate not installed: nothing to check
    try:
        result = sf.check(root)
    except Exception as exc:  # a broken predicate must not trap the Stop hook
        return f"state_freshness failed: {type(exc).__name__}: {exc}"
    return sf.render(result) if (not result.get("ok") or result.get("stale")) else ""


def check(payload: dict) -> int:
    if payload.get("stop_hook_active"):
        return 0
    root = project_root(payload.get("cwd"))
    if root is None:
        return 0  # no memory/ in this project
    session_id = str(payload.get("session_id", "default"))

    report = freshness_report(root)
    if report and _first_time("freshness", session_id):
        print(
            "[STATE FRESHNESS] memory/STATE.md needs review:\n"
            f"{report}\n"
            "Compare the listed decisions with STATE.md, change only missing or contradicting facts, "
            "then acknowledge the reviewed IDs (or run /endday). If this session is not the place for it, "
            "say so in one line and stop. Do not rewrite STATE just to clear this message.",
            file=sys.stderr,
        )
        return 2

    written = session_writes(session_id)
    outputs = [p for p in written if p.startswith(OUTPUTS) and (root / p).exists()]
    if outputs and STATE not in written and _first_time("sync", session_id):
        sample = ", ".join(outputs[:3])
        print(
            f"[STATE SYNC] this session wrote {len(outputs)} file(s) under {OUTPUTS} (e.g. {sample}) "
            f"and did not touch {STATE}.\n"
            "If the report changes a priority, a status, a blocker or a number that STATE tracks, update "
            "STATE.md now (and add a DECISION line to today's daily file if it is a decision). "
            "If it does not, say so in one line and stop.",
            file=sys.stderr,
        )
        return 2
    return 0


def main(argv: list[str]) -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    if "--record" in argv:
        return record(payload)
    if "--check" in argv:
        return check(payload)
    print("usage: stop_tripwire.py --record | --check  (reads hook JSON on stdin)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
