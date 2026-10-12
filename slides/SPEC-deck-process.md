# SPEC — add one slide: "HOW A QUESTION BECOMES AN ANSWER"

You are editing **two** files, and nothing else:

1. `slides/presentation.html` — the deck (self-contained Reveal.js, all CSS inline in one `<style>`
   block; only CDN deps are reveal.js and Google Fonts).
2. `docs/shareholder-deck.md` — the published page that lists the slides.

Do NOT touch the `<script>` block at the bottom of the deck. Do NOT hand-edit any slide number: the
status bar ("SLIDE nn / nn") is generated at runtime from the section count. Do NOT touch
`docs/shareholder-deck/presentation.html`, `docs/shareholder-deck/png/`, or any other file — the
orchestrator re-renders and copies those after your edit.

## Step 1 — read the deck first

Read `slides/presentation.html` end to end before writing anything. Match it exactly: the CSS custom
properties (colours and fonts), the `.panel` box model (4px border + `box-shadow: 0 0 0 4px var(--deep),
6px 6px 0 4px #000`), the `.panel > .tab` label, the `.hd` header panel (`<h2>` + `.owns`), the
`.foot` footnote line, the `.frame` wrapper, the inline-SVG chart idiom (`.chart`, `shape-rendering:
crispEdges`, square marks, mono/pixel labels), and the per-slide class convention (`.lin`, `.arc`,
`.fn`, `.aud`, `.agt` …).

Read the two slides at the insertion point in particular:
`<!-- 19. The whole stack -->` (`<section class="arc" data-status="the architecture">`, heading
`THE WHOLE STACK`) and the section that follows it (`<section class="fn" data-status="the functions">`).

Also read the reference image `slides/.ref-process.jpg` with your Read tool. It is a vendor's
operational diagram of a "context layer": sources on the left, raw and modelled data, a semantic
layer and context-layer tables, an autonomous agent reached over MCP tooling, and an application on
the right. **Adapt the idea, not the artwork.** Do not reproduce its layout, its boxes, its icons or
any of its wording, and never print a vendor name, logo or mark.

## Step 2 — insert the new section

Insert a new `<section>` **immediately after** the closing `</section>` of the architecture section
(the one whose `<h2>` is `THE WHOLE STACK`, `class="arc"`, ending at the line
`<!-- The functions, and how it runs -->`) and **immediately before** that functions section.
Give it `class="prc"` and `data-status="the process"`.

Add a matching CSS block for `.prc` in the `<style>` block, placed near the `.arc` / `.fn` blocks,
using the same idioms. Everything is absolutely positioned inside a fixed 1280×720 frame: content
runs from left:20px with a 1240px content width; the status bar occupies top:664px; the footnote
line sits at top:~620px. Keep everything clear of those.

Precede the CSS block with a fit-budget comment in the deck's own style (see the comment above
`.fn` or `.arc`): the panel geometry, the type sizes you chose, and how many lines each panel needs
versus how many it can hold.

### Layout skeleton (follow it; adjust only what the fit requires)

- `.prc .hd` — left 20, top 20, width 1240, height 96. Header panel with `<h2>` and `.owns`.
- `.prc .flow` — left 20, top 140, width 1240, height 300, padding 12px 18px 6px. Holds one inline
  `<svg class="chart">` whose viewBox is 1196 × 280 at scale 1 (the same idiom as `.arc .flow`).
- `.prc .ev` — left 20, top 464, width 608, height 142, padding 12px 14px 6px.
- `.prc .action` — left 652, top 464, width 608, height 142, padding 12px 14px 6px.
- `.prc .foot` — left 20, top 620, width 1240, one line, 22px, `color: var(--dim)`.

Each of `.prc .flow`'s, `.ev`'s and `.action`'s tab stands ~12px above its top border and each
panel's shadow runs ~10px below it, so leave the gaps clear.

Colour bookkeeping, following the deck's own lineage convention (comment it in the CSS):
teal = where the data lives · amber = the platform's own layers · teal-hi = what a consumer reads ·
a dashed amber stroke = the agent, drawn the way the architecture slide draws `AGENT PLUGS IN HERE`.

## Step 3 — the slide content (VERIFIED — use exactly these facts, invent nothing)

Heading (`<h2>`): `HOW A QUESTION BECOMES AN ANSWER`
Subheading (`.owns`): `The same loop, whether a person or an agent is asking`

### 3a. The walk — six steps, left to right, in the `.flow` SVG

Six boxes across the 1196px diagram, equal width, with the deck's small teal-hi arrow (`<rect
class="arw">` + `<polygon class="arw">`) between neighbours. Each box: a small pixel-font label
(`font-size: 12px`, `fill: var(--text)` or amber) and two to four short lines of 12px mono. The
step number belongs in the label (`1 · A QUESTION`), so the order is unmistakable without counting.
Do not let any box's copy overflow its box.

1. **A QUESTION** — `why did Paris miss so many deliveries in January?`
   (this is the deck's own question: the storm-week slide asks exactly this)
2. **THE TOOL SURFACE** — `the warehouse's tools over MCP: lookup, lineage, vector search. Never a
   guessed number.`
3. **TWO SOURCES OF TRUTH** — used differently. This box is split into two stacked sub-boxes,
   because the slide's point is that the two are **not** interchangeable:
   - `SEMANTIC LAYER · THE NUMBER` — `10 governed metrics. The definition belongs to the business,
     not to whoever wrote the last query.` (outline in amber)
   - `KNOWLEDGE BASE · THE CAUSE` — `vector cosine, top 10, over 7 document sources: transcripts,
     CRM notes, incidents, dispatch.` (outline in teal-hi)
4. **THE ANSWER** — `the number and the cause, kept visibly apart: 56.60% on time · the 14-16 Jan
   storm.`
5. **THE EVIDENCE** — `lineage, back to the source system that recorded it, and the tests that guard
   those columns.`
6. **THE ACTION** — `a person decides, or an agent acts.` Draw the agent half the way the
   architecture slide draws its dashed amber agent marker.

Along the bottom of the same SVG, inside a dashed amber band spanning the full 1196px, put the
closing statement in two lines of 13px mono, with the first sentence in amber and set apart:

```
THIS LOOP IS A DESIGN, NOT A RUNNING SYSTEM.
The warehouse, the semantic layer, the embeddings and the retrieval are real and built. The agent on
top is what the data now makes possible.
```

### 3b. The two lower panels

`.ev` — tab `THE EVIDENCE, ON THIS ONE ANSWER`, two lines of 18px mono:

- `The number rests on fct_shipments.is_ontime — from stg_shipments + int_shipment_touchpoints —
  back to the transport system that recorded it.`
- `340 tests run on every build, and a failing test stops the release.`

`.action` — tab `THE ACTION`, 18px mono:

- `A person decides, or an agent acts:`
- `route a complaint · raise the service-level risk before the customer feels it · stop a dispatch
  when a driver's certification has lapsed`

Both action lines are the deck's own (the agentic slide's `SLA WATCH` and `GATE` band, and its agent's
step 5).

### 3c. The footnote

`.foot`, one 22px line, declaring the adaptation (this deck is published publicly):

`Adapted from the context-layer pattern, not copied — the same loop in our own register.`

## Binding honesty rules

- **Never imply an agent is in production.** Everything the agent does on this slide is drawn dashed
  and the closing band says plainly that the loop is a design. The warehouse, the semantic layer, the
  embeddings and the retrieval are real and built; the agent on top is not.
- **No vendor logos, marks, names or artwork.** The reference image is a vendor's slide; this is not.
- **Every figure comes from the merged reports or the platform warehouse. Invent nothing.** The only
  figures admissible on this slide are: the question itself; `10` semantic-layer metrics; `top 10`
  cosine retrieval; `7` document sources; `56.60%` Paris on-time in January (and the 14-16 January
  storm); `fct_shipments.is_ontime`, `stg_shipments`, `int_shipment_touchpoints`, `the transport
  system`; `340` tests. Do not add a cost, a duration, a percentage, a tool count, a model name or an
  id of your own. Do not print a Databricks job id, a workspace or schema name, or an account id.
- Do not claim the semantic layer and the knowledge base are one thing, and do not merge the number
  and the cause into a single sentence — keeping them apart is the slide's argument.

## Step 4 — the published page

In `docs/shareholder-deck.md`:

1. Change `Twenty-six slides:` to `Twenty-seven slides:` and add the new slide to that sentence's
   running list — after "the whole stack that produces it" and before "the functions it calls":
   `a slide on the process — how a question becomes an answer —`.
2. In the "Slide by slide" list, insert the new thumbnail as slide **20** and renumber every entry
   after it, so the list ends at slide 27 with `deck-26.png`. The new line is exactly:

   ```
   [![Slide 20: how a question becomes an answer](shareholder-deck/png/deck-19.png)](shareholder-deck/presentation.html)
   ```

   Keep every other line's format byte-identical apart from its number and its `deck-NN.png`.
   There are 27 slides, so `deck-00.png` … `deck-26.png`.

## Layout bar

Six boxes plus a closing band in one diagram is dense. Keep every label and every line inside its box
and inside the 1196px viewBox; nothing may be clipped, and no box may overlap its neighbour or its
arrow. The six steps must read left to right at a glance. Cut your own connective wording before you
cut any of the verified copy. When you are done, re-read your new section and confirm by arithmetic
that every line of text fits the box or panel it sits in.
