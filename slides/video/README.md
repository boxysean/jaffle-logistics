# Deck video

Turn the shareholder deck into video. This is the first try: a working render pipeline
plus one 30-second proof clip.

## The clip

    slides/video/out/jaffle-30s.mp4   (30.0s, 1280x720, H.264, ~1.7 MB, committed)

A 30-second cut of the deck (the light cut in `slides/deck-light/manifest.txt`): the title,
the business in brief, the year in numbers, the one account that fell behind, Amsterdam bay 3,
analytics engineer to context engineer, and the close. Each clip's `narration` is that slide's
real speaker notes, copied verbatim (the manifest's `notes=` if it has one, else the slide's
own `<aside class="notes">`).

## Files

    script.json       the one file we edit: clips, durations and cues
    anim.css          CSS the seek hook needs (SVG bars scale about their own baseline)
    seek.js           the `?t=` seek hook: holds every animation at an exact time
    render_video.py   builds the deck, drives Chromium over CDP, encodes with ffmpeg
    probe/            the step-1 proof that headless Chromium can capture deterministic frames

## How it works

Headless Chromium cannot record video, so we capture **deterministic frames**: for each
frame the deck is loaded with the animation clock seeked to an exact local time and
screenshotted, then ffmpeg encodes the sequence.

`render_video.py` builds the deck (`slides/build_deck.py`), injects `anim.css` + `seek.js`
into a throwaway copy (`out/presentation-video.html` — the real `slides/presentation.html`
is never touched), along with the manifest's slide names in deck order as
`window.__vslides`. Clips address slides by name (`?name=bay3`), never by position, and the
hook resolves the name at runtime, so reordering the manifest cannot render the wrong slide.
It then launches one persistent Chromium and drives it over CDP. Per frame it
calls `window.__vseek(t)`, which recomputes and writes every animated value as inline
styles, so a screenshot at `t=1.5` is always the same pixels.

The animation, using only CSS/SVG transforms on existing elements:

- panels fade + rise in reading order, stepped to match the 16-bit skin;
- chart bars grow from their baseline;
- chart lines draw left to right (stroke-dashoffset);
- numbers on screen count up to their final value.

Frames cache under `out/frames/` (one directory per clip), so a re-run after a small edit
only re-renders what changed. `--force` ignores the cache.

## Run it

    python3 slides/build_deck.py                       # optional; render_video builds it too
    python3 slides/video/render_video.py \
        --script slides/video/script.json \
        --out slides/video/out/jaffle-30s.mp4

Requires ffmpeg and a Chromium under `~/.cache/ms-playwright/`. No npm, no GPU, no
services.

## Adding a clip

Add an entry to `script.json`. `slide` is a manifest slide's file name without `.html`
(e.g. `storm`); the render stops if it is not in the manifest. `seconds` is the clip's length; `cues` shift the start of
each animation group (`panels-in`, `charts`, `count-up`) in seconds local to the clip.
