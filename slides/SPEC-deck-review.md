# SPEC — deck revisions from the business user's slide-by-slide review

Work ONLY in `slides/presentation.html` (plus `slides/render_deck.py` where section 10 says so).
This is a Reveal.js deck: one `<section>` per slide inside `.reveal .slides`. The status-bar slide
number is generated at runtime from the section count — never hand-number anything.

Identify each slide by its `<h2>` heading, never by index. **Delete nothing that is not named here**,
and **add no slide that is not named here** (other cards are adding slides to this same file).

All numbers below are verified facts from the shipped seeds and the merged reports — use them
exactly, invent nothing. If a number is not given here, do not put it on a slide.

Match the deck's existing CSS, fonts, palette (`--deep --navy --navy-2 --teal --teal-hi --hot --amber
--text --dim`), pixel/mono fonts, `.panel`/`.tab` borders, `.hd` header, `.src` caption and status-bar
conventions. No new libraries. Inline SVG only. Every chart keeps `class="chart"` and its
`role="img" aria-label`.

Add ONE new palette variable next to the others in `:root`: `--violet: #a06bff;` (used only for Q4,
section 4). Everything else uses existing colours.

--------------------------------------------------------------------------------
## 1. Slide "THE BUSINESS IN BRIEF"
--------------------------------------------------------------------------------
Current section: `<section data-src="reports/company-profile.md">` with `.panel.hd`, `.panel.brief`
(a `<ul>` of 4 bullets) and `.tiles` (3 `.panel.tile`).

1. **Delete the third bullet** of `.brief` — the line `Five hubs across five countries, <strong>one of them outside the EU</strong>.`
2. **Delete all three tiles** inside `.tiles` (the `5 HUBS`, `97%`, `€52,954.86` tiles).
3. **Replace the right-hand bar with the network map**, as inline SVG in the `.tiles` area
   (position `left:744px; top:148px; width:516px; height:452px`). The map shows **only the city
   names** and the customs point on the non-EU leg — **no other furniture** (no capacities, no
   on-time, no stats, no legend beyond the customs label).
   Draw it in the deck's retro register (square nodes, stepped/right-angle connector lines from
   Amsterdam, hard pixels — model it on `slides/map-retro.html`'s figure but as a compact schematic,
   no d3, no external data). Geography (approx. positions in the 516x452 box, north up):
     - AMSTERDAM — HQ, top-centre/north-west
     - BERLIN — north-east
     - PARIS — west/south-west
     - VIENNA — east/south-east
     - ZÜRICH — centre-south
   Spokes run from Amsterdam (the HQ) to each other city. The **Zürich** spoke is the non-EU leg:
   draw it dashed and mark it with a small `CUSTOMS` tag at the Swiss line. Every node is labelled
   with its **city name only** (`AMSTERDAM PARIS BERLIN VIENNA ZÜRICH`). Nothing else on the map.
4. **Make clearer that the business moves different products.** The seeds support this exactly
   (`seeds/clients.csv`, `seeds/shipments.csv`): the five accounts sit on **three lines of business** —
   **LTL** (Werke, Papier), **last-mile** (Warenhuis, Maison) and **warehousing** (Getränke) — and the
   book carries **three service levels**: **standard, freight, expedited** (2025: 1,123 standard /
   479 freight / 407 expedited of 2,009). Add one bullet to `.brief`, e.g.
   "It moves <strong>different freight for different accounts</strong> — LTL, last-mile and
   warehousing — at <strong>three service levels</strong> (standard, freight, expedited)."
   Do not invent a product line, a commodity or a market. Keep the existing bullets 1, 2 and 4
   ("a promise, not just transport": the 1%-per-point / 10% cap SLA wording stays).

--------------------------------------------------------------------------------
## 2. Remove the standalone network-map slide
--------------------------------------------------------------------------------
Delete the whole `<section class="img" … data-src="slides/map-retro.html">` slide (the full-bleed
"European Network" image slide). Do **not** delete `slides/map-retro.html` or `slides/png/map-*.png`
— those stay for the docs gallery.

--------------------------------------------------------------------------------
## 3. Slide "THE YEAR IN NUMBERS"
--------------------------------------------------------------------------------
Current section: `<section class="res" data-src="revenue_ledger">`, heading `THE YEAR IN NUMBERS`,
sub `.owns` = `FY2025, and the two years before it`; a `.strip` of 3 tiles; a `.grid.years` of four
chart panels (`REVENUE · €M`, `ON TIME · %`, `CREDITS · €K`, `MAINTENANCE · €K`); and a `.notes`
block of three `<p>`.

1. **Overlay volume on the on-time chart.** In the `ON TIME · %` panel, add **shipments per year as a
   secondary series** so reliability is read against volume. Verified data:
       on-time %   : 2023 97.51 · 2024 97.23 · 2025 93.28
       shipments   : 2023 1,848 · 2024 1,949 · 2025 2,009
   Give the panel two scales — on-time % (left, keep the existing 90/95/100 gridlines and the 97%
   target line) and shipments (right, a small axis), with a compact legend naming both series.
   The 2023–24 shipments are **not** identical to 2025 (the old "2,009 every year" claim is obsolete —
   `seeds/shipments.csv` holds 1,848 / 1,949 / 2,009), so draw the real series. Add **one short line**
   to the panel making the point: volume rose only about 3% a year (1,848 → 1,949 → 2,009), so the 2025
   fall is a **reliability** fall, not a volume one.
2. **Delete the three `<p>` lines** in `.notes` (the whole `.notes` block).
3. **Subheading**: change `.owns` to exactly `FY2023 - FY2024 - FY2025`.
4. **Profit margin — state honestly what is missing** (do NOT compute or invent a margin). Verified
   from `reports/company-profile.md` §3: revenue is a **real** ledger; the cost ledger is **modelled**,
   **by hub/month**, and runs about **2.49×** gross revenue (2023 2.43×, 2024 2.37×, 2025 2.49×); the two
   ledgers were not built to reconcile; there is **no P&L, no balance sheet and no per-account cost**
   (only modelled maintenance is assignable). Put **one short line** on the slide stating that a margin
   cannot be computed and what is missing (put it where the deleted `.notes` was, or as a compact tile).

--------------------------------------------------------------------------------
## 4. Slide "THE QUARTERS"
--------------------------------------------------------------------------------
Current section: `<section class="res" data-src="revenue_ledger">`, heading `THE QUARTERS`, sub
`.owns` = `How 2025 unwound, three months at a time`; a `.grid.quarters` with a wide on-time chart
plus `REVENUE · €K`, `SERVICE CREDITS · €K`, `DISPATCH EXCEPTIONS`; and `.notes` of two `<p>`.

1. **Subheading**: change `.owns` to exactly `FY2025`.
2. **Delete the two `<p>` lines** in `.notes` (the whole `.notes` block).
3. **Colour Q1 as the storm quarter and give Q4 its own separate colour.** Q1 = `--hot` (the storm);
   Q4 = `--violet` (new var); Q2/Q3 stay the default `--amber`. Apply consistently across the slide's
   four panels' 2025 marks (the on-time Q1/Q4 points, and the Q1/Q4 bars in the revenue, credits and
   exceptions charts). Add a compact one-line legend in the header area: `Q1 storm · Q4 late-year drift`.
   Verified 2025 series:
       on-time %:  Q1 90.33 · Q2 95.40 · Q3 95.12 · Q4 92.62   (2024 ghosts: 97.03 97.39 97.48 97.06)
       revenue €k: 695.8 · 635.5 · 697.6 · 850.8
       credits €k: 4.8 · 7.2 · 13.5 · 27.5
       exceptions: 1,209 · 176 · 255 · 781
4. **Answer the question the slide cannot currently answer — why Q4 is bad.** The January storm was
   week 3; it is **not** the cause of Q4. Verified: Q4 2025 ran 44 misses of 596 shipments (92.62%),
   the year's heaviest quarter; **November (16) + December (20) = 36** of those 44. From ISO **week 45
   (w/c 3 Nov 2025)** every one of the five hubs ran above its 2023–24 exception rate, every week, to
   year-end — a network-wide **late-year drift**, separate from the storm. Add **one short, accurate
   line** on the slide naming Q4's own cause (not the storm), and make sure the chart ordering/labels do
   not imply the January storm damaged Q4 (keep/strengthen the `storm` marker on Q1 and the `week 45`
   marker on Q4).

--------------------------------------------------------------------------------
## 5. Move the storm slide
--------------------------------------------------------------------------------
Move the `<section class="storm" …>` slide ("THE STORM WEEK") so it sits **immediately after "THE
QUARTERS"** (and before "CUSTOMER REVIEW"). Change nothing else about it.

--------------------------------------------------------------------------------
## 6. Slide "ACTUALS AGAINST THE CONTRACT" → rename "CUSTOMER REVIEW"
--------------------------------------------------------------------------------
Current section: `<section class="res" data-src="ledger + contracts">`, heading
`ACTUALS AGAINST THE CONTRACT`, a `.grid.accounts` of five per-account quarter charts (each with `.tab`
tier, the account name, `contract NN%`, and a Y grid of 80/90/100%), plus a `.panel.band` of findings.

1. **Rename the heading** to exactly `CUSTOMER REVIEW`.
2. **Show each account's contract size** — the revenue it represents. Add a compact revenue line to
   each account panel (e.g. under the account name: `€963,695 · 33.5%`). Verified 2025 gross revenue:
       Jaffle Werke    €963,695  (33.5% of revenue)
       Jaffle Papier   €524,260  (18.2%)
       Jaffle Getränke €487,795  (16.9%)
       Jaffle Maison   €458,802  (15.9%)
       Jaffle Warenhuis €445,180 (15.5%)
       whole book      €2,879,732
3. **Label the Y axis on every account chart.** The reader cannot tell what the vertical axis measures.
   Add a short vertical-axis title (`on-time %`) to each of the five charts (and label it clearly enough
   that 80/90/100 read as percentages).

--------------------------------------------------------------------------------
## 7. "EXECUTIVE LEADERSHIP" slide — rebuild as native deck artwork
--------------------------------------------------------------------------------
Currently the deck has a full-bleed **image** slide `<section class="img exec" … data-src="slides/exec-retro.html">`
(the rendered management-team screen). **Delete that image section** and build a **new native slide**
(class `res` or a new class in the deck's own register — same `.panel`/`.tab`, pixel font, palette,
`.hd` header, auto status bar; NOT `class="img"`, so the status bar shows).

- Place it **immediately after the "CUSTOMER REVIEW" slide**.
- Heading: `EXECUTIVE LEADERSHIP`. Sub `.owns`: one short line, e.g. `Seven seats, one headline number each`.
- Lay out the **seven seats** as native panels (a grid of 7, e.g. 4 + 3), each: `No.0x`, role name,
  its mandate (`OWNS …`) and **one headline number** — matching the seat slides exactly:
       No.01 CHIEF FINANCIAL OFFICER      · where the money goes        · headline +157%
       No.02 CHIEF OPERATING OFFICER      · whether the network runs    · headline 93.3%   (97.5 ▸ 97.2 ▸ 93.3 on time)
       No.03 CHIEF REVENUE OFFICER        · whether the book holds      · headline ~1/3    (one account ≈ 1/3 of revenue, ≈ 1/2 the misses)
       No.04 CUSTOMER EXPERIENCE          · what the customer feels     · headline 17 ▸ 17 ▸ 72  (that account's tickets)
       No.05 FLEET & MAINTENANCE          · what the assets cost        · headline 63%     (collision repair, share of 2025 maintenance)
       No.06 PEOPLE                       · who actually drives         · headline 0 / 56  (drivers with a current certification)
       No.07 DATA                         · can we trust the numbers    · headline 1,848 / 1,949 / 2,009  (shipments by year)
   Do not repeat the obsolete "2,009 every year" claim anywhere. Keep `slides/exec-retro.html` and
   `slides/png/exec-*.png` (docs gallery).

--------------------------------------------------------------------------------
## 8. Slide "HEAD OF CUSTOMER EXPERIENCE" → rename "CUSTOMER EXPERIENCE"
--------------------------------------------------------------------------------
Current section: `<section data-src="reports/persona-customer-experience.md">`, heading
`<span class="no">No.04</span>HEAD OF CUSTOMER EXPERIENCE`, a `.panel.stats` and a `.panel.facts`.

1. **Rename the heading** to `<span class="no">No.04</span>CUSTOMER EXPERIENCE`.
2. **Add a breakdown of the top three ticket topics**, using the real classification already in the
   corpus (`eval_ticket_triage.true_category` — the machine-graded ticket categories). Verified 2025
   counts (all 189 tickets): **general_inquiry 100 · delivery_delay 61 · delivery_failed 24 ·
   wrong_item 4**. Show the categories and counts (top three highlighted), and label the basis plainly
   (e.g. `machine-graded ticket categories, 2025`). If space forces a cut, keep the three named topics
   and the counts for the whole book.
3. **Cost per ticket — investigate and state honestly.** There is **no defensible handling cost** in
   the data: `seeds/support_tickets.csv` has no cost column (only `first_response_hours`,
   `resolution_hours`), the cost ledger is by hub/month and prices no ticket or exception, and payroll
   is driver pay, not agent handling. Do **not** invent a cost per ticket. Put **one short line** on
   the slide saying no per-ticket handling cost exists in the data, and name what is missing.
   Keep the existing slide content (tickets 17→17→72, 124 of 327 resolved-not-positive, Warenhuis 29→16).

--------------------------------------------------------------------------------
## 9. Slide "EVERY NUMBER TRACES BACK" — add structured vs unstructured volume
--------------------------------------------------------------------------------
Current section: `<section class="lin" data-src="reports/persona-data.md">`. Add **one clear line or a
small paired readout** with the bytes of structured against unstructured data. Verified from the
repository's own source files under `seeds/` (26 files, classified by whether the file is a tabular
record set or free text) — count them yourself and use these figures:

- **structured: 19 tabular files, ~156,000 rows — 16,615,523 bytes (~16.6 MB)**
- **unstructured: 7 free-text files (call transcripts, CRM notes, dispatch notes, HR docs, incident
  reports, legal docs, Slack threads) — 715,924 bytes (~716 KB)**

Make the point that the free text is exactly what the **23 AI models** read, and the pipeline carries
both kinds of data to the same warehouse. Label the basis plainly: `source files as shipped: tabular
vs free text` (so nobody mistakes a file size for a warehouse table size). Place it so nothing is
clipped — the slide's bands run 140–272 / 296–442 / 466–578 / 590–648 and the status bar sits at 664.
A short second `.foot` line, or an extra line inside the `.cost` panel, are both acceptable if they fit.

--------------------------------------------------------------------------------
## 10. Renderer + docs
--------------------------------------------------------------------------------
- `slides/render_deck.py` hardcodes the **main repo** slides path (`SLIDES_DIR =
  "/home/hermes/projects/jaffle-logistics/slides"`) and `COUNT = 18`. Change it so it renders **this
  working tree's own deck**: set `SLIDES_DIR = os.path.dirname(os.path.abspath(__file__))` and derive
  `COUNT` from the file (count the `<section` elements in `presentation.html`) instead of a literal.
  Keep everything else (the Playwright chromium glob, `--window-size=1280,720`, per-slide `#/i`
  screenshots) exactly as it is. Note: after this work the deck is **17 slides**.
- Do **not** edit `docs/` — the orchestrator regenerates the docs page after rendering.

--------------------------------------------------------------------------------
## 11. House rules
--------------------------------------------------------------------------------
- Never hand-edit a slide number; it is generated at runtime.
- Do not reintroduce the embedded-agent / MCP-client / data feature surfaces — LifeOS-style surfaces
  do not belong here; this is the logistics deck.
- No tokens, environment ids, PATs or personal account names anywhere (the deck is published publicly).
- Keep every existing `data-src` / `data-status` attribute so the status bar stays correct.
