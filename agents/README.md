# Agents as folders

An agent here is not a prompt file with a name. It is a folder the session walks through: a
short identity, a routing table, stable reference files, and numbered stages, each with its own
contract and its own output folder. Reading the folder is what turns a general session into that
agent, and the owner can open and edit every intermediate file. The method comes from
Interpretable Context Methodology (Jake Van Clief): the files carry the workflow, so the model
does not have to hold it, and each stage sees only the context it needs.

Not the same as Claude Code subagents (`.claude/agents/*.md`): a subagent is one prompt that
runs in a separate context. A folder here is a workspace the main session works inside.

## Folder, skill or nothing?
Ask three questions about the job:
1. Does it repeat (weekly or more often, or 5+ times) with the same steps on different input?
2. Is there a point where the owner must look and correct before the work goes on?
3. Is there stable reference (a voice, rules, sources) that is separate from each run's drafts?

| Answers | Build |
|---|---|
| three yes | an agent folder here |
| only question 1 | a skill: `.claude/skills/<name>/SKILL.md` |
| none | nothing; ask in chat when needed |

Do not create stages "for later". An empty stage is dead weight that every session has to read past.

## Anatomy
```
agents/<name>/
├── CLAUDE.md        L0  identity: what it produces, for whom, status, what it never does
├── CONTEXT.md       L1  routing: modes (owner says -> stages -> output) and gates
├── _config/         L3  STABLE reference that survives every run: voice.md, rules.md, sources.md
├── stages/
│   ├── 01_<verb>/   L2  CONTEXT.md: Inputs -> Process -> Outputs -> Gate -> Done when
│   │   └── output/  L4  RUN artifacts: YYYY-MM-DD_<slug>.md
│   ├── 02_<verb>/
│   └── 03_<verb>/
└── log.md               one line per run: output, the owner's verdict, the lesson
```
`memory/` is the shared L3 reference for every agent at once.
Start from `agents/_template/`; `agents/twitter/` is a filled example.

### Rules for each piece
- **CLAUDE.md**: under ~40 lines. Claude Code loads it when the session reads any file in the folder.
- **CONTEXT.md**: a table of modes. A mode may run a subset of stages ("draft this idea" skips research).
- **_config/**: only what survives runs. A file rewritten on every run belongs in a stage `output/`.
- **Stage CONTEXT.md**: must have `## Inputs`, `## Process` and `## Outputs`; `## Gate` where the owner approves; `## Done when` with a condition anyone can check. Inputs name exact paths.
- **Stage names**: two digits and a verb (`01_research`, `02_ideas`, `03_drafts`). Two to five stages; more usually means two jobs.
- **output/**: every file is an edit surface. The owner may change it before the next stage runs, and the next stage reads the edited file, not the chat.
- **log.md**: newest last, `| date | mode | output | owner verdict | lesson |`.

## Gates
A gate is the point where the owner approves before the work goes on.
- Put it **before the expensive stage**, not after it: editing a list of ideas takes a minute, rewriting five finished drafts takes an hour.
- Always a gate before anything leaves the machine (a post, a reply, an email, a payment) or spends money beyond the budget in `CLAUDE.md` § Hard limits.
- The agent never passes a gate alone, and a yes for one item is not a yes for the next.

## How agents use memory
| The agent needs | It reads | It writes |
|---|---|---|
| who the owner is, their audience | `memory/USER.md` | nothing; owner facts change only when the owner says so |
| what matters now | `memory/STATE.md` | nothing directly; a change of priority is a `DECISION:` line in today's daily |
| what is already known | `memory/wiki/` (INDEX first) | new knowledge that matters beyond this job: a wiki page, or `/ingest` for a source |
| how this job is done | its own `_config/` and stage files | the owner's corrections, once they repeat (learning loop below) |
| what happened | its own `log.md` | one line per run in `log.md` and one line in `memory/daily/<today>.md` |

Never copy memory files into an agent folder. Two copies drift, and the agent believes the old one.

## Learning loop
1. The owner edits or rejects an output: one line in `log.md` saying what changed.
2. The same kind of edit twice: move it into `_config/` (`voice.md`, `rules.md`) as a rule with an example.
3. A correction of the AI's behaviour that applies beyond this job: `memory/learnings/mistakes.md`.

## Lifecycle
- **New:** `/new-agent`. One at a time: build the job used most often, use it daily for a week or two, then build the next.
- **Manual first:** run an agent on request until it is used every day. Automate it (a schedule, a routine) only after that, and keep its gates.
- **Register:** one line per active agent in `agents/INDEX.md`.
- **Retire:** not run for 30+ days, or the owner says stop: move it to `agents/_archive/<name>/` and remove its INDEX line. Never delete.
- **Check:** `python3 .claude/scripts/check_os.py` validates every folder against this anatomy and the registry.
