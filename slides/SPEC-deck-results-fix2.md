# Two last defects on the results slides

## 1. The 2024 comparison line on `THE QUARTERS` is not visible

The top chart on `THE QUARTERS` has a legend entry for `2024` (a grey swatch) but **no grey line
is drawn anywhere in the plot** - a legend promising a series that is not visible is worse than no
legend at all. The 2024 quarters are `97.03`, `97.39`, `97.48`, `97.06`, and the dashed 97%
contract rule sits right in the same place, so the two are indistinguishable at this scale.

Fix it so a reader can actually see the comparison:
- Draw the 2024 series as a clearly visible line of its own (light grey, with small markers, and
  a stroke weight that reads against the navy) - it must not be hidden behind the dashed rule.
- If the two are within a pixel or two of each other at the current scale, **change the y scale**
  so both are legible: for example run the axis from 85% to 100% instead of 90% to 100%, which
  puts the 2024 line clearly above the 97% rule. Keep the axis labels honest and round.
- Label the 2024 points with their values, or otherwise make it obvious that 2024 ran at or above
  97% in every quarter - that contrast against 2025's 90.33 in Q1 is the whole point of the chart.
- Keep the legend in step with what is actually drawn: if a series is shown in the legend, it must
  be visible in the plot.

## 2. A panel heading wraps onto two lines on `THE YEAR IN NUMBERS`

The `SERVICE CREDITS · €k` heading on the year-in-numbers slide wraps and its second line touches
the panel's top border. Give it one line: shorten the heading to `CREDITS · €k` (the slide heading
and the footnote already say these are service credits), or widen/reflow so every panel heading
sits on a single line inside its border without touching it. Check the other three headings on
that slide while you are there - they must all be single-line and clear of the border.

Change nothing else: same figures, same charts, same styling, and the other slides untouched.
Verify the file loads and reveal.js initialises.
