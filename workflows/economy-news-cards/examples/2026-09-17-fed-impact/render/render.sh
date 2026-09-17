#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUTPUT_FILE="$ROOT_DIR/market-impact.png"
CHROME_PROFILE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/market-impact-render.XXXXXX")"

cleanup() {
  rm -rf "$CHROME_PROFILE_ROOT"
}
trap cleanup EXIT

if [[ ! -x "$CHROME_BIN" ]]; then
  echo "Chrome executable not found: $CHROME_BIN" >&2
  exit 1
fi

PAGE_URL="file://$ROOT_DIR/index.html"
DOM_OUTPUT="$("$CHROME_BIN" \
  --headless=new \
  --incognito \
  --user-data-dir="$CHROME_PROFILE_ROOT/dom" \
  --disable-gpu \
  --allow-file-access-from-files \
  --virtual-time-budget=1000 \
  --dump-dom \
  "$PAGE_URL" 2>/dev/null)"

if [[ "$DOM_OUTPUT" != *'data-render-ready="true"'* ]]; then
  echo "Page did not reach a render-ready state." >&2
  exit 1
fi

if [[ "$DOM_OUTPUT" == *'data-overflow="true"'* ]]; then
  OVERFLOW_TARGETS="${DOM_OUTPUT#*data-overflow-targets=\"}"
  OVERFLOW_TARGETS="${OVERFLOW_TARGETS%%\"*}"
  echo "Text overflow: $OVERFLOW_TARGETS" >&2
  exit 1
fi

if [[ "$DOM_OUTPUT" != *'data-safe="true"'* ]]; then
  SAFE_TARGETS="${DOM_OUTPUT#*data-safe-targets=\"}"
  SAFE_TARGETS="${SAFE_TARGETS%%\"*}"
  echo "Safe-area violation: $SAFE_TARGETS" >&2
  exit 1
fi

"$CHROME_BIN" \
  --headless=new \
  --incognito \
  --user-data-dir="$CHROME_PROFILE_ROOT/screenshot" \
  --disable-gpu \
  --hide-scrollbars \
  --allow-file-access-from-files \
  --force-device-scale-factor=1 \
  --window-size=1080,1920 \
  --virtual-time-budget=1000 \
  --screenshot="$OUTPUT_FILE" \
  "$PAGE_URL" >/dev/null 2>&1

DIMENSIONS="$(sips -g pixelWidth -g pixelHeight "$OUTPUT_FILE" | awk '/pixelWidth/{width=$2} /pixelHeight/{height=$2} END{print width "x" height}')"
if [[ "$DIMENSIONS" != "1080x1920" ]]; then
  echo "Unexpected dimensions: $DIMENSIONS" >&2
  exit 1
fi

echo "Rendered $OUTPUT_FILE ($DIMENSIONS)"
