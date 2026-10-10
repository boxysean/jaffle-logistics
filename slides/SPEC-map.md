# Brief: three slide-ready map graphics of the Jaffle Logistics network

You are a designer producing **three standalone HTML graphics**, each a fixed 1920x1080 (16:9)
slide canvas, for a deck about a logistics company. Each file must be self-contained (CSS and
JS inline in the file) and open directly in a browser.

## The subject

Jaffle Logistics — a European LTL / last-mile / warehousing carrier. Five hubs:

| City | Role | Capacity (packages/day) | Country |
|---|---|---|---|
| Amsterdam | Headquarters | 42,000 | NL |
| Paris | largest hub, worst 2025 performer | 68,000 | FR |
| Berlin | warehouse | 51,000 | DE |
| Vienna | hub | 47,000 | AT |
| Zürich | hub, **only non-EU leg** (customs) | 39,000 | CH |

City coordinates for placement (lng, lat): Amsterdam `4.90, 52.37` · Paris `2.35, 48.86` ·
Berlin `13.40, 52.52` · Vienna `16.37, 48.21` · Zürich `8.54, 47.38`.

The five customer accounts, for a legend or corner note: Jaffle Werke (industrial, the
at-risk strategic account), Jaffle Warenhuis (retail last-mile), Jaffle Maison (workwear
last-mile), Jaffle Getränke (beverages, warehousing), Jaffle Papier (packaging).

The only numbers you may print — do not invent any others:

- on-time target for the two strategic accounts: **97%**
- whole-book on-time: **97.5% (2023)**, **97.2% (2024)**, **93.3% (2025)**
- five hubs, five countries, one non-EU border crossing (Zürich)

## What to build — three distinct styles, not three recolours

**1. `map-retro.html` — 16-bit management-game map.** Think a 1990s console airline-tycoon
screen: chunky square pixel type, limited palette (deep navy/teal background, one hot accent
for routes, amber for highlights), thick stepped route lines between cities, chunky square
nodes, a status bar of blunt labels like `ON-TIME 93.3%` and `HUB PARIS 68K`, a header strip
with the company name, a blinking-cursor feel. Pixel font is fine (Google Fonts has
pixel faces) with a monospace fallback. It should feel like a screen, not a printed map:
visible panel borders, a bottom status line.

**2. `map-dark.html` — modern operations screen.** Dark, quiet, precise: muted landmass in a
single desaturated tone, hairline country borders, nodes glowing subtly and scaled by
capacity, routes as thin arcs with the Zürich leg visibly interrupted or dashed to signal the
customs crossing, labels in a clean grotesque, one restrained accent. Density and legibility
over decoration. This one is the one a COO would actually put on a wall.

**3. `map-light.html` — clean editorial / Swiss corporate.** Light background, pale landmass,
dark ink type, generous whitespace, a strong typographic hierarchy (big display title, small
data captions), nodes as simple filled dots with the at-risk account flagged, a thin legend,
and one accent used sparingly. Print-like: no glow, no gradients, no shadows.

## Requirements for all three

- Fixed 1920x1080 canvas, centred, the whole composition visible without scrolling.
- **Real geography**: load a simplified world topojson and render actual country shapes with
  d3-geo (`countries-110m` from jsdelivr, pinned: `https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json`,
  and d3 v7 from jsdelivr). Zoom to a Europe viewport that comfortably contains all five
  cities. Do not hand-draw a fake coastline.
- Every city labelled, nodes positioned from the coordinates above, not eyeballed.
- Titles: `Jaffle Logistics — European Network`. A discreet footer reading
  `synthetic dataset` is honest and welcome.
- No filler: no invented metrics, no decorative stat grids, no fake dashboards.
- Avoid the tells of generic AI design: no purple/indigo tech gradient, no glassmorphism,
  no rounded-square icon over every heading, no equal-weight feature card rows.
- Type: pick deliberately per style and use hierarchy (scale, weight, space) before boxes
  or colour.
- Constraint: the network is hub-and-spoke. Draw the routes from Amsterdam outward, with
  Amsterdam, Paris, Berlin and Vienna inside the EU and Zürich beyond the customs line.

## Deliverables

Three files in this directory: `map-retro.html`, `map-dark.html`, `map-light.html`.
Verify each one loads without console errors before you finish. Save nothing else.
