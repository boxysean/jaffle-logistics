# Add three results slides, with charts, immediately after the executive-group slide

Insert **three new slides** into `slides/presentation.html`, between the executive-group slide
(slide 4) and the CFO slide. The deck becomes **fifteen** slides; renumber every status bar to
`SLIDE NN / 15`. Match the existing retro panel style exactly - same fonts, same colours, same
panel borders, same status bar - reusing the CSS already in the file.

**Charts are hand-written inline SVG** (there is no charting library in this deck and none may be
added). They must read as part of the same 16-bit game screen: amber for the main series, the
deck's red for failure, a dashed rule for a target line, axis labels in the mono face, no
gradients, no drop shadows, no rounded corners, no chart junk. Label every axis and every value
that matters. Keep body text at 24px or larger; chart labels may be smaller than that but never
below 14px.

Every figure below is verified against the warehouse and reconciles with the reports. Use them
exactly; invent nothing.

---

## Slide A - heading `THE YEAR IN NUMBERS`, subheading `FY2025, and the two years before it`

Data strip at the top, three blocks: `€2,879,732` / `revenue, up 4.55%`, `93.28%` / `on time,
against a 97% target`, `€52,955` / `service credits paid`.

**Chart 1 - revenue by year, bars, €m:** 2023 `2.64`, 2024 `2.75`, 2025 `2.88`. Annotate the 2025
bar: `+€125,326 on 2024`.

**Chart 2 - on-time by year, bars or points with a dashed 97% target rule:** 2023 `97.51`, 2024
`97.23`, 2025 `93.28`. Annotate 2025: `−3.95 points`.

**Chart 3 - service credits by year, bars, €k:** 2023 `0`, 2024 `0`, 2025 `52.96`. Annotate:
`1.84% of gross revenue`.

**Chart 4 - maintenance cost by year, bars, €k:** 2023 `90.4`, 2024 `104.1`, 2025 `267.6`.
Annotate on 2025: `+157%`.

Three short footnotes, each one line:
- `Revenue grew 4.55%. Credits went from nothing to €52,955.`
- `Every year contains exactly 2,009 shipments, so volume is not comparable year to year.`
- `Maintenance more than doubled while routes grew 3.1%.`

Status bar right label: `revenue_ledger + fct_shipments`

---

## Slide B - heading `THE QUARTERS`, subheading `How 2025 unwound, three months at a time`

**Chart 1 - on-time by quarter, a line with a dashed 97% target rule, 2025 solid and 2024 faint
behind it, x axis Q1..Q4:**
2025: `90.33`, `95.40`, `95.12`, `92.62`. 2024: `97.03`, `97.39`, `97.48`, `97.06`.
Annotate Q1 `storm` and Q4 `week 45`.

**Chart 2 - revenue by quarter, bars, €k:** Q1 `695.8`, Q2 `635.5`, Q3 `697.6`, Q4 `850.8`.

**Chart 3 - service credits by quarter, bars, €k:** Q1 `4.8`, Q2 `7.2`, Q3 `13.5`, Q4 `27.5`.
Annotate: `5.8x through the year`.

**Chart 4 - dispatch exceptions by quarter, bars:** Q1 `1,209`, Q2 `176`, Q3 `255`, Q4 `781`.

Two footnotes:
- `Q1 is the storm. Q4 is the stretch the network never recovered from.`
- `Exceptions may not be comparable across these quarters: how they were counted changed in March and November.`

Status bar right label: `revenue_ledger + fct_shipments`

---

## Slide C - heading `ACTUALS AGAINST THE CONTRACT`, subheading `Each account's quarter, against the promise that was signed`

Five small multiples, one per account, each a four-quarter line (Q1..Q4 2025) with **that
account's own contractual target as a dashed rule**. Account name, target and tier in each
panel:

- `Jaffle Werke` - strategic, target **97%** - `86.14`, `89.58`, `82.47`, `78.69` (colour the line red)
- `Jaffle Warenhuis` - strategic, target **97%** - `89.29`, `98.92`, `98.85`, `98.37`
- `Jaffle Maison` - mid, target **95%** - `91.76`, `97.50`, `99.11`, `98.35`
- `Jaffle Getränke` - mid, target **95%** - `89.76`, `98.44`, `97.92`, `95.33`
- `Jaffle Papier` - small, target **92%** - `95.51`, `94.12`, `97.00`, `92.68`

Below the panels, one band of three short facts:
- `Werke is 33.5% of revenue and half the missed shipments.`
- `Four of the five accounts were back above their target by Q2. Only Werke never was.`
- `Werke's contract was renewed at 97% in May 2025. It finished the year at 78.69%.`

Status bar right label: `revenue_ledger + contracts`

---

## Rules

- Insert the three slides only; leave the other twelve slides exactly as they are apart from the
  `/ 15` renumbering.
- Nothing invented: no budget line, no forecast, no revenue-plan figures. The only "target" in
  this deck is the contractual service level, and it must always be labelled as the contract.
- Verify the file loads and reveal.js still initialises, and report the renumbering you applied.
