#!/usr/bin/env python3
"""SessionStart hook: start every session with a compact digest of memory/.

What Claude sees at the start of a session (in this order):
  0. a setup notice, only while memory/USER.md still holds FILL IN placeholders
  1. a STATE review warning, only when the freshness predicate says STATE needs review
  2. memory/STATE.md (trimmed)
  3. the last session: DECISION lines and "Next" lines of the newest memory/daily/ file
  4. the newest lessons from memory/learnings/mistakes.md (title + trigger) and pattern titles
  5. active agents from agents/INDEX.md (what each one does and how it is triggered)
  6. recent commits
  7. wiki topic names from memory/wiki/INDEX.md (what is already researched)

Why a budget: Claude Code caps the text a hook injects into context at 10,000 characters.
Past the cap, the text is saved to a file and replaced by its path plus a 2,000-character
preview, and Claude is not asked to read that file: the session quietly starts without its
context. The digest stays under BUDGET_CHARS; the untrimmed version is written to
.claude/.session-digest.txt in case something had to be cut.

Usage:
  hook:    prints {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ...}}
  manual:  python3 .claude/hooks/session_start.py --print
Standard library only. Python 3.9+.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

BUDGET_CHARS = 9000        # hard cap for the injected text (Claude Code's own cap is 10,000)
STATE_CHARS = 3500         # STATE.md beyond this is cut; keep STATE short instead
NEXT_LINES = 6             # "Next" lines from the newest daily file
MISTAKES = 3               # newest lessons shown
PATTERNS = 8               # pattern titles shown
COMMITS = 5
BACKUP = ".claude/.session-digest.txt"

DAILY_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}.*\.md$")
ENTRY = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\W*(.*)$")   # "## 2026-10-14 - title"
DECISION = re.compile(r"^\s*(?:[-*+]\s+)?(?:\*\*)?DECISION:")
WIKI_LINK = re.compile(r"\[\[([^\]]+)\]\]")
AGENT_LINE = re.compile(r"^\s*[-*]\s+`agents/[^/`]+/`")
NEXT_HEADINGS = {"next", "next steps", "tomorrow"}


def project_root() -> Path:
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "memory" / "STATE.md").is_file():
            return candidate
    return here


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def unfenced(text: str) -> list[str]:
    """Lines outside ``` code fences: format examples inside fences are not entries."""
    out, fenced = [], False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(ln)
    return out


def clip(text: str, limit: int, source: str) -> str:
    """Cut at a line boundary under `limit` characters and say where the rest is."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit("\n", 1)[0]
    return f"{cut}\n... (cut to fit; full text: {source})"


def section_setup(root: Path) -> str:
    user = re.sub(r"<!--.*?-->", "", read(root / "memory" / "USER.md"), flags=re.DOTALL)
    if "FILL IN" not in user:
        return ""
    return ("## SETUP NOT DONE - memory/USER.md is still a template\n"
            "Before anything else, tell the owner and follow START_HERE.md (interview, memory, first agent).")


def section_freshness(root: Path) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    sys.dont_write_bytecode = True  # no __pycache__ (it stores this machine's absolute path)
    try:
        import state_freshness as sf
        result = sf.check(root)
    except Exception:
        return ""  # predicate not installed or broken: the digest still loads
    if result.get("ok") and not result.get("stale"):
        return ""
    return ("## STATE NEEDS REVIEW - read this before planning from STATE\n"
            + clip(sf.render(result), 1500, "python3 .claude/scripts/state_freshness.py --json"))


def section_state(root: Path) -> str:
    text = read(root / "memory" / "STATE.md")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return "## STATE\n(memory/STATE.md is missing or empty: fill it in before planning)"
    return "## STATE (memory/STATE.md)\n" + clip(text, STATE_CHARS, "memory/STATE.md")


def section_last_session(root: Path) -> str:
    daily = root / "memory" / "daily"
    files = sorted(p for p in daily.glob("*.md") if DAILY_NAME.match(p.name)) if daily.is_dir() else []
    if not files:
        return ""
    latest = files[-1]
    lines = read(latest).splitlines()
    decisions = [ln.strip() for ln in lines if DECISION.match(ln)]
    nxt, inside = [], False
    for ln in lines:
        if ln.startswith("## "):
            inside = ln[3:].strip().lower() in NEXT_HEADINGS
            continue
        if inside and ln.strip():
            nxt.append(ln.rstrip())
    out = [f"## LAST SESSION (memory/daily/{latest.name})"]
    out += decisions[:5]
    if nxt:
        out.append("Next:")
        out += nxt[:NEXT_LINES]
    if len(out) == 1:
        out.append("(no decisions or next steps recorded)")
    return "\n".join(out)


def section_learnings(root: Path) -> str:
    entries, current = [], None
    for ln in unfenced(read(root / "memory" / "learnings" / "mistakes.md")):
        m = ENTRY.match(ln)
        if m:
            current = {"date": m.group(1), "title": m.group(2).strip(), "trigger": ""}
            entries.append(current)
        elif current and ln.startswith("**Trigger:**"):
            current["trigger"] = ln.split("**Trigger:**", 1)[1].strip()
    entries.sort(key=lambda e: e["date"], reverse=True)
    out = []
    if entries:
        out.append(f"## RECENT LESSONS (memory/learnings/mistakes.md, newest {min(MISTAKES, len(entries))} of {len(entries)})")
        for e in entries[:MISTAKES]:
            out.append(f"- {e['date']} {e['title']}")
            if e["trigger"]:
                out.append(f"  Trigger: {e['trigger']}")
    patterns = [ln[3:].strip() for ln in unfenced(read(root / "memory" / "learnings" / "patterns.md"))
                if ln.startswith("## ")]
    if patterns:
        out.append("## PATTERNS (memory/learnings/patterns.md): " + "; ".join(patterns[:PATTERNS]))
    return "\n".join(out)


def section_agents(root: Path) -> str:
    text = re.sub(r"<!--.*?-->", "", read(root / "agents" / "INDEX.md"), flags=re.DOTALL)
    lines = [ln.strip() for ln in text.splitlines() if AGENT_LINE.match(ln)]
    if not lines:
        return ""
    return clip("## AGENTS (agents/INDEX.md; read agents/<name>/CLAUDE.md before running one)\n"
                + "\n".join(lines), 2000, "agents/INDEX.md")


def section_commits(root: Path) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(root), "log", "--oneline", f"-{COMMITS}"],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0 or not proc.stdout.strip():
        return ""
    return "## RECENT COMMITS\n" + proc.stdout.strip()


def section_wiki(root: Path) -> str:
    topics = list(dict.fromkeys(WIKI_LINK.findall(read(root / "memory" / "wiki" / "INDEX.md"))))
    if not topics:
        return ""
    return clip("## WIKI TOPICS (already researched; read the page before researching again)\n"
                + ", ".join(topics), 1500, "memory/wiki/INDEX.md")


HEADER = ("# SESSION DIGEST (injected by .claude/hooks/session_start.py)\n"
          "Excerpts, not full files: open the source file before relying on a detail.")
FOOTER = f"--- end of digest. Untrimmed copy: {BACKUP}"


def build(root: Path) -> tuple[str, str]:
    """Return (digest within budget, full digest)."""
    if not (root / "memory").is_dir():
        text = HEADER + "\nNo memory/ directory here: follow START_HERE.md, or copy memory/ and agents/ from the kit."
        return text, text
    builders = [section_setup, section_freshness, section_state, section_last_session, section_learnings,
                section_agents, section_commits, section_wiki]
    sections = [s for s in (b(root) for b in builders) if s]
    full = "\n\n".join([HEADER, *sections, FOOTER])
    # Over budget: drop the least important sections from the end, then hard-cut.
    kept = list(sections)
    while kept and len("\n\n".join([HEADER, *kept, FOOTER])) > BUDGET_CHARS:
        kept.pop()
    digest = "\n\n".join([HEADER, *kept, FOOTER])
    if len(digest) > BUDGET_CHARS:
        digest = clip(digest, BUDGET_CHARS - 200, BACKUP)
    return digest, full


def main(argv: list[str]) -> int:
    if "--print" not in argv:
        sys.stdin.read()  # the SessionStart payload; nothing in it is needed here
    root = project_root()
    try:
        digest, full = build(root)
    except Exception as exc:  # never block a session start
        digest = full = f"{HEADER}\nDigest failed ({type(exc).__name__}: {exc}). Read memory/STATE.md manually."
    try:
        backup = root / BACKUP
        if backup.parent.is_dir():
            backup.write_text(full + "\n", encoding="utf-8")
    except OSError:
        pass
    if "--print" in argv:
        print(digest)
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": digest}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
