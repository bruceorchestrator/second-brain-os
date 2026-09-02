"""Tests for scripts/state_freshness.py — the STATE.md freshness predicate.

Run: .venv/bin/python -m pytest scripts/test_state_freshness.py -q
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_freshness as sf  # noqa: E402

TODAY = date(2026, 9, 2)
SCRIPT = Path(__file__).resolve().parent / "state_freshness.py"


def make_repo(tmp_path: Path, state_date: str | None, dailies: dict[str, str] | None = None) -> Path:
    mem = tmp_path / "memory"
    (mem / "daily").mkdir(parents=True)
    header = f"Last updated: {state_date}\n\n" if state_date else ""
    (mem / "STATE.md").write_text(f"# State\n\n{header}## Current focus\n1. Something.\n", encoding="utf-8")
    for name, text in (dailies or {}).items():
        (mem / "daily" / name).write_text(text, encoding="utf-8")
    return tmp_path


def bump_mtime(path: Path, seconds: int) -> None:
    st = path.stat()
    os.utime(path, (st.st_atime + seconds, st.st_mtime + seconds))


def test_fresh_when_state_is_recent_and_decisions_predate_it(tmp_path):
    root = make_repo(tmp_path, "2026-09-01", {
        "2026-08-09.md": "# 2026-08-09\n- **DECISION:** post deferred\n",
    })
    r = sf.check(root, today=TODAY)
    assert r["ok"] and not r["stale"]
    assert r["unmirrored"] == []
    assert r["age_days"] == 1


def test_stale_when_a_later_daily_has_a_decision(tmp_path):
    root = make_repo(tmp_path, "2026-07-28", {
        "2026-08-09.md": "# 2026-08-09\n- LinkedIn post\n- **DECISION:** community post deferred, acquisition = LinkedIn\n",
        "2026-08-10.md": "# 2026-08-10\n- routine work\n",
    })
    r = sf.check(root, today=TODAY, max_age=365)  # age alone must not trigger here
    assert r["stale"]
    assert len(r["unmirrored"]) == 1
    assert r["unmirrored"][0]["file"] == "memory/daily/2026-08-09.md"
    assert "DECISION" in r["reasons"][0]


def test_stale_by_age_alone(tmp_path):
    root = make_repo(tmp_path, (TODAY - timedelta(days=15)).isoformat())
    r = sf.check(root, today=TODAY)
    assert r["stale"]
    assert r["unmirrored"] == []
    assert "15 days old" in r["reasons"][0]


def test_exactly_max_age_is_still_fresh(tmp_path):
    root = make_repo(tmp_path, (TODAY - timedelta(days=14)).isoformat())
    assert not sf.check(root, today=TODAY)["stale"]


def test_same_day_decision_counts_only_if_daily_modified_after_state(tmp_path):
    root = make_repo(tmp_path, "2026-09-02", {
        "2026-09-02.md": "# 2026-09-02\n- **DECISION:** implement freshness check\n",
    })
    state = root / "memory" / "STATE.md"
    daily = root / "memory" / "daily" / "2026-09-02.md"
    # daily older than STATE (e.g. STATE bumped after logging the decision) -> fresh
    bump_mtime(state, +60)
    assert not sf.check(root, today=TODAY)["stale"]
    # daily touched after STATE -> the decision came later -> stale
    bump_mtime(daily, +120)
    r = sf.check(root, today=TODAY)
    assert r["stale"] and len(r["unmirrored"]) == 1


def test_missing_header_is_stale(tmp_path):
    root = make_repo(tmp_path, None)
    r = sf.check(root, today=TODAY)
    assert r["stale"]
    assert "no `Last updated" in r["reasons"][0]


def test_only_decision_prefixed_lines_count(tmp_path):
    root = make_repo(tmp_path, "2026-08-01", {
        "2026-08-05.md": (
            "# 2026-08-05\n"
            "- we decided to ship later (not a marker)\n"
            "- the DECISION: word mid-line does not count\n"
            "  - **DECISION:** nested list marker counts\n"
            "* DECISION: plain marker counts\n"
            "DECISION: bare line counts\n"
        ),
    })
    r = sf.check(root, today=TODAY, max_age=365)
    assert [u["line"] for u in r["unmirrored"]] == [
        "- **DECISION:** nested list marker counts",
        "* DECISION: plain marker counts",
        "DECISION: bare line counts",
    ]


def test_missing_state_file_reports_error(tmp_path):
    r = sf.check(tmp_path, today=TODAY)
    assert r["ok"] is False


def test_find_root_walks_up(tmp_path):
    root = make_repo(tmp_path, "2026-09-01")
    deep = root / "a" / "b"
    deep.mkdir(parents=True)
    assert sf.find_root(deep) == root.resolve()
    assert sf.find_root(Path("/")) is None or True  # never raises


def test_cli_exit_codes_and_quiet(tmp_path):
    root = make_repo(tmp_path, "2026-07-28", {"2026-08-09.md": "- **DECISION:** x\n"})
    p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "--today", "2026-09-02", "--json"],
                       capture_output=True, text=True)
    assert p.returncode == 1
    assert '"stale": true' in p.stdout

    fresh = make_repo(tmp_path / "fresh", "2026-09-02")
    p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(fresh), "--today", "2026-09-02", "--quiet"],
                       capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout == ""

    p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path / "nowhere")],
                       capture_output=True, text=True)
    assert p.returncode == 2
