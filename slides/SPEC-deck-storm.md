# Add a slide: the storm week

Add **one new slide** to `slides/presentation.html`, insert it **immediately after the COO slide**
(so the deck becomes twelve slides, and the CRO, customer-experience, fleet, people and data
slides each move down one). Match the existing retro panel style exactly - same fonts, same
colours, same panel borders, same status bar - reusing whatever CSS the deck already defines.
Use the deck's existing red/accent colour for this slide's emphasis: it is a failure story.

Then **renumber**: every status bar must read `SLIDE NN / 12` with its correct new number.

Also, on the two full-bleed image slides (the network map and the executive group), **hide
reveal.js's slide-number badge and its progress bar** - they currently sit on top of those two
graphics. Keep them on every other slide.

## The content of the new slide - use exactly this, invent nothing

**Heading:** `THE STORM WEEK`

**Subheading:** `What happened in Paris, what it cost, and what to do before the next winter`

**Dateline strip:** `WEEK 3 · 13-19 JANUARY 2025 · PARIS`

**Four stat blocks:**

- `570` / `exceptions in one week`
- `23.5%` / `of the whole year's exceptions`
- `56.60%` / `Paris on-time that January, against a 97% target`
- `9 WEEKS` / `of elevated exceptions before it settled`

**Panel headed `WHAT HAPPENED`:**

- A winter storm hit Paris on **14-16 January 2025**.
- A truck jackknifed on an icy on-ramp. The incident report is in the corpus.
- One week produced **570 exceptions**, nearly a quarter of 2025's total.
- The largest account's freight was in the delayed batch. Five days later its quarterly
  review was described, in the record, as tense.

**Panel headed `WHAT IT COST`:**

- Paris ran January at **56.60% on time** against a contract target of **97%**.
- The network did not settle for **nine weeks** - weeks 1 to 9.
- Paris finished the year with **106 partial or cancelled routes**, against about **9.9 per 100**
  at the other hubs.
- The account's tickets climbed to **72** for the year, most of them in January - and its credits
  are the bulk of the **€52,954.86** paid in 2025.

**Panel headed `WHAT TO DO BEFORE NEXT WINTER` (three numbered moves):**

1. **Move the biggest account's winter freight off Paris in advance.** Paris in winter is a dated
   risk, not a surprise. Berlin and Vienna ran the year better.
2. **Call the customer before the service level breaks.** The record shows the customer raised it
   first - the tense review came five days later. Their complaint volume is the earliest warning
   the company has.
3. **Read the storm and the trend separately.** There is a second, weather-independent slide
   underneath the recovery. If next January looks like this one, the company must be able to tell
   a storm from a drift.

**Bottom line of the slide (small, at the foot of the content):**
`Witnesses in the corpus: reports/persona-coo.md §3.3 · CRM-9001 · CT-99001 · IR-9001 · SLK-99010`

The status bar for this new slide shows `reports/persona-coo.md` on the right, like every other
content slide, and there is no separate SOURCE line under the panel.

Body text stays 24px or larger. Verify the file loads and reveal.js still initialises, and report
the slight renumbering you applied.
