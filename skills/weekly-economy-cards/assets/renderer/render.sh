#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUTPUT_DIR="$ROOT_DIR/output"
CHROME_PROFILE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/market-impact-render.XXXXXX")"

cleanup() {
  rm -rf "$CHROME_PROFILE_ROOT"
}
trap cleanup EXIT

if [[ ! -x "$CHROME_BIN" ]]; then
  echo "Chrome executable not found: $CHROME_BIN" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/weekly-economy-0[1-5].png
RENDERED=0

for CARD in 1 2 3 4 5; do
  PAGE_URL="file://$ROOT_DIR/index.html?card=$CARD"
  DOM_OUTPUT="$("$CHROME_BIN" \
    --headless=new \
    --incognito \
    --user-data-dir="$CHROME_PROFILE_ROOT/dom-$CARD" \
    --disable-gpu \
    --allow-file-access-from-files \
    --virtual-time-budget=1000 \
    --dump-dom \
    "$PAGE_URL" 2>/dev/null || true)"

  if [[ "$DOM_OUTPUT" == *'data-card-available="false"'* ]]; then
    break
  fi
  if [[ "$DOM_OUTPUT" != *'data-card-available="true"'* || "$DOM_OUTPUT" != *'data-render-ready="true"'* ]]; then
    echo "Card $CARD did not reach a render-ready state." >&2
    exit 1
  fi
  if [[ "$DOM_OUTPUT" == *'data-overflow="true"'* ]]; then
    OVERFLOW_TARGETS="${DOM_OUTPUT#*data-overflow-targets=\"}"
    OVERFLOW_TARGETS="${OVERFLOW_TARGETS%%\"*}"
    echo "Card $CARD text overflow: $OVERFLOW_TARGETS" >&2
    exit 1
  fi
  if [[ "$DOM_OUTPUT" != *'data-safe="true"'* ]]; then
    SAFE_TARGETS="${DOM_OUTPUT#*data-safe-targets=\"}"
    SAFE_TARGETS="${SAFE_TARGETS%%\"*}"
    echo "Card $CARD safe-area violation: $SAFE_TARGETS" >&2
    exit 1
  fi

  OUTPUT_FILE="$OUTPUT_DIR/weekly-economy-$(printf '%02d' "$CARD").png"
  "$CHROME_BIN" \
    --headless=new \
    --incognito \
    --user-data-dir="$CHROME_PROFILE_ROOT/screenshot-$CARD" \
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
    echo "Unexpected dimensions for card $CARD: $DIMENSIONS" >&2
    exit 1
  fi
  RENDERED="$CARD"
  echo "Rendered $OUTPUT_FILE ($DIMENSIONS)"
done

if [[ "$RENDERED" -lt 1 ]]; then
  echo "No cards rendered; data.js must contain 1..5 cards." >&2
  exit 1
fi
