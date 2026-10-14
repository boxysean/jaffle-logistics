#!/usr/bin/env bash
set -euo pipefail
cd /home/hermes/projects/jaffle-logistics/.worktrees/t_21f8c999
git add -A slides/video
git commit -q -F - <<'MSG'
Deck video: probe proves deterministic frame capture (WAAPI seek)

Step 1 checkpoint. Throwaway square test: --virtual-time-budget alone drifts
(pixels ~50ms behind the requested time), while seeking document.getAnimations()
currentTime via ?t= lands exactly (t=0/0.5/1/2 -> x=0/250/500/1000).
MSG
git log --oneline -1
