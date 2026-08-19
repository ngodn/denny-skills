#!/usr/bin/env bash
set -euo pipefail

# The team installer for Linux and macOS (Windows: scripts/link-skills.ps1).
#
# Links every skill in this repository into the local skill directories used
# by each agent harness:
#   - ~/.claude/skills  (Claude Code)
#   - ~/.agents/skills  (Codex and other Agent Skills-compatible harnesses)
# Each entry is a symlink into this repo, so a `git pull` keeps installed
# skills current. Re-run after a skill is added, removed, or renamed.
#
# It also installs the team's global instructions file,
# templates/CLAUDE.global.md, as ~/.claude/CLAUDE.md (and ~/.codex/AGENTS.md
# when ~/.codex exists). It never overwrites a copy that differs from the
# template: it tells you so and leaves merging to you.
#
# Anything it replaces is copied into backup/<timestamp>/ inside this repo
# first, and the path is printed when it finishes. That directory is
# gitignored.
#
# Usage:
#   ./scripts/link-skills.sh                  install or upgrade
#   ./scripts/link-skills.sh --list-backups   show what can be restored
#   ./scripts/link-skills.sh --restore [ID]   put a backup back

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DESTS=("$HOME/.claude/skills" "$HOME/.agents/skills")
BACKUP_ROOT="$REPO/backup"

# ---- backup helpers ---------------------------------------------------------
# A backup directory is created lazily, on the first thing actually saved, so a
# no-op run leaves no empty directory behind.
BACKUP_DIR=""
BACKUP_COUNT=0

# Sets $BACKUP_DIR in this shell. Deliberately not a command substitution:
# that runs in a subshell, so the assignment would be lost and every call
# would re-initialise (and truncate) the manifest.
_ensure_backup_dir() {
  [ -n "$BACKUP_DIR" ] && return 0
  local stamp base n
  base="$BACKUP_ROOT/$(date +%Y%m%d-%H%M%S)"
  # Two runs inside the same second must not share a directory: the second
  # would truncate the first's manifest and silently orphan everything it
  # had saved. Suffix until the name is free.
  stamp="$base"; n=1
  while [ -e "$stamp" ]; do stamp="$base-$n"; n=$((n + 1)); done
  BACKUP_DIR="$stamp"
  mkdir -p "$BACKUP_DIR/files" "$BACKUP_DIR/dirs"
  : > "$BACKUP_DIR/MANIFEST.tsv"
}

# save_file <path>   save_dir <path>
# Records the original absolute path so a restore knows where it came from.
save_file() {
  local src="$1" slot
  [ -e "$src" ] || return 0
  _ensure_backup_dir
  BACKUP_COUNT=$((BACKUP_COUNT + 1))
  slot="files/$(printf '%03d' "$BACKUP_COUNT")-$(basename "$src")"
  cp -p "$src" "$BACKUP_DIR/$slot"
  printf 'FILE\t%s\t%s\n' "$src" "$slot" >> "$BACKUP_DIR/MANIFEST.tsv"
}

save_dir() {
  local src="$1" slot
  [ -d "$src" ] || return 0
  _ensure_backup_dir
  BACKUP_COUNT=$((BACKUP_COUNT + 1))
  slot="dirs/$(printf '%03d' "$BACKUP_COUNT")-$(basename "$src")"
  cp -a "$src" "$BACKUP_DIR/$slot"
  printf 'DIR\t%s\t%s\n' "$src" "$slot" >> "$BACKUP_DIR/MANIFEST.tsv"
}

list_backups() {
  if [ ! -d "$BACKUP_ROOT" ] || [ -z "$(ls -A "$BACKUP_ROOT" 2>/dev/null)" ]; then
    echo "No backups yet. One is written the first time an install replaces something."
    return 0
  fi
  echo "Backups in $BACKUP_ROOT:"
  local d n
  for d in "$BACKUP_ROOT"/*/; do
    [ -f "$d/MANIFEST.tsv" ] || continue
    n="$(wc -l < "$d/MANIFEST.tsv" | tr -d ' ')"
    printf '  %-20s %s item%s\n' "$(basename "$d")" "$n" "$([ "$n" = 1 ] || echo s)"
    while IFS=$'\t' read -r kind orig _; do
      printf '      %-5s %s\n' "$kind" "$orig"
    done < "$d/MANIFEST.tsv"
  done
  echo
  echo "Restore one with: ./scripts/link-skills.sh --restore <id>"
}

restore_backup() {
  local id="${1:-}" dir
  if [ -z "$id" ]; then
    list_backups
    echo
    read -r -p "Which backup id? " id
  fi
  dir="$BACKUP_ROOT/$id"
  if [ ! -f "$dir/MANIFEST.tsv" ]; then
    echo "error: no backup '$id' (looked for $dir/MANIFEST.tsv)" >&2
    exit 1
  fi

  echo "This will put the following back, overwriting what is there now:"
  while IFS=$'\t' read -r kind orig _; do
    printf '  %-5s %s\n' "$kind" "$orig"
  done < "$dir/MANIFEST.tsv"
  echo
  read -r -p "Proceed? [y/N] " reply
  case "$reply" in
    [yY]*) ;;
    *) echo "Nothing restored."; exit 0 ;;
  esac

  while IFS=$'\t' read -r kind orig slot; do
    mkdir -p "$(dirname "$orig")"
    case "$kind" in
      FILE)
        cp -p "$dir/$slot" "$orig"
        echo "restored file $orig"
        ;;
      DIR)
        # Remove whatever occupies the path now, including a symlink the
        # installer put there, then put the saved directory back.
        if [ -L "$orig" ]; then rm -f "$orig"; else rm -rf "$orig"; fi
        cp -a "$dir/$slot" "$orig"
        echo "restored dir  $orig"
        ;;
    esac
  done < "$dir/MANIFEST.tsv"
  echo
  echo "Restored from $dir"
  echo "Re-run ./scripts/link-skills.sh when you want the skills linked again."
}

case "${1:-}" in
  --list-backups) list_backups; exit 0 ;;
  --restore)      restore_backup "${2:-}"; exit 0 ;;
  --help|-h)      sed -n '3,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  "")             ;;
  *)              echo "error: unknown option '$1' (try --help)" >&2; exit 1 ;;
esac

# ---- link the skills --------------------------------------------------------
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

    # A real directory here is someone's own copy of a skill. Save it before
    # replacing it with a symlink, or the install destroys their work.
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      save_dir "$target"
      rm -rf "$target"
    fi

    ln -sfn "$src" "$target"
    echo "linked $name -> $src ($DEST)"
  done
done

# ---- global instructions file -----------------------------------------------
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
    # Not overwritten, but saved anyway: the next thing the user does is often
    # to merge by hand, and a copy from before that is worth having.
    save_file "$target"
    echo "note: $target differs from templates/CLAUDE.global.md; not overwritten." >&2
    echo "      Merge by hand, e.g.: diff \"$TEMPLATE\" \"$target\"" >&2
  fi
done

# ---- report ------------------------------------------------------------------
echo
if [ -n "$BACKUP_DIR" ]; then
  echo "Backed up $BACKUP_COUNT item(s) this run:"
  echo "  $BACKUP_DIR"
  echo "Undo with: ./scripts/link-skills.sh --restore $(basename "$BACKUP_DIR")"
  echo "See all:   ./scripts/link-skills.sh --list-backups"
else
  echo "Nothing needed backing up this run."
fi
