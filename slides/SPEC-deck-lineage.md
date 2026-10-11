# Add a slide for the Head of Data: every number traces back to its source system

Add **one new slide** to `slides/presentation.html`, placed **immediately after the existing
`Head of Data` slide**, so it closes the deck. The deck becomes **sixteen** slides; renumber every
status bar to `SLIDE NN / 16`. Match the existing retro style exactly - same fonts, same colours,
same panel borders, same status bar, same conventions for headings and footnotes. The diagram is
**hand-written inline SVG** (no libraries), in the same 16-bit register as the deck's charts:
chunky boxes, pixel labels, amber for the data platform's own layers, no gradients, no shadows.

The seat voice for this slide is the Head of Data explaining why the company can answer a question
about a number the way it just did. All counts below are verified against the repository and the
platform - use them exactly, invent nothing.

## Heading

`EVERY NUMBER TRACES BACK`

**Subheading:** `From the boardroom to the system that recorded it, in one direction`

## Panel 1 - the lineage, left to right (the diagram)

Three columns with arrows between them:

**Column 1 - `26 SOURCE SYSTEMS`**, a grid of small labelled boxes. Label them with the kinds of
system, not invented product names: `billing`, `CRM`, `ticketing`, `telephony`, `Slack`, `dispatch`,
`telemetry`, `fleet`, `inspections`, `safety`, `HR`, `payroll`, `legal`, `contracts`, `TMS`,
`the ledger`, and so on to fill the grid.

**Column 2 - the platform**, one box with the dbt layers listed inside it, in order:
`24 staging` → `3 intermediate` → `8 marts`, and beside it a second box:
`25 context models · 23 of them AI`.
Label the arrow into column 2: `landed once, loaded continuously`.

**Column 3 - `THE REPORTS · THIS DECK`**, one box.

## Panel 2 - `TWO NUMBERS, TRACED` (the point of the slide)

Two chains, each written as a path from the number to the system that recorded it, with an arrow
between each step:

- `93.28% on time` → `fct_shipments.is_ontime` → `stg_shipments + int_shipment_touchpoints` → `the transport system`
- `€52,954.86 credited` → `fct_account_revenue.credited_amount` → `stg_revenue_ledger` → `billing`

Under them, one line: `Nothing in this deck is a number someone typed. Each one is a column with a
lineage.`

## Panel 3 - `WHAT IT COSTS TO REBUILD ALL OF IT`

The platform's own record of the last full rebuild, one command, from source:

- `seed 5.4 min` · `run 35.3 min` · `test 0.9 min` · **`42 minutes end to end`**
- `The AI enrichment - 23 models - rides along inside that build.`
- `Every model is tested on every build. A failing test stops the release.`

## Footnote (small, at the foot of the content)

`In a live deployment each source arrives through its own connector; in this worked example the 26
sources are seeded, so the whole pipeline runs anywhere.`

Status bar right label: `sources -> marts -> reports`

## Rules

- Insert this slide only, at the end, after the Head of Data slide; the other fifteen slides stay
  exactly as they are apart from the `/ 16` renumbering.
- No invented tool names, no invented vendors, no invented volumes or timings.
- Everything must fit inside the slide with the status bar visible; nothing clipped or overlapping
  (check the panel heights, as earlier slides needed a fix for exactly this).
- Verify the file loads and reveal.js still initialises, and report the renumbering.
