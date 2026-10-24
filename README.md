# Second Brain OS

A personal operating system for your AI agent, made of plain folders and markdown. Two parts:

- **`memory/`: one shared brain.** What you know, what you decided, what matters now, and what
  the AI learned from your corrections. Built on [Andrej Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
  sources are saved untouched, knowledge is compiled into linked topic pages, and the AI keeps it tidy.
- **`agents/`: one folder per job.** "I need Twitter research" becomes `agents/twitter/`: an
  identity file, a routing table, your voice and rules, and numbered stages (research, ideas,
  drafts), each with its own instructions and its own output folder. You check and edit the
  ideas before any draft is written. Nothing is posted or sent without your yes.

Agents read the shared memory and never keep their own copy of it, so what you teach the
system once reaches every agent.

```
memory/                       agents/
├── USER.md     who you are   ├── INDEX.md       the active agents
├── STATE.md    what matters  ├── README.md      how an agent folder works
├── daily/      what happened ├── _template/     copy this for a new agent
├── wiki/       what you know └── twitter/       a filled example
├── raw/        sources            ├── CLAUDE.md      who it is, what it never does
├── outputs/    reports            ├── CONTEXT.md     modes and gates
└── learnings/  lessons            ├── _config/       voice, rules, sources
                                   ├── stages/01_research, 02_ideas, 03_drafts
                                   └── log.md         every run and your verdict
```

## Set it up (about 20 minutes)
You need an AI coding agent that can read and write files and run commands.
[Claude Code](https://claude.com/claude-code) gets everything (skills, session hooks);
Codex, Cursor and others read `AGENTS.md` and follow the same files by hand. Plus git and
Python 3.9+.

**Option A.** Clone it and let the agent do the rest:
```bash
git clone https://github.com/bruceorchestrator/second-brain-os my-brain
cd my-brain
claude
```
Then say: *"Set up my second brain."*

**Option B.** Give your agent the link: *"Read https://github.com/bruceorchestrator/second-brain-os/blob/main/START_HERE.md and set up my second brain."*

Either way the agent follows [`START_HERE.md`](START_HERE.md): it asks you 8 questions about
you, your goals and the jobs you want AI to do, fills the memory with your answers, sorts the
jobs into agents and skills, builds your first agent, and checks that everything holds together.
It never invents your facts or your writing; what you do not tell it stays empty.

## Every day
| Say | What happens |
|---|---|
| `/morning` | what happened last time, your priorities, agents waiting for you, one first step |
| "run twitter" (or your agent's phrase) | the agent walks its stages and stops at the gate for your edits |
| "ingest <link>" | the source is saved and compiled into the wiki |
| `/new-agent` | a new job becomes a new folder, after you approve its stages |
| `/endday` | the day is logged, STATE is updated, lessons from your corrections are proposed |
| `/lint` | a health check of the memory and the agent folders |

## What keeps it honest
- `python3 .claude/scripts/check_os.py` checks the structure: wiki links, pages missing from
  the index, agent folders missing a stage contract, agents not registered.
- `python3 .claude/scripts/state_freshness.py` flags `STATE.md` when a decision in the daily log
  has not been carried into it, or when it is older than 14 days.
- A session-start hook gives the AI a digest of your memory and agents every time
  (Claude Code), and a stop hook reminds it when STATE fell behind.
- Tests: `python3 -B -m unittest discover -s .claude/tests`.

## Credits
- Memory: [Andrej Karpathy, LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
- Agents as folders: Interpretable Context Methodology by Jake Van Clief ([repo](https://github.com/RinDig/Interpretable-Context-Methodology-ICM-)).

Built by [Borys Puchkov](https://x.com/BorysPuchkov), founder of
[ChangesWithAI](https://changeswithai.com). This is the structure his own company runs on,
cleaned up for anyone to copy. The earlier `agent-os-starter` layout is kept under the git tag
`v1`. MIT license.
