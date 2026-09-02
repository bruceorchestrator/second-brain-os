#!/usr/bin/env bash
# context.sh — generate session-start context summary.
#
# Collects STATE + learnings MISTAKES + latest daily + recent commits + INDEX files into a
# single text block. Used by hooks/session-start.sh to inject into the session at start,
# but works standalone too:
#
#   bash scripts/context.sh                    # all defaults
#   bash scripts/context.sh <client-name>      # include memory/projects/<client-name>.md
#   bash scripts/context.sh --full             # no budget guard, dump everything (manual use)
#
# ---------------------------------------------------------------------------------------
# SIZE MATTERS MORE THAN IT LOOKS.
#
# The SessionStart hook injects this via additionalContext, and agent harnesses cap that
# payload. Past the cap the harness does NOT trim the tail — it persists the whole thing to
# a file and injects a short preview instead. So one byte over and you lose EVERYTHING,
# silently: no error, no warning, and the agent happily runs the session with no state.
#
# This is easy to miss because it only bites once memory/ has real content in it. An empty
# template emits half a kilobyte and looks fine forever.
#
# Two defences below: bounded per-section limits, and a guard that drops low-value sections
# itself (loudly) rather than letting the harness drop all of them (silently).
# Check the number any time with: bash scripts/context_budget.sh
# ---------------------------------------------------------------------------------------

set -e

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$REPO_ROOT" 2>/dev/null

# Conservative target. Raise only if you have measured your harness's real cap.
BUDGET="${CONTEXT_BUDGET_BYTES:-8192}"
# The hook adds a preamble before the harness sees this, so aim below the cap, not at it.
PREAMBLE_RESERVE="${CONTEXT_PREAMBLE_RESERVE:-700}"
EFFECTIVE=$((BUDGET - PREAMBLE_RESERVE))

CLIENT_NAMESPACE="$1"
FULL_MODE="false"
if [ "$CLIENT_NAMESPACE" = "--full" ]; then
  FULL_MODE="true"
  CLIENT_NAMESPACE=""
fi

# Headings from quoted files are demoted so they cannot be confused with the digest's own
# structure — and so the drop logic below never has to parse them.
demote() { sed 's/^#\{1,3\} /#### /'; }

# Each section lives in its own variable. Dropping one is then unsetting a variable rather
# than doing text-surgery on the assembled blob: the files we quote carry their own "## "
# headings, so any parse-the-output approach mis-slices them.
# STATE freshness — a mechanical predicate, not a judgment (scripts/state_freshness.py):
# stale <=> a line starting with `DECISION:` in memory/daily/ dated after STATE's
# `Last updated:`, or STATE older than 14 days. Silent when fresh. Emitted FIRST and never
# dropped by the budget guard: a session that plans from a stale STATE plans wrong.
SEC_FRESH=""
if [ -f scripts/state_freshness.py ]; then
  FRESH_OUT="$(python3 scripts/state_freshness.py --quiet 2>/dev/null || true)"
  if [ -n "$FRESH_OUT" ]; then
    SEC_FRESH="## !! STATE.md IS STALE — reconcile it before acting on the STATE below
$FRESH_OUT
"
  fi
fi

SEC_STATE=""
if [ -f memory/STATE.md ]; then
  SEC_STATE="## STATE
$(head -60 memory/STATE.md | demote)
"
fi

SEC_MISTAKES=""
if [ -f memory/learnings/mistakes.md ]; then
  SEC_MISTAKES="## RECENT MISTAKES (don't repeat)
$(head -40 memory/learnings/mistakes.md | demote)
"
elif [ -f memory/learnings.md ]; then
  # Simple Mode fallback — single-file learnings with a MISTAKES section
  SEC_MISTAKES="## RECENT MISTAKES (don't repeat)
$(awk '/^## MISTAKES/,/^## WINS/' memory/learnings.md | head -40 | demote)
"
fi

SEC_DAILY=""
LATEST_DAILY=$(ls -t memory/daily/*.md 2>/dev/null | head -1)
if [ -n "$LATEST_DAILY" ]; then
  SEC_DAILY="## LATEST DAILY: $(basename "$LATEST_DAILY")
$(head -30 "$LATEST_DAILY" | demote)
"
fi

SEC_COMMITS=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  # `|| true`: in a repo with no commits yet `git log` exits 128, and under `set -e` a failing
  # command substitution kills the whole script — the session context came out EMPTY on a
  # fresh `git init` project, with no error. Found 2026-09-02 while verifying the freshness block.
  SEC_COMMITS="## RECENT COMMITS
$(git log --oneline --no-decorate -5 2>/dev/null || true)
"
fi

SEC_CLIENT=""
if [ -n "$CLIENT_NAMESPACE" ] && [ -f "memory/projects/$CLIENT_NAMESPACE.md" ]; then
  SEC_CLIENT="## CLIENT: $CLIENT_NAMESPACE
$(head -60 "memory/projects/$CLIENT_NAMESPACE.md" | demote)
"
fi

SEC_WIKI=""
if [ -f memory/wiki/INDEX.md ]; then
  SEC_WIKI="## WIKI INDEX
$(head -30 memory/wiki/INDEX.md | demote)
"
fi

SEC_INDEX=""
if [ -f memory/INDEX.md ]; then
  SEC_INDEX="## INDEX
$(head -30 memory/INDEX.md | demote)
"
fi

DROPPED=""

assemble() {
  printf '%s\n' "# Session Context" "Generated: $(date '+%Y-%m-%d %H:%M')" ""
  for s in "$SEC_FRESH" "$SEC_STATE" "$SEC_MISTAKES" "$SEC_DAILY" "$SEC_COMMITS" \
           "$SEC_CLIENT" "$SEC_WIKI" "$SEC_INDEX"; do
    [ -n "$s" ] && printf '%s\n' "$s"
  done
  printf '%s' "$DROPPED"
  printf '%s\n' "---" \
    "Digest only. Read the source file before relying on any detail:" \
    "memory/STATE.md · memory/projects/<name>.md · memory/learnings/ · memory/wiki/INDEX.md"
}

CONTEXT="$(assemble)"

if [ "$FULL_MODE" != "true" ]; then
  # Drop lowest-value sections first — loudly — until we fit. Order is deliberate: the two
  # INDEX files are maps that are cheap to re-read on demand; the daily log goes last.
  for victim in "SEC_INDEX:memory/INDEX.md" \
                "SEC_WIKI:memory/wiki/INDEX.md" \
                "SEC_DAILY:memory/daily/"; do
    [ "$(printf '%s' "$CONTEXT" | wc -c)" -le "$EFFECTIVE" ] && break
    var="${victim%%:*}"; hint="${victim##*:}"
    [ -z "${!var}" ] && continue
    eval "$var=''"
    DROPPED="${DROPPED}Dropped to fit the context budget — read on demand: $hint
"
    CONTEXT="$(assemble)"
  done

  # Still over: what remains is load-bearing, so say so instead of pretending it fits.
  SIZE="$(printf '%s' "$CONTEXT" | wc -c | tr -d ' ')"
  if [ "$SIZE" -gt "$EFFECTIVE" ]; then
    CONTEXT="$CONTEXT
!! WARNING: this context is ${SIZE}B, over the ${BUDGET}B budget. Your harness may drop it
!! entirely and inject only a short preview. Trim memory/STATE.md or lower the head -N
!! limits in scripts/context.sh. Diagnose with: bash scripts/context_budget.sh"
  fi
fi

printf '%s\n' "$CONTEXT"
