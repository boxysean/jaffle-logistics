#!/usr/bin/env python3
"""Build the Reveal.js deck from its parts in slides/deck/.

    slides/deck/deck.html     the page: head, Reveal setup, and three marker lines
    slides/deck/css/*.css     the stylesheet, one file per slide family
    slides/deck/slides/*.html one file per slide
    slides/assets/            the status-bar logos, inlined as data URIs so the built file
                              needs nothing beside it (the docs site publishes only the HTML)

A slide's SVG can place the same logos with a marker comment, which the build swaps for an
inlined <image> carrying the attributes it is given:
    <!-- build_deck.py logo: fivetran x="0" y="0" width="86.25" height="24" -->

Parts are joined in file-name order, so the number prefix sets the order: to add a slide
between 030 and 040, name it 035-*.html. Slide numbers in the status bar are generated in
JS at load time, so adding or removing a slide never touches the other slides.

The built deck is not committed. It goes to slides/presentation.html (open it from disk),
and the docs workflow builds it again into docs/shareholder-deck/presentation.html.

A second build, the light deck, is made from the same parts plus slides/deck-light/ (see its
README): the same story with one idea per slide, the dense working moved to an appendix.

Run:  python3 slides/build_deck.py [--out PATH]
      python3 slides/build_deck.py --variant light [--out PATH]
"""
import argparse
import base64
import glob
import os
import re

SLIDES_DIR = os.path.dirname(os.path.abspath(__file__))
DECK_DIR = os.path.join(SLIDES_DIR, "deck")
OUT = os.path.join(SLIDES_DIR, "presentation.html")
LIGHT_DIR = os.path.join(SLIDES_DIR, "deck-light")
LIGHT_OUT = os.path.join(SLIDES_DIR, "presentation-light.html")
NOTES_SCRIPT = '<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/notes/notes.js"></script>\n'
CSS_MARK = "/* build_deck.py inserts slides/deck/css/*.css here"
SLIDE_MARK = "<!-- build_deck.py inserts slides/deck/slides/*.html here"
LOGO_MARK = "<!-- build_deck.py inserts slides/assets/ logos here"
ASSETS_DIR = os.path.join(SLIDES_DIR, "assets")
# the official white logos, unmodified, in status-bar order
LOGOS = [("fivetran-logo-white.svg", "image/svg+xml", "Fivetran"), ("dbt-logo-white.png", "image/png", "dbt")]
SVG_LOGO_MARK = re.compile(r"<!-- build_deck\.py logo: (\w+) (.*?) -->")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parts(pattern):
    return "".join(read(p) for p in sorted(glob.glob(os.path.join(DECK_DIR, pattern))))


def parts_light(pattern):
    return "".join(read(p) for p in sorted(glob.glob(os.path.join(LIGHT_DIR, pattern))))


def data_uri(name, mime):
    with open(os.path.join(ASSETS_DIR, name), "rb") as fh:
        return f"data:{mime};base64,{base64.b64encode(fh.read()).decode('ascii')}"


def logos():
    return "".join(f'<img src="{data_uri(name, mime)}" alt="{alt}">\n' for name, mime, alt in LOGOS)


def svg_logo(match):
    # the default preserveAspectRatio keeps the logo's own proportions inside the box it is given
    name, mime, alt = next(logo for logo in LOGOS if logo[2].lower() == match.group(1))
    return f'<image href="{data_uri(name, mime)}" {match.group(2)}><title>{alt}</title></image>'


def light_slides():
    """The light deck's slides, in manifest order. Each manifest line names a slide file, found in
    deck-light/slides/ first and deck/slides/ second, optionally followed by ' | key=value' edits:
    title= and sub= swap the heading and its one-line subtitle, notes= adds speaker notes."""
    out = []
    for line in read(os.path.join(LIGHT_DIR, "manifest.txt")).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, *edits = [f.strip() for f in line.split(" | ")]
        path = os.path.join(LIGHT_DIR, "slides", name)
        if not os.path.exists(path):
            path = os.path.join(DECK_DIR, "slides", name)
        html = read(path)
        for edit in edits:
            key, value = edit.split("=", 1)
            if key == "title":
                html = re.sub(r"(<h2>).*?(</h2>)", lambda m: m.group(1) + value + m.group(2), html, count=1, flags=re.S)
            elif key == "sub":
                html = re.sub(r'(<div class="owns">).*?(</div>)', lambda m: m.group(1) + value + m.group(2), html, count=1, flags=re.S)
            elif key == "notes":
                head, _, tail = html.rpartition("</section>")
                html = f'{head}<aside class="notes">{value}</aside>\n</section>{tail}'
            else:
                raise SystemExit(f"{name}: unknown edit {key!r}")
        out.append(html)
    return "".join(out)


def build(variant="full"):
    light = variant == "light"
    out = []
    for line in read(os.path.join(DECK_DIR, "deck.html")).splitlines(keepends=True):
        if line.strip().startswith(CSS_MARK):
            out.append(parts("css/*.css"))
            if light:
                out.append(parts_light("css/*.css"))
        elif line.strip().startswith(SLIDE_MARK):
            out.append(SVG_LOGO_MARK.sub(svg_logo, light_slides() if light else parts("slides/*.html")))
        elif line.strip().startswith(LOGO_MARK):
            out.append(logos())
        elif light and "reveal.js@5/dist/reveal.js" in line:
            # the light deck carries speaker notes, opened with S
            out.append(line + NOTES_SCRIPT)
        elif light and line.strip() == "hash: true,":
            out.append(line + "    plugins: [RevealNotes],\n")
        else:
            out.append(line)
    return "".join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--variant", choices=["full", "light"], default="full", help="which deck to build")
    p.add_argument("--out", help="where to write the deck (default slides/presentation.html, or presentation-light.html)")
    args = p.parse_args()
    html = build(args.variant)
    args.out = args.out or (LIGHT_OUT if args.variant == "light" else OUT)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {os.path.relpath(args.out)} ({html.count('<section')} slides)")


if __name__ == "__main__":
    main()
