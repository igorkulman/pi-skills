#!/usr/bin/env bash
# Compares the saved Xcode skill snapshots with a fresh export from the selected Xcode.
# Usage: scripts/check-xcode-skill-exports.sh [export-dir]
# Without an argument, exports to a temporary directory. Exits non-zero when anything differs.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SKILLS="$ROOT/skills"
EXPORT=${1:-}
if [ -z "$EXPORT" ]; then
  EXPORT=$(mktemp -d)
  trap 'rm -rf "$EXPORT"' EXIT
  xcrun agent skills export --output-dir "$EXPORT" >/dev/null
fi

echo "Xcode: $(xcodebuild -version | tr '\n' ' ')"
status=0

# The export writes frontmatter keys in a random order, so compare frontmatter as a sorted set
# and the body byte for byte.
frontmatter() { awk '/^---$/{n++; next} n==1' "$1" | sort; }
body() { awk 'n>=2; /^---$/{n++}' "$1"; }

compare_skill() {
  local snapshot=$1 exported=$2
  if diff -u <(frontmatter "$snapshot") <(frontmatter "$exported") && diff -u <(body "$snapshot") <(body "$exported"); then
    echo "same: ${snapshot#"$ROOT"/}"
  else
    echo "DIFFERS: ${snapshot#"$ROOT"/}"
    status=1
  fi
}

compare_file() {
  local snapshot=$1 exported=$2
  if diff -u "$snapshot" "$exported"; then
    echo "same: ${snapshot#"$ROOT"/}"
  else
    echo "DIFFERS: ${snapshot#"$ROOT"/}"
    status=1
  fi
}

for upstream in "$SKILLS"/*/upstream.md; do
  name=$(basename "$(dirname "$upstream")")
  if [ ! -f "$EXPORT/$name/SKILL.md" ]; then
    echo "MISSING from export: $name"
    status=1
    continue
  fi
  compare_skill "$upstream" "$EXPORT/$name/SKILL.md"
  for reference in "$EXPORT/$name"/references/*; do
    [ -e "$reference" ] || continue
    local_copy="$SKILLS/$name/references/$(basename "$reference")"
    if [ -f "$local_copy" ]; then
      compare_file "$local_copy" "$reference"
    else
      echo "NEW reference in export: $name/references/$(basename "$reference")"
      status=1
    fi
  done
done

exit $status
