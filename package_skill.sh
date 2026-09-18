#!/usr/bin/env bash
# Build an uploadable skill package.
#
# Skill uploaders expect SKILL.md in the archive's top-level folder. In this
# repo it lives at skills/parallax-presentation/SKILL.md, so GitHub's
# "Download ZIP" is nested too deep and gets rejected. This produces a zip
# shaped the way an uploader wants:
#
#   parallax-presentation/
#     SKILL.md
#     reference/ scripts/ examples/
set -euo pipefail
cd "$(dirname "$0")"

SRC="skills/parallax-presentation"
OUT="dist"
STAGE="$OUT/parallax-presentation"

rm -rf "$OUT"
mkdir -p "$STAGE"
cp -R "$SRC"/. "$STAGE"/

# the example lives outside the skill dir in this repo; bundle it so the
# skill is self-contained, and point SKILL.md at the bundled copy
mkdir -p "$STAGE/examples/glass-flowers"
# deck.json only -- the example README points at repo assets/ that are not
# part of the skill package
cp examples/glass-flowers/deck.json "$STAGE/examples/glass-flowers/"
sed -i '' 's|\.\./\.\./examples/glass-flowers/deck\.json|examples/glass-flowers/deck.json|g' \
  "$STAGE/SKILL.md" 2>/dev/null || \
sed -i 's|\.\./\.\./examples/glass-flowers/deck\.json|examples/glass-flowers/deck.json|g' \
  "$STAGE/SKILL.md"

find "$STAGE" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '.DS_Store' -delete 2>/dev/null || true

( cd "$OUT" && zip -qr parallax-presentation.zip parallax-presentation )
echo "built $OUT/parallax-presentation.zip"
unzip -l "$OUT/parallax-presentation.zip" | sed -n '4,40p'
