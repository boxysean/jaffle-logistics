#!/usr/bin/env bash
cd "$(dirname "$0")"
CHROME=/home/hermes/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome
echo "=== budget 2000 ==="
timeout 90 "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1280,720 \
  --virtual-time-budget=2000 --screenshot="one-2000.png" "file://$PWD/square.html"
echo "exit=$?"
ls -la one-2000.png 2>&1
