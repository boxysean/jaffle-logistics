#!/usr/bin/env python3
"""Render a script of deck clips to one MP4.

    python3 slides/video/render_video.py --script slides/video/script.json \
        --out slides/video/out/jaffle-30s.mp4

How it works
------------
Headless Chromium cannot record video, so we capture *deterministic frames*: the deck is
built, the seek hook (slides/video/seek.js + anim.css) is injected into a throwaway copy,
and then a single persistent Chromium is driven over CDP. Per frame we call
``window.__vseek(t)`` to hold every animation at an exact local time and take a PNG. The
sequence is handed to ffmpeg.

Frames cache under slides/video/out/frames/ (one directory per clip), so a re-run after a
small edit only re-renders what changed. Pass --force to ignore the cache.

The existing deck (slides/presentation.html) and its parts are never modified: the video
page is written to slides/video/out/presentation-video.html.
"""
import argparse
import asyncio
import base64
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
SLIDES = os.path.dirname(HERE)
sys.path.insert(0, SLIDES)
import build_deck  # noqa: E402

DECK = os.path.join(SLIDES, "presentation.html")
VIDEO_PAGE = os.path.join(HERE, "out", "presentation-video.html")
FRAMES = os.path.join(HERE, "out", "frames")
SEQ = os.path.join(HERE, "out", "seq")


def chromium():
    for p in ("/home/hermes/.cache/ms-playwright/chromium-*/chrome-linux64/chrome",
              "/home/hermes/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"):
        hits = sorted(glob.glob(p))
        if hits:
            return hits[-1]
    raise SystemExit("no chromium under ~/.cache/ms-playwright/")


def build_video_page(stems):
    """Build the deck and inject the seek hook into a separate video-only page.

    The manifest's stems go in as window.__vslides, so the hook finds a slide by name."""
    html = build_deck.build()
    with open(DECK, "w", encoding="utf-8") as fh:
        fh.write(html)
    # one top-level <section> per manifest line, in manifest order
    count = len(re.findall(r'<section\b', html))
    if count != len(stems):
        raise SystemExit("built deck has %d slides, manifest names %d" % (count, len(stems)))
    with open(os.path.join(HERE, "anim.css"), encoding="utf-8") as fh:
        css = fh.read()
    with open(os.path.join(HERE, "seek.js"), encoding="utf-8") as fh:
        js = fh.read()
    html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>", 1)
    html = html.replace("</body>", f"<script>window.__vslides = {json.dumps(stems)};</script>\n"
                                   f"<script>\n{js}\n</script>\n</body>", 1)
    os.makedirs(os.path.dirname(VIDEO_PAGE), exist_ok=True)
    with open(VIDEO_PAGE, "w", encoding="utf-8") as fh:
        fh.write(html)
    return count


def manifest_stems():
    """The deck's slide stems in manifest order (= build order). Each must resolve the way
    build_deck.py resolves it: deck-light/slides first, then deck/slides."""
    stems = []
    with open(os.path.join(SLIDES, "deck-light", "manifest.txt"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = line.split(" | ")[0].strip()
            if not any(os.path.exists(os.path.join(SLIDES, d, "slides", name))
                       for d in ("deck-light", "deck")):
                raise SystemExit("manifest names a missing slide file: %r" % name)
            stems.append(os.path.splitext(name)[0])
    return stems


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_chrome(port, profile):
    shutil.rmtree(profile, ignore_errors=True)
    os.makedirs(profile, exist_ok=True)
    proc = subprocess.Popen(
        [chromium(), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         "--force-device-scale-factor=1", "--window-size=1280,720",
         "--remote-debugging-port=%d" % port, "--remote-allow-origins=*",
         "--user-data-dir=" + profile, "--no-first-run", "--no-default-browser-check",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=0.5):
                return proc
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise SystemExit("chromium did not open its debug port")


def page_target(port):
    with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=2) as fh:
        targets = json.load(fh)
    for t in targets:
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            return t["webSocketDebuggerUrl"]
    raise SystemExit("no page target")


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self._id = 0
        self._pending = {}

    async def call(self, method, **params):
        self._id += 1
        mid = self._id
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})
            # otherwise it is an event we do not consume

    async def eval(self, expression, await_promise=False):
        r = await self.call("Runtime.evaluate", expression=expression,
                            returnByValue=True, awaitPromise=await_promise)
        return r.get("result", {}).get("value")

    async def shot(self):
        r = await self.call("Page.captureScreenshot", format="png")
        return base64.b64decode(r["data"])


async def wait_ready(cdp, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        v = await cdp.eval(
            "window.__vseekReady === true && document.fonts.status === 'loaded'")
        if v is True:
            return
        flag = await cdp.eval("String(window.__vseekReady)")
        if flag in ("noreveal", "noslide", "nomatch", "noname"):
            raise RuntimeError("seek hook failed: " + flag)
        await asyncio.sleep(0.1)
    raise RuntimeError("deck did not become ready")


def frame_path(clip_no, slug, i):
    d = os.path.join(FRAMES, "%02d-%s" % (clip_no, slug))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "f-%05d.png" % i)


async def render(script, out, force=False):
    fps = script["fps"]
    size = script["size"]
    stems = manifest_stems()
    count = build_video_page(stems)
    print("built video page: %d slides" % count)

    # check every clip first, so a bad name fails before we launch a browser
    clips = []
    for i, clip in enumerate(script["clips"], 1):
        if clip["slide"] not in stems:
            raise SystemExit("script names a slide not in the manifest: %r" % clip["slide"])
        clips.append((i, clip))

    profile = os.path.join(HERE, "out", "chrome-profile")
    port = free_port()
    proc = start_chrome(port, profile)
    print("chromium on port %d" % port)
    try:
        ws_url = page_target(port)
        async with websockets.connect(ws_url, max_size=None) as ws:
            cdp = CDP(ws)
            await cdp.call("Page.enable")
            await cdp.call("Runtime.enable")
            await cdp.call("Emulation.setDeviceMetricsOverride",
                           width=size[0], height=size[1], deviceScaleFactor=1, mobile=False)

            for clip_no, clip in clips:
                slug = re.sub(r"[^a-z0-9]+", "-", clip["slide"].lower()).strip("-")
                cues = json.dumps(clip.get("cues", []))
                url = "file://%s?name=%s&t=0&cues=%s" % (
                    VIDEO_PAGE, urllib.parse.quote(clip["slide"]), urllib.parse.quote(cues))
                await cdp.call("Page.navigate", url=url)
                await wait_ready(cdp)
                n = round(clip["seconds"] * fps)
                t0 = time.time()
                for i in range(n):
                    dst = frame_path(clip_no, slug, i)
                    if os.path.exists(dst) and not force:
                        continue
                    await cdp.eval("window.__vseek(%r)" % (i / fps))
                    await cdp.shot()  # ignore: first capture flushes the paint
                    data = await cdp.shot()
                    with open(dst, "wb") as fh:
                        fh.write(data)
                print("  clip %d %-46s %d frames in %.1fs" % (clip_no, clip["slide"], n, time.time() - t0))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()

    # assemble the sequence (hardlinks where possible) and encode
    shutil.rmtree(SEQ, ignore_errors=True)
    os.makedirs(SEQ, exist_ok=True)
    k = 0
    for clip_no, clip in clips:
        slug = re.sub(r"[^a-z0-9]+", "-", clip["slide"].lower()).strip("-")
        for i in range(round(clip["seconds"] * fps)):
            src = frame_path(clip_no, slug, i)
            dst = os.path.join(SEQ, "f-%05d.png" % k)
            try:
                os.link(src, dst)
            except OSError:
                shutil.copyfile(src, dst)
            k += 1
    print("assembled %d frames -> ffmpeg" % k)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", os.path.join(SEQ, "f-%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", str(fps),
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("wrote %s (%.2f MB)" % (out, os.path.getsize(out) / 1e6))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--script", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--force", action="store_true", help="re-render every frame, ignoring the cache")
    args = p.parse_args()
    with open(args.script, encoding="utf-8") as fh:
        script = json.load(fh)
    asyncio.run(render(script, args.out, force=args.force))


if __name__ == "__main__":
    main()
