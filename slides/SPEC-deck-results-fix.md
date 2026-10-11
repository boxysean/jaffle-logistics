# Two defects on the new results slides - fix both

## 1. On `THE YEAR IN NUMBERS` (and check `THE QUARTERS`) the stat strip is overlapped by the charts

On the "year in numbers" slide the three stat blocks and the four chart panels collide: the chart
row starts too high and covers the bottom of the stat text, so the third stat's line is cut off
after "against a 97%" and the chart panel headings ("REVENUE · €M", "SERVICE CREDITS · €k") are
half hidden under it. Same risk on "the quarters" slide, which has the same top strip.

Fix the vertical rhythm so nothing overlaps:
- The stat strip sits entirely above the chart row, with real space between them - no element
  from one row may overlap the other.
- The third stat's text must read in full: `on time, against a 97% target`.
- Each chart panel's own heading must be fully visible at the top of its panel.
- The footnotes stay fully visible above the status bar, as they are now.

Do it by making room (tighter stat type, a shorter strip, or a smaller chart height), not by
shrinking body text below 24px and not by hiding anything. Both slides must end with every line
of text complete and nothing clipped at any edge.

## 2. The status bar's right-hand label collides with the slide number

On all three new slides the right-hand source label runs straight into `SLIDE 05 / 15` with no
gap - it reads `SLIDE 05 / 15revenue_ledger + fct_shipments`. Two changes:

- **Shorten the labels**: on `THE YEAR IN NUMBERS` and `THE QUARTERS` use `revenue_ledger`;
  on `ACTUALS AGAINST THE CONTRACT` use `ledger + contracts`.
- **Make the bar defensive**: the centre (`SLIDE NN / 15`) and right label must never touch -
  give the right label real padding the way the existing slides do, and if the label is long the
  bar should shorten it rather than run into the number. Check the other twelve slides still read
  cleanly after the change.

Leave the twelve original slides otherwise untouched, keep the charts and all figures exactly as
they are, and keep the retro styling. Verify the file still loads and reveal.js initialises.
