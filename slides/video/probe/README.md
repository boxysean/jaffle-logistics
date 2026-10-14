# Step-1 probe: can headless Chromium capture deterministic animation frames?

The whole pipeline rests on this, so it was proven in isolation before anything was built.

    bash slides/video/probe/probe.sh

Two throwaway pages animate a square across 1000px over 2 seconds (`left: 0 -> 1000px`),
so the square's x position is exactly `t_ms / 2`. `measure.py` finds the square in each PNG
and prints its x range.

    square.html    plain CSS animation
    square2.html   the same animation, plus the ?t= seek hook
    measure.py     locate the magenta square in a PNG and report its x range

Result (the exact rows are stable; the virtual-time drift wanders a little run to run):

    vt-500.png    x ~275..407    <- wanted 250 --virtual-time-budget runs ~50-80ms behind
    vt-1000.png   x ~533..649    <- wanted 500
    vt-2000.png   x 1000..1099   <- wanted 1000 (animation finished)

    seek-0.png    x 0..99        <- exact
    seek-0.5.png  x 250..349     <- exact
    seek-1.png    x 500..599     <- exact
    seek-2.png    x 1000..1099   <- exact

So `--virtual-time-budget` alone is deterministic but clocked a little behind the requested
time, while seeking the Web Animations API (`document.getAnimations()` + `currentTime` via a
`?t=` URL parameter) lands exactly. The pipeline uses the seek approach: `render_video.py`
launches Chromium once and calls `window.__vseek(t)` per frame (`slides/video/seek.js`).
