#!/usr/bin/env python3
"""Build the Reveal.js deck from its parts in slides/deck/.

    slides/deck/deck.html     the page: head, Reveal setup, and two marker lines
    slides/deck/css/*.css     the stylesheet, one file per slide family
    slides/deck/slides/*.html one file per slide

Parts are joined in file-name order, so the number prefix sets the order: to add a slide
between 030 and 040, name it 035-*.html. Slide numbers in the status bar are generated in
JS at load time, so adding or removing a slide never touches the other slides.

The built deck is not committed. It goes to slides/presentation.html (open it from disk),
and the docs workflow builds it again into docs/shareholder-deck/presentation.html.

Run:  python3 slides/build_deck.py [--out PATH]
"""
import argparse
import glob
import os

SLIDES_DIR = os.path.dirname(os.path.abspath(__file__))
DECK_DIR = os.path.join(SLIDES_DIR, "deck")
OUT = os.path.join(SLIDES_DIR, "presentation.html")
CSS_MARK = "/* build_deck.py inserts slides/deck/css/*.css here"
SLIDE_MARK = "<!-- build_deck.py inserts slides/deck/slides/*.html here"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parts(pattern):
    return "".join(read(p) for p in sorted(glob.glob(os.path.join(DECK_DIR, pattern))))


def build():
    out = []
    for line in read(os.path.join(DECK_DIR, "deck.html")).splitlines(keepends=True):
        if line.strip().startswith(CSS_MARK):
            out.append(parts("css/*.css"))
        elif line.strip().startswith(SLIDE_MARK):
            out.append(parts("slides/*.html"))
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
