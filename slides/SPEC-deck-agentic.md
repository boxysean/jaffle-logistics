# Add a closing slide: the agentic layer — the support-case agent the storm argues for

Add **one more slide** to `slides/presentation.html`, placed **immediately after the last
slide** (`WE AUDITED OURSELVES`, the `class="aud"` slide, currently the last). The deck becomes
**eighteen** slides. Do **not** hand-edit any status-bar numbering: the numbers are generated at
runtime from the slide count by the script at the foot of the file.

Insert the new `<section class="agt" ...>` block at the very end of `<div class="slides">`, i.e.
after the closing `</section>` of the `WE AUDITED OURSELVES` slide (line ~1059) and before the
`</div>\n</div>` that closes the slides container.

Add the new CSS block immediately after the `/* audit slide ... */` CSS block and before
`/* full-bleed image slides */`, in the same style as its neighbours.

Match the existing retro style exactly — same fonts, colours, panel borders, status bar,
heading/subheading/footnote conventions. **No new libraries.** Anything drawn is inline SVG
in the deck's own register.

The voice is the Head of Data answering the board's "so what?": the warehouse is not there to
be reported on, it is there to put agents on.

## Honesty rules — non-negotiable

- The slide must be **explicit that the agent layer is a design, not something running today**.
  The warehouse, the embeddings, the retrieval and the classifiers are real; the agent is what
  that makes possible. Do not let a reader believe a support agent is in production.
- **Invent nothing.** Every figure is copied from the merged reports.

## Heading

`SO WHAT? PUT AGENTS ON IT`

**Subheading** (`.owns`, with the `px` label prefix like the other persona slides):

`<span class="px">WHAT THE STORM ARGUES FOR</span>a support-case agent, on the data that already exists`

## Section element

```html
<section class="agt" data-src="reports/persona-coo.md" data-status="a design, not live">
```
(`data-status` is the status-bar right label — the honesty flag belongs there.)

## Layout — use these exact measurements

The deck is a fixed 1280x720 screen. The body region runs from y=132 to y=650 and the status
bar sits at `top: 664px`. Panels carry a 4px border and a `6px 6px 0 4px #000` shadow, and a
panel's `.tab` stands 12px above its top border — so **every panel needs at least 24px of clear
space above the next one** (matching the `.lin` slide).

```
.agt .hd     { height: 96px; }                                           /* 20,20 1240x96  -> 116 */
.agt .prb    { left:20px; top:138px; width:1240px; height:116px; padding:12px 18px 8px; }   /* -> 254 */
.agt .cols   { left:20px; top:278px; width:1240px; height:224px;
               display:grid; grid-template-columns: 740px 1fr; column-gap:20px; }
.agt .cols .panel { position: relative; }
.agt .band   { left:20px; top:526px; width:1240px; height:76px; padding:12px 18px 8px; }    /* -> 602 */
.agt .foot   { position:absolute; left:20px; top:626px; width:1240px; font-size:24px; line-height:1.2; color:var(--dim); }
```

Column widths: 740 + 20 gap + 480 = 1240.

## Panel 1 — `.prb`, tab `THE STORM, IN SUPPORT TERMS`

Three bullets, **one line each**, at 24px, on the `.lin .cost` convention (square amber bullet,
`padding-left:20px`, `line-height:1.15`, `white-space:nowrap` so a line that overruns is
visible in a render rather than silently wrapping). Keep each line's **rendered text under 82
characters** — that is the width of the panel's inner line at 24px mono. Use `<strong>` for the
figures (amber, as elsewhere in the deck):

- `Week 3: <strong>570 exceptions</strong>, 23.5% of the year's; Paris on-time <strong>56.60%</strong> against 97%.`
- `Nine weeks to settle; Paris <strong>106 broken routes</strong> against <strong>9.9 per 100</strong> elsewhere.`
- `At-risk account: tickets <strong>17 → 17 → 72</strong>, negative <strong>2 → 3 → 45</strong>, delay every 3 days.`

## Panel 2 — left column, tab `THE AGENT THAT ANSWERS IT`

A one-line lead-in at 24px, then a five-item numbered list at 24px (use the deck's `ol`
counter convention as on the storm slide: `counter-reset`/`counter-increment`, pixel-font
numbers in amber). Each item **one line, under 47 characters rendered** (740px panel minus
padding minus a 26px number gutter):

Lead-in: `An agent on the warehouse that already exists:`

1. `reads the case and the account behind it` (40)
2. `retrieves from knowledge_base by cosine` (38)
3. `classifies it with the 23-model AI layer` (38)
4. `pulls the contract's SLA and the route's status` (46)
5. `drafts the reply; routes the breach to the owner` (47)

(`knowledge_base` should be in a `<code>`-styled span; the five numbers are counts the project
really has — 23 AI-enrichment models exist under `models/context/ai/`.)

## Panel 3 — right column, tab `NOT RUNNING TODAY`

**This panel is the honesty.** Give it the amber border/tab treatment (`.panel` with
`border-color: var(--amber)` and its `.tab` background amber) so it reads as a warning, and
three short sentences at 24px, each allowed to wrap:

- `This is a design, not a deployment.`
- `The warehouse, the embeddings, the retrieval and the classifiers are real.`
- `The agent is what they make possible.`

Do not soften or remove any of these three lines.

## Band — `.band`, tab `WHERE ELSE IT SLOTS`

One row, three cells (`grid-template-columns: repeat(3, 1fr); column-gap: 24px`). Each cell is
one line: a pixel-font label in amber followed by ordinary 24px text, on the `.hd .owns .px`
convention (pixel 16px, `margin-right:12px`, `vertical-align:2px`). Each cell's total rendered
text must fit **two lines at most** inside its ~1170px/3 = 390px column (≈27 chars of 24px mono
plus the pixel label).

- `<b class="px">SLA WATCH</b>the trend, not nine weeks later`
- `<b class="px">GATE</b>block the lapsed driver licence`
- `<b class="px">FLEET</b>flag the collision pattern`

## Footnote — `.foot`

One line, under 82 characters rendered:

`The agent layer is a design: nothing on this slide is deployed. Figures: the merged reports.`

## Rules

- Insert this one slide at the end (after `WE AUDITED OURSELVES`); leave the other seventeen
  slides exactly as they are.
- All four regions must fit with the status bar visible and **nothing clipped or overlapping** —
  check the panel heights before you finish, as this has needed a fix before.
- Verify the file still loads and `Reveal.initialize` still runs, and report what you added.
