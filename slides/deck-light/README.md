# The deck

The shareholder deck: one idea per slide, a headline that states the point, a picture or a few
big numbers instead of paragraphs, and the dense working moved to an appendix. Speaker notes carry the detail that used to sit on the slide
(press `S` in the deck to open the speaker view).

    python3 slides/build_deck.py      # writes slides/presentation.html

- `manifest.txt`: the slide order. A line names a slide file, looked up in `slides/` here first and
  `../deck/slides/` second, so an unchanged slide is reused, not copied. A line may add
  ` | title=...`, ` | sub=...` (swap the heading and its subtitle) or ` | notes=...` (speaker notes).
- `slides/*.html`: slides written or adapted for this cut (plain names, no number prefixes).
- `css/*.css`: the kit these slides use, added after `slides/deck/css/`. `.lt-flow` slides light up
  one step per click; `.lt-cards` and `.lt-big` are the picture-and-number layouts.

The slides after `APPENDIX` are the original cut's dense slides, untouched, for answering
questions. `slides/deck/` holds the page template, the base CSS and those borrowed slides.
