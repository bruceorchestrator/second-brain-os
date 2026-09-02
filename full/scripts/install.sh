#!/usr/bin/env bash
# install.sh — wire up agent-os into the current project.
#
# Detects which AI tool is in use (Claude Code, Codex, Cursor, Aider, Windsurf)
# and copies the matching adapter into place. Sets up git hooks for staleness
# checking. Does NOT overwrite existing files without confirmation.
#
# Run from the project root where you want to install agent-os:
#   bash /path/to/agent-os-starter/full/scripts/install.sh
#
# Or copy this entire repo and run from inside `full/`:
#   bash scripts/install.sh

set -e

# Resolve paths relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"  # full/ directory
TARGET_ROOT="${PWD}"

if [ "$SOURCE_ROOT" = "$TARGET_ROOT" ]; then
  echo "Run install.sh from your project root, not from inside the starter."
  echo "Example: cd /path/to/your-project && bash $SCRIPT_DIR/install.sh"
  exit 1
fi

echo "Installing agent-os into: $TARGET_ROOT"
echo ""

# ── Detect tool ────────────────────────────────────────────────
detected_tools=()
[ -d "$TARGET_ROOT/.claude" ] && detected_tools+=("claude-code")
[ -d "$TARGET_ROOT/.cursor" ] && detected_tools+=("cursor")
[ -d "$TARGET_ROOT/.codex" ] && detected_tools+=("codex")
[ -f "$TARGET_ROOT/.aider.conf.yml" ] && detected_tools+=("aider")
[ -f "$TARGET_ROOT/.windsurfrules" ] && detected_tools+=("windsurf")

if [ ${#detected_tools[@]} -eq 0 ]; then
  echo "No AI tool config detected. Choose a tool to install for:"
  echo "  1) Claude Code      → CLAUDE.md + .claude/settings.json"
  echo "  2) Codex / OpenCode → AGENTS.md only"
  echo "  3) Cursor           → .cursor/rules/main.mdc"
  echo "  4) Aider            → CONVENTIONS.md"
  echo "  5) Windsurf         → .windsurfrules"
  read -r -p "Choose [1-5]: " choice
  case "$choice" in
    1) detected_tools=("claude-code") ;;
    2) detected_tools=("codex") ;;
    3) detected_tools=("cursor") ;;
    4) detected_tools=("aider") ;;
    5) detected_tools=("windsurf") ;;
    *) echo "Invalid choice. Exiting."; exit 1 ;;
  esac
fi

echo "Tool(s) to install for: ${detected_tools[*]}"
echo ""

# ── Helpers ────────────────────────────────────────────────────

# Single-file copy with explicit overwrite prompt. Default = skip.
copy_file_safe() {
  local src="$1"
  local dst="$2"
  if [ -e "$dst" ]; then
    read -r -p "  $dst exists. Overwrite? [y/N] " yn
    case "$yn" in [Yy]*) ;; *) echo "  Skipped: $dst"; return 0 ;; esac
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "  Copied: $dst"
}

# Directory copy with skip/merge/backup options. Default = skip.
# Merge = only files that don't exist in dst (never overwrites).
# Backup = mv existing dst to .backup-TIMESTAMP, then full copy from src.
copy_dir_safe() {
  local src="$1"
  local dst="$2"
  local label="$3"
  if [ ! -d "$src" ]; then
    echo "  Source missing: $src (skipped)"
    return 0
  fi
  if [ ! -d "$dst" ]; then
    cp -R "$src" "$dst"
    echo "  Copied: $dst"
    return 0
  fi
  echo "  $label/ already exists at $dst"
  echo "    [s]kip (default)  — leave existing as-is"
  echo "    [m]erge           — copy only new files, never overwrite"
  echo "    [b]ackup-replace  — mv existing to .backup-TIMESTAMP, install fresh"
  read -r -p "    Choose [s/m/b]: " choice
  case "$choice" in
    m|M)
      # Merge: copy file-by-file, only when dst doesn't have it
      (cd "$src" && find . -type f) | while read -r rel; do
        if [ ! -e "$dst/$rel" ]; then
          mkdir -p "$dst/$(dirname "$rel")"
          cp "$src/$rel" "$dst/$rel"
        fi
      done
      echo "    Merged new files into $dst (existing files untouched)"
      ;;
    b|B)
      local backup="$dst.backup-$(date +%Y%m%d-%H%M%S)"
      mv "$dst" "$backup"
      cp -R "$src" "$dst"
      echo "    Backed up original to: $backup"
      echo "    Installed fresh: $dst"
      ;;
    *)
      echo "    Skipped: $dst (kept existing)"
      ;;
  esac
}

# ── Copy core directories (memory + agent-os) ──────────────────
echo "Installing memory/ and agent-os/..."
copy_dir_safe "$SOURCE_ROOT/memory" "$TARGET_ROOT/memory" "memory"
copy_dir_safe "$SOURCE_ROOT/agent-os" "$TARGET_ROOT/agent-os" "agent-os"

# ── Copy scripts (file-by-file, never directory-wide) ──────────
echo "Installing scripts/..."
mkdir -p "$TARGET_ROOT/scripts/git-hooks"
copy_file_safe "$SOURCE_ROOT/scripts/context.sh"                    "$TARGET_ROOT/scripts/context.sh"
copy_file_safe "$SOURCE_ROOT/scripts/context_budget.sh"             "$TARGET_ROOT/scripts/context_budget.sh"
copy_file_safe "$SOURCE_ROOT/scripts/mine_learnings.py"            "$TARGET_ROOT/scripts/mine_learnings.py"
copy_file_safe "$SOURCE_ROOT/scripts/test_mine_learnings.py"       "$TARGET_ROOT/scripts/test_mine_learnings.py"
copy_file_safe "$SOURCE_ROOT/scripts/state_freshness.py"           "$TARGET_ROOT/scripts/state_freshness.py"
copy_file_safe "$SOURCE_ROOT/scripts/test_state_freshness.py"      "$TARGET_ROOT/scripts/test_state_freshness.py"
copy_file_safe "$SOURCE_ROOT/scripts/git-hooks/pre-commit"          "$TARGET_ROOT/scripts/git-hooks/pre-commit"
copy_file_safe "$SOURCE_ROOT/scripts/git-hooks/check-staleness.py"  "$TARGET_ROOT/scripts/git-hooks/check-staleness.py"
copy_file_safe "$SOURCE_ROOT/scripts/git-hooks/README.md"           "$TARGET_ROOT/scripts/git-hooks/README.md"
chmod +x "$TARGET_ROOT/scripts/context.sh" 2>/dev/null
chmod +x "$TARGET_ROOT/scripts/context_budget.sh" 2>/dev/null
chmod +x "$TARGET_ROOT/scripts/state_freshness.py" 2>/dev/null
chmod +x "$TARGET_ROOT/scripts/git-hooks/check-staleness.py" 2>/dev/null
chmod +x "$TARGET_ROOT/scripts/git-hooks/pre-commit" 2>/dev/null

echo ""

# ── Wire up adapter for each detected tool ─────────────────────
for tool in "${detected_tools[@]}"; do
  echo "Wiring adapter: $tool"
  case "$tool" in
    claude-code)
      copy_file_safe "$SOURCE_ROOT/CLAUDE.md" "$TARGET_ROOT/CLAUDE.md"
      copy_file_safe "$SOURCE_ROOT/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
      # Without this the SessionStart hook never fires and memory/ is never auto-loaded.
      # An existing settings.json is never clobbered — copy_file_safe asks, default skip.
      if [ -e "$TARGET_ROOT/.claude/settings.json" ]; then
        echo "  .claude/settings.json exists — leaving it alone."
        echo "  To enable auto-loading, merge the hooks block from agent-os/hooks/README.md"
      else
        copy_file_safe "$SOURCE_ROOT/adapters/claude-code/.claude/settings.json" "$TARGET_ROOT/.claude/settings.json"
      fi
      ;;
    codex)
      copy_file_safe "$SOURCE_ROOT/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
      ;;
    cursor)
      copy_file_safe "$SOURCE_ROOT/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
      copy_file_safe "$SOURCE_ROOT/adapters/cursor/.cursor/rules/main.mdc" "$TARGET_ROOT/.cursor/rules/main.mdc"
      ;;
    aider)
      copy_file_safe "$SOURCE_ROOT/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
      copy_file_safe "$SOURCE_ROOT/adapters/aider/CONVENTIONS.md" "$TARGET_ROOT/CONVENTIONS.md"
      ;;
    windsurf)
      copy_file_safe "$SOURCE_ROOT/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
      copy_file_safe "$SOURCE_ROOT/adapters/windsurf/.windsurfrules" "$TARGET_ROOT/.windsurfrules"
      ;;
  esac
done

echo ""

# ── Wire up git hooks ─────────────────────────────────────────
if [ -d "$TARGET_ROOT/.git" ]; then
  echo "Wiring up git hooks (staleness check + PII block)..."
  current_hooks_path=$(git -C "$TARGET_ROOT" config --get core.hooksPath 2>/dev/null || echo "")
  if [ "$current_hooks_path" = "scripts/git-hooks" ]; then
    echo "  core.hooksPath already set to scripts/git-hooks ✓"
  elif [ -n "$current_hooks_path" ]; then
    echo "  WARN: core.hooksPath is set to '$current_hooks_path'. Skipping to avoid conflict."
    echo "  To enable agent-os hooks: git config core.hooksPath scripts/git-hooks"
  else
    git -C "$TARGET_ROOT" config core.hooksPath scripts/git-hooks
    echo "  Set core.hooksPath = scripts/git-hooks ✓"
  fi
else
  echo "Not a git repo — skipping git hooks setup."
fi

echo ""
echo "Install complete. Next steps:"
echo "  1. Verify memory loads: bash scripts/context.sh"
echo "     (should print STATE + INDEX + learnings + latest daily without errors)"
echo "  2. Check the session cost: bash scripts/context_budget.sh"
echo "     (must say the context is UNDER budget — past the cap your harness drops it"
echo "      entirely and silently, and memory/ stops reaching the agent)"
echo "  3. Open the project in your AI tool — it should auto-load AGENTS.md/CLAUDE.md"
echo "  4. Replace the Acme Notes example content with your real project context"
echo "  5. Optional: rename memory/USER.md.template → memory/USER.md and fill in"
echo "  6. Optional: rename agent-os/rules/identity.md.template → identity.md to define your AI's persona"
