# Add an architecture slide to the shareholder deck, after "EVERY NUMBER TRACES BACK"

Add **one new slide** to `slides/presentation.html`, placed **immediately after the
`EVERY NUMBER TRACES BACK` slide** (the one with `<section class="lin" ...>`) and **before the
`WE AUDITED OURSELVES` slide**. Nothing else in the file may change except: the new `<section>`,
its CSS block, and the `<!-- 18. ... -->` style comment above the following slide (renumber the HTML
comments for the two slides after yours so the sequence stays ascending).

Do **not** touch the status bar: it is generated at runtime from the slide count.

Match the deck's existing retro style exactly - read `slides/presentation.html` first for its CSS,
fonts, colours, panel borders, tab/label conventions and footnotes. **Inline SVG only; no libraries,
no gradients, no shadows on SVG marks.** The whole slide is one fixed 1280x720 frame.

This deck is **published on a public GitHub Pages site**. Product names (dbt Platform, Databricks)
are fine. Never put a token, PAT, environment id, account number, host URL, or any personal name on
the slide - in particular do **not** print the lakehouse schema name anywhere (it embeds a personal
name). All counts below are verified against the repository and the platform: use them exactly,
invent nothing.

## Heading

`THE WHOLE STACK`

**Subheading:** `Twelve operational systems, one build overnight, and the way out to an agent`

`data-status` for the section: `the architecture` (no `data-src`).

## Geometry (fixed - keep every gap clear; a panel's tab stands 12px above its top border and its
## shadow 10px below its bottom border, so 24px gaps stay clear)

- `.hd` header panel: `left:20px; top:20px; width:1240px; height:96px` (same as `.lin .hd`).
- Diagram panel: `left:20px; top:140px; width:1240px; height:300px`, tab `THE STACK, LEFT TO RIGHT`,
  inner padding `12px 18px 6px`. Bottom edge 440.
- Two lower panels, `top:464px; height:142px`: left `left:20px; width:608px` (tab `THE AI LAYER`),
  right `left:652px; width:608px` (tab `WHAT BUILDS IT`). Bottom edge 606.
- Footnote `.foot`: `left:20px; top:620px; width:1240px; font-size:22px; color:var(--dim);
  white-space:nowrap`.

## The diagram (inline SVG, `width="1196" height="270" viewBox="0 0 1196 270"`)

One left-to-right band of **five** boxes, in the deck's own register: chunky square corners
(`shape-rendering: crispEdges`), 2px teal outline on the deep background, pixel-font layer title
above each box, mono labels inside. Colour follows `.lin`: teal = where the data lives, amber = the
platform's own layers, teal-hi = what a consumer reads.

Box geometry: `width=207, height=104, y=20`; x positions `0, 247, 494, 741, 988`. Arrows between
each pair of boxes: a teal-hi shaft at `y=72` from `x=(prev right edge)` to `x=(next left edge - 12)`
with a teal-hi triangle head, exactly like `.lin .chart .arw`.

Layer title (pixel, 12px, centred over its box, `y=12`): `SOURCES`, `LANDING`, `TRANSFORMATION`,
`CONTEXT + AI`, `CONSUMPTION`.

Inside each box, four centred lines, first line mono 14px `text.val` (the headline), then three mono
12px lines: the first teal-hi-ish for the box that is the consumer, dim otherwise. Lines are:
`x = box_x + 103.5`, `y = 52, 74, 92, 110`.

- SOURCES: `26 SOURCE FILES` / `12 operational` / `systems, seeded` / `not connected`
- LANDING: `raw relations` / `in the lakehouse` / `structured +` / `unstructured text`
- TRANSFORMATION: `24 staging · 3 int` / `8 marts` / `dbt on the` / `dbt Platform`
- CONTEXT + AI: `25 context models` / `23 of them AI` / `vectors · 10 metrics` / `semantic layer`
- CONSUMPTION: `the persona reports` / `this deck · the docs site` / `read over MCP`

Amber for the platform's own layers: give boxes 3 and 4 an amber outline (`.plat` style, stroke
`var(--amber)`), and SOURCES/LANDING a teal outline, CONSUMPTION a teal-hi outline (`.rep` style).

**The agent marker**, a dashed amber rectangle attached under the two right-hand boxes - it ties to
the agentic-layer slide and is the slide's one small marker, not a second diagram:
`x=741, y=148, width=455, height=56`, `fill:none; stroke:var(--amber); stroke-width:3;
stroke-dasharray:12 8`. One short teal-hi arrow from `x=860, y=148` up to `x=860, y=126` pointing
into CONTEXT + AI's bottom border. Inside it, three centred lines at `x=968.5`:
- `y=170` pixel 11px amber: `AGENT PLUGS IN HERE`
- `y=188` mono 13px `text`: `MCP tool surface · 43 tools · lookup + vector cosine`
- `y=202` mono 13px dim: `scoped per account and time`

## Panel `THE AI LAYER` (left, 608x142, padding 12px 14px 6px, font 20px)

Four lines, font 20px, colour `var(--dim)`, the key term in `var(--text)`:

1. `Embeddings: ai_query('databricks-gte-large-en')`
2. `Retrieval: vector_cosine_similarity, top k`
3. `Seven document sources, one knowledge_base`
4. `The query embeds with the same model as the corpus`

(Tab carries the heading `THE AI LAYER`; put `<b class="amb">` on nothing here - keep it dim with
the model name and function names in `var(--text)`.)

## Panel `WHAT BUILDS IT` (right, 608x142, same padding, font 20px)

Four lines, dim, numbers in `var(--text)`:

1. `Nightly job 933320 - one build, end to end`
2. `seed 5.4 min · run 35.3 · test 0.9 = 42 min`
3. `Same three commands every night, on a schedule`
4. `A failing test stops the release`

## Footnote

`Seeded, not connected: 26 files stand in for the managed connectors of a live deployment.`

## Style notes

- Add one CSS block under the existing `.lin` block, commented like the others, with the fit budget
  spelled out in the comment (the deck's convention): 20px mono is 12px/char, 23px/line; a lower
  panel is 580 inside, so 48 characters a line, 4 lines = 92 of 118 available; the footnote's 84
  characters at 22px need 1109 of 1240.
- Class name for the slide: `arc`.
- Do not renumber the status bar or change any other slide's content.
