# Brief: three slide-ready graphics of the Jaffle Logistics executive group

You are a designer producing **three standalone HTML graphics**, each a fixed 1920x1080 (16:9)
slide canvas, for a deck introducing a logistics company's leadership team. Self-contained
files (CSS and JS inline), openable directly in a browser.

## The subject

Jaffle Logistics — a European LTL / last-mile / warehousing carrier headquartered in
Amsterdam, with hubs in Paris, Berlin, Vienna and Zürich. The seven seats below are the
executive group. Each has a mandate and **one headline fact that is real in this company's
data** — print only these facts, never invent a number, and never invent a person's name.
These are seats, not people: label them as roles.

| Seat | Owns | Headline fact (use verbatim, nothing else) |
|---|---|---|
| Chief Financial Officer | where the money goes | Fleet maintenance spend rose **157%** while routes rose **3.1%** |
| Chief Operating Officer | whether the network runs | Whole-book on-time fell to **93.3%** in 2025, from **97.5%** and **97.2%** |
| Chief Revenue Officer | whether the book holds | One account is roughly **a third of revenue** and **half the missed shipments** |
| Head of Customer Experience | what the customer feels | The at-risk account's tickets went **17 → 17 → 72** |
| Head of Fleet & Maintenance | what the assets cost | Collision repair is **63% of 2025 maintenance spend** |
| Head of People | who actually drives | Contractors cost **twice as much per route**; **nobody was hired in 2025** |
| Head of Data | whether the numbers can be trusted | Every year contains exactly **2,009 shipments** — volume is not comparable |

Context you may state once, in a corner or footer, if a style needs balance: five hubs, five
countries, one non-EU border crossing, and a **97% on-time target** on the two strategic
accounts. A discreet `synthetic dataset` footer is welcome.

## What to build — three distinct styles, not three recolours

**1. `exec-retro.html` — 16-bit management-game roster.** The screen a 1990s console
tycoon game would show when you open your management team: seven chunky tiles in a grid, each
with a pixel-block abstract portrait (simple geometric avatar, no faces), a role label, a
short mandate line, and a small block-bar or number for the headline fact. Header strip,
bottom status bar, limited palette (deep navy, one hot accent, amber highlight), pixel or
monospace type, visible panel borders. Must feel like a game screen, not a web page.

**2. `exec-dark.html` — modern leadership cockpit.** Dark and precise: an explicit
**org-chart structure** (one chief executive node over the finance / operations / revenue
trio, with the four functional heads on a second tier), hairline connectors, each seat
carrying its mandate in a small caption and its headline fact in a strong numeric treatment.
One restrained accent, desaturated palette, clean grotesque type, high information density
without clutter. This is the one for a board pack.

**3. `exec-light.html` — editorial roster.** Light background, dark ink, one accent used
sparingly. A strong typographic composition: large role names, mandate lines as small caps
or captions, headline facts set at a clearly larger size than the surrounding text, hairline
rules instead of boxes, generous whitespace. Print-like and uncluttered — the version that
survives being projected in a bright room.

## Requirements for all three

- Fixed 1920x1080 canvas, centred, whole composition visible without scrolling; body text
  at 24px or larger at that size.
- Seven seats present in every style, all labelled with the same role names.
- Type chosen deliberately per style; hierarchy from scale, weight and space **before**
  boxes, icons or colour.
- No invented metrics, no fake names, no stock-photo placeholders, no decorative stat grids.
- Avoid generic AI-design tells: no purple/indigo tech gradient, no glassmorphism, no
  rounded-square icon above every heading, no centred hero.
- Verify each file loads without console errors before finishing.

## Deliverables

Three files in this directory: `exec-retro.html`, `exec-dark.html`, `exec-light.html`.
Save nothing else.
