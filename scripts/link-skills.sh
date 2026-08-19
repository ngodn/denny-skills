#!/usr/bin/env bash
set -euo pipefail

# The team installer for Linux and macOS (Windows: scripts/link-skills.ps1).
#
# Links all skills in the repository into the local skill directories used by
# each agent harness:
#   - ~/.claude/skills  (Claude Code)
#   - ~/.agents/skills  (Codex and other Agent Skills-compatible harnesses)
# Each entry is a symlink into this repo, so a `git pull` is all that's needed
# to keep installed skills up to date. Re-run after adding, removing, or
# renaming a skill.
#
# It also installs the team's global instructions file,
# templates/CLAUDE.global.md, as ~/.claude/CLAUDE.md (and ~/.codex/AGENTS.md
# when ~/.codex exists). It never overwrites a file that differs from the
# template: it tells you so and leaves merging to you.
#
# Usage:
#   ./scripts/link-skills.sh

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DESTS=("$HOME/.claude/skills" "$HOME/.agents/skills")

# Collect the repo's skills once, link into every destination.
names=()
srcs=()
while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  names+=("$(basename "$src")")
  srcs+=("$src")
done < <(find "$REPO/skills" -name SKILL.md -not -path '*/node_modules/*' -not -path '*/deprecated/*' -print0)

for DEST in "${DESTS[@]}"; do
  # If $DEST is a symlink that resolves into this repo, we'd end up writing the
  # per-skill symlinks back into the repo's own skills/ tree. Detect and bail
  # out instead of polluting the working copy.
  if [ -L "$DEST" ]; then
    resolved="$(readlink -f "$DEST")"
    case "$resolved" in
      "$REPO"|"$REPO"/*)
        echo "error: $DEST is a symlink into this repo ($resolved)." >&2
        echo "Remove it (rm \"$DEST\") and re-run; the script will recreate it as a real dir." >&2
        exit 1
        ;;
    esac
  fi

  mkdir -p "$DEST"

  for i in "${!names[@]}"; do
    name="${names[$i]}"
    src="${srcs[$i]}"
    target="$DEST/$name"

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      rm -rf "$target"
    fi

    ln -sfn "$src" "$target"
    echo "linked $name -> $src ($DEST)"
  done
done

# ---- global instructions file -------------------------------------------------
TEMPLATE="$REPO/templates/CLAUDE.global.md"
targets=("$HOME/.claude/CLAUDE.md")
[ -d "$HOME/.codex" ] && targets+=("$HOME/.codex/AGENTS.md")

for target in "${targets[@]}"; do
  if [ ! -e "$target" ]; then
    mkdir -p "$(dirname "$target")"
    cp "$TEMPLATE" "$target"
    echo "installed global rules -> $target"
  elif cmp -s "$TEMPLATE" "$target"; then
    echo "global rules up to date ($target)"
  else
    echo "note: $target differs from templates/CLAUDE.global.md; not overwritten." >&2
    echo "      Merge by hand, e.g.: diff \"$TEMPLATE\" \"$target\"" >&2
  fi
done
