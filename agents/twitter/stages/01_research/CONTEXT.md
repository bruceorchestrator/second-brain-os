# Stage 01 - Research (L2)

## Inputs
- The topic from the owner's request; with no topic, the niche in `_config/sources.md`.
- `_config/sources.md`: where to look, accounts to watch, budget.
- `memory/wiki/INDEX.md` and the pages it lists on this topic: start from what is already known.
- `log.md`: briefs on the same topic from the last 14 days. Do not redo them; build on them.

## Process
1. Read the related wiki pages first. Note what is known and what is missing.
2. Search what happened on the topic in the last 7 days: news, launches, numbers, posts with unusual traction.
3. For every candidate finding, open the primary source. Record the date, what it says and the link.
4. Keep 5-10 findings. A finding you could not trace to a primary source is dropped, or kept and marked `unverified`.
5. For each finding, one line on why the owner's audience (`memory/USER.md` § Audience) would care.

## Outputs
`output/YYYY-MM-DD_<topic-slug>_brief.md`:
```
# Brief: <topic> (YYYY-MM-DD)

## Findings
1. <one-line finding> | <date> | <primary source link> | verified / unverified
   Why it matters: <one line>

## Already known (memory/wiki)
- [[page]]: <one line>

## Gaps
- <what could not be found or confirmed>
```

## Done when
- Every finding has a date, a link and a verified / unverified mark.
- A finding useful beyond X is added to `memory/wiki/`, or its source goes through `/ingest`.
