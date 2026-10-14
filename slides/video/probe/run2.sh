#!/usr/bin/env bash
cd "$(dirname "$0")"
CHROME=/home/hermes/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome
for t in 0 0.5 1 2; do
  timeout 90 "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1280,720 \
    --virtual-time-budget=3000 --screenshot="seek-$t.png" "file://$PWD/square2.html?t=$t" >/dev/null 2>&1
  echo "t=$t exit=$?"
done
ls -la seek-*.png
