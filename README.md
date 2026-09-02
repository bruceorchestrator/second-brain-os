# agent-os-starter

> A concrete implementation of [Andrej Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), adapted for AI coding agents working in real codebases.

Drop this into your project so your AI agent has **persistent memory, behavioral discipline, and operational continuity** across sessions. Works with Claude Code, Codex, Cursor, Aider, Windsurf — any agent that reads markdown.

## Why Karpathy is credited

The foundational idea — **3-layer wiki** (raw / wiki / outputs) + **3 operations** (ingest / query / lint) — is Andrej Karpathy's. See his [LLM wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). All flowers to him.

He intentionally keeps the gist abstract and invites the community to instantiate it. This repo is one such instantiation, focused on the **working-codebase use case**, and adds:

- Live operational state (`STATE.md`, `projects/`, `daily/`, `learnings/`)
- Multi-domain agent state (4-file pattern: `STATUS` / `MEMORY` / `PROJECT_MAP` / `RULES`)
- A **trace → learnings loop** (`/mine-learnings`): mine a session transcript for corrections + repeated tool failures into a human-reviewed candidate queue
- Memory-loop scaling by commit class
- Mechanical governance (pre-commit staleness check, source-of-truth map)
- A **STATE freshness predicate** so `STATE.md` cannot rot silently: decisions are logged in `daily/` as `DECISION:` lines, and one rule — *a `DECISION:` after STATE's date, or STATE older than 14 days, means stale* — is checked by the session context, by `/endday`, and by the pre-commit hook. Works with zero hooks (Claude Cowork, Cursor, Codex) as a two-line reading rule in `CLAUDE.md`
- Tool adapters (Claude Code, Codex, Cursor, Aider, Windsurf)

The pattern is his. The packaging is one way to use it on real projects.

## Two modes

| | Simple Mode | Advanced Mode |
|---|---|---|
| Files | 19 | ~70 |
| Memory | single `memory/learnings.md` (MISTAKES / WINS / PATTERNS in one file) | `memory/learnings/` split by lifecycle (`mistakes` / `patterns` / `decisions` / `constraints` / `archive`) + `inbox/` candidate queue |
| Includes | `memory/`, `AGENTS.md`/`CLAUDE.md`, 5 core skills (`morning`, `endday`, `ingest`, `lint`, `review-learnings`) | + more skills incl. **`/mine-learnings`** (trace → learnings loop), `agent-os/{rules,agents,hooks}/`, `adapters/`, `scripts/` (incl. `mine_learnings.py` + tests) |
| Best for | Solo + 1–2 collaborators, getting started, personal knowledge wiki | Multi-person, multi-domain, governance needed |
| Setup time | 5 min (copy + adapt) | 15 min (`install.sh` + adapt) |

Both build on the same foundation. **Start Simple, graduate to Advanced when you outgrow it** — just copy `full/agent-os/` over your starter setup. The single `learnings.md` becomes the `learnings/` directory once it outgrows one file.

## Install

### Option A — paste-into-AI (recommended)

1. Open your existing project in your AI agent (Claude Code, Codex, Cursor, etc.)
2. Paste the contents of [`INSTALL_PROMPT.md`](INSTALL_PROMPT.md) into the chat
3. The AI inspects your project, picks Simple or Advanced, and installs the adapted version

### Option B — manual

```bash
git clone https://github.com/bruceorchestrator/agent-os-starter
cd /path/to/your-project/

# Advanced Mode (recommended for real projects)
bash /path/to/agent-os-starter/full/scripts/install.sh

# Or Simple Mode (just copy starter/ into your project)
cp -R /path/to/agent-os-starter/starter/. /path/to/your-project/
```

See [`INSTALL.md`](INSTALL.md) for the full manual walkthrough.

### Option C — copy what you want

Each piece is independent:

- Want only the wiki pattern? → copy `starter/memory/` + `starter/AGENTS.md`
- Want only the rules? → copy `full/agent-os/rules/`
- Want only the staleness check? → copy `full/scripts/git-hooks/`
- Want only "STATE.md never silently rots"? → copy `full/scripts/state_freshness.py` and adopt the `DECISION:` line convention in `daily/`

## When to use which mode

**Simple Mode** if:
- You're new to AI memory systems
- Project is small or solo
- You want minimum overhead

**Advanced Mode** if:
- You have a real team (or will soon)
- Multiple AI agents work in parallel
- Codebase has clear domain boundaries (backend / frontend / infra / data)
- You want pre-commit governance against drift

Either way, the foundation is the same Karpathy wiki. Advanced just adds discipline scaffolding.

## Tour

See [`EXAMPLE_TOUR.md`](EXAMPLE_TOUR.md) — 5-minute walkthrough of the fictional Acme Notes example, showing what changes for you day-to-day after the install.

## What this is NOT

- A code editor or IDE
- A code generator (your AI does that; agent-os just gives it persistent context)
- A focus / discipline tool (still on you to ship)
- A drop-in replacement for project management — agent-os is operational memory, not Linear/Jira

## Credits

- **[Andrej Karpathy's LLM wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** — the foundational pattern. All flowers to him.
- **[Anthropic Claude Code](https://docs.claude.com/claude-code)** — runtime primitives (CLAUDE.md, auto-loaded rules, skills, hooks) that make this pattern executable inside an AI coding agent.
- **This repo** — the adaptation: extending Karpathy's personal-knowledge wiki into operational state + agent state + governance + memory-loop discipline, so the pattern survives when applied to real projects with real deadlines and real agents.

## License

MIT. See [LICENSE](LICENSE).

## Status

Early days. Pattern is stable; specific files may evolve. Pin to a commit hash if reproducibility matters.

Issues and PRs welcome.
