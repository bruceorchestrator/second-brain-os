# Acme Notes — AI Agent Schema (Advanced Mode)

> Control plane for the agent-os pattern: memory protocol, agent dispatch, source-of-truth map, and pointers to rules/skills/hooks. Based on [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), extended with operational state and governance for working codebases.

This file is a router. It tells your AI agent **what to read, when, and where things live** — not the full content of rules. Detailed policies live in `agent-os/rules/`. Workflows live in `agent-os/skills/`. Domain ownership lives in `agent-os/agents/`.

## If you are an AI agent installing this into an existing project

1. Copy this schema and the `memory/` + `agent-os/` + `scripts/` layout into the target repo.
2. Preserve existing project files — never overwrite or delete without asking the user first.
3. Replace the Acme Notes example content with the user's real project context (priorities, learnings, wiki topics, agent definitions).
4. Run `bash scripts/install.sh` (or the equivalent for the user's tool) to wire up adapters and git hooks.

---

## Identity

Optional persona layer. If `agent-os/rules/identity.md` exists (renamed from `.template`), read it for the AI's name, tone, and behavioral defaults. Otherwise use neutral defaults: helpful, peer-to-peer, concise.

Communication preferences live in `agent-os/rules/language.md` (also `.template` until renamed).

---

## Memory protocol

### Three layers (Karpathy) + live state

| Path | Purpose | Mutability |
|---|---|---|
| `memory/raw/` | Immutable source dumps (articles, transcripts, scrapes) | Never edit, never rename |
| `memory/wiki/` | Topic pages, cross-linked via `[[topic-name]]` | LLM-maintained |
| `memory/outputs/` | Generated deliverables (specs, research, drafts) | Append + iterate |
| `memory/STATE.md` | Current priorities, blockers | Mirror of every `DECISION:` in daily/; `scripts/state_freshness.py` flags it stale otherwise |
| `memory/learnings/` | `mistakes` / `patterns` / `decisions` / `constraints` / `archive` | Append `mistakes.md`; curate the rest |
| `memory/projects/*.md` | Per-project / per-client live state | Update as relationships evolve |
| `memory/inbox/` | Un-triaged capture + the `/mine-learnings` review queue | Drained as you triage |
| `memory/daily/*.md` | Append-only event log per day; any change of priority / direction / blocker / money is a line starting with `DECISION:` | New section per session |
| `memory/INDEX.md` | Navigation map | Update on structural changes |

### Operations

Three operations from Karpathy's pattern, implemented as skills:

- **Ingest** → `agent-os/skills/ingest/SKILL.md` — reflexive on URL/file/text share
- **Query** — implicit; read `memory/wiki/INDEX.md` first, drill from there
- **Lint** → `agent-os/skills/lint/SKILL.md` — periodic wiki health check

### Session start protocol

Read in order at the start of every session:

1. `memory/STATE.md` — current priorities and blockers. **Check it is still true before acting on it:** `python3 scripts/state_freshness.py` (the Claude Code session hook runs it for you and prints a `STATE.md IS STALE` block first; in tools without hooks — Cowork, Codex, Cursor — run it, or do it by eye: STATE's `Last updated:` vs. any later daily with a `DECISION:` line, or >14 days old). Stale → mirror the listed decisions into STATE.md and bump the date first. No judgment: a date compare and one grep
2. `memory/learnings/mistakes.md` — past corrections (the hot file; read every session)
3. `memory/INDEX.md` + `memory/wiki/INDEX.md` — navigation maps
4. Latest `memory/daily/*.md` — recent events
5. `memory/projects/<active>.md` if a specific project/client is in scope

This is the minimum context to act. Don't re-read the whole wiki; drill from the indexes.

---

## Single source of truth

When a fact lives in multiple places, the table below defines which is authoritative. Mirrors must update in the same commit, never independently.

| Fact | Authoritative source | Read-only mirrors |
|---|---|---|
| Project priorities | `memory/STATE.md` | client files reference it |
| Client live snapshot | `memory/projects/<name>.md` | STATE.md row summarizes |
| Code paths + responsibilities | `agent-os/agents/<name>/PROJECT_MAP.md` | — |
| Agent operational status | `agent-os/agents/<name>/STATUS.md` | client/STATE rows summarize |
| Today's events | `memory/daily/YYYY-MM-DD.md` | STATUS event line cross-references |
| Permanent learnings | `memory/learnings/` (mistakes / patterns / decisions / constraints / archive) | — |
| Learning candidates (un-promoted) | `memory/inbox/learnings-candidates.md` (`/mine-learnings` queue) | promoted into `learnings/` only after review |

**Rule:** when you touch one source, scan its mirrors for stale markers and bring them along in the same commit. Test counts, status flags, deadline dates, and "as of YYYY-MM-DD" markers drift fastest.

The pre-commit hook (`scripts/git-hooks/check-staleness.py`) hard-blocks commits where a current-state file's body changed but the date marker is stale, and warns when a staged daily carries a `DECISION:` line without `memory/STATE.md` in the same commit.

**STATE freshness is one predicate in three places** — `scripts/state_freshness.py`: stale ⇔ a `DECISION:` line in daily/ after STATE's `Last updated:`, or >14 days. The session-start context prints it first, `/endday` step 2 enforces it, the pre-commit hook couples the two files. "Update STATE if priorities shifted" was a judgment that never fired; this is a date compare and a grep.

---

## Behavioral rules

Auto-loaded policies. Read each rule when its trigger context applies.

| Rule | When to consult | File |
|---|---|---|
| Verification before completion | Always — non-negotiable IRON LAW | `agent-os/rules/quality-gate.md` |
| Plan mode for multi-stage tasks | Tasks with 3+ stages | `agent-os/rules/quality-gate.md` §1 |
| Bug-fix protocol (test-first) | Any bug report | `agent-os/rules/quality-gate.md` §4 |
| Agent dispatch + memory loop | When dispatching subagents | `agent-os/rules/agent-quality.md` |
| Self-correction → learnings/mistakes.md | Any user correction | `agent-os/rules/self-monitor.md` |
| Test requirements | Engines, validators, security boundaries, bugs | `agent-os/rules/testing.md` |
| File-size triggers | Before adding code to existing files | `agent-os/rules/file-size-triggers.md` |
| LLM cost discipline | When designing LLM pipelines | `agent-os/rules/cost-aware-llm.md` |

Rules are policy. Don't restate them — refer to them.

---

## Agent dispatch

| Task scope | Agent | When NOT to use |
|---|---|---|
| `api/`, `sync/`, `db/migrations/`, `lib/billing/` | `backend-dev` | Frontend work; cross-cutting refactors |
| Trivial fixes, single-file edits | (main agent) | Multi-file structural changes |
| Cross-domain refactors | (main agent — orchestrate) | When scope is purely single-domain |

Each domain agent maintains 4 files in `agent-os/agents/<name>/`: STATUS, MEMORY, PROJECT_MAP, RULES. See `agent-os/agents/README.md`.

**Size gate (hard rule):** ≤ 10 lines / 1 file → never dispatch an agent. Multi-file or >30 lines or deploy pipeline → dispatch the matching specialist. 10–30 lines → judgment.

---

## Skills

Reusable workflows. Invoked by trigger phrase or `/skill-name`.

| Skill | Trigger | What it does |
|---|---|---|
| `/morning` | Start of day, "morning" | Load context, propose plan |
| `/endday` | End of day, "wrap up" | Save context for next session |
| `/ingest` | URL/file/text shared | Karpathy ingest → raw/ + wiki/ + daily/ |
| `/lint` | "lint", "audit memory" | Wiki health check (mechanical + semantic) |
| `/create-spec` | "spec", before 2+ hour task | Generate structured spec → outputs/specs/ |
| `/call-debrief` | Transcript pasted, audio dropped | Extract decisions/actions → outputs/call-debriefs/ |
| `/web-researcher` | "research", "investigate", "compare" | Multi-source research → outputs/research/ |
| `/create` | "make a skill", "automate this" | Bootstrap new skill or agent |
| `/swarm` | "parallel agents", "decompose" | Multi-agent task decomposition |
| `/review-learnings` | "review learnings", file > target size | Curate `learnings/` — promote to patterns, archive stale |
| `/mine-learnings` | "mine learnings", end of session | Mine the session transcript → candidate learnings into the review queue (human-approved before promotion) |

See `agent-os/skills/README.md` and individual `SKILL.md` files for full procedures.

---

## Hooks

Runtime enforcement. Fire automatically at events.

| Hook | When | What |
|---|---|---|
| `session-start.sh` | Session start | Auto-loads `STATE.md` + recent context via `scripts/context.sh` |
| `commit-memory-reminder.sh` | After successful `git commit` | Nudges memory updates per commit class |
| `scripts/git-hooks/pre-commit` | Before `git commit` | PII block + staleness check (hard-blocks 3 patterns) |

See `agent-os/hooks/README.md` and `scripts/git-hooks/README.md` for wiring.

---

## File-size discipline

Before adding code to an existing file, run `wc -l <file>`:

- < 500 lines → edit freely
- 500–1000 → ask user about split if introducing new concern
- 1000–2000 → no new features without explicit approval
- > 2000 → stop, decompose first

Full rule + cohesion exceptions: `agent-os/rules/file-size-triggers.md`.

---

## References

- **[Karpathy's LLM wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** — the foundational pattern
- **[agent-os-starter](https://github.com/bruceorchestrator/agent-os-starter)** — this repo
- **`memory/INDEX.md`** — top-level navigation
- **`agent-os/rules/`** — behavioral policies (read on demand, per the rules table above)
- **`agent-os/skills/`** — workflows (invoked by trigger or slash command)
- **`agent-os/agents/`** — domain specialists with persistent state

---

## When to update this file

Add to AGENTS.md ONLY when:

- A new agent is added to dispatch map
- A new rule warrants a row in the rules table
- A new skill is added to skills routing
- The source-of-truth map needs a new fact

DO NOT add to AGENTS.md:

- Rule content (lives in `agent-os/rules/<name>.md`)
- Skill procedures (lives in `agent-os/skills/<name>/SKILL.md`)
- Code examples
- Detailed conventions

Keep this file under 250 lines. If it grows past that, extract content into the layered system below it.
