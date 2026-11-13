#!/usr/bin/env bash
# Build the content of the public repository from the current commit.
#
# Usage: scripts/public_export.sh <target-dir> [--without-original-traces]
#
# The export contains the tracked files of HEAD without reference/ (ADR 0007:
# the original Delphi program never goes into a public repository). Protocols
# of runs of the original (traces/original-runs/) are included, as Alec decided
# on 2026-11-13; --without-original-traces leaves them out.
# The export has no git history, because the private history contains
# reference/. The script refuses to write into a non-empty directory and stops
# if a check fails.
set -euo pipefail

target="${1:?usage: public_export.sh <target-dir> [--without-original-traces]}"
with_traces="yes"
if [[ "${2:-}" == "--without-original-traces" ]]; then with_traces="no"; fi

repo="$(git rev-parse --show-toplevel)"
cd "$repo"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "error: working tree has uncommitted changes; commit first" >&2
  exit 2
fi
if [[ -e "$target" && -n "$(ls -A "$target" 2>/dev/null)" ]]; then
  echo "error: $target exists and is not empty" >&2
  exit 2
fi
mkdir -p "$target"

exclude=(":(exclude)reference")
if [[ "$with_traces" == "no" ]]; then exclude+=(":(exclude)traces/original-runs"); fi

git archive --format=tar HEAD -- . "${exclude[@]}" | tar -x -C "$target"
commit="$(git rev-parse HEAD)"

# The public README replaces the README of the private repository.
if [[ -f "$target/public/README.md" ]]; then
  mv "$target/public/README.md" "$target/README.md"
  rmdir "$target/public" 2>/dev/null || true
fi

# Check 1: no reference/ in the export.
if [[ -e "$target/reference" ]]; then
  echo "error: reference/ found in export" >&2; exit 1
fi

# Check 2: no non-empty file identical to a file of reference/.
python3 - "$repo/reference" "$target" <<'EOF'
import hashlib, os, sys
ref_root, out_root = sys.argv[1], sys.argv[2]
def digests(root):
    out = {}
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                out.setdefault(hashlib.sha256(open(p, "rb").read()).hexdigest(), p)
    return out
ref = digests(ref_root) if os.path.isdir(ref_root) else {}
hits = [(p, ref[h]) for h, p in digests(out_root).items() if h in ref]
for p, r in hits:
    print(f"error: {p} is identical to {r}", file=sys.stderr)
sys.exit(1 if hits else 0)
EOF

# Check 3: no e-mail addresses except the commit attribution address and the
# author's published contact address.
if grep -rIEo "[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}" "$target" \
    | grep -v -e "noreply@anthropic.com" -e "alec.sproten@aol.be" | grep -q .; then
  echo "error: e-mail address found in export:" >&2
  grep -rIEo "[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}" "$target" \
    | grep -v -e "noreply@anthropic.com" -e "alec.sproten@aol.be" >&2
  exit 1
fi

echo "$commit" > "$target/EXPORTED_FROM_COMMIT"
echo "export of $commit written to $target (original traces: $with_traces)"
echo "files: $(find "$target" -type f | wc -l), size: $(du -sh "$target" | cut -f1)"
