---
name: review-learnings
description: Curates memory/learnings/mistakes.md so it stays short enough to be read - proposes which repeated lessons to promote into patterns.md rules, which old ones to move to archive.md, and which near-duplicates to merge. Proposes only; every change waits for the user's yes per item. Use when the user says "review learnings", "curate learnings", "clean up mistakes", "promote patterns", or when mistakes.md passes about 900 lines.
allowed-tools: Read Grep Edit(memory/learnings/**) Bash(wc -l *) Bash(git log *)
---

# /review-learnings

A lessons file that nobody can read in one pass stops being read at all. This skill keeps
`memory/learnings/mistakes.md` dense: repeated lessons become one durable rule, old ones move
to the archive, nothing is ever deleted.

## The lifecycle
```
memory/daily/                  raw event log, append-only, never curated
memory/learnings/mistakes.md   active lessons, newest first, Wrong / Correct / Why / Trigger
memory/learnings/patterns.md   rules distilled from lessons that repeated
memory/learnings/archive.md    full original entries, searchable, not loaded into sessions
```

| mistakes.md size | What to do |
|---|---|
| under 500 lines | nothing |
| 500-900 | curate only if repeats or stale entries are visible |
| 900-1,100 | curation recommended |
| over 1,100 | curate before adding new lessons |

## Steps

### 1. Read
Read `mistakes.md` end to end and `patterns.md`. Note the line count (`wc -l`).

### 2. Classify every entry
- **Promote**: the same root cause appears in two or more entries with the same lesson. Draft one pattern that replaces them.
- **Archive**: the trigger situation has not come up for 60-90 days and the lesson is history rather than guidance. Keep at least the last 60 days of lessons active, whatever they look like.
- **Merge**: two or more entries describe the same incident class with no different lesson. Draft one entry that keeps the strongest specifics of each.
- **Keep**: everything else. One-off lessons stay where they are.

Before calling an old problem "resolved", check the code or `git log` for the fix. Do not trust
a narrative that says it was fixed.

### 3. Propose, then stop
```markdown
# Learnings review YYYY-MM-DD
Now: N lines, M lessons, P patterns.

## Promote
1. Lessons: <titles>
   Pattern:
   > **Rule:** ... **Trigger:** ... **Check:** ...
   Approve? (y/n)

## Archive
1. "YYYY-MM-DD - title" - why it is history now. Approve? (y/n)

## Merge
1. Lessons: <titles> -> merged text. Approve? (y/n)
```
Wait for a decision on each item. The user's judgment is the point of this skill.

### 4. Apply only what was approved
- **Promote**: add the pattern to `patterns.md`; move the source entries to `archive.md` verbatim (append, original dates kept).
- **Archive**: move the entry to `archive.md` verbatim.
- **Merge**: replace the entries in `mistakes.md` with the merged one; append the originals to `archive.md`.

Pattern format in `patterns.md`:
```markdown
## <rule name>
**Rule:** one or two sentences
**Trigger:** the concrete signals that should bring this rule to mind
**Check:** the command, file or question that proves it was followed
**Past incidents (archived):** YYYY-MM-DD one-line summary; YYYY-MM-DD one-line summary
```

### 5. Verify and report
- `wc -l` on all three files: the reduction matches what was approved, and archive.md grew by what left.
- Grep a few moved titles in `archive.md` to confirm the full text arrived.
- Report before and after: lines, lessons, patterns, and what moved where.

When moving many entries, prefer several targeted edits over rewriting the whole file at
once, and check the counts after each step. A single bulk rewrite is how a section gets
duplicated or lost.

## Never
- Apply anything without a per-item yes.
- Delete an entry. Moving to `archive.md` is the only way out.
- Promote a one-off. A pattern needs a real repeat.
- Compress a lesson until its Trigger is vague. The Trigger is what makes it fire again.
