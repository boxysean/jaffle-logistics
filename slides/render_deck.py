#!/usr/bin/env python3
"""Render every slide of the Reveal.js deck to a PNG.

Reveal moves between slides by hash (``#/3``), so each slide is a separate chromium load at
exactly the deck's own 1280x720 canvas - no letterboxing, no scaling.
"""
import glob
import os
import subprocess

SLIDES_DIR = "/home/hermes/projects/jaffle-logistics/slides"
DECK = "presentation.html"
OUT = os.path.join(SLIDES_DIR, "png")
COUNT = 17
SIZE = "1280,720"


def chromium():
    for p in ("/home/hermes/.cache/ms-playwright/chromium-*/chrome-linux64/chrome",
              "/home/hermes/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"):
        hits = sorted(glob.glob(p))
        if hits:
            return hits[-1]
    raise SystemExit("no chromium")


def main():
    chrome = chromium()
    os.makedirs(OUT, exist_ok=True)
    for i in range(COUNT):
        dst = os.path.join(OUT, f"deck-{i:02d}.png")
        url = f"file://{SLIDES_DIR}/{DECK}#/{i}"
        r = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--force-device-scale-factor=1", f"--window-size={SIZE}",
             "--virtual-time-budget=20000", f"--screenshot={dst}", url],
            capture_output=True, text=True, timeout=300)
        size = os.path.getsize(dst) if os.path.exists(dst) else 0
        print(f"  slide {i:02d}: exit={r.returncode} png={size}"
              + (f"  {r.stderr.strip()[-120:]}" if not size else ""))


if __name__ == "__main__":
    main()
