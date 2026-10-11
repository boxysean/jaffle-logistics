#!/usr/bin/env python3
"""Rasterise the slide HTML files at 1920x1080 using the Playwright Chromium already on disk.

The browser tool died mid-session and the box has no chromium on PATH, but browser-use left a
full Chromium under ~/.cache/ms-playwright - headless screenshot mode is all this needs.
"""
import glob
import os
import subprocess
import sys

SLIDES = "/home/hermes/projects/jaffle-logistics/slides"
OUT = os.path.join(SLIDES, "png")


def find_chromium():
    pats = [
        "/home/hermes/.cache/ms-playwright/chromium-*/chrome-linux64/chrome",
        "/home/hermes/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        "/home/hermes/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
    ]
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits:
            return hits[-1]
    return None


def main(names):
    chrome = find_chromium()
    if not chrome:
        sys.exit("no chromium found under ~/.cache/ms-playwright")
    print("chromium:", chrome)
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        src = os.path.join(SLIDES, f"{name}.html")
        dst = os.path.join(OUT, f"{name}.png")
        if not os.path.exists(src):
            print(f"  {name}: MISSING {src}")
            continue
        cmd = [
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--force-device-scale-factor=1",
            "--window-size=1920,1080", "--virtual-time-budget=15000",
            f"--screenshot={dst}", f"file://{src}",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        size = os.path.getsize(dst) if os.path.exists(dst) else 0
        print(f"  {name}: exit={r.returncode} png={size} bytes"
              + (f"  stderr={r.stderr.strip()[-160:]}" if r.returncode or not size else ""))


if __name__ == "__main__":
    main(sys.argv[1:] or ["map-retro", "map-dark", "map-light"])
