# The deck, in parts

The shareholder deck is built from the files here by `python3 slides/build_deck.py`, which
writes `slides/presentation.html` (open it from disk). The built file is not committed: the docs
workflow builds its own copy when it publishes.

- `deck.html`: the page itself (head, Reveal setup, the status-bar script), with one marker
  line where the CSS goes and one where the slides go.
- `css/NNN-*.css`: the stylesheet, one file per slide or slide family. `010-base.css` holds
  what every slide shares (palette, frame, status bar). The rest follow in their original
  cascade order, so file order matters here.
- `slides/NNN-*.html`: one `<section>` per file, in deck order.

Files are joined in name order. The numbers go up in tens so there's room to insert: a slide
between `030-*` and `040-*` is `035-*`, and one before the first slide is `001-*`. Don't renumber
existing files to make room, since that touches every file and conflicts with open work.
Slide numbers in the status bar are generated at load time, so adding a slide changes nothing
else.

To change a slide, edit its file and any CSS file whose rules it uses, then rebuild.
