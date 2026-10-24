---
name: lint
description: Health check of the second brain. Runs .claude/scripts/check_os.py (broken wiki links, pages missing from INDEX, missing summaries or sources, agent folders that break the anatomy, agents/INDEX.md out of sync), then reads flagged and sampled pages for stale claims, contradictions and missing links. Fixes the safe issues and lists the rest for the owner. Use when the owner says "lint", "check the memory", "health check", "audit the wiki", after a day with many ingests, or once a month.
allowed-tools: Read Grep Glob Edit(memory/wiki/**) Edit(agents/INDEX.md) Bash(python3 .claude/scripts/check_os.py *) Bash(git log *) Bash(mkdir *) Bash(touch *)
---

# /lint

The lint operation of Karpathy's LLM wiki, plus a check of the agent folders.

## 1. Mechanical
Run `python3 .claude/scripts/check_os.py` and read the whole output.

## 2. Read-through
Read every page the script flagged, plus 5 pages picked at random. Look for:
- time-sensitive claims ("currently", "this month", prices, versions) that may no longer hold;
- two pages that contradict each other;
- topic names in plain text that should be `[[links]]`;
- INDEX lines that no longer match the page.

For each active agent in `agents/INDEX.md`: stage Inputs that point to files that no longer
exist, and a `log.md` with no run for 30+ days (propose retiring it).

## 3. Fix
Safe without asking: a missing INDEX line (use the page's summary), a missing `updated:` (from
`git log -1 --format=%as -- <file>`), an obvious typo in a `[[link]]`, a missing `output/` folder.

Ask first: deleting or merging pages, rewriting a claim, resolving a contradiction, retiring an agent.
Never edit `memory/raw/`.

## 4. Report
```
Lint YYYY-MM-DD: N wiki pages, N agents
Fixed: ...
Needs you: 1. ... 2. ...
```
Run `check_os.py` again after the fixes and show its last line.
