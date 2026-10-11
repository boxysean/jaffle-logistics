Two verification fixes in this repository. Make only these two changes.

1. `slides/presentation.html` — the new slide's footnote overflows the slide edge. Replace the exact
   text of the `.foot` div inside the `class="dt"` section:
   FROM: An argument, not a measurement. The context layer and the audit are real; the agents are a design.
   TO:   An argument, not a measurement. The context layer is built; the agents are a design.
   Touch nothing else on the slide — not the panels, not the header, not the CSS.

2. `docs/shareholder-deck.md` — the intro paragraph is soft-wrapped at about 98 columns; the line you
   edited is now 141 characters. Rewrap that whole paragraph (the three lines starting "A briefing on
   the business" through "support-case agent, and where else agents slot in.") so that every line is
   at most 100 characters, keeping the same words and the trailing "," in the inserted clause.
