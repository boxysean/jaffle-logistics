#!/usr/bin/env python3
"""Generate the Customer Experience persona-report charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible without the
warehouse. The source of every number is reports/assets/personas/_data/data-pack.md
(sections Q2, Q4b, Q11), whose SQL is copied into the appendix of
reports/persona-customer-experience.md.

Output: reports/assets/personas/*.svg  (committed alongside the report).

Design rules (match scripts/cfo_charts.py):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar;
  * the 97% contractual on-time target drawn as a reference line on the rate chart;
  * consistent colour meaning: red = negative / below target, grey-blue ramp = years,
    neutral blue = a series with no target of its own.

Run from the repo root:  python3 scripts/persona_cx_charts.py
"""
import os
import statistics
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "personas")
TARGET = 97.0  # whole-book contractual on-time reference line, %

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # negative sentiment / below target
BLUE = "#2c6fbb"     # neutral series
GREY = "#555555"
GRID = "#d9d9d9"
INK = "#1a1a1a"
LIGHT = "#9aa7b5"
MID = "#5b7fa6"
YEAR_COLS = [(LIGHT, "2023"), (MID, "2024"), (BLUE, "2025")]

FONT = "Helvetica, Arial, sans-serif"


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from the data pack)
# (client_id, short name) in client-id order
ACCOUNTS = [
    ("CLI-0007", "Storefronts"),
    ("CLI-0042", "Equipment"),
    ("CLI-0155", "Crew Outfitters"),
    ("CLI-0169", "Beverage Co"),
    ("CLI-0201", "Paper & Packaging"),
]

# Q2 — ticket volume by account by year (stg_support_tickets joined to eval_ticket_triage)
TICKETS = {
    "CLI-0007": (29, 16, 23),
    "CLI-0042": (17, 17, 72),
    "CLI-0155": (19, 17, 24),
    "CLI-0169": (19, 30, 35),
    "CLI-0201": (23, 27, 35),
}

# Q2 — 2025 graded sentiment (negative, neutral, positive) by account
SENTIMENT_2025 = {
    "CLI-0007": (5, 2, 16),
    "CLI-0042": (45, 1, 26),
    "CLI-0155": (2, 4, 18),
    "CLI-0169": (5, 7, 23),
    "CLI-0201": (9, 2, 24),
}

# Q2 — whole-book ticket count by graded category, 2023-2025 (sums to 403)
CATEGORIES = [
    ("general_inquiry", 206),
    ("delivery_delay", 118),
    ("delivery_failed", 61),
    ("wrong_item", 18),
]

# Q4b — the 31 gaps (days) between consecutive CLI-0042 delivery_delay tickets in 2025
GAPS_0042_2025 = [0, 0, 1, 0, 0, 1, 0, 18, 0, 17, 83, 34, 3, 20, 0, 2, 1, 29, 2, 8,
                  0, 0, 1, 19, 2, 2, 5, 21, 5, 30, 11]
MEDIAN_ALL_YEARS = 3          # Q4: CLI-0042 delivery_delay, all 44 pairs 2023-2025
OTHERS_DELAY_MEDIANS = (27, 37)  # Q4: the other four accounts' delivery_delay median gaps

# Q11 — on-time % by account by year (fct_account_health)
ONTIME = {
    "CLI-0007": (97.4, 97.1, 96.6),
    "CLI-0042": (98.1, 98.1, 83.9),
    "CLI-0155": (97.6, 97.2, 97.0),
    "CLI-0169": (97.2, 96.8, 94.7),
    "CLI-0201": (97.4, 96.9, 94.7),
}


# ---------------------------------------------------------------- SVG helpers
def canvas(w, h, title, subtitle=""):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="{FONT}">',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff"/>',
        f'<text x="{w/2}" y="30" text-anchor="middle" font-size="20" font-weight="bold" '
        f'fill="{INK}">{esc(title)}</text>',
    ]
    if subtitle:
        parts.append(f'<text x="{w/2}" y="50" text-anchor="middle" font-size="12.5" '
                     f'fill="{GREY}">{esc(subtitle)}</text>')
    return parts


def line(x1, y1, x2, y2, color=GRID, w=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{w}"{d}/>')


def text(x, y, s, size=12, color=INK, anchor="start", weight="normal", rotate=None):
    tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{tr}>{esc(s)}</text>')


def rect(x, y, w, h, fill, stroke="none"):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}"/>')


def save(name, parts):
    parts.append("</svg>")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write("\n".join(parts) + "\n")
    print("wrote", os.path.relpath(path, os.path.join(os.path.dirname(__file__), "..")))


def y_gridlines(parts, x0, x1, top, bot, vmin, vmax, ticks, fmt):
    for v in ticks:
        yy = bot - (v - vmin) / (vmax - vmin) * (bot - top)
        parts.append(line(x0, yy, x1, yy, GRID, 1))
        parts.append(text(x0 - 8, yy + 4, fmt(v), 11.5, GREY, "end"))


def y_title(parts, x, top, bot, label):
    parts.append(text(x, (top + bot) / 2, label, 12, GREY, "middle", rotate=-90))


def account_labels(parts, cx, bot, cid, name):
    parts.append(text(cx, bot + 20, name, 12, INK, "middle"))
    parts.append(text(cx, bot + 36, cid, 10.5, GREY, "middle"))


def year_legend(parts, x, y):
    for col, lab in YEAR_COLS:
        parts.append(rect(x, y - 10, 14, 12, col))
        parts.append(text(x + 20, y, lab, 12, INK))
        x += 80
    return x


# ---------------------------------------------------------------- chart 1: ticket volume
def chart_ticket_volume():
    W, H = 960, 500
    x0, x1 = 100, 920
    top, bot = 90, 410
    vmax = 80
    parts = canvas(W, H, "Support tickets by account, 2023 / 2024 / 2025",
                   "Count of stg_support_tickets by year opened. 107 + 107 + 189 = 403 tickets.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 20), str)
    y_title(parts, 40, top, bot, "Tickets opened (count)")
    group_w = (x1 - x0) / len(ACCOUNTS)
    bar_w = group_w * 0.24

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (cid, name) in enumerate(ACCOUNTS):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate(TICKETS[cid]):
            bx = gx + j * (bar_w + 4)
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), YEAR_COLS[j][0]))
            parts.append(text(bx + bar_w / 2, yy(val) - 5, str(val), 11, INK, "middle"))
        account_labels(parts, x0 + i * group_w + group_w / 2, bot, cid, name)
    year_legend(parts, x0, 72)
    parts.append(text((x0 + x1) / 2, H - 10, "Account (Jaffle Logistics)", 12, GREY, "middle"))
    save("01-ticket-volume-by-account-year.svg", parts)


# ---------------------------------------------------------------- chart 2: 2025 sentiment mix
def chart_sentiment_mix():
    W, H = 960, 520
    x0, x1 = 100, 920
    top, bot = 100, 430
    vmax = 80
    segs = [(RED, "negative"), (LIGHT, "neutral"), (BLUE, "positive")]
    parts = canvas(W, H, "2025 tickets by graded sentiment, per account",
                   "Stacked counts. Sentiment is a machine-graded label (eval_ticket_triage), "
                   "not the customer's own score.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 20), str)
    y_title(parts, 40, top, bot, "Tickets opened in 2025 (count)")
    group_w = (x1 - x0) / len(ACCOUNTS)
    bar_w = group_w * 0.38

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (cid, name) in enumerate(ACCOUNTS):
        bx = x0 + i * group_w + (group_w - bar_w) / 2 - 12
        base = 0
        centres = []
        for (col, _lab), val in zip(segs, SENTIMENT_2025[cid]):
            parts.append(rect(bx, yy(base + val), bar_w, yy(base) - yy(base + val), col))
            centres.append([(yy(base) + yy(base + val)) / 2 + 4, val, col])
            base += val
        # value labels beside the bar, nudged apart so none overlap (min 13px)
        for k in range(1, len(centres)):
            if centres[k - 1][0] - centres[k][0] < 13:
                centres[k][0] = centres[k - 1][0] - 13
        for cy, val, col in centres:
            parts.append(text(bx + bar_w + 6, cy, str(val), 11, GREY if col == LIGHT else col, "start", "bold"))
        parts.append(text(bx + bar_w / 2, yy(base) - 6, f"{base} total", 11, INK, "middle"))
        account_labels(parts, bx + bar_w / 2, bot, cid, name)
    lx = x0
    for col, lab in segs:
        parts.append(rect(lx, 66, 14, 12, col))
        parts.append(text(lx + 20, 76, lab, 12, INK))
        lx += 110
    parts.append(text((x0 + x1) / 2, H - 10, "Account (Jaffle Logistics)", 12, GREY, "middle"))
    save("02-sentiment-mix-by-account-2025.svg", parts)


# ---------------------------------------------------------------- chart 3: category mix
def chart_category_mix():
    W, H = 960, 380
    x0, x1 = 190, 860
    top, bot = 80, 310
    vmax = 250
    parts = canvas(W, H, "What customers wrote about, 2023–2025",
                   "Whole book, all 403 tickets, by machine-graded category (eval_ticket_triage.true_category).")
    for v in range(0, vmax + 1, 50):
        xx = x0 + v / vmax * (x1 - x0)
        parts.append(line(xx, top, xx, bot, GRID, 1))
        parts.append(text(xx, bot + 18, str(v), 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 42, "Tickets (count)", 12, GREY, "middle"))
    row_h = (bot - top) / len(CATEGORIES)
    for i, (cat, n) in enumerate(CATEGORIES):
        yy = top + i * row_h + row_h * 0.18
        h = row_h * 0.64
        w = n / vmax * (x1 - x0)
        parts.append(rect(x0, yy, w, h, BLUE))
        parts.append(text(x0 - 10, yy + h * 0.65, cat, 12.5, INK, "end"))
        parts.append(text(x0 + w + 8, yy + h * 0.65, str(n), 12, INK, "start", "bold"))
    parts.append(text(x0 - 10, top - 10, "Category", 12, GREY, "end"))
    save("03-category-mix.svg", parts)


# ---------------------------------------------------------------- chart 4: repeat intervals
def chart_repeat_intervals():
    W, H = 960, 440
    x0, x1 = 90, 920
    top, bot = 110, 360
    vmax = 90
    gaps = GAPS_0042_2025
    med = statistics.median(gaps)
    parts = canvas(W, H, "Jaffle Equipment: days between consecutive delivery-delay tickets, 2025",
                   f"CLI-0042, {len(gaps)} gaps between {len(gaps) + 1} delivery_delay tickets. "
                   "One dot per gap; dots stack when gaps are equal.")

    def xx(v):
        return x0 + v / vmax * (x1 - x0)

    # the other four accounts' delivery_delay median band
    lo, hi = OTHERS_DELAY_MEDIANS
    parts.append(rect(xx(lo), top, xx(hi) - xx(lo), bot - top, "#eef1f5"))
    parts.append(text((xx(lo) + xx(hi)) / 2, top + 16, "Other four accounts:", 11, GREY, "middle"))
    parts.append(text((xx(lo) + xx(hi)) / 2, top + 30, f"median gap {lo}–{hi} days", 11, GREY, "middle"))
    for v in range(0, vmax + 1, 10):
        parts.append(line(xx(v), bot, xx(v), bot + 5, GREY, 1))
        parts.append(text(xx(v), bot + 20, str(v), 11.5, GREY, "middle"))
    parts.append(line(x0, bot, x1, bot, GREY, 1))
    parts.append(text((x0 + x1) / 2, bot + 44, "Gap since the previous delivery_delay ticket (days)",
                      12, GREY, "middle"))
    # dots
    stack = {}
    for g in gaps:
        k = stack.get(g, 0)
        stack[g] = k + 1
        parts.append(f'<circle cx="{xx(g):.1f}" cy="{bot - 9 - k * 15:.1f}" r="4.2" '
                     f'fill="{RED}" fill-opacity="0.85"/>')
    tallest = max(stack.values())
    parts.append(text(xx(4), bot - 9 - (tallest - 1) * 15 + 4,
                      f"← {stack[0]} same-day repeats (gap 0)", 11, INK))
    parts.append(text(xx(83), bot - 24, "Feb→May: account quiet", 11, GREY, "end"))
    # medians
    parts.append(line(xx(med), top - 20, xx(med), bot, INK, 1.5, "5,3"))
    parts.append(text(xx(med) + 4, top - 24, f"2025 median: {med:g} days", 11.5, INK, "start", "bold"))
    parts.append(line(xx(MEDIAN_ALL_YEARS), top - 2, xx(MEDIAN_ALL_YEARS), bot, GREY, 1.2, "2,3"))
    parts.append(text(xx(MEDIAN_ALL_YEARS) + 4, top - 6,
                      f"2023–2025 median (44 pairs): {MEDIAN_ALL_YEARS} days", 11, GREY))
    save("04-repeat-intervals-equipment.svg", parts)


# ---------------------------------------------------------------- chart 5: on-time vs target
def chart_ontime():
    W, H = 960, 500
    x0, x1 = 100, 920
    top, bot = 90, 410
    vmin, vmax = 80, 100
    parts = canvas(W, H, "On-time rate by account, 2023 / 2024 / 2025",
                   "The service the complaints sit against (fct_account_health). "
                   "Dashed line = 97% contractual target.")
    y_gridlines(parts, x0, x1, top, bot, vmin, vmax, [80, 85, 90, 95, 100], lambda v: f"{v}%")
    y_title(parts, 40, top, bot, "Shipments delivered on time (%)")
    parts.append(text(x0 - 8, bot + 14, "(axis starts at 80%)", 9.5, GREY, "end"))

    def yy(v):
        return bot - (v - vmin) / (vmax - vmin) * (bot - top)

    group_w = (x1 - x0) / len(ACCOUNTS)
    bar_w = group_w * 0.24
    labels = []
    for i, (cid, name) in enumerate(ACCOUNTS):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate(ONTIME[cid]):
            bx = gx + j * (bar_w + 4)
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), YEAR_COLS[j][0]))
            labels.append((bx + bar_w / 2, yy(val) - 5, f"{val:.1f}"))
        account_labels(parts, x0 + i * group_w + group_w / 2, bot, cid, name)
    # target line over the bars, value labels over the line (white halo keeps them legible)
    yt = yy(TARGET)
    parts.append(line(x0, yt, x1, yt, RED, 1.5, "6,4"))
    for lx_, ly_, s in labels:
        parts.append(f'<text x="{lx_:.1f}" y="{ly_:.1f}" font-size="10" fill="{INK}" '
                     f'text-anchor="middle" stroke="#ffffff" stroke-width="3" '
                     f'paint-order="stroke">{esc(s)}</text>')
    lx = year_legend(parts, x0, 72)
    parts.append(line(lx, 68, lx + 24, 68, RED, 1.5, "6,4"))
    parts.append(text(lx + 30, 72, "97% contractual target", 12, RED, "start", "bold"))
    parts.append(text((x0 + x1) / 2, H - 10, "Account (Jaffle Logistics)", 12, GREY, "middle"))
    save("05-ontime-by-account-year.svg", parts)


if __name__ == "__main__":
    chart_ticket_volume()
    chart_sentiment_mix()
    chart_category_mix()
    chart_repeat_intervals()
    chart_ontime()
