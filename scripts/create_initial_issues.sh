#!/usr/bin/env bash
# Creates the initial GitHub issues from .github/initial-issues/*.md via the REST API.
# Each file: first line is the title, a line "---" follows, the rest is the body.
# Requires an authenticated GitHub CLI (gh auth login). Run once from the repo root.
# Usage: scripts/create_initial_issues.sh [owner/repo]
set -euo pipefail

repo="${1:-alec85/psi-gw}"

if ! gh api "repos/$repo/labels/aufgabe" >/dev/null 2>&1; then
  gh api "repos/$repo/labels" -f name=aufgabe -f color=0E8A16 \
    -f description="Aufgabe in Session-Größe" >/dev/null
fi

for file in .github/initial-issues/*.md; do
  title="$(head -n 1 "$file")"
  body="$(tail -n +3 "$file")"
  number="$(gh api "repos/$repo/issues" -f title="$title" -f body="$body" \
    -f "labels[]=aufgabe" --jq .number)"
  echo "#$number  $title"
done
