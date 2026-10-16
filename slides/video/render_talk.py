#!/usr/bin/env python3
"""Render the light deck as a narrated video: a voiceover over the slides, cued to it.

    python3 slides/video/render_talk.py --script slides/video/talk.json \
        --out slides/video/out/talk-take-1.mp4

The script (talk.json) names the voiceover and, per slide, the second of the voiceover at
which that slide is on screen (`at`), how it arrives (`transition`, an ffmpeg xfade name)
and, for a slide with click reveals, when each click lands (`steps`). The cue times come
from a word-timestamped transcript of the take.

How it works
------------
Like render_video.py, it captures deterministic frames: the deck is built, the seek hook
(seek.js + anim.css) is injected into a throwaway copy, and one headless Chrome is driven
over CDP. Per slide it captures the entrance animation (panels rise, bars grow, numbers
count up) for `intro_seconds`, then a still of each click-reveal state. ffmpeg holds the
last frame until the next cue, cross-fades each reveal in, joins the slides with their
transitions and lays the loudness-normalised voiceover (EBU R128, -16 LUFS) underneath.

`deck` names the cut to render (slides/video/deck/, the slides cut down for video; without it,
the light deck). Slides are looked up by file stem in that cut's manifest order, which is the
built deck's order. A clip's `intro` overrides `intro_seconds` (the storm slide's truck crash
needs longer). The live deck is never modified.

Needs ffmpeg, Google Chrome (or a Chromium under ~/.cache/ms-playwright/) and the
`websockets` Python package.
"""
import argparse
import asyncio
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
SLIDES = os.path.dirname(HERE)
ROOT = os.path.dirname(SLIDES)
sys.path.insert(0, SLIDES)
sys.path.insert(0, HERE)
import build_deck  # noqa: E402
from render_video import CDP, free_port, page_target, wait_ready  # noqa: E402

VIDEO_PAGE = os.path.join(HERE, "out", "presentation-video.html")
WORK = os.path.join(HERE, "out", "talk")
# click reveals snap in the stills; ffmpeg does the fade between them
EXTRA_CSS = ".vseek .reveal .fragment { transition: none !important; }\n"


def chrome():
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-*/chrome"),
              os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium")):
        hits = sorted(glob.glob(p))
        if hits:
            return hits[-1]
    raise SystemExit("no Chrome or Chromium found")


def start_chrome(port, profile, tries=3):
    """Start headless Chrome with a debug port. The x64 build under Rosetta is slow and now and
    then never opens the port, so a launch that stalls is killed and retried on a fresh port."""
    import urllib.request
    for attempt in range(tries):
        if attempt:
            port = free_port()
        shutil.rmtree(profile, ignore_errors=True)
        os.makedirs(profile, exist_ok=True)
        log = open(os.path.join(os.path.dirname(profile), "chrome-talk.log"), "w")
        proc = subprocess.Popen(
            [chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1", "--window-size=1280,720",
             "--remote-debugging-port=%d" % port, "--remote-allow-origins=*",
             "--user-data-dir=" + profile, "--no-first-run", "--no-default-browser-check",
             "about:blank"],
            stdout=log, stderr=subprocess.STDOUT)
        for _ in range(300):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=0.5):
                    return proc, port
            except Exception:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
        proc.kill()
        proc.wait()
        print("  chrome did not open its debug port (try %d of %d)" % (attempt + 1, tries))
    raise SystemExit("chrome did not open its debug port; see out/chrome-talk.log")


def cut_dir(script):
    """The cut of the deck to render: the script's `deck` folder, or the light deck."""
    return os.path.join(ROOT, script["deck"]) if script.get("deck") else None


def manifest_stems(cut=None):
    """The cut's slides, as file stems, in built order."""
    stems = []
    with open(os.path.join(cut or os.path.join(SLIDES, "deck-light"), "manifest.txt"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                stems.append(os.path.splitext(line.split("|")[0].strip())[0])
    return stems


def build_video_page(cut=None):
    html = build_deck.build(cut)
    if not cut:  # the light deck: keep slides/presentation.html in step with what is rendered
        with open(os.path.join(SLIDES, "presentation.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
    with open(os.path.join(HERE, "anim.css"), encoding="utf-8") as fh:
        css = fh.read() + EXTRA_CSS
    with open(os.path.join(HERE, "seek.js"), encoding="utf-8") as fh:
        js = fh.read()
    html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>", 1)
    html = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>", 1)
    os.makedirs(os.path.dirname(VIDEO_PAGE), exist_ok=True)
    with open(VIDEO_PAGE, "w", encoding="utf-8") as fh:
        fh.write(html)
    return html.count("<section")


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


def events(clip):
    """A clip's timed changes, in order: {"at": s, "reveal": n} lights the next n click reveals,
    {"at": s, "hl": selector} highlights what the voice is talking about (null clears it). The
    older `steps` list is shorthand for one reveal at each time."""
    ev = [dict(e) for e in clip.get("events", [])]
    ev += [{"at": t, "reveal": 1} for t in clip.get("steps", [])]
    return sorted(ev, key=lambda e: e["at"])


def states(clip):
    """The slide's state after each event: (click reveals shown, highlight selector)."""
    shown, hl, out = 0, None, []
    for e in events(clip):
        shown += e.get("reveal", 0)
        if "hl" in e:
            hl = e["hl"]
        out.append((shown, hl))
    return out


def timeline(script, audio_len):
    """Per clip: where it starts in the output (origin) and how long its own video runs.
    A clip starts half a transition before its cue and overlaps the next by one transition."""
    T = script["transition_seconds"]
    clips = script["clips"]
    end = audio_len + script["tail_seconds"]
    out = []
    for i, c in enumerate(clips):
        origin = 0.0 if i == 0 else c["at"] - T / 2
        stop = end if i == len(clips) - 1 else clips[i + 1]["at"] + T / 2
        out.append((origin, stop - origin))
    return out, end


async def capture(script, plan, force):
    fps = script["fps"]
    stems = manifest_stems(cut_dir(script))
    with open(VIDEO_PAGE, encoding="utf-8") as fh:
        page = fh.read()
    profile = os.path.join(HERE, "out", "chrome-profile-talk")
    proc, port = start_chrome(free_port(), profile)
    try:
        async with websockets.connect(page_target(port), max_size=None) as ws:
            cdp = CDP(ws)
            await cdp.call("Page.enable")
            await cdp.call("Runtime.enable")
            await cdp.call("Emulation.setDeviceMetricsOverride", width=script["size"][0],
                           height=script["size"][1], deviceScaleFactor=1, mobile=False)
            for k, clip in enumerate(script["clips"]):
                d = os.path.join(WORK, "%02d-%s" % (k, clip["slide"]))
                st = states(clip)
                reveals = any(e.get("reveal") for e in events(clip))
                n_intro = round(clip.get("intro", script["intro_seconds"]) * fps)
                sig = hashlib.sha1((json.dumps(clip, sort_keys=True) + page).encode()).hexdigest()
                sig_path = os.path.join(d, "sig.txt")
                if not force and os.path.exists(sig_path) and open(sig_path).read() == sig:
                    continue
                shutil.rmtree(d, ignore_errors=True)
                os.makedirs(d)
                sidx = stems.index(clip["slide"])
                url = "file://%s?slide=%d&t=0&cues=%s" % (urllib.parse.quote(VIDEO_PAGE), sidx,
                                                          urllib.parse.quote(json.dumps(clip.get("cues", []))))
                await cdp.call("Page.navigate", url=url)
                await wait_ready(cdp)
                # a slide without timed clicks shows every reveal from the start
                if reveals:
                    await cdp.eval("Reveal.slide(%d, 0, -1)" % sidx)
                else:
                    await cdp.eval("Reveal.getCurrentSlide().querySelectorAll('.fragment')"
                                   ".forEach(function (e) { e.classList.add('visible'); })")
                t0 = time.time()
                for i in range(n_intro):
                    await cdp.eval("window.__vseek(%r)" % (i / fps))
                    await cdp.shot()  # the first capture flushes the paint
                    with open(os.path.join(d, "f-%05d.png" % i), "wb") as fh:
                        fh.write(await cdp.shot())
                for s, (shown, hl) in enumerate(st, 1):
                    if reveals:
                        await cdp.eval("Reveal.slide(%d, 0, %d)" % (sidx, shown - 1))
                    await cdp.eval("window.__vseek(99)")
                    hits = await cdp.eval("window.__vhl(%s)" % json.dumps(hl))
                    if hl and not hits:
                        raise SystemExit("%s: highlight matches nothing: %s" % (clip["slide"], hl))
                    await asyncio.sleep(0.15)
                    await cdp.shot()
                    with open(os.path.join(d, "still-%d.png" % s), "wb") as fh:
                        fh.write(await cdp.shot())
                shutil.copyfile(os.path.join(d, "f-%05d.png" % (n_intro - 1)), os.path.join(d, "still-0.png"))
                with open(sig_path, "w") as fh:
                    fh.write(sig)
                print("  %-40s %d frames, %d states in %.1fs" % (clip["slide"], n_intro, len(st), time.time() - t0))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


def encode_clip(script, k, clip, origin, length):
    """One clip's own video: the entrance animation, held, with each click reveal faded in."""
    fps = script["fps"]
    X = 0.3  # a click reveal's fade
    d = os.path.join(WORK, "%02d-%s" % (k, clip["slide"]))
    out = os.path.join(WORK, "clip-%02d.mp4" % k)
    steps = [e["at"] - origin for e in events(clip)]
    norm = "fps=%d,format=yuv420p,settb=AVTB" % fps
    inputs = ["-framerate", str(fps), "-i", os.path.join(d, "f-%05d.png")]
    first = (steps[0] + X) if steps else length
    intro = clip.get("intro", script["intro_seconds"])
    graph = ["[0:v]tpad=stop_mode=clone:stop_duration=%.3f,trim=duration=%.3f,%s[s0]"
             % (max(first - intro, 0) + 1, first, norm)]
    for s in range(1, len(steps) + 1):
        seg = (steps[s] - steps[s - 1] + X) if s < len(steps) else (length - steps[s - 1])
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", "%.3f" % seg,
                   "-i", os.path.join(d, "still-%d.png" % s)]
        graph.append("[%d:v]%s[s%d]" % (s, norm, s))
    cur = "s0"
    for s in range(1, len(steps) + 1):
        graph.append("[%s][s%d]xfade=transition=fade:duration=%.3f:offset=%.3f[x%d]"
                     % (cur, s, X, steps[s - 1], s))
        cur = "x%d" % s
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", "[%s]" % cur,
         "-t", "%.3f" % length, "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
         "-pix_fmt", "yuv420p", out])
    return out


def loudnorm_filter(audio):
    """Two-pass EBU R128 normalisation to -16 LUFS, true peak -1.5 dB."""
    target = "I=-16:TP=-1.5:LRA=11"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", audio, "-af",
                        "highpass=f=70,loudnorm=%s:print_format=json" % target, "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    print("  voice measured %s LUFS, true peak %s dB" % (m["input_i"], m["input_tp"]))
    return ("highpass=f=70,loudnorm=%s:measured_I=%s:measured_TP=%s:measured_LRA=%s:"
            "measured_thresh=%s:offset=%s:linear=true" % (
                target, m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"],
                m["target_offset"]))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--script", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--force", action="store_true", help="re-capture every slide, ignoring the cache")
    args = p.parse_args()
    with open(args.script, encoding="utf-8") as fh:
        script = json.load(fh)
    audio = os.path.join(ROOT, script["audio"])
    # a clip may start before the voiceover (a negative `at`, e.g. a title card): the whole
    # timeline moves later by that much and the voice is delayed to match
    lead = max(0.0, -min(c["at"] for c in script["clips"]))
    for c in script["clips"]:
        c["at"] += lead
        for e in c.get("events", []):
            e["at"] += lead
        if "steps" in c:
            c["steps"] = [t + lead for t in c["steps"]]
    plan, end = timeline(script, duration(audio) + lead)

    print("built video page: %d slides" % build_video_page(cut_dir(script)))
    os.makedirs(WORK, exist_ok=True)
    asyncio.run(capture(script, plan, args.force))

    clips = [encode_clip(script, k, c, *plan[k]) for k, c in enumerate(script["clips"])]
    print("encoded %d clips" % len(clips))

    T = script["transition_seconds"]
    inputs, graph = [], []
    for c in clips:
        inputs += ["-i", c]
    cur = "0:v"
    for k in range(1, len(clips)):
        kind = script["clips"][k].get("transition", script.get("transition", "fade"))
        graph.append("[%s][%d:v]xfade=transition=%s:duration=%.3f:offset=%.3f[v%d]"
                     % (cur, k, kind, T, script["clips"][k]["at"] - T / 2, k))
        cur = "v%d" % k
    # fade_in_seconds: 0 opens on the first slide as drawn (no fade up from black)
    fade_in = script.get("fade_in_seconds", 0.5)
    graph.append("[%s]%sfade=t=out:st=%.3f:d=1.2[vout]"
                 % (cur, "fade=t=in:d=%.3f," % fade_in if fade_in else "", end - 1.2))
    graph.append("[%d:a]%s,adelay=%d:all=1,apad,atrim=duration=%.3f,aresample=48000[aout]"
                 % (len(clips), loudnorm_filter(audio), round(lead * 1000), end))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    run(["ffmpeg", "-y", *inputs, "-i", audio, "-filter_complex", ";".join(graph),
         "-map", "[vout]", "-map", "[aout]", "-t", "%.3f" % end,
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", args.out])
    print("wrote %s (%.1f s, %.1f MB)" % (args.out, duration(args.out), os.path.getsize(args.out) / 1e6))


if __name__ == "__main__":
    main()
