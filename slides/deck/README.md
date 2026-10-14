# The deck's shared parts

The shareholder deck is built by `python3 slides/build_deck.py`, which writes
`slides/presentation.html` (open it from disk). The built file is not committed: the docs
workflow builds its own copy when it publishes. The slide order lives in
`slides/deck-light/manifest.txt`; see that folder's README.

This folder holds the parts the deck is built on:

- `deck.html`: the page itself (head, Reveal setup, the status-bar script), with one marker
  line where the CSS goes, one where the slides go, and one where the status-bar logos go.
  The logos come from `slides/assets/` and are inlined as data URIs, so the built file needs
  nothing beside it.
- `css/NNN-*.css`: the base stylesheet, one file per slide or slide family. `010-base.css` holds
  what every slide shares (palette, frame, status bar). The rest follow in their original
  cascade order, so file order matters here. `slides/deck-light/css/` is added after them.
- `slides/NNN-*.html`: one `<section>` per file. These are slides from the original, longer
  cut of the deck that the manifest still uses, by file name. A slide no line of the manifest
  names is not in the deck.

Slide numbers in the status bar are generated at load time, so adding a slide changes nothing
else. To change a slide, edit its file and any CSS file whose rules it uses, then rebuild.
