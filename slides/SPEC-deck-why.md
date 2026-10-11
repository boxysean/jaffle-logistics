# Task: add one slide to the shareholder deck — "WHY CONTEXT ENGINEERING"

You are editing `slides/presentation.html` in this worktree. It is a Reveal.js deck, one
`<section>` per slide, 1280x720, dark 16-bit game-management styling. **Read the whole file
first**, especially the `<style>` block and the four most recent slides (lineage, audit, agentic)
— your slide must match their conventions exactly:

- every slide is `<section class="X" data-src="..." data-status="...">` wrapping a single
  `<div class="frame">`;
- panels are `<div class="panel NAME">` with an absolutely-positioned title comment in the CSS
  and a `<span class="tab">LABEL</span>` inside;
- the first panel is `<div class="panel hd">` with an `<h2>` heading and a `<div class="owns">`
  subheading;
- the status bar is injected at runtime from `data-status` (or `data-src`) — you do not write it;
- the pixel comments above each CSS block document the fit budget (body extents in px, characters
  per line at the deck's type sizes, lines needed vs available). Write one for your slide too.
- inline SVG only, no libraries, no new fonts, no vendor logos.

## Placement

Insert the new slide **immediately before** the lineage slide
(`<!-- 16. Lineage -->` / `<section class="lin" ...>`), so it renders as slide 16 and the
lineage slide becomes 17. Renumber the `<!-- N. Name -->` comment on every slide after it by +1.
Do not change any other slide's markup, copy, CSS or order.

## Content (use exactly this wording — it is the business user's, keep it verbatim)

Class: `why`. Heading, subheading, four panels in this order:

**Heading (h2):** `WHY CONTEXT ENGINEERING`

**Subheading (.owns):** your own one short line that sets it up. Suggested:
`The case for modelling the business once, before anything reads it`

**Panel 1** — tab `THE REVIEW MOVES UPSTREAM`
- headline (the business user's words, keep them): **Nobody reviews an agent's every step.**
- body (the business user's words): So the context has to be right **before** the work runs.
  The review moves upstream, to the data the agent reads, instead of downstream at the output it
  produced.
- one line under it, in the deck's dim colour, your words: You cannot check every answer, so you
  have to get the inputs right.

**Panel 2** — tab `THE CONTEXT GAP`
- headline: **AI rolled out to every employee in a year, and the context those tools read never
  rolled in.**
- body: The tools arrived; the shared understanding of the business did not arrive with them.

**Panel 3** — tab `TEN WIRES, ONE LAYER`
- headline: **Each tool wired itself straight to raw. One shared context layer replaces the
  wiring.**
- body: Ten tools wired to raw data is ten integrations and ten versions of the truth. Modelled
  once in a context layer, every tool reads the same thing.

**Panel 4** — tab `PAID FOR ONCE`. This one is the slide's closing statement and must dominate
(give it the full deck width and the largest type on the slide).
- headline: **Unengineered context gets paid for three times. Engineered context is paid for
  once.**
- smaller text beneath it, the argument's own logic: Paid once to wire the raw data again for each
  tool; paid again to keep that wiring correct as the sources move; and paid a third time by
  whoever acts on an answer that was wrong.

**Footnote** (like the other slides' `.foot`, dim, one line): `An argument, not a measurement. The
context layer is built; the agents on top are a design.`

## Layout intent

Body region is roughly y=140 to y=650, status bar at y=664 (never overlap it). Suggested: three
panels across the top row (points 1–3, equal columns, 12px gaps), then one full-width panel for
point 4 below them, then the footnote. Panels 1–3 are narrow: their copy may need a smaller type
size than 24px (the deck already uses 16–26px across slides) — pick sizes that fit, and if
something will not fit, **cut your own explanatory lines, never the business user's wording**.
Every point is a headline plus at most a couple of lines; keep it spare.

## Honesty (non-negotiable)

This slide is an argument, not a measurement. Invent no figures, counts of tools, hours or money.
The "three times" is stated as logic, exactly as above. Refer to the context layer, the semantic
layer and the knowledge base as **built** and the agents on top as a **design**, as the rest of
the deck does.

## Also in scope

`slides/render_deck.py` already renders whatever tree it lives in and counts sections
dynamically — do not modify it.

## Verify before you finish

1. Render your slide and its neighbours and look at them:

   ```
   cd slides && python3 - <<'PY'
   import glob, os, re, subprocess
   D = os.path.dirname(os.path.abspath("presentation.html")) or "."
   chrome = sorted(glob.glob("/home/hermes/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"))[-1]
   for i in (14, 15, 16, 17):
       dst = f"/tmp/why-{i:02d}.png"
       subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                       "--force-device-scale-factor=1", "--window-size=1280,720",
                       "--virtual-time-budget=15000", f"--screenshot={dst}",
                       f"file://{os.getcwd()}/presentation.html#/{i}"], check=True)
       print(dst)
   PY
   ```

   (adjust the index range to the slides you actually moved; slide hash `#/N` is 0-based).
2. **Read each PNG with the Read tool** and confirm: four panels, the business wording intact,
   nothing clipped, nothing spilling past its panel or under the status bar, panel 4 clearly the
   heaviest.
3. Fix and re-render until it is clean.

## Do NOT

- Do not touch `docs/`, `docs/shareholder-deck.md`, or any file other than `slides/presentation.html`.
- Do not commit or branch — the orchestrator handles git.
- Do not add figures, logos or reference styling.
