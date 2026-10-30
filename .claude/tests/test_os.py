"""Tests for the second brain's hooks and scripts. Standard library only.

Run from the project root (-B: leave no __pycache__ behind):
    python3 -B -m unittest discover -s .claude/tests -v

Every test builds its own throwaway project in a temp directory, so your real memory/ and
agents/ are never read or changed, except TestShippedKit, which only reads this repository.
Hooks run the way Claude Code runs them: a subprocess with the hook JSON on stdin.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]          # the folder holding .claude/, memory/, agents/
HOOKS = ROOT / ".claude" / "hooks"
FRESHNESS = ROOT / ".claude" / "scripts" / "state_freshness.py"
CHECK = ROOT / ".claude" / "scripts" / "check_os.py"
PY = sys.executable
TODAY = date.today()

STAGE = "# Stage\n\n## Inputs\n- x\n\n## Process\n1. x\n\n## Outputs\n- x\n"
PAGE = "---\ntopic: {name}\nupdated: 2026-10-24\n---\n\n> Summary.\n\n{body}\n\n## Sources\n- the owner\n"


def run(script: Path, payload, *args: str, env: dict | None = None, cwd: Path | None = None):
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    full_env = dict(os.environ)
    full_env.pop("CLAUDE_PROJECT_DIR", None)
    full_env.update(env or {})
    return subprocess.run([PY, str(script), *args], input=stdin, capture_output=True, text=True,
                          env=full_env, cwd=str(cwd) if cwd else None, timeout=120)


def make_project(base: Path, state_date: date | None = TODAY, daily: dict | None = None) -> Path:
    """A minimal, valid second brain: memory/ with one wiki page, agents/ with one agent."""
    root = base / "proj"
    for d in ("memory/daily", "memory/learnings", "memory/wiki", ".claude"):
        (root / d).mkdir(parents=True, exist_ok=True)
    header = f"Last updated: {state_date.isoformat()}\n" if state_date else ""
    (root / "memory" / "STATE.md").write_text(f"# State\n\n{header}\n## Focus\n1. Grow the X account.\n")
    (root / "memory" / "USER.md").write_text("# Owner\n\n## Who\n- Sam, writes about coffee.\n")
    (root / "memory" / "wiki" / "INDEX.md").write_text("# Wiki\n- [[coffee]] - the market\n")
    (root / "memory" / "wiki" / "coffee.md").write_text(PAGE.format(name="coffee", body="Body."))
    for day, text in (daily or {}).items():
        (root / "memory" / "daily" / f"{day}.md").write_text(text)
    make_agent(root, "_template")
    make_agent(root, "twitter")
    (root / "agents" / "INDEX.md").write_text(
        "# Agents\n<!-- format: - `agents/<name>/` - what -->\n- `agents/twitter/` - drafts. Say: \"run twitter\"\n")
    return root


def make_agent(root: Path, name: str, stages=("01_research", "02_ideas")) -> Path:
    folder = root / "agents" / name
    (folder / "_config").mkdir(parents=True, exist_ok=True)
    for f in ("CLAUDE.md", "CONTEXT.md", "log.md"):
        (folder / f).write_text(f"# {f}\n")
    for stage in stages:
        (folder / "stages" / stage / "output").mkdir(parents=True, exist_ok=True)
        (folder / "stages" / stage / "CONTEXT.md").write_text(STAGE)
    return folder


def pristine() -> bool:
    """True while this repository is the unconfigured kit: setup removes the kit-example
    marker from memory/STATE.md (START_HERE.md step 2; check_os.py --after-setup enforces it)."""
    return "kit-example" in (ROOT / "memory" / "STATE.md").read_text(encoding="utf-8")


def check(root: Path, *args: str):
    return run(CHECK, "", "--root", str(root), *args)


class TestCheckOS(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make_project(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def assertIssue(self, text: str, *args: str):
        result = check(self.root, *args)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(text, result.stdout)

    def test_valid_project_passes(self):
        result = check(self.root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.strip().splitlines()[-1], "OK")
        self.assertIn("agents: 1 active (twitter)", result.stdout)

    def test_unregistered_agent_fails(self):
        make_agent(self.root, "email-triage")
        self.assertIssue("agents/email-triage/: not registered in agents/INDEX.md")

    def test_registered_agent_without_folder_fails(self):
        shutil.rmtree(self.root / "agents" / "twitter")
        self.assertIssue("agents/INDEX.md: lists agents/twitter/, which does not exist")

    def test_index_format_example_inside_comment_is_ignored(self):
        index = self.root / "agents" / "INDEX.md"
        index.write_text(index.read_text() + "<!--\n- `agents/ghost/` - only an example\n-->\n")
        self.assertEqual(check(self.root).returncode, 0)

    def test_archived_agents_are_not_active(self):
        make_agent(self.root, "_archive")
        self.assertEqual(check(self.root).returncode, 0)

    def test_stage_without_contract_fails(self):
        (self.root / "agents" / "twitter" / "stages" / "02_ideas" / "CONTEXT.md").unlink()
        self.assertIssue("agents/twitter/stages/02_ideas/: no CONTEXT.md")

    def test_stage_contract_without_outputs_section_fails(self):
        contract = self.root / "agents" / "twitter" / "stages" / "01_research" / "CONTEXT.md"
        contract.write_text("# Stage\n\n## Inputs\n- x\n\n## Process\n1. x\n")
        self.assertIssue("agents/twitter/stages/01_research/CONTEXT.md: no `## Outputs` section")

    def test_badly_named_stage_fails(self):
        make_agent(self.root, "twitter", stages=("research",))
        self.assertIssue("stage name must be NN_<verb>")

    def test_stage_without_output_folder_fails(self):
        shutil.rmtree(self.root / "agents" / "twitter" / "stages" / "01_research" / "output")
        self.assertIssue("agents/twitter/stages/01_research/: no output/ folder")

    def test_agent_without_config_or_log_fails(self):
        shutil.rmtree(self.root / "agents" / "twitter" / "_config")
        (self.root / "agents" / "twitter" / "log.md").unlink()
        result = check(self.root)
        self.assertIn("agents/twitter/: no _config/ folder", result.stdout)
        self.assertIn("agents/twitter/: no log.md", result.stdout)

    def test_missing_template_fails(self):
        shutil.rmtree(self.root / "agents" / "_template")
        self.assertIssue("agents/_template/: missing")

    def test_broken_wiki_link_fails(self):
        (self.root / "memory" / "wiki" / "coffee.md").write_text(PAGE.format(name="coffee", body="See [[roasting]]."))
        self.assertIssue("memory/wiki/coffee.md: [[roasting]] has no page")

    def test_wiki_links_inside_code_are_not_links(self):
        body = "Write links as `[[topic]]`.\n\n```\n- [[example]] - format\n```"
        (self.root / "memory" / "wiki" / "coffee.md").write_text(PAGE.format(name="coffee", body=body))
        self.assertEqual(check(self.root).returncode, 0, check(self.root).stdout)

    def test_page_missing_from_index_fails(self):
        (self.root / "memory" / "wiki" / "tea.md").write_text(PAGE.format(name="tea", body="Body."))
        self.assertIssue("memory/wiki/tea.md: not listed in memory/wiki/INDEX.md")

    def test_page_without_summary_or_sources_fails(self):
        (self.root / "memory" / "wiki" / "coffee.md").write_text("---\ntopic: coffee\nupdated: 2026-10-24\n---\n\nBody.\n")
        result = check(self.root)
        self.assertIn("does not open with a `>` summary", result.stdout)
        self.assertIn("no `## Sources` section", result.stdout)

    def test_state_without_date_fails(self):
        root = make_project(Path(self.tmp.name) / "b", state_date=None)
        result = check(root)
        self.assertIn("memory/STATE.md: no `Last updated: YYYY-MM-DD` line", result.stdout)

    def test_after_setup_flags_placeholders_and_examples(self):
        (self.root / "memory" / "USER.md").write_text("# Owner\n- Name: FILL IN\n")
        (self.root / "agents" / "twitter" / "_config" / "voice.md").write_text("FILL IN\n<!-- kit-example -->\n")
        self.assertEqual(check(self.root).returncode, 0)  # placeholders are fine before setup
        result = check(self.root, "--after-setup")
        self.assertEqual(result.returncode, 1)
        self.assertIn("memory/USER.md: 1 `FILL IN` left", result.stdout)
        self.assertIn("agents/twitter/_config/voice.md: example content left", result.stdout)

    def test_after_setup_ignores_template_outputs_raw_and_comments(self):
        (self.root / "agents" / "_template" / "CLAUDE.md").write_text("FILL IN\n")
        (self.root / "agents" / "twitter" / "stages" / "01_research" / "output" / "x.md").write_text("FILL IN\n")
        (self.root / "memory" / "raw").mkdir()
        (self.root / "memory" / "raw" / "2026-10-24_src.md").write_text("FILL IN\n")
        (self.root / "memory" / "USER.md").write_text("# Owner\n<!-- setup replaces every FILL IN -->\n- Sam\n")
        result = check(self.root, "--after-setup")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_not_a_second_brain_folder(self):
        bare = Path(self.tmp.name) / "bare"
        bare.mkdir()
        self.assertEqual(check(bare).returncode, 2)


class TestStateFreshness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, root: Path, *args: str, today: date = TODAY):
        return run(FRESHNESS, "", "--root", str(root), "--today", today.isoformat(), *args)

    def pending(self, root: Path) -> list[dict]:
        return json.loads(self.check(root, "--json").stdout)["pending_decisions"]

    def test_fresh_state(self):
        result = self.check(make_project(self.base))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("fresh", result.stdout)

    def test_old_state_needs_review(self):
        result = self.check(make_project(self.base, state_date=TODAY - timedelta(days=20)))
        self.assertEqual(result.returncode, 1)
        self.assertIn("20 days old", result.stdout)

    def test_state_without_date_needs_review(self):
        self.assertEqual(self.check(make_project(self.base, state_date=None)).returncode, 1)

    def test_missing_state_cannot_be_checked(self):
        (self.base / "empty").mkdir()
        self.assertEqual(self.check(self.base / "empty").returncode, 2)

    def test_decision_logged_after_state_needs_review(self):
        root = make_project(self.base, daily={TODAY.isoformat(): "- **DECISION:** twitter agent first\n"})
        pending = self.pending(root)
        self.assertEqual(len(pending), 1)
        self.assertIn("twitter agent first", pending[0]["line"])

    def test_decision_logged_before_state_date_is_not_pending(self):
        day = (TODAY - timedelta(days=3)).isoformat()
        root = make_project(self.base, daily={day: "- DECISION: old call, already in STATE\n"})
        self.assertEqual(self.pending(root), [])

    def test_acknowledged_decision_stays_reviewed_after_unrelated_edits(self):
        root = make_project(self.base, daily={TODAY.isoformat(): "- **DECISION:** twitter agent first\n"})
        daily = root / "memory" / "daily" / f"{TODAY.isoformat()}.md"
        self.assertEqual(self.check(root, "--acknowledge", self.pending(root)[0]["id"]).returncode, 0)
        daily.write_text(daily.read_text() + "- twitter: 5 drafts\n")
        self.assertEqual(self.check(root).returncode, 0)

    def test_edited_decision_needs_review_again(self):
        root = make_project(self.base, daily={TODAY.isoformat(): "- **DECISION:** twitter agent first\n"})
        daily = root / "memory" / "daily" / f"{TODAY.isoformat()}.md"
        self.check(root, "--acknowledge", self.pending(root)[0]["id"])
        daily.write_text("- **DECISION:** email triage first after all\n")
        self.assertEqual(len(self.pending(root)), 1)

    def test_bumping_state_date_does_not_hide_a_pending_decision(self):
        root = make_project(self.base, daily={TODAY.isoformat(): "- **DECISION:** twitter agent first\n"})
        self.assertEqual(self.check(root, "--begin-review", "--json").returncode, 1)
        later = TODAY + timedelta(days=1)
        state = root / "memory" / "STATE.md"
        state.write_text(state.read_text().replace(TODAY.isoformat(), later.isoformat()))
        self.assertEqual(len(json.loads(self.check(root, "--json", today=later).stdout)["pending_decisions"]), 1)

    def test_future_state_date_needs_review_and_keeps_decisions_pending(self):
        # Issue #1 (@mattabate): a typo like 11-30 for 10-30 made STATE look fresh.
        root = make_project(self.base, state_date=TODAY + timedelta(days=30),
                            daily={TODAY.isoformat(): "- **DECISION:** Postgres over SQLite\n"})
        result = self.check(root)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("in the future", result.stdout)
        self.assertEqual(len(self.pending(root)), 1)

    def test_begin_review_never_pins_a_future_cutoff(self):
        root = make_project(self.base, state_date=TODAY + timedelta(days=30),
                            daily={TODAY.isoformat(): "- **DECISION:** Postgres over SQLite\n"})
        self.check(root, "--begin-review", "--json")
        receipts = json.loads((root / "memory" / "state-receipts.json").read_text())
        self.assertEqual(receipts["tracking_since"], TODAY.isoformat())
        self.assertEqual(len(self.pending(root)), 1)

    def test_unknown_id_is_rejected(self):
        result = self.check(make_project(self.base), "--acknowledge", "0" * 64)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown decision ID", result.stderr)

    def test_broken_receipts_file_is_reported(self):
        root = make_project(self.base)
        (root / "memory" / "state-receipts.json").write_text("{not json")
        self.assertEqual(self.check(root).returncode, 2)


class TestStopTripwire(unittest.TestCase):
    HOOK = HOOKS / "stop_tripwire.py"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "tmp").mkdir()
        self.session = uuid.uuid4().hex

    def tearDown(self):
        self.tmp.cleanup()

    def hook(self, root: Path, mode: str, payload: dict):
        payload = {"session_id": self.session, "cwd": str(root), **payload}
        return run(self.HOOK, payload, mode, env={"CLAUDE_PROJECT_DIR": str(root), "TMPDIR": str(self.base / "tmp")})

    def write(self, root: Path, rel: str):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("report\n")
        return self.hook(root, "--record", {"tool_name": "Write", "tool_input": {"file_path": str(path)}})

    def test_fresh_state_and_no_reports_is_silent(self):
        self.assertEqual(self.hook(make_project(self.base), "--check", {}).returncode, 0)

    def test_stale_state_nudges_once_per_session(self):
        root = make_project(self.base, state_date=TODAY - timedelta(days=30))
        first = self.hook(root, "--check", {})
        self.assertEqual(first.returncode, 2)
        self.assertIn("[STATE FRESHNESS]", first.stderr)
        self.assertEqual(self.hook(root, "--check", {}).returncode, 0)

    def test_loop_guard(self):
        root = make_project(self.base, state_date=TODAY - timedelta(days=30))
        self.assertEqual(self.hook(root, "--check", {"stop_hook_active": True}).returncode, 0)

    def test_report_without_state_update_nudges_once(self):
        root = make_project(self.base)
        self.assertEqual(self.write(root, "memory/outputs/research/2026-10-24_tools.md").returncode, 0)
        first = self.hook(root, "--check", {})
        self.assertEqual(first.returncode, 2)
        self.assertIn("[STATE SYNC]", first.stderr)
        self.assertEqual(self.hook(root, "--check", {}).returncode, 0)

    def test_report_with_state_update_is_silent(self):
        root = make_project(self.base)
        self.write(root, "memory/outputs/research/2026-10-24_tools.md")
        self.hook(root, "--record", {"tool_name": "Edit", "tool_input": {"file_path": str(root / "memory" / "STATE.md")}})
        self.assertEqual(self.hook(root, "--check", {}).returncode, 0)

    def test_agent_run_outputs_do_not_nudge(self):
        root = make_project(self.base)
        self.write(root, "agents/twitter/stages/01_research/output/2026-10-24_brief.md")
        self.assertEqual(self.hook(root, "--check", {}).returncode, 0)

    def test_project_without_memory_is_silent(self):
        bare = self.base / "bare"
        bare.mkdir()
        self.assertEqual(self.hook(bare, "--check", {}).returncode, 0)


class TestSessionStart(unittest.TestCase):
    HOOK = HOOKS / "session_start.py"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self, root: Path) -> str:
        result = run(self.HOOK, "", "--print", env={"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def full_project(self) -> Path:
        root = make_project(self.base, daily={
            TODAY.isoformat(): "# day\n\n## Decisions\n- **DECISION:** twitter agent first\n\n## Next\n- Run 03_drafts\n"})
        (root / "memory" / "learnings" / "mistakes.md").write_text(
            "# Mistakes\n\n```\n## 2026-01-01 - format example\n```\n\n"
            "## 2026-10-23 - Drafted before the voice file had samples\n**Wrong:** x\n**Correct:** y\n**Why:** z\n"
            "**Trigger:** before an agent writes in the owner's name\n")
        return root

    def test_digest_has_every_section(self):
        out = self.digest(self.full_project())
        for marker in ["## STATE (memory/STATE.md)", "Grow the X account", "## LAST SESSION", "twitter agent first",
                       "Run 03_drafts", "## RECENT LESSONS", "Drafted before the voice file had samples",
                       "Trigger: before an agent writes", "## AGENTS", "`agents/twitter/` - drafts",
                       "## WIKI TOPICS", "coffee"]:
            self.assertIn(marker, out)
        self.assertNotIn("format example", out)   # entries inside code fences are formats, not lessons
        self.assertNotIn("agents/<name>/` - what", out)  # the INDEX header comment is not an agent
        self.assertNotIn("SETUP NOT DONE", out)

    def test_template_user_file_means_setup_not_done(self):
        root = self.full_project()
        (root / "memory" / "USER.md").write_text("# Owner\n<!-- START_HERE fills this -->\n- Name: FILL IN\n")
        out = self.digest(root)
        self.assertIn("SETUP NOT DONE", out)
        self.assertLess(out.index("SETUP NOT DONE"), out.index("## STATE (memory/STATE.md)"))

    def test_hook_mode_emits_json_within_the_cap(self):
        root = self.full_project()
        result = run(self.HOOK, {"hook_event_name": "SessionStart", "source": "startup"},
                     env={"CLAUDE_PROJECT_DIR": str(root)})
        data = json.loads(result.stdout)
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertLessEqual(len(data["hookSpecificOutput"]["additionalContext"]), 10000)
        self.assertTrue((root / ".claude" / ".session-digest.txt").is_file())

    def test_huge_memory_still_fits_the_cap(self):
        root = self.full_project()
        state = root / "memory" / "STATE.md"
        state.write_text(state.read_text() + "\n".join(f"- line {i} " + "x" * 80 for i in range(2000)))
        (root / "memory" / "wiki" / "INDEX.md").write_text("\n".join(f"- [[topic-{i}]] - page" for i in range(3000)))
        (root / "agents" / "INDEX.md").write_text("\n".join(f"- `agents/a{i}/` - " + "z" * 100 for i in range(300)))
        long_decisions = "".join(f"- **DECISION:** {i} " + "y" * 1500 + "\n" for i in range(5))
        (root / "memory" / "daily" / f"{TODAY.isoformat()}.md").write_text(long_decisions)
        out = self.digest(root)
        self.assertLessEqual(len(out), 9001)
        self.assertIn("cut to fit", out)
        self.assertIn("## STATE (memory/STATE.md)", out)  # the budget drops the tail, not the head

    def test_stale_state_warning_comes_before_state(self):
        out = self.digest(make_project(self.base, state_date=TODAY - timedelta(days=30)))
        self.assertLess(out.index("STATE NEEDS REVIEW"), out.index("## STATE (memory/STATE.md)"))

    def test_project_without_memory_points_to_setup(self):
        bare = self.base / "bare"
        bare.mkdir()
        self.assertIn("START_HERE.md", self.digest(bare))

    def test_hooks_write_no_bytecode(self):
        root = make_project(self.base, state_date=TODAY - timedelta(days=30))
        prefix = self.base / "pycache"
        env = {"CLAUDE_PROJECT_DIR": str(root), "PYTHONPYCACHEPREFIX": str(prefix),
               "PYTHONDONTWRITEBYTECODE": "", "TMPDIR": str(self.base)}
        self.assertEqual(run(self.HOOK, "", "--print", env=env).returncode, 0)
        run(HOOKS / "stop_tripwire.py", {"session_id": uuid.uuid4().hex, "cwd": str(root)}, "--check", env=env)
        self.assertEqual(sorted(p.name for p in prefix.rglob("state_freshness*.pyc")), [])


class TestShippedKit(unittest.TestCase):
    """This repository itself: the pieces reference each other by path."""

    def test_kit_passes_its_own_structure_check(self):
        result = check(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_template_and_example_agent_are_valid(self):
        result = check(ROOT)
        self.assertNotIn("agents/_template", result.stdout)
        self.assertNotIn("agents/twitter", result.stdout)

    def test_settings_parse_and_every_hook_file_exists(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
        commands = [h["command"] for groups in settings["hooks"].values() for g in groups for h in g["hooks"]]
        self.assertTrue(commands)
        for command in commands:
            match = re.search(r"\$CLAUDE_PROJECT_DIR/(\S+?\.py)", command)
            self.assertIsNotNone(match, command)
            self.assertTrue((ROOT / match.group(1)).is_file(), match.group(1))

    def test_skills_have_valid_frontmatter(self):
        skills = sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))
        self.assertTrue(skills)
        for skill in skills:
            with self.subTest(skill=skill.parent.name):
                text = skill.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                front = text.split("---\n", 2)[1]
                self.assertRegex(front, rf"(?m)^name: {re.escape(skill.parent.name)}$")
                description = re.search(r"(?m)^description: (.+)$", front)
                self.assertIsNotNone(description)
                self.assertLessEqual(len(description.group(1)), 1024)
                self.assertNotRegex(front, r"[<>]")

    def test_every_skill_named_in_claude_md_exists(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        for name in re.findall(r"^- `/([a-z-]+)`", text, re.MULTILINE):
            self.assertTrue((ROOT / ".claude" / "skills" / name / "SKILL.md").is_file(), name)

    def test_paths_named_in_setup_files_exist(self):
        # START_HERE.md names the example files that setup deletes: check it only before setup.
        docs = ["CLAUDE.md", "agents/README.md", "README.md"] + (["START_HERE.md"] if pristine() else [])
        for doc in docs:
            text = (ROOT / doc).read_text(encoding="utf-8")
            for path in re.findall(r"`((?:memory|agents|\.claude)/[A-Za-z0-9_./-]+\.(?:md|py|json))`", text):
                if "YYYY" in path:  # a naming pattern, not a file
                    continue
                with self.subTest(doc=doc, path=path):
                    self.assertTrue((ROOT / path).exists(), path)

    def test_agents_md_points_to_claude_md(self):
        agents_md = ROOT / "AGENTS.md"
        self.assertTrue(agents_md.is_symlink())
        self.assertEqual(os.readlink(agents_md), "CLAUDE.md")

    def test_rule_frontmatter_only_uses_paths(self):
        for rule in sorted((ROOT / ".claude" / "rules").glob("*.md")):
            text = rule.read_text(encoding="utf-8")
            if text.startswith("---\n"):
                front = text.split("---\n", 2)[1]
                keys = {ln.split(":", 1)[0] for ln in front.splitlines() if ln and not ln.startswith((" ", "-"))}
                self.assertEqual(keys, {"paths"}, rule.name)

    def test_python_files_compile(self):
        for path in sorted([*HOOKS.glob("*.py"), FRESHNESS, CHECK]):
            with self.subTest(file=path.name):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


if __name__ == "__main__":
    unittest.main()
