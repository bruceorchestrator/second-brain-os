#!/usr/bin/env python3
"""check_os.py - does the second brain still match its own structure?

memory/
  - STATE.md and USER.md exist; STATE.md has a `Last updated: YYYY-MM-DD` line
  - wiki: every [[link]] in a wiki page or INDEX.md points to an existing memory/wiki/<name>.md
  - wiki: every page is listed in INDEX.md, has frontmatter with `topic:` and `updated:`,
    opens with a `>` summary and has a `## Sources` section
agents/
  - every folder except _template, _archive and dot folders has CLAUDE.md, CONTEXT.md, log.md,
    _config/ and stages/ with 1+ stage named NN_<verb>; every stage has CONTEXT.md with
    ## Inputs, ## Process and ## Outputs, and an output/ folder (_template is checked too)
  - agents/INDEX.md lists exactly the active folders
--after-setup (what START_HERE.md must leave behind)
  - no `FILL IN` and no `kit-example` marker left in CLAUDE.md, memory/ (outside raw/) or
    an active agent folder (outside its output/ folders)

Usage:
    python3 .claude/scripts/check_os.py [--root DIR] [--after-setup]
Exit codes: 0 OK, 1 issues found, 2 not a second-brain folder.
Standard library only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WIKI_LINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
STAGE_NAME = re.compile(r"^\d{2}_[a-z0-9][a-z0-9-]*$")
INDEX_LINE = re.compile(r"^\s*[-*]\s+`agents/([^/`]+)/`", re.MULTILINE)
LAST_UPDATED = re.compile(r"^Last updated:\s*\d{4}-\d{2}-\d{2}", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
STAGE_SECTIONS = ("Inputs", "Process", "Outputs")
AGENT_FILES = ("CLAUDE.md", "CONTEXT.md", "log.md")
NOT_AGENTS = {"_template", "_archive"}
PLACEHOLDER = "FILL IN"
EXAMPLE_MARKER = "kit-example"


def find_root(start: Path) -> Path | None:
    start = start.resolve()
    for p in (start, *start.parents):
        if (p / "memory").is_dir() and (p / "agents").is_dir():
            return p
    return None


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def without_code(text: str, inline: bool = False) -> str:
    """Drop HTML comments and ``` fenced blocks (and `inline code` when asked): format
    examples there are not content."""
    out, fenced = [], False
    for line in COMMENT.sub("", text).splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(INLINE_CODE.sub("", line) if inline else line)
    return "\n".join(out)


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    keys = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            keys[key.strip()] = value.strip()
    return keys


def body_after_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[end + 4:]
    return text


def check_memory(root: Path, issues: list[str]) -> dict:
    memory = root / "memory"
    state = read(memory / "STATE.md")
    if not state:
        issues.append("memory/STATE.md: missing or empty")
    elif not LAST_UPDATED.search(state):
        issues.append("memory/STATE.md: no `Last updated: YYYY-MM-DD` line")
    if not (memory / "USER.md").is_file():
        issues.append("memory/USER.md: missing")

    wiki = memory / "wiki"
    pages = {p.stem: p for p in sorted(wiki.glob("*.md")) if p.name != "INDEX.md"} if wiki.is_dir() else {}
    index_text = read(wiki / "INDEX.md")
    if not index_text:
        issues.append("memory/wiki/INDEX.md: missing or empty")
    listed = set(WIKI_LINK.findall(without_code(index_text, inline=True)))
    links = 0
    for name in sorted(listed - set(pages)):
        issues.append(f"memory/wiki/INDEX.md: [[{name}]] has no page memory/wiki/{name}.md")
    for name, path in pages.items():
        rel = f"memory/wiki/{path.name}"
        text = read(path)
        if name not in listed:
            issues.append(f"{rel}: not listed in memory/wiki/INDEX.md")
        front = frontmatter(text)
        for key in ("topic", "updated"):
            if not front.get(key):
                issues.append(f"{rel}: frontmatter has no `{key}:`")
        first = next((ln for ln in body_after_frontmatter(text).splitlines() if ln.strip()), "")
        if not first.startswith(">"):
            issues.append(f"{rel}: does not open with a `>` summary")
        if not re.search(r"^## Sources\b", text, re.MULTILINE):
            issues.append(f"{rel}: no `## Sources` section")
        for target in WIKI_LINK.findall(without_code(text, inline=True)):
            links += 1
            if target not in pages:
                issues.append(f"{rel}: [[{target}]] has no page memory/wiki/{target}.md")
    return {"pages": len(pages), "links": links}


def check_agent(folder: Path, root: Path, issues: list[str]) -> None:
    rel = folder.relative_to(root).as_posix()
    for name in AGENT_FILES:
        if not (folder / name).is_file():
            issues.append(f"{rel}/: no {name}")
    if not (folder / "_config").is_dir():
        issues.append(f"{rel}/: no _config/ folder")
    stages_dir = folder / "stages"
    stages = sorted(p for p in stages_dir.iterdir() if p.is_dir()) if stages_dir.is_dir() else []
    if not stages:
        issues.append(f"{rel}/: no stages/NN_<verb>/ folder")
    for stage in stages:
        srel = f"{rel}/stages/{stage.name}"
        if not STAGE_NAME.match(stage.name):
            issues.append(f"{srel}/: stage name must be NN_<verb> (two digits, lowercase)")
        contract = read(stage / "CONTEXT.md")
        if not contract:
            issues.append(f"{srel}/: no CONTEXT.md")
        else:
            for section in STAGE_SECTIONS:
                if not re.search(rf"^##\s+{section}\b", contract, re.MULTILINE):
                    issues.append(f"{srel}/CONTEXT.md: no `## {section}` section")
        if not (stage / "output").is_dir():
            issues.append(f"{srel}/: no output/ folder")


def check_agents(root: Path, issues: list[str]) -> list[str]:
    agents = root / "agents"
    folders = sorted(p for p in agents.iterdir() if p.is_dir() and not p.name.startswith("."))
    active = [p for p in folders if p.name not in NOT_AGENTS]
    template = agents / "_template"
    if template.is_dir():
        check_agent(template, root, issues)
    else:
        issues.append("agents/_template/: missing (new agents are copied from it)")
    for folder in active:
        check_agent(folder, root, issues)

    index_text = read(agents / "INDEX.md")
    if not index_text:
        issues.append("agents/INDEX.md: missing or empty")
    registered = set(INDEX_LINE.findall(without_code(index_text)))
    names = {p.name for p in active}
    for name in sorted(names - registered):
        issues.append(f"agents/{name}/: not registered in agents/INDEX.md")
    for name in sorted(registered - names):
        issues.append(f"agents/INDEX.md: lists agents/{name}/, which does not exist")
    return sorted(names)


def leftovers(root: Path, agents: list[str]) -> list[str]:
    """FILL IN placeholders and kit-example markers that setup should have replaced."""
    files = [root / "CLAUDE.md"]
    files += [p for p in sorted((root / "memory").rglob("*.md")) if "raw" not in p.relative_to(root / "memory").parts]
    for name in agents:
        files += [p for p in sorted((root / "agents" / name).rglob("*.md")) if "output" not in p.parts]
    found = []
    for path in files:
        text = read(path)
        rel = path.relative_to(root).as_posix()
        if EXAMPLE_MARKER in text:
            found.append(f"{rel}: example content left (`{EXAMPLE_MARKER}` marker)")
        count = without_code(text).count(PLACEHOLDER)
        if count:
            found.append(f"{rel}: {count} `{PLACEHOLDER}` left")
    return found


def run(root: Path, after_setup: bool = False) -> tuple[list[str], dict]:
    issues: list[str] = []
    stats = check_memory(root, issues)
    stats["agents"] = check_agents(root, issues)
    if after_setup:
        issues += leftovers(root, stats["agents"])
    return issues, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check the second brain's structure.")
    ap.add_argument("--root", help="folder holding memory/ and agents/ (default: walk up from cwd)")
    ap.add_argument("--after-setup", action="store_true",
                    help="also fail on FILL IN placeholders and kit-example content left behind")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    if root is None or not (root / "memory").is_dir() or not (root / "agents").is_dir():
        print("check_os: no folder with memory/ and agents/ found (use --root)", file=sys.stderr)
        return 2
    issues, stats = run(root, after_setup=args.after_setup)
    agents = ", ".join(stats["agents"]) or "none"
    print(f"memory: {stats['pages']} wiki page(s), {stats['links']} link(s)")
    print(f"agents: {len(stats['agents'])} active ({agents})")
    if issues:
        print(f"ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
        print(f"{len(issues)} issue(s)")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
