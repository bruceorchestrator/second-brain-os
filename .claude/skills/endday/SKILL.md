---
name: endday
description: End-of-session handoff. Writes today's memory/daily/ log (actions, DECISION lines, insights, next steps), reconciles memory/STATE.md with any new decisions, drafts lessons from this session's corrections for approval, and reports what changed. Use when the user says "endday", "end of day", "wrap up", "let's stop here", "save context", "handoff", or before closing a long session.
allowed-tools: Read Grep Glob Edit(memory/**) Bash(python3 .claude/scripts/state_freshness.py *) Bash(git status *) Bash(git diff *) Bash(git log *)
---

# /endday

The next session starts from what this one writes down. A few minutes here saves the first
half hour tomorrow.

## Steps

### 1. Collect what happened
From this conversation and the repository:
- what was built, fixed, shipped or abandoned, and why;
- decisions: changes of priority, direction, blocker or money;
- non-obvious insights: a gotcha, a workaround, a platform quirk;
- what is next, and what is half-done.

Check the files with `git status --short`, `git diff --stat` and `git log --oneline -10`.
Every agent run today needs its line in that agent's `log.md`; add a missing one.
Work that is not committed is not saved: say so in the log.

### 2. Write today's daily file
Path: `memory/daily/YYYY-MM-DD.md` (today's date). If it exists from an earlier session today,
append to its sections; never rewrite what is already there.

```markdown
# YYYY-MM-DD

## Actions
- what was done, concretely: files, features, results; "not committed yet" where true

## Decisions
- **DECISION:** the change and the reason

## Insights
- something non-obvious learned today

## Next
- the first thing next session, with its first concrete step
```

The `DECISION:` prefix is literal: `.claude/scripts/state_freshness.py` looks for it and keeps
STATE.md flagged until the line has been reviewed. Use it for a change of priority, direction,
blocker or money, not for every small choice. Keep the file to 10-30 lines; a short session
gets a short log.

### 3. Reconcile STATE.md
1. `python3 .claude/scripts/state_freshness.py --begin-review --json` before editing STATE. It pins the review cutoff and acknowledges nothing.
2. For each entry in `pending_decisions`: is it already reflected in STATE? If yes, leave STATE alone. If not, change only the missing or contradicting part.
3. Bump `Last updated:` only after a real reconciliation.
4. Record exactly the IDs you compared: `python3 .claude/scripts/state_freshness.py --acknowledge <id> [<id> ...]`.
5. Run the check once more; it should print "fresh".

Never pick new priorities for the user to make STATE look current. If a decision needs the
user, ask. Script missing? Compare STATE's `Last updated:` with the `DECISION:` lines in daily
files dated on or after it, update STATE by hand, then bump the date.

### 4. Lessons from this session
Scan the conversation for:
- the user correcting your approach (not a scope change, not a clarification, not a typo);
- the same tool call failing two or more times for the same reason.

For each, draft an entry:
```
## YYYY-MM-DD - short title
**Wrong:** what was done
**Correct:** what should have been done
**Why:** what it cost, or would have cost
**Trigger:** the concrete situation in which to recall this
```
Search `memory/learnings/mistakes.md` first and update an existing lesson instead of adding a
twin. Show the drafts; write only the ones the user approves, newest first.

### 5. Report
One line per file changed, plus anything left uncommitted or unresolved:
```
daily/2026-10-24.md: 4 actions, 1 decision
STATE.md: Active work row for the twitter agent updated, decision acknowledged
agents/twitter/log.md: 2 runs logged, owner verdict on 8 ideas
mistakes.md: 1 lesson added (approved)
Uncommitted: agents/twitter/_config/voice.md
```

## Rules
- Do not touch files that did not change. Noise is worse than silence.
- Never invent progress. "Started", "blocked" and "not committed" are valid states.
- Never delete or rewrite earlier daily entries.
- No secrets, tokens or private personal data in any memory file.
