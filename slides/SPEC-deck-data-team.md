# Task: add one slide to the shareholder deck — "WHY THE DATA TEAM"

You are editing the Reveal.js deck at `slides/presentation.html` in this repository (cwd). Match the
deck's existing conventions exactly. Read the file first.

## 1. Where it goes

Insert the new section **immediately after** the `<!-- 16. Why context engineering -->` section
(the one with `<section class="why" ...>`), and **immediately before** the `<!-- 17. Lineage -->`
comment / `<section class="lin" ...>`.

Then renumber the HTML comment markers that follow, so they stay consecutive:
`<!-- 17. Why the data team -->` for the new one, then `18. Lineage`, `19. The dbt audit`,
`20. The agentic layer`. Do not touch anything else about those sections.

Do **not** hand-edit slide numbers: the status bar ("SLIDE nn / nn") is generated at runtime from the
slide count.

## 2. The CSS block

Add this block in the `<style>` section **immediately after** the existing
`/* why-context-engineering slide: ... */` rule block (i.e. right after the `.why .foot` line) and
before the `/* lineage slide: ... */` comment. Copy the surrounding comment style exactly:

```
  /* why-the-data-team slide: body 176-654. two panels 176-424, the closing statement 448-612,
     footnote 626-654. the header runs to 148 because the subheading carries the business user's
     two-sentence pivot on two lines. fit budget at the deck's type sizes (mono: 14.4px/char at 24px,
     10.8px/char and 20.7px/line at 18px, 12px/char and 23px/line at 20px 600): a panel is 614 wide,
     590 inside its 12px pads = 54 characters at 18px. panel one needs 2 + 2 + 2 + 2 lines with three
     6px gaps = 46 + 41 + 41 + 41 + 18 = 187 of 224 inside; panel two 2 + 2 + 2 + two gaps = 128 + 12 =
     140. the closing statement is the slide's largest type: 1204 inside, its headline at 32px
     (19.2px/char) breaks at 62 characters = 2 lines = 70 tall, the clause beneath at 22px
     (13.2px/char, 25.3px/line) = 2 lines = 51, with an 8px gap = 129 of 146. each tab stands 12px
     above its panel and each shadow 10px below, so the 24px gaps stay clear */
  .dt .hd { height: 128px; }
  .dt .hd .owns { margin-top: 8px; }
  .dt strong { color: var(--amber); font-weight: 600; }
  .dt .pts { position: absolute; left: 20px; top: 176px; width: 1240px; height: 248px; display: grid; grid-template-columns: repeat(2, 1fr); column-gap: 12px; }
  .dt .pts .panel { position: relative; padding: 18px 12px 6px; }
  .dt .pts .k { font-size: 20px; line-height: 1.15; font-weight: 600; color: var(--amber); }
  .dt .pts p { margin: 6px 0 0; font-size: 18px; line-height: 1.15; }
  .dt .pts p.dim { color: var(--dim); }
  .dt .close { left: 20px; top: 448px; width: 1240px; height: 164px; padding: 12px 18px 6px; background: var(--navy-2); border-color: var(--amber); }
  .dt .close > .tab { background: var(--amber); }
  .dt .close .k { font-size: 32px; line-height: 1.1; font-weight: 600; color: var(--text); }
  .dt .close p { margin: 8px 0 0; font-size: 22px; line-height: 1.15; color: var(--dim); }
  .dt .close p strong { color: var(--amber); }
  .dt .foot { position: absolute; left: 20px; top: 626px; width: 1240px; font-size: 22px; line-height: 1.2; color: var(--dim); white-space: nowrap; }
```

## 3. The section markup

Insert exactly this (keep the deck's indentation style, two spaces, as in the section above it).
Every word of the copy below is fixed — do not rewrite, add or invent any of it:

```html
<!-- 17. Why the data team -->
<section class="dt" data-status="who owns the data">
  <div class="frame">
    <div class="panel hd">
      <h2>WHY THE DATA TEAM</h2>
      <div class="owns">Modeling data for BI was analytics engineering. Modeling it for AI is context engineering.</div>
    </div>
    <div class="pts">
      <div class="panel">
        <span class="tab">A DIFFERENT CONSUMER</span>
        <div class="k">Analytics engineering modelled data so a person could read it.</div>
        <p>The right grain, the joins, a metric's definition written down, tests on what must never be null.</p>
        <p>Context engineering models that same data so an agent can read it.</p>
        <p class="dim">Same craft — for a reader who never asks a clarifying question, and never notices a wrong answer.</p>
      </div>
      <div class="panel">
        <span class="tab">LOAD-BEARING FOR AI</span>
        <div class="k">Tests, documented definitions and contracts were good practice for BI.</div>
        <p>For AI they are load-bearing: on the tables an agent reads by name.</p>
        <p class="dim">Our own audit found the contracts and exposures still missing — which is why this slide matters.</p>
      </div>
    </div>
    <div class="panel close">
      <span class="tab">THE TEAM THAT OWNS THE DATA</span>
      <div class="k">The team that owns the data now owns how good the company's AI gets.</div>
      <p>Model quality became answer quality. If the definition of "on time" is wrong in the model, every agent that reads it is wrong — and confidently so.</p>
    </div>
    <div class="foot">An argument, not a measurement. The context layer and the audit are real; the agents are a design.</div>
  </div>
</section>
```

Copy the text verbatim, character for character: the apostrophes in "metric's" and "company's" are
straight ASCII apostrophes, and the quotes around "on time" are straight ASCII double quotes — write
them as-is inside the markup (no entity escaping needed here; the deck escapes only `&` in its own
headings).

## 4. Renderer and docs

- `slides/render_deck.py`: change the hardcoded `COUNT = 18` to `COUNT = 19`. Touch nothing else in
  that file.
- `docs/shareholder-deck.md`:
  - change "Eighteen slides:" to "Nineteen slides:";
  - in the intro paragraph, immediately after "the argument for engineering that context at all,"
    insert "the case for the team that already owns that data,";
  - in the "Slide by slide" list, insert after the Slide 15 line:
    `[![Slide 16: why the data team](shareholder-deck/png/deck-15.png)](shareholder-deck/presentation.html)`
  - then renumber the three following entries to Slide 17 / 18 / 19 and shift their image indices to
    `deck-16.png`, `deck-17.png`, `deck-18.png` respectively. Keep the existing alt-text wording.

Do not create or modify any other file. Do not touch the image-slide HTML, the reports, or the CSS
outside the new block.
