---
paths:
  - "memory/**"
  - "agents/**"
  - "CLAUDE.md"
---

# Memory loop

Loads when the AI touches `memory/`, `agents/` or `CLAUDE.md`. It answers one question:
what else has to change so the files do not contradict each other?

## Layout
- `memory/raw/`: immutable copies of sources (`YYYY-MM-DD_slug.md`). Never edited.
- `memory/wiki/`: compiled knowledge, one page per topic, cross-linked as `[[topic-name]]`. Each page opens with a `>` summary and ends with `## Sources`. Catalog: `wiki/INDEX.md`.
- `memory/outputs/<type>/`: deliverables that belong to no agent.
- `memory/USER.md`: who the owner is. `memory/STATE.md`: what is current.
- `memory/daily/YYYY-MM-DD.md`: what happened, append-only.
- `memory/learnings/`: `mistakes.md` (active), `patterns.md` (promoted rules), `archive.md` (history).
- `agents/<name>/`: one folder per recurring job (`agents/README.md`), registered in `agents/INDEX.md`.

## One source of truth per fact
| Fact | Lives in | Elsewhere |
|---|---|---|
| Who the owner is, their audience | `USER.md` | agents read it; never copy it into an agent folder |
| Priorities, focus, blockers | `STATE.md` | link to it; do not restate |
| What happened and what was decided | `daily/` | STATE gets the current consequence, not the story |
| How something works, researched facts | `wiki/<topic>.md` | link with `[[topic]]` |
| How one recurring job is done | `agents/<name>/_config/` and its stage files | nowhere else |
| A run of that job | `agents/<name>/stages/*/output/` + a line in its `log.md` | one line in `daily/` with the path |
| Lessons | `learnings/` | never duplicated into CLAUDE.md or rules unless promoted on purpose |
| Hard limits, budget | `CLAUDE.md` § Hard limits | |

Two copies of a fact drift apart, and the next session believes the wrong one.

## Agent runs and memory
- After every agent run: one line in the agent's `log.md` and one line in today's daily file with the output path.
- A finding that matters beyond the job (a market fact, a tool, a person) goes to `memory/wiki/` too.
- The owner's edits to an agent's output go to its `log.md`; the same kind of edit twice becomes a rule in its `_config/`.
- A new agent folder, a retired one or a renamed one: update `agents/INDEX.md` in the same change. `python3 .claude/scripts/check_os.py` fails when the folder and the registry disagree.

## Decisions and STATE freshness
- Any change of priority, direction, blocker or money goes into today's daily file as a line starting with `DECISION:` (`- **DECISION:** ...`).
- `.claude/scripts/state_freshness.py` flags STATE when a DECISION line has not been reviewed yet, or STATE is older than 14 days. The session digest, `/morning`, `/endday` and the Stop tripwire all use this same check.
- Reconcile in this order: `--begin-review --json` before editing STATE (pins the baseline, acknowledges nothing); compare each pending line with STATE; change only missing or contradicting facts; then `--acknowledge ID ...` for exactly the IDs you compared.
- A pending decision means "needs comparison", not "STATE is wrong". Never acknowledge unread IDs and never rewrite priorities just to clear the warning.
- Receipts live in `memory/state-receipts.json`. Commit them together with the STATE change they belong to.

## Markers move with the body
A file with a freshness marker on top (`Last updated:`, `updated:` in wiki frontmatter) gets the marker bumped in the same edit that changes its current-state body. A date inside an old dated section is history: leave it.

## Scale the update to the change
| Change | Minimum memory update |
|---|---|
| New agent, new skill, new kind of file | daily (1-3 lines) + the registry or map that lists it |
| An agent run | its `log.md` + one daily line |
| A small fix or tweak | one daily line, or nothing if today's log already covers it |

## What deserves a written lesson
Record it when any of these is true:
- the owner corrected the approach, and it would matter in a future session;
- a tool or platform behaves differently from its documentation;
- a convention is non-obvious but load-bearing;
- a decision looks arbitrary but has a reason (a future session will want to undo it).

Do not record: "task done" (that is the daily log), anything already in CLAUDE.md or a rule, the obvious, one-off details.
