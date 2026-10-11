# SPEC — add one slide: "THE FUNCTIONS — AND HOW IT RUNS"

You are editing a single file: `slides/presentation.html` (a self-contained Reveal.js deck, ~1577
lines, all CSS inline in one `<style>` block, no libraries except reveal.js + Google Fonts from CDN).
Do NOT touch any other file. Do NOT touch the `<script>` block. Do NOT hand-edit a slide number
anywhere — the status bar is generated at runtime from the section count.

## Step 1 — read the deck first

Read `slides/presentation.html` end to end before writing anything. Match it exactly: the CSS
custom properties (colours, fonts), the `.panel` box model (4px teal border + box-shadow), the
`.panel > .tab` label, the `.hd` header panel with `<h2>` heading and `.owns` subheading, the
`.foot` footnote line, `.frame` wrapper, and the per-slide class convention (`.arc`, `.lin`, `.why`,
`.dt`, `.aud`, `.agt` …). Also read the two slides that bracket the insertion point:
`<section class="arc" data-status="the architecture">` (heading `THE WHOLE STACK`) and the section
after it, `<section class="aud" …>` (heading `WE AUDITED OURSELVES`).

## Step 2 — insert the new section

Insert a new `<section>` **immediately after** the closing `</section>` of the architecture section
(the one whose `<h2>` is `THE WHOLE STACK`, `class="arc"`) and **immediately before** the audit
section (the comment `<!-- 20. The dbt audit -->`). Give it class `fn`, and
`data-status="the functions"`.

Add a matching CSS block for the `.fn` slide in the `<style>` block, placed with the other
per-slide blocks (near `.arc` / `.aud`). Use the same idioms those use. Everything is absolutely
positioned inside a fixed 1280×720 frame; the status bar sits at top:664px, the footnote line at
top:~620px. Stay inside the 1240px content width (left:20px) and above top:620px.

## Step 3 — the slide content (VERIFIED — use exactly these facts, invent nothing)

Heading (`<h2>`): `THE FUNCTIONS · AND HOW IT RUNS`
Subheading (`.owns`): `The functions are commodity. The pipeline between them is the engineering.`

A five-row table with three columns. Column headers: `STAGE`, `WHAT WE RUN`, `WHERE IT LIVES`.
These are the ONLY admissible function/stage facts — every one was verified against the repository
and the Databricks warehouse for this slide:

| stage | what we run | where it lives |
|---|---|---|
| `parse` | **not built** — the sources arrive as text; transcript bodies are exploded into turns and documents split into sentences in plain SQL | — |
| `chunk` | `chunk()` — token-bounded packing, pure window SQL, **no AI call** | dbt models (`models/context`) |
| `embed` | `cast(ai_query('databricks-gte-large-en', ...) as array<float>)` — **1024-dimension** vectors | dbt models (`models/context/ai`) |
| `search` | `vector_cosine_similarity` — top 10, scoped per account and time | the knowledge base (`models/context/ai/search.sql`) |
| `hybrid` | **not built** — retrieval is vector-only; exact identifiers are confirmed with a separate row-level lookup | — |

Rules for the table:
- `parse` and `hybrid` MUST be plainly marked as not built. Do not paper over them and do not
  present a function name we never call. That honesty is the slide's own point.
- Do NOT print any other function name. In particular do not print `ai_embed`, `ai_parse_document`,
  `ai_extract`, `SPLIT_TEXT_RECURSIVE_CHARACTER`, `VECTOR_SEARCH`, or any Snowflake/BigQuery/
  Postgres name — this project calls none of them on its Databricks path.
- Keep the code tokens in the deck's monospace code style (the deck uses `<code>` / a `.k` span).

Then one panel labelled `HOW IT IS RUN`, carrying these four verified points (one line each or a
short bullet list):

1. **Modelled in dbt on the dbt Platform: 24 staging, 3 intermediate and 8 mart models, plus 25
   context models of which 23 are AI.** The AI layer is gated behind the `ai_functions_enabled`
   variable — built deliberately, never as a side effect of an ordinary build.
2. **One platform job rebuilds the whole thing from source.** The last full rebuild took
   **42 minutes** — seed `5.4`, run `35.3`, test `0.9`.
3. **Every model is tested on every build, and a failing test stops the release.**
4. **Cheap checks first: the whole project builds and tests locally in under a minute**, so a change
   is proved before it is ever run against the warehouse.

Footnote (`.foot`), matching the caveat the other slides carry:
`Seeded, not connected: 26 files stand in for the managed connectors of a live deployment.`

## Binding honesty rules

- Public deck: **no tokens, ids, host URLs or personal names.** (In particular do not print the
  Databricks job id, the workspace/schema name, or any account id.)
- No invented performance numbers and no invented function names. The four panel points and the
  table are the entire factual content of this slide.
- Do not oversell the functions — the slide's own point is that they are commodity and the pipeline
  is the engineering.

## Layout bar

A five-row table plus one panel is dense. Keep type sizes consistent with the rest of the deck
(the deck's body text runs ~18–24px; SVG captions smaller). The table must be legible at 1280×720
and nothing may be clipped or overflow its panel. Cut your own connective wording before you cut
any proof. When done, re-read your new section and confirm every row is inside its panel bounds.
