#!/usr/bin/env python3
"""Build the Reveal.js deck from its parts in slides/deck/ and slides/deck-light/.

    slides/deck/deck.html     the page: head, Reveal setup, and three marker lines
    slides/deck/css/*.css     the stylesheet, one file per slide family
    slides/deck/slides/*.html slides the deck borrows, named in slides/deck-light/manifest.txt
    slides/assets/            the status-bar logos, inlined as data URIs so the built file
                              needs nothing beside it (the docs site publishes only the HTML)

A slide's SVG can place the same logos with a marker comment, which the build swaps for an
inlined <image> carrying the attributes it is given:
    <!-- build_deck.py logo: fivetran x="0" y="0" width="86.25" height="24" -->

The slide order is slides/deck-light/manifest.txt (see its README). Slide numbers in the
status bar are generated in JS at load time, so adding or removing a slide never touches the
other slides.

The built deck is not committed. It goes to slides/presentation.html (open it from disk),
and the docs workflow builds it again into docs/shareholder-deck/presentation.html.

--theme corporate re-skins the built deck in the Fivetran + dbt Labs corporate theme (see
slides/corporate/theme.py); the slides and their order are the same either way.

Run:  python3 slides/build_deck.py [--out PATH] [--theme corporate]
"""
import argparse
import base64
import glob
import os
import re
import sys

SLIDES_DIR = os.path.dirname(os.path.abspath(__file__))
DECK_DIR = os.path.join(SLIDES_DIR, "deck")
OUT = os.path.join(SLIDES_DIR, "presentation.html")
LIGHT_DIR = os.path.join(SLIDES_DIR, "deck-light")
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


def light_slides(cut_dir=None):
    """The light deck's slides, in manifest order. Each manifest line names a slide file, found in
    deck-light/slides/ first and deck/slides/ second, optionally followed by ' | key=value' edits:
    title= and sub= swap the heading and its one-line subtitle, notes= adds speaker notes.
    With cut_dir (another cut of the deck, e.g. slides/video/deck/), its manifest is read instead
    and its slides/ is looked in first."""
    out = []
    for line in read(os.path.join(cut_dir or LIGHT_DIR, "manifest.txt")).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, *edits = [f.strip() for f in line.split(" | ")]
        dirs = ([cut_dir] if cut_dir else []) + [LIGHT_DIR, DECK_DIR]
        path = next((p for p in (os.path.join(d, "slides", name) for d in dirs) if os.path.exists(p)),
                    os.path.join(DECK_DIR, "slides", name))
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


def build(cut_dir=None):
    """The deck as one HTML page. cut_dir builds another cut (see light_slides) and adds its
    css/*.css after the light deck's."""
    out = []
    for line in read(os.path.join(DECK_DIR, "deck.html")).splitlines(keepends=True):
        if line.strip().startswith(CSS_MARK):
            out.append(parts("css/*.css"))
            out.append(parts_light("css/*.css"))
            if cut_dir:
                out.append("".join(read(p) for p in sorted(glob.glob(os.path.join(cut_dir, "css", "*.css")))))
        elif line.strip().startswith(SLIDE_MARK):
            out.append(SVG_LOGO_MARK.sub(svg_logo, light_slides(cut_dir)))
        elif line.strip().startswith(LOGO_MARK):
            out.append(logos())
        elif "reveal.js@5/dist/reveal.js" in line:
            # the deck carries speaker notes, opened with S
            out.append(line + NOTES_SCRIPT)
        elif line.strip() == "hash: true,":
            out.append(line + "    plugins: [RevealNotes],\n")
        else:
            out.append(line)
    return "".join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", help="where to write the deck (default slides/presentation.html)")
    p.add_argument("--cut", help="build another cut of the deck from this folder (e.g. slides/video/deck)")
    p.add_argument("--theme", choices=["retro", "corporate"], default="retro",
                   help="retro: the 16-bit game skin (default); corporate: the Fivetran + dbt Labs theme")
    args = p.parse_args()
    html = build(os.path.abspath(args.cut) if args.cut else None)
    if args.theme == "corporate":
        sys.path.insert(0, os.path.join(SLIDES_DIR, "corporate"))
        sys.dont_write_bytecode = True
        import theme
        html = theme.apply(html)
    args.out = args.out or OUT
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {os.path.relpath(args.out)} ({html.count('<section')} slides)")


if __name__ == "__main__":
    main()
