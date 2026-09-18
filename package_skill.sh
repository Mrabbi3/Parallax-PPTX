#!/usr/bin/env bash
# Build a minimal, uploadable skill archive.
#
# SKILL.md lives at the repo root, so GitHub's "Download ZIP" is already
# addable as a skill. This produces a smaller archive with the same layout,
# leaving out the README screenshots in assets/ (~5.5MB) that the skill
# itself never uses:
#
#   parallax-pptx/
#     SKILL.md
#     reference/ scripts/ examples/
set -euo pipefail
cd "$(dirname "$0")"

OUT="dist"
STAGE="$OUT/parallax-pptx"

rm -rf "$OUT"
mkdir -p "$STAGE/examples/glass-flowers"

cp SKILL.md "$STAGE"/
cp -R reference scripts "$STAGE"/
cp examples/glass-flowers/deck.json "$STAGE/examples/glass-flowers/"

find "$STAGE" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '.DS_Store' -delete 2>/dev/null || true

( cd "$OUT" && zip -qr parallax-pptx.zip parallax-pptx )
echo "built $OUT/parallax-pptx.zip"
unzip -l "$OUT/parallax-pptx.zip" | sed -n '4,40p'
