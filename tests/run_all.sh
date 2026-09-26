#!/usr/bin/env bash
# Full regression: sample deck × every theme through build + rendered QA, outline pipeline, runtime interaction tests, exports.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SF="$ROOT/skills/slide-forge"; OUT="${1:-$ROOT/tests/_out}"
FONTS="${FONTS:-link}"   # FONTS=embed to test offline font embedding
rm -rf "$OUT"; mkdir -p "$OUT"; fail=0
echo "== themes × sample deck =="
for css in "$SF"/assets/themes/*.css; do t=$(basename "$css" .css)
  python3 "$SF/scripts/build.py" "$SF/assets/examples/sample.src.html" -o "$OUT/$t.html" --theme "$t" --fonts "$FONTS" >/dev/null 2>&1 || { echo "✗ build $t"; fail=1; }
  python3 "$SF/scripts/check.py" "$OUT/$t.html" --out "$OUT/qa-$t" --no-shots 2>/dev/null | head -1 | grep -q "0 errors" && echo "✓ $t" || { echo "✗ $t"; python3 "$SF/scripts/check.py" "$OUT/$t.html" --out "$OUT/qa-$t" --no-shots | head -8; fail=1; }
done
echo "== outline pipeline =="
cp "$SF/assets/examples/outline.example.md" "$OUT/outline.md"
python3 "$SF/scripts/outline.py" scaffold "$OUT/outline.md" -o "$OUT/ol.src.html" >/dev/null && python3 "$SF/scripts/build.py" "$OUT/ol.src.html" --fonts "$FONTS" >/dev/null 2>&1 \
  && python3 "$SF/scripts/check.py" "$OUT/ol.html" --out "$OUT/qa-ol" --no-shots | head -1 || fail=1
echo "== checker catches known defects (negative test) =="
python3 "$SF/scripts/build.py" "$ROOT/tests/bad.src.html" -o "$OUT/bad.html" --fonts none >/dev/null 2>&1
BAD=$(python3 "$SF/scripts/check.py" "$OUT/bad.html" --out "$OUT/qa-bad" --no-shots 2>&1)
for code in overflow overlap tiny-text contrast broken-image density; do
  echo "$BAD" | grep -q " $code:" && echo "✓ detects $code" || { echo "✗ missed $code"; fail=1; }
done
echo "== runtime interaction =="
python3 "$ROOT/tests/test_runtime.py" "$OUT/signal.html" | tail -1 | grep -q "0 failed" && echo "✓ runtime" || { python3 "$ROOT/tests/test_runtime.py" "$OUT/signal.html" | grep FAIL; fail=1; }
echo "== visuals (images, icons, credits) =="
python3 "$ROOT/tests/test_visuals.py" "$OUT/visuals" | tail -1 | grep -q "0 failed" && echo "✓ visuals" || { python3 "$ROOT/tests/test_visuals.py" "$OUT/visuals2" | grep FAIL; fail=1; }
echo "== video (Remotion × three.js) =="
python3 "$ROOT/tests/test_video.py" "$OUT/video" > "$OUT/video.log" 2>&1; tail -1 "$OUT/video.log" | grep -q " 0 failed" && echo "✓ video ($(tail -1 "$OUT/video.log"))" || { grep -E "FAIL|SKIP" "$OUT/video.log"; fail=1; }
echo "== exports =="
python3 "$SF/scripts/export.py" "$OUT/washi.html" --pdf "$OUT/washi.pdf" | grep -q "16 pages" && echo "✓ pdf" || { echo "✗ pdf"; fail=1; }
exit $fail
