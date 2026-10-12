#!/usr/bin/env python3
"""Build the Reveal.js deck from its parts in slides/deck/.

    slides/deck/deck.html     the page: head, Reveal setup, and three marker lines
    slides/deck/css/*.css     the stylesheet, one file per slide family
    slides/deck/slides/*.html one file per slide
    slides/assets/            the status-bar logos, inlined as data URIs so the built file
                              needs nothing beside it (the docs site publishes only the HTML)

Parts are joined in file-name order, so the number prefix sets the order: to add a slide
between 030 and 040, name it 035-*.html. Slide numbers in the status bar are generated in
JS at load time, so adding or removing a slide never touches the other slides.

The built deck is not committed. It goes to slides/presentation.html (open it from disk),
and the docs workflow builds it again into docs/shareholder-deck/presentation.html.

Run:  python3 slides/build_deck.py [--out PATH]
"""
import argparse
import base64
import glob
import os

SLIDES_DIR = os.path.dirname(os.path.abspath(__file__))
DECK_DIR = os.path.join(SLIDES_DIR, "deck")
OUT = os.path.join(SLIDES_DIR, "presentation.html")
CSS_MARK = "/* build_deck.py inserts slides/deck/css/*.css here"
SLIDE_MARK = "<!-- build_deck.py inserts slides/deck/slides/*.html here"
LOGO_MARK = "<!-- build_deck.py inserts slides/assets/ logos here"
ASSETS_DIR = os.path.join(SLIDES_DIR, "assets")
# the official white logos, unmodified, in status-bar order
LOGOS = [("fivetran-logo-white.svg", "image/svg+xml", "Fivetran"), ("dbt-logo-white.png", "image/png", "dbt")]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parts(pattern):
    return "".join(read(p) for p in sorted(glob.glob(os.path.join(DECK_DIR, pattern))))


def logos():
    out = []
    for name, mime, alt in LOGOS:
        with open(os.path.join(ASSETS_DIR, name), "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        out.append(f'<img src="data:{mime};base64,{data}" alt="{alt}">\n')
    return "".join(out)


def build():
    out = []
    for line in read(os.path.join(DECK_DIR, "deck.html")).splitlines(keepends=True):
        if line.strip().startswith(CSS_MARK):
            out.append(parts("css/*.css"))
        elif line.strip().startswith(SLIDE_MARK):
            out.append(parts("slides/*.html"))
        elif line.strip().startswith(LOGO_MARK):
            out.append(logos())
        else:
            out.append(line)
    return "".join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default=OUT, help="where to write the deck (default slides/presentation.html)")
    args = p.parse_args()
    html = build()
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {os.path.relpath(args.out)} ({html.count('<section')} slides)")


if __name__ == "__main__":
    main()
