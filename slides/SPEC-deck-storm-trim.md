# The storm slide overflows - trim it so everything fits

The storm-week slide (the new one after the COO slide) is **too tall**: its two lower panels run
past the bottom status bar and the last line of each is cut off. Fix it by **shortening the copy**,
not by shrinking the type - body text must stay 24px or larger, and nothing may be clipped,
scrolled or hidden. Replace that slide's content with exactly this shorter version:

**Heading:** `THE STORM WEEK`

**Subheading:** `What happened in Paris, what it cost, and what to do before the next winter`

**Dateline strip:** `WEEK 3 · 13-19 JAN 2025 · PARIS`

**Four stat blocks, one short line each:**

- `570` / `exceptions, one week`
- `23.5%` / `of the year's total`
- `56.60%` / `Paris on-time, January`
- `9 WEEKS` / `to settle`

**Panel `WHAT HAPPENED` - three bullets, each one line:**

- A winter storm hit Paris **14-16 January**; a truck jackknifed on an icy on-ramp.
- One week produced **570 exceptions** - nearly a quarter of the year's.
- The largest account's freight was in the delayed batch, and its review five days later was tense.

**Panel `WHAT IT COST` - three bullets, each one line:**

- Paris ran January at **56.60% on time**, against a **97%** target.
- The network took **nine weeks** - weeks 1 to 9 - to settle.
- Paris closed on **106 partial or cancelled routes**; the other hubs ran about **9.9 per 100**.

**Panel `WHAT TO DO BEFORE NEXT WINTER` - three numbered moves, one sentence each:**

1. **Move the biggest account's winter freight off Paris.** Paris in winter is a dated risk, not a
   surprise; Berlin and Vienna ran the year better.
2. **Call the customer before the service level breaks.** The record shows they raised it first.
3. **Read the storm and the trend apart.** Under the recovery sits a weather-independent slide.

**A single small line at the foot of the content:** `See the COO report, §3.3`

Keep the status bar reading `reports/persona-coo.md`, the red accent, and every other slide exactly
as it now is. Before you finish, satisfy yourself that the slide's total height fits inside 720px
with the status bar visible - measure it or reason it out from your own CSS; do not leave anything
overflowing.
