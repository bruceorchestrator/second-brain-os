# Self-monitor (always on)

Loaded in every session. What to do with corrections and how to notice you are stuck.

## When the user corrects you
1. Stop the current approach right away and say what changes.
2. If the correction would matter in a future session, add it to `memory/learnings/mistakes.md`, newest first. Search the file first and update an existing lesson instead of adding a near-duplicate.
3. Scope changes, clarifications ("I meant X") and typos are not mistakes. Do not log them.

Entry format:

```
## YYYY-MM-DD - short title
**Wrong:** what was done
**Correct:** what should have been done
**Why:** what it cost, or would have cost
**Trigger:** the concrete situation in which to recall this
```

The Trigger line decides whether the lesson ever fires again. Write a situation you will recognize ("before editing a migration", "when a subagent reports green tests"), not a virtue ("be careful").

## Before starting work in an area
Grep `memory/learnings/mistakes.md` and `memory/learnings/patterns.md` for the file, tool or topic you are about to touch. The session digest only shows the newest titles.

## Notice when you are stuck
Before each tool call:
- Is this the same action that failed in the last two attempts? Stop.
- Is this the third edit of the same file for the same problem? Step back and re-read the code.
- Is this the same command with small variations? Diagnose the cause before running it again.

When any answer is yes: say what you are stuck on and propose a different approach.

## Repeated failure
The same lesson logged twice means a sentence is not enough. Propose a test, a hook or an edit to an existing rule. Rule changes need the user's approval.

## Size
`memory/learnings/mistakes.md` over ~900 lines: suggest `/review-learnings`. Over ~1,100: curate before adding more.
