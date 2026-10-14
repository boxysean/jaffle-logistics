#!/usr/bin/env bash
# Step-1 probe: prove headless Chromium can capture deterministic animation frames.
#
#   bash slides/video/probe/probe.sh
#
# Square slides left->right over 2s, so left px == ms/2.
#   vt-*.png    --virtual-time-budget alone (drifts behind the requested time)
#   seek-*.png  document.getAnimations() currentTime via ?t= (exact)
cd "$(dirname "$0")"
CHROME=$(ls /home/hermes/.cache/ms-playwright/chromium-*/chrome-linux64/chrome | tail -1)

for b in 500 1000 2000; do
  timeout 90 "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1280,720 \
    --virtual-time-budget=$b --screenshot="vt-$b.png" "file://$PWD/square.html" >/dev/null 2>&1
done

for t in 0 0.5 1 2; do
  timeout 90 "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1280,720 \
    --virtual-time-budget=3000 --screenshot="seek-$t.png" "file://$PWD/square2.html?t=$t" >/dev/null 2>&1
done

python3 measure.py .
