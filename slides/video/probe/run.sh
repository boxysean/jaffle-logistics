#!/usr/bin/env bash
cd "$(dirname "$0")"
CHROME=/home/hermes/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome
for b in 500 1000 2000; do
  timeout 90 "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1280,720 \
    --virtual-time-budget=$b --screenshot="vt-$b.png" "file://$PWD/square.html" >/dev/null 2>&1
  echo "budget=$b exit=$?"
done
ls -la vt-*.png
