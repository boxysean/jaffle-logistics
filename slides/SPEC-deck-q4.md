# Add a deck slide: the Q4 decline — what the storm does not explain

Add **one new slide** to `slides/presentation.html`, placed **immediately after the storm-week
slide** (`<section class="storm" ...>`, the one headed `THE STORM WEEK`, currently slides 5) and
**before the customer-review slide** (`<section class="res" ...>` headed `CUSTOMER REVIEW`). The
two deep-dives then sit together right after the quarters slide. Do **not** hand-edit any status-bar
numbering: the numbers are generated at runtime from the slide count by the script at the foot of
the file. Do **not** renumber or otherwise touch any existing `<!-- N. -->` comment in the file —
they are legacy and already out of order; just add your own comment line for the new slide.

Then update `docs/shareholder-deck.md` (details at the end of this spec).

Match the deck's existing retro style exactly — same fonts, colours, panel borders, `.frame`/
`.panel` system, `.hd` header, status bar, footnote conventions, `data-src` attribute. **No new
libraries.** Anything drawn is inline SVG or styled HTML in the deck's own register.

## The slide's voice and point

The business user asked "why was Q4 so bad?". The answer is measured and on the record: Q4 is the
**second-worst quarter of the year, it is not the storm, and it is almost entirely one account**.
The storm slide tells the storm half; this slide tells the other half. Its whole point is the third
column: the documented cause covers **Amsterdam only**, while the Q4 damage is **wider** — Paris and
**Berlin have no recorded cause**. Say that plainly and do not hint at a cause for Paris or Berlin.

## Honesty rules — non-negotiable

- Every figure in this spec is measured. **Copy them exactly; do not adjust, round differently,
  invent or embellish any number.**
- The documented root cause applies to **Amsterdam**. Paris and Berlin are **undocumented**. Never
  imply the Amsterdam finding explains the quarter.
- Attribute the root-cause review and its actions to **the record** ("a 20 Oct review", "the
  root-cause review"), never to the platform team.
- The dataset is synthetic and seeded — keep the deck's standing caveat tone; no vendor logos.

## Heading and section element

Heading `h2` (pixel font, exactly as the storm slide's `h2`):

```
Q4 — WHAT THE STORM DOES NOT EXPLAIN<span class="when">OCT–DEC 2025</span>
```

(the `span.when` is the "when" chip, mirroring the storm slide — but see the **colour** section).

`.hd .owns` — **one single line only** (the header is 96px tall and fits exactly one 24px line):
`The second-worst quarter of 2025, and it is not the storm`

Section element:

```html
<section class="q4" data-src="CRM-9030 + analysis" data-status="CRM-9030 + analysis">
```

`data-status` is the status-bar right label and must stay short (≈23 characters max) or the deck
ellipsises it.

## Colour: violet, and deliberately quieter than the pink storm slide

The storm slide (`THE STORM WEEK`) is the pink one: full-saturation `--hot` (`#ff3d6e`) on its
header border, tab strips, tile borders and values. **This slide is its quieter sibling. Use violet
as accents only, and never as a large saturated area.**

Define these two local values at the top of the `.q4` CSS block and use them throughout:

```css
/* line and edge accents: a muted violet, deliberately low-saturation so the slide reads calmer
   than the pink storm slide */
--q4-edge: #5f4b96;
/* fills behind the chip and the tabs: a dark, near-desaturated violet over the navy panel */
--q4-fill: #241b45;
```

Rules:

- **Text accents** (the heading, the stat values, `<strong>` inside body copy, the tab labels, the
  chip label, bullet markers): `var(--violet)` (`#a06bff`).
- **Edges** (the header border, the stat-tile borders, the `.point` column border): `var(--q4-edge)`
  (the muted violet) — **not** `var(--violet)`.
- **Fills** (the `.when` chip, the `.tab` strips): `var(--q4-fill)` with violet text — **not** a
  full-saturation violet fill.
- **Panels stay navy** (the default `--navy` / `--navy-2`). Body text stays the deck's normal
  `--text` / `--dim` except where `<strong>` carries a key value.

Do **not** wash the slide purple: no solid violet blocks, no violet panel backgrounds, no chip or
tab inverted to full-saturation violet.

## Layout — use these exact measurements

The deck is a fixed 1280x720 screen. The body region runs from y=132 to y≈650 and the status bar
sits at `top: 664px`. Panels carry a 4px border and a `6px 6px 0 4px #000` shadow, and a panel's
`.tab` stands 12px above its top border — so every block needs at least ~24px of clear space above
the next.

```
.q4 .hd     { height: 96px; }                                             /* 20,20  1240x96  -> 116 */
.q4 .tiles4 { left:20px; top:132px; width:1240px; height:74px;
              display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }   /* -> 206 */
.q4 .acct   { left:20px; top:218px; width:1240px; height:76px; padding:14px 18px 8px; }  /* -> 294 */
.q4 .cols   { left:20px; top:306px; width:1240px; height:242px;
              display:grid; grid-template-columns:380px 380px 1fr; column-gap:12px; }   /* -> 548 */
.q4 .cols .panel { position:relative; padding:14px 12px 10px; }
.q4 .rec    { left:20px; top:562px; width:1240px; height:52px; padding:8px 18px 4px;
              display:grid; grid-template-columns:repeat(3,1fr); column-gap:24px; }    /* -> 614 */
.q4 .foot   { position:absolute; left:20px; top:626px; width:1240px; font-size:24px; line-height:1.2; color:var(--dim); }
```

Wrap `.tiles4`, `.acct`, `.cols` and `.rec` in a `<div class="body">` with
`position:absolute; left:20px; top:132px; width:1240px;` if that suits the storm slide's pattern —
either the absolute positions above or the storm slide's `.body` flex pattern is fine, as long as
the four blocks land at the y-positions listed.

**Line budgets** (24px mono = 14.4px/char, 27.6px/line; 20px = 12px/char, 23px/line):
a `.cols` panel is 380/380/456 wide → 356/356/432px inside → **24 / 24 / 30 characters per line**;
inside a 242px-tall panel there is ~218px of usable height → **about 7 rendered lines**. The
third column at 30 chars/line holds ~200 characters; **keep each column's rendered text inside
those line counts** — this slide has needed a fit fix before.

Add a CSS comment above the `.q4` block recording this budget in the deck's own style.

## Copy — use this exactly (deviate only by dropping your own connective words if it will not fit)

### Stat tiles (`.tiles4`, four `.panel.tile`, value in `.v`, note in `.note`)

1. `.v` `92.62%` — `.note` `Q4 on time — second-worst quarter`
2. `.v` `91.07%` — `.note` `December — after Oct 95.27, Nov 92.12`
3. `.v` `78.69%` — `.note` `Jaffle Werke's Q4 — the whole-book number`
4. `.v` `77.78%` — `.note` `the worst week, 10 November`

### Account strip (`.panel.acct`, full width, tab `IT IS ONE ACCOUNT`)

One line of body copy at 24px:

`Jaffle Werke 78.69% · Warenhuis 98.37 · Maison 98.35 · Getränke 95.33 · Papier 92.68 — the other four are at or near target, and the whole-book number is Werke's number.`

(Give `78.69%` and the other four rates `<strong>`; this panel is 1204px inside, ≈83 chars/line.)

### Three columns (`.cols`, three `.panel.col`, each with a `.tab` and a `<ul>`)

**Column 1 — tab `THE QUARTER`** (24 chars/line):

- `Q4 on time 92.62%, against 97.06% a year earlier; below Q2 (95.40) and Q3 (95.12).`
- `Oct 95.27 → Nov 92.12 → Dec 91.07: worse every month.`
- `Worst weeks: 10 Nov 77.78%, 8 Dec 84.31%.`
- `Q1, the storm quarter, was 90.33 — a different failure, later in the year.`

**Column 2 — tab `WHAT'S DOCUMENTED`** (24 chars/line):

- `A 20 Oct root-cause review names two factors: the January Paris storm, and a recurring Amsterdam handling pattern (bay 3 forklift staging, three incidents).`
- `Amsterdam, this account: 93.75 → 90.91 → 88.24 → 73.68.`

**Column 3 — tab `WHAT ISN'T`** — this is the slide's point, give the panel
`class="panel col point"` (border in `var(--q4-edge)`), and its bullet markers violet:

- `Q4's damage is wider than Amsterdam: Paris fell to 60.87% (from 94.74 in Q3) and Berlin to 76.92%.`
- `There is no recorded cause for either.`
- `Paris is the worst hub in the quarter, across all clients (87.93%).`

### Recommendation band (`.rec`, three cells, tab-less)

Each cell: a pixel-font label `<b class="px">` in violet, then ordinary 20px text on one flow
(mirror the `.agt .band` convention). Each cell must fit **two lines at most**:

- `<b class="px">SOP AUDIT</b>the Amsterdam superintendent's, under way`
- `<b class="px">TRACK BY CAUSE</b>weather vs handling, from Q4`
- `<b class="px">ADD THE FLOOR</b>dispatch notes and Slack miss the corpus`

### Footnote (`.foot`)

One line, under ~85 characters rendered:

`The account is a third of revenue and the whole-book miss; the exposure is service credits.`

## CSS to add — immediately after the `/* storm-week slide ... */` block and before the `.res` block

Write it in the deck's own style, as a sibling of the `.storm` block. Use the values above. The tab
strips use `background: var(--q4-fill); color: var(--violet)`; the `.when` chip uses
`background: var(--q4-fill); color: var(--violet); padding:5px 10px; font-size:16px` inside the
flex h2. Bullet markers are 10px violet squares `position:absolute; left:0; top:8px;
width:10px; height:10px; background: var(--violet)` with `padding-left:20px` on the `li`. `<strong>`
in the columns is `color: var(--violet); font-weight: 600`.

## After the slide: update `docs/shareholder-deck.md`

1. Change the intro's "**Nineteen slides**" to "**Twenty slides**".
2. In the intro paragraph, after "the storm week that broke Paris," add the new slide:
   "the Q4 decline the storm does not explain," so the reading order is named.
3. In the "## Slide by slide" thumbnail list: insert the new line at position 6 and renumber the
   rest so the list runs 1..20:
   - new: `[![Slide 6: Q4 — what the storm does not explain](shareholder-deck/png/deck-05.png)](shareholder-deck/presentation.html)`
   - the current slides 6..19 become 7..20 (their `deck-NN.png` targets shift by one, so the
     customer-review slide becomes `deck-06.png` at "Slide 7", and the last becomes `deck-19.png`
     at "Slide 20").

## Rules

- Insert exactly one slide, and only between the storm slide and the customer-review slide. Leave
  every other slide byte-for-byte unchanged.
- Do not touch `slides/render_deck.py` or the runtime status-bar script.
- All four regions (tiles, account strip, three columns, recommendation band) plus the footnote
  must fit with the status bar visible and **nothing clipped, overflowing or overlapping**. Check
  your rendered line counts against the budgets above before you finish.
- Report what you added: the section, its CSS, and the `docs/shareholder-deck.md` edits.
