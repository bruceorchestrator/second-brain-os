# Routing (L1)

| Mode | Owner says | Stages | Output |
|---|---|---|---|
| Full run | "run twitter", "ideas for X about <topic>" | 01 -> 02 -> gate -> 03 | drafts file |
| Research | "what is going on with <topic>" | 01 | brief |
| Ideas | "give me post ideas" (no topic) | 02, from `memory/STATE.md`, the last 7 days of `memory/daily/` and the latest briefs | ideas file |
| Draft | "write a post about <idea>" | 03; check any unchecked fact in the idea first (01 on that fact only) | drafts file |
| Own story | the owner sends a few lines about something that happened | 03 with the owner's words kept | drafts file |

Files: `stages/01_research/output/YYYY-MM-DD_<topic>_brief.md`,
`stages/02_ideas/output/YYYY-MM-DD_ideas.md`, `stages/03_drafts/output/YYYY-MM-DD_drafts.md`.

## Gates
- **After 02:** the owner writes `keep` or `kill` next to each idea in the ideas file, or edits a hook. Stage 03 drafts only `keep` rows of the edited file.
- **After 03:** the owner edits and posts. The agent never does.

## After every run
- `log.md`: date, mode, output path; later, what the owner kept, changed or killed, and the post URL once it is live.
- `memory/daily/<today>.md`: one line with the output path.
