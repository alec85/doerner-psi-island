#!/usr/bin/env bash
# Assemble a runnable copy of the Delphi original from reference/delphi-original
# (sources, data, protocols) and reference/delphi-runtime (executables, bitmaps,
# waves). The reference folders are never modified; all runs happen in the copy.
#
# Usage: scripts/assemble_original.sh <target-dir> [PsiCode|PsiMice-Goal]
set -euo pipefail

target="${1:?usage: assemble_original.sh <target-dir> [PsiCode|PsiMice-Goal]}"
program="${2:-PsiCode}"
root="$(cd "$(dirname "$0")/.." && pwd)"

src="$root/reference/delphi-original/$program"
rt="$root/reference/delphi-runtime/$program"
[ -d "$src" ] || { echo "missing $src" >&2; exit 1; }
[ -d "$rt" ] || { echo "missing $rt" >&2; exit 1; }

if [ -e "$target" ] && [ -n "$(ls -A "$target" 2>/dev/null)" ]; then
  echo "target $target exists and is not empty" >&2
  exit 1
fi
mkdir -p "$target"
cp -a "$src/." "$target/"
cp -a "$rt/." "$target/"
rm -f "$target/HERKUNFT.md" "$target/SHA256SUMS"
chmod -R u+w "$target"
echo "assembled $program in $target"
