# Brief: a retro shareholder presentation deck (Reveal.js, ~11 slides)

Build **one self-contained HTML deck**: `slides/presentation.html`. Use **Reveal.js** (the
easy web-based slide library) loaded from a pinned CDN — `https://cdn.jsdelivr.net/npm/reveal.js@5`.
No build step, no bundler: a single file that opens in a browser and is navigated with the
arrow keys. 16:9 canvas (1280x720 in reveal.js units), slide numbers visible.

## The look: 1990s console management game

Match the two graphics already in this folder (`map-retro.png`, `exec-retro.png`) — a
shareholder deck skinned as a 16-bit tycoon-game screen:

- Deep navy/near-black background, panel borders, one hot accent for emphasis (the game
  screens use an amber/orange accent), amber highlights for the numbers that matter.
- A pixel display face (Google Fonts has pixel faces) for **headings and labels only**, on a
  monospace body face — never set a paragraph in a pixel font, it is unreadable at size.
- A persistent bottom status bar on every slide: company name on the left, `SLIDE 03 / 11`
  in the middle, and `synthetic dataset` on the right. Repeat it, do not rely on reveal's own
  page numbers alone.
- Body text must stay **24px or larger** at 1280x720. Dense is fine; small is not.
- No purple/indigo gradient, no glassmorphism, no rounded-square icons.

## The slides (11). Use exactly this content — do not invent numbers or claims

**1. Title.** `JAFFLE LOGISTICS` / `European Network · Shareholder Briefing` / a subtitle
line `Amsterdam · Paris · Berlin · Vienna · Zürich` / footer `prepared from the company's own
operating data` and `synthetic dataset`. Give it a game-title feel (a blinking "PRESS START"
style prompt is welcome).

**2. The business in brief.** A European LTL, last-mile and warehousing carrier. Owns its
fleet and drivers (not a broker). Five hubs across five countries, one of them outside the EU.
It sells a promise, not just transport: an on-time service level, backed by a credit of
**1% of monthly spend per point missed, capped at 10%**. Numbers to show as stat blocks:
`5 HUBS · 5 COUNTRIES · 1 NON-EU LEG`, `97% ON-TIME TARGET` (the two strategic accounts),
`€52,954.86 SERVICE CREDITS PAID IN 2025`.

**3. The network.** Full-bleed image `png/map-retro.png`, caption: `Five hubs, one
hub-and-spoke network out of Amsterdam. Zürich crosses a customs border.`

**4. The executive group.** Full-bleed image `png/exec-retro.png`, caption: `Seven seats,
each judged on one number the data can prove.`

**5. CFO — "where the money goes".** Facts: maintenance spend rose **157%** while routes
rose **3.1%**; **€52,954.86** of service credits were paid in 2025, **1.84%** of spend on the
affected account. Report file: `reports/persona-cfo.md`.

**6. COO — "whether the network runs".** Facts: whole-book on-time **93.3%** in 2025, against
**97.5%** and **97.2%** in the two years before; the network turned in **week 45 (w/c 3 Nov
2025)** and never recovered; one winter storm week in Paris produced **570 exceptions**.
Report file: `reports/persona-coo.md`.

**7. CRO — "whether the book holds".** Facts: **Jaffle Werke (CLI-0042)** fell from **97.96%
to 83.89%** on time; that one account is **33.5% of 2025 revenue on 20.7% of shipments**;
the credits it earned are **1.84%** of its spend. Report file: `reports/persona-cro.md`.

**8. Head of Customer Experience — "what the customer feels".** Facts: that account's tickets
went **17 → 17 → 72**; **124 of 327** tickets closed as `resolved` (37.9%) were not actually
resolved; every other account had an ordinary year (Warenhuis 29 → 16 tickets). Report file:
`reports/persona-customer-experience.md`.

**9. Head of Fleet & Maintenance — "what the assets cost".** Facts: the vehicles are **not**
why deliveries failed, once you adjust for how much each one runs; spend rose **157%**
(€104,101 → €267,578) while routes rose **3.1%**; collision repair alone was **€169,799, 63%**
of 2025 spend and **69%** of the increase, and eight collision repairs (€64,191) are
under-reported. Report file: `reports/persona-fleet.md`.

**10. Head of People — "who actually drives".** Facts: **not one of the 56 drivers holds a
current certification** (the latest expired **2025-08-26**) and **nobody was hired in 2025**;
a contractor route cost **€723.02** against **€370.83** for an employee route; six working
drivers in Vienna ran **123.5 routes each, 2.6× a normal load**. Report file:
`reports/persona-people.md`.

**11. Head of Data — "can we trust the numbers".** Facts: the headline numbers hold —
**97.51% → 97.23% → 93.3%**; but the volume figures were an artefact: every year contained
exactly **2,009 shipments**, so year-over-year volume was never comparable; and the reports
now use the European names while **production does not** — the warehouse reload is the open
item. Report file: `reports/persona-data.md`.

## Rules

- Every slide names the report file it came from, so a reader can go to the source.
- Nothing else on the slides: no invented metrics, no filler taglines, no fake quotes.
- Keep the honesty markers: `synthetic dataset` stays on every slide.
- Verify the file loads and that reveal.js initialises (no console errors) before finishing.
- Print-friendly: a reader should be able to use the browser's PDF export.

## Deliverable

One file: `slides/presentation.html`. Save nothing else.
