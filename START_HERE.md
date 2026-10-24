# START HERE: set up this second brain

For the AI agent. The owner gave you this repository to set up their personal operating
system: one shared memory (`memory/`) and one folder per recurring job (`agents/`). Read
`CLAUDE.md`, `agents/README.md` and `memory/wiki/llm-wiki-pattern.md` first, then follow the
steps in order. Talk to the owner in the language they write in. Files the AI reads as
instructions stay in English; the owner's facts are written in their own words.

It takes about 20 minutes, most of it the owner answering questions. Nothing here posts,
sends or pays for anything.

## 0. Find where you are
| Situation | Do |
|---|---|
| You are inside a clone of this repository (`START_HERE.md` and `agents/_template/` are here) | Set up right here. Run `git remote -v`. If `origin` points to the public kit (`second-brain-os`), run `git remote remove origin` and tell the owner why: their memory must never be pushed to the public kit. They can add their own private remote later. |
| You only have the link | Ask where the system should live (suggest `~/second-brain`), then `git clone https://github.com/bruceorchestrator/second-brain-os <folder>` and continue there as in the row above. Tell the owner to open that folder in their AI tool from now on. |
| The owner wants it inside a folder that already has files | Copy without overwriting: `rsync -a --ignore-existing --exclude .git <kit>/ <folder>/`. If the folder already had `CLAUDE.md` or `.claude/settings.json`, merge sections and hook entries instead of replacing them, and show the owner the result. |

Then check `python3 --version`: 3.9 or newer is all the checks and hooks need.

## 1. Interview (one message)
Ask everything below in a single numbered message and say short answers or a voice note are
fine. Skip anything the owner already told you.
1. Your name, and how should I address you?
2. What do you do? Work, business, projects, in 2-3 lines.
3. Who is your audience or customer, if you have one?
4. What matters most in the next 1-3 months? Top 3, with dates if there are any.
5. What do you want AI to do for you? List the jobs in your own words ("research Twitter and pitch post ideas in my voice", "sort my email every morning", "prepare me for calls").
6. Which accounts and tools are involved (X, Telegram, Gmail, Notion...)? Names only, never passwords.
7. What must I never do without asking you? By default nothing gets posted, sent, paid for or deleted without your yes. What is your monthly budget for paid tools?
8. If a job writes in your name: where can I read 5-10 things you wrote and liked?

Wait for the answers. Ask a follow-up only where an answer blocks a step.

## 2. Fill the memory
Write only what the owner said. What they did not say stays `FILL IN` or is left out.
- `memory/USER.md`: answers 1, 2, 3, 5, 6. Leave § How they like to work empty: it fills over time from the owner's corrections. Set `Last updated:` to today.
- `CLAUDE.md`: § Owner (two lines and the chat language) and § Hard limits (answer 7).
- `memory/STATE.md`: replace every example line. Focus = answer 4. Active work = the agent you are about to build. `Last updated:` today. Remove the `kit-example` marker.
- `memory/daily/<today>.md`: what was set up, plus a `- **DECISION:** ...` line for the focus and one for which agent goes first.
- `memory/wiki/`: a page only for durable knowledge the owner gave (their business, their audience), with `## Sources` saying "the owner, setup interview, <date>", and a line in `wiki/INDEX.md`. Keep `llm-wiki-pattern.md`.
- Delete the examples: `memory/daily/2026-10-23.md`, and the example entry plus its marker in `memory/learnings/mistakes.md` (keep the format comment at the top).

## 3. Sort the jobs
Put every job from answer 5 through the test in `agents/README.md` § Folder, skill or nothing,
and show the owner a table:

| Job | Build (agent folder / skill / nothing) | Why | Order |

Recommend building **one** agent now: the job they will use most often. The others go to
STATE.md § Not now until the first one is used daily. Wait for the owner's OK.

## 4. Build the first agent
Follow `.claude/skills/new-agent/SKILL.md` (`/new-agent` in Claude Code). You already have most
of its interview; ask only what is missing.
- An X / Twitter job: adapt `agents/twitter/` instead of starting from the template. Fill `_config/voice.md` with the owner's real posts, `_config/sources.md` with their niche and accounts, the red list from their answers, and remove the `kit-example` marker.
- No X / Twitter job: delete `agents/twitter/` and its line in `agents/INDEX.md`.
- Never delete `agents/_template/`.
- A job that came out as a skill in step 3: `.claude/skills/<name>/SKILL.md` with `name` and `description` frontmatter, if the owner wants it now.

## 5. Verify
Run each command and read the whole output:
```bash
python3 .claude/scripts/check_os.py --after-setup       # last line must be "OK"
python3 -B -m unittest discover -s .claude/tests         # last line must be "OK"
python3 .claude/scripts/state_freshness.py --begin-review --json
```
- `check_os.py --after-setup` lists every `FILL IN` and `kit-example` left in the owner's files and active agents. Fill each one from the answers, or ask the owner. A voice file the owner has not given samples for yet may stay `FILL IN`: say so in the hand-over instead.
- Freshness: compare each pending DECISION line with STATE.md (you just wrote both), then `python3 .claude/scripts/state_freshness.py --acknowledge <id> ...`, and run it once more. It must print "fresh".
- In Claude Code: `python3 .claude/hooks/session_start.py --print` must show the owner's STATE and their agent.

## 6. Commit
Stage the changed paths by name (never `git add -A`) and commit as `setup: second brain for <name>`.
Nothing from `.env`, no secrets.

## 7. Hand over
Tell the owner, in their language and in under 15 lines:
- what is set up: the memory, the first agent, where its files are;
- how to use it day to day: `/morning` and `/endday`, "ingest <link>" to keep a source, the agent's trigger phrase from `agents/INDEX.md`, `/new-agent` for the next job;
- one next step, usually: run the first agent once, now;
- that this file can stay where it is; it is only needed again to redo the setup.
