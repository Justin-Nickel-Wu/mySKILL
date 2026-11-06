#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/SKILL"
SCOPE="user"
PROJECT_DIR=""
REPLACE=0

# Print installation options and the source directory layout.
usage() {
  cat <<'HELP'
Usage: bash install.sh [--user | --project PATH] [--replace]
  Copy skill directories from this repository's SKILL/ directory.
  --user          Install to ~/.agents/skills (default)
  --project PATH  Install to PATH/.agents/skills
  --replace       Back up existing same-named skills outside skills directory,
                  then install the new versions (needed when upgrading old skill)
HELP
}

while (($#)); do
  case "$1" in
    --user) SCOPE="user"; shift ;;
    --project)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      SCOPE="project"; PROJECT_DIR="$2"; shift 2 ;;
    --replace) REPLACE=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ "$SCOPE" == "user" ]]; then
  DEST="$HOME/.agents/skills"
  BACKUP_ROOT="$HOME/.codex/skill-backups"
else
  [[ -d "$PROJECT_DIR" ]] || { echo "Project directory not found: $PROJECT_DIR" >&2; exit 1; }
  PROJECT_DIR="$(cd -- "$PROJECT_DIR" && pwd -P)"
  DEST="$PROJECT_DIR/.agents/skills"
  BACKUP_ROOT="$PROJECT_DIR/.agents/skill-backups"
fi

# Discover skills before creating or changing the installation directory.
sources=()
for src in "$SKILLS_DIR"/*; do
  [[ -d "$src" && -f "$src/SKILL.md" ]] || continue
  sources+=("$src")
done
if ((${#sources[@]} == 0)); then
  echo "No skills found in $SKILLS_DIR (expected <skill>/SKILL.md)" >&2
  exit 1
fi

mkdir -p -- "$DEST"
for src in "${sources[@]}"; do
  name="${src##*/}"
  dst="$DEST/$name"
  if [[ -e "$dst" || -L "$dst" ]]; then
    if ((REPLACE)); then
      mkdir -p -- "$BACKUP_ROOT"
      backup="$BACKUP_ROOT/${name}.$(date +%Y%m%d-%H%M%S).$$"
      mv -- "$dst" "$backup"
      echo "Backed up $dst -> $backup"
    else
      echo "SKIP $dst (already exists; use --replace to upgrade)"
      continue
    fi
  fi
  cp -R -- "$src" "$dst"
  echo "INSTALLED $dst"
done

echo "Completed. Restart Codex CLI, then use \$review or \$tutor."
echo "Review session data: <workspace>/.ai/sessions/review/ (created on demand)."
