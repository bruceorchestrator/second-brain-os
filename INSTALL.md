# Manual Install

For users who prefer not to use the AI-paste flow ([`INSTALL_PROMPT.md`](INSTALL_PROMPT.md)).

## Prerequisites

- A project (any tech stack — language, framework, scale all irrelevant to the pattern)
- An AI tool (Claude Code, Codex, Cursor, Aider, Windsurf — anything that reads markdown)
- Optional: git (Advanced Mode pre-commit hooks need it)

## Choose mode

**Simple Mode** — minimum viable. 19 files. Karpathy wiki + minimal live state (single `learnings.md`) + 5 core skills. 5-minute setup.

**Advanced Mode** — complete framework. ~70 files. Adds rules, agents, skills, hooks, governance, a lifecycle-split `learnings/` directory, and the `/mine-learnings` trace→learnings loop. 15-minute setup.

If unsure → start Simple. Graduate later by copying `full/agent-os/` over your existing setup.

## Simple Mode install

```bash
git clone https://github.com/bruceorchestrator/agent-os-starter
cp -R agent-os-starter/starter/. /path/to/your-project/
```

Then edit:

1. `your-project/memory/STATE.md` — replace Acme Notes priorities with yours; bump `Last updated:` to today
2. `your-project/memory/learnings.md` — keep the format spec, clear the example MISTAKES/WINS/PATTERNS
3. `your-project/memory/wiki/` — replace Acme example pages with your topics, OR delete them and start with empty `INDEX.md` (populate via `/ingest` later)
4. `your-project/memory/daily/` — delete the example day, your AI will create today's entry on first session
5. Open the project in your AI agent — it auto-loads `AGENTS.md` (or `CLAUDE.md`)

That's it. 19 files, ~5 minutes. The `agent-os/skills/` folder (morning / endday / ingest / lint / review-learnings) comes along with the copy and needs no edits.

### Keeping `STATE.md` honest (both modes)

`STATE.md` is the file every session reads first, and it is the file that rots first: a
decision gets written into `daily/` and nobody mirrors it. Two habits close that gap, and
neither needs hooks (so they work in Claude Cowork, Cursor and Codex too):

1. **Log decisions with the word.** Any change of priority / direction / blocker / money goes
   into `memory/daily/YYYY-MM-DD.md` as a line starting with `DECISION:` — `- **DECISION:** …`.
2. **Close working sessions with `/endday`.** Its STATE step is mechanical: grep `DECISION:` in
   dailies since STATE's `Last updated:` → mirror each into STATE → bump the date.

The rule the agent checks at session start: *STATE is stale if a `DECISION:` line exists in a
daily dated after STATE's `Last updated:`, or STATE is older than 14 days.* Advanced Mode runs
it for you (`scripts/state_freshness.py`, wired into the session context and the pre-commit
hook); Simple Mode states it in `CLAUDE.md` § Session start so the agent does it by eye.

## Advanced Mode install

```bash
git clone https://github.com/bruceorchestrator/agent-os-starter
cd /path/to/your-project/
bash /path/to/agent-os-starter/full/scripts/install.sh
```

The installer:

- Detects your AI tool
- Asks before overwriting any existing files (default = skip)
- Copies `memory/`, `agent-os/`, `adapters/`, `scripts/`
- Wires git hooks for the staleness check
- Prints next-step verification

After install:

1. **Verify:** `bash scripts/context.sh` — should print STATE + INDEX without errors. Until you bump `Last updated:` in `memory/STATE.md` it will open with a `STATE.md IS STALE` block — that is the freshness check working (`python3 scripts/state_freshness.py` runs it on its own; see "Keeping STATE.md honest" above)
2. **Check the budget:** `bash scripts/context_budget.sh` — shows what every session costs you (schema + always-on rules + session context) and warns if the session context has outgrown the harness cap. Re-run it whenever you add a rule or grow `memory/`. Past the cap the harness drops the *whole* payload and injects a short preview instead, so your project state stops loading with no error — this check is the only thing that surfaces it
3. **Replace example data** with your project's reality:
   - `memory/STATE.md` — your priorities
   - `memory/learnings/` — empty the Acme example entries from `mistakes.md` / `patterns.md` / `decisions.md` / `constraints.md` / `archive.md` (keep the format/intro blocks). Leave `inbox/learnings-candidates.md` as the empty queue
   - `memory/projects/` — delete Bluefin/Tessera, add yours (or leave empty)
   - `memory/wiki/` — delete sync-engine/billing-flows/etc., add yours (or empty `INDEX.md`)
   - `memory/outputs/specs/` and `outputs/research/` — delete the Acme samples
   - `memory/daily/` — delete the Acme example day
   - `agent-os/agents/backend-dev/PROJECT_MAP.md` — replace with your stack/dirs
4. **Try the trace→learnings loop:** `python scripts/mine_learnings.py --no-llm` mines your latest session transcript for candidate learnings (zero setup; review via `/mine-learnings`)
5. **Optional persona:** rename `agent-os/rules/identity.md.template` → `identity.md`, customize
6. **Optional personal context:** rename `memory/USER.md.template` → `USER.md`, fill in
7. **Open in your AI agent** — verify `AGENTS.md` is auto-loaded

## Customizing for your stack

The schema is stack-agnostic. Stack only appears in:

- `agent-os/agents/backend-dev/PROJECT_MAP.md` — has explicit `<!-- REPLACE WITH YOUR STACK -->` marker
- Optionally any rules you write yourself

Replace those with your stack. Everything else (rules, skills, hooks, schema) is universal.

## Tool-specific notes

| Tool | Auto-loaded | Extra files |
|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/settings.json` — written by `install.sh`, wires the session-start hook. Skipped if you already have one; merge the block from `agent-os/hooks/README.md` |
| Codex / OpenCode | `AGENTS.md` | none |
| Cursor | `.cursor/rules/main.mdc` (manual or via `install.sh`) | references `AGENTS.md` |
| Aider | `CONVENTIONS.md` (manual or via `install.sh`) | also `aider --read AGENTS.md` |
| Windsurf | `.windsurfrules` (manual or via `install.sh`) | references `AGENTS.md` |

We ship both `AGENTS.md` and `CLAUDE.md` (identical content) at root because different tools auto-load different files. No conflict.

## Troubleshooting

**My AI doesn't see `AGENTS.md`**
Different tools auto-load different files. We ship both `AGENTS.md` and `CLAUDE.md` at root — most tools pick one. If your tool needs a tool-specific entry (`.cursor/rules/`, `CONVENTIONS.md`, `.windsurfrules`), see `full/adapters/` or run `install.sh`.

**`bash scripts/context.sh` fails**
Likely `memory/STATE.md` doesn't exist yet. Make sure you copied the full `memory/` directory, or that you renamed the file correctly.

**Pre-commit hook blocks my commit**
The staleness check fired. Two paths:
- (a) bump the `Last updated:` date in the file you edited (the right move 95% of the time)
- (b) `STALENESS_SKIP=1 git commit ...` if you're intentionally preserving an old date

**Session context opens with `STATE.md IS STALE`**
Not an error — the freshness predicate found a `DECISION:` line in `memory/daily/` newer than
STATE's `Last updated:`, or STATE is older than 14 days. Mirror the listed decisions into
`memory/STATE.md`, bump the date, and `python3 scripts/state_freshness.py` prints `fresh`.
Fresh install: just bump the date after you replace the Acme example priorities.

**Multiple AI tools open in the same project**
Fine. They all read markdown; the schema is identical. Each tool picks its own auto-load file.

**Existing `memory/` directory at install time**
The installer asks: skip / merge (only new files) / backup-and-replace. Default is skip. Your existing notes are sacred.

## Uninstall

```bash
rm -rf memory/ agent-os/ AGENTS.md CLAUDE.md
# Plus tool-specific adapter files if you wired them
git config --unset core.hooksPath  # if you set it
```

The pattern is filesystem-only — no daemons, no installed binaries, no system integration to clean up.

## License

MIT.
