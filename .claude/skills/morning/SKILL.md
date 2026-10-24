---
name: morning
description: Start-of-day briefing. Checks that memory/STATE.md is still current, then shows what happened last session, the top priorities, blockers, agents waiting for the owner at a gate, and one concrete first step. Use when the user says "morning", "good morning", "start the day", "what's the plan", "where were we", "what's next", or at the start of a working session.
allowed-tools: Read Grep Glob Bash(python3 .claude/scripts/state_freshness.py *) Bash(git log *) Bash(git status *) Bash(wc -l *) Bash(ls *)
---

# /morning

A 15-line briefing that starts the day from current facts, not from a stale page.

## Steps

1. **Freshness first.** Run:
   ```bash
   python3 .claude/scripts/state_freshness.py --begin-review --json
   ```
   - `"stale": false`: go on.
   - `"stale": true`: read `reasons` and `pending_decisions`. Compare each pending DECISION line with `memory/STATE.md`. Fix only facts that are missing or contradicted, then record the IDs you compared:
     ```bash
     python3 .claude/scripts/state_freshness.py --acknowledge <id> [<id> ...]
     ```
     If STATE is stale only by age, ask the user whether the focus still holds before planning from it. Never change priorities on your own to clear the warning.
   - Script missing? Do the same check by eye: STATE's `Last updated:` date against any `DECISION:` line in `memory/daily/` files dated on or after it, and STATE older than 14 days means review.
2. **Read `memory/STATE.md`.**
3. **Read the newest file in `memory/daily/`**: what happened, which decisions were made, what was planned next. No file from the last few days: say so; do not invent a yesterday.
4. **Agents:** for each line in `agents/INDEX.md`, read the last rows of its `log.md` and list its newest `stages/*/output/` files. Mention an agent waiting at a gate (an output with no owner verdict in `log.md` yet) and one not run for 7+ days. Then `git status --short`: anything left uncommitted from last time.
5. **Learnings size:** `wc -l memory/learnings/mistakes.md`. Over 900 lines: add one line suggesting `/review-learnings`. Over 1,100: say curation is due before new lessons go in.

## Output

```
## Morning

Last session: <2-3 bullets from the newest daily file>
Priorities: <top 3 from STATE, each with its next action>
Blockers: <from STATE, or "none">
Agents: <waiting at a gate, or not run lately; only if any>

Start with: <one task, why it comes first, and the first concrete step>
```

## Rules
- At most 15 lines. No filler.
- Recommend one task with a reason, not a menu of five.
- Resolve the freshness warning before planning; comparing facts comes before acknowledging IDs.
- Do not start working on the task until the user says go.
