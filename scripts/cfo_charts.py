#!/usr/bin/env python3
"""Generate the CFO arrival-briefing charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible from
reports/cfo-arrival-briefing.md's appendix queries.

Output: reports/assets/cfo/*.svg  (committed alongside the report).

Design rules (sober, unaudited-numbers-safe):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar;
  * the 97% contractual on-time target drawn as a reference line on any rate chart;
  * consistent colour meaning: red = below target / worsening, green = at or above target,
    neutral blue = a series with no target of its own.

Source of every number: hive_metastore.dbt_smcintyre_jaffle_logistics_prod, via the
dbt Platform remote MCP `execute_sql` tool. The dataset's present is 2025-12-31.
"""
import os
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "cfo")
TARGET = 97.0  # whole-book contractual on-time reference line, %

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # below target / worsening
GREEN = "#2e7d32"    # at or above target
BLUE = "#2c6fbb"     # neutral series
GREY = "#555555"
GRID = "#d9d9d9"
INK = "#1a1a1a"

FONT = "Helvetica, Arial, sans-serif"


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from execute_sql)
# 1. whole-book + Jaffle Equipment (CLI-0042) on-time % by quarter
QUARTERS = [
    ("2023-Q1", 97.12, 97.00), ("2023-Q2", 97.24, 98.91), ("2023-Q3", 97.97, 99.05),
    ("2023-Q4", 97.65, 97.46), ("2024-Q1", 96.91, 99.17), ("2024-Q2", 97.47, 97.83),
    ("2024-Q3", 97.56, 97.47), ("2024-Q4", 96.98, 97.56), ("2025-Q1", 90.33, 86.14),
    ("2025-Q2", 95.40, 89.58), ("2025-Q3", 95.12, 82.47), ("2025-Q4", 92.62, 78.69),
]

# 2. 2025 missed shipments by account (ranked) + the account's 2025 on-time %
MISSED_2025 = [
    ("Jaffle Equipment", 67, 83.89),
    ("Jaffle Paper & Packaging", 22, 94.69),
    ("Jaffle Beverage Co", 21, 94.67),
    ("Jaffle Storefronts", 13, 96.64),
    ("Jaffle Crew Outfitters", 12, 96.98),
]

# 3. three-year on-time rate by account
ONTTIME_3YR = [
    ("Jaffle Equipment", 98.07, 98.07, 83.89),
    ("Jaffle Paper & Packaging", 97.36, 96.90, 94.69),
    ("Jaffle Beverage Co", 97.16, 96.81, 94.67),
    ("Jaffle Storefronts", 97.36, 97.11, 96.64),
    ("Jaffle Crew Outfitters", 97.56, 97.16, 96.98),
]

# 4. fleet maintenance spend ($) by hub by year
MAINT_HUB = [
    ("Chicago", 12576, 17588, 64456),
    ("Cincinnati", 17423, 437, 31362),
    ("Columbus", 15538, 48044, 78083),
    ("Detroit", 27990, 19829, 46581),
    ("Indianapolis", 16828, 18203, 47096),
]

# 5. maintenance spend ($) by month, 2025
MAINT_MONTH_2025 = [
    (1, 35350), (2, 33574), (3, 17045), (4, 24675), (5, 25458), (6, 31939),
    (7, 20757), (8, 34710), (9, 3868), (10, 8748), (11, 13055), (12, 18399),
]

# 6. support ticket volume by account by year
TICKETS = [
    ("Jaffle Equipment", 17, 17, 72),
    ("Jaffle Paper & Packaging", 23, 27, 35),
    ("Jaffle Beverage Co", 19, 30, 35),
    ("Jaffle Crew Outfitters", 19, 17, 24),
    ("Jaffle Storefronts", 29, 16, 23),
]

# 7. contract-credit exposure, computed from monthly on-time vs each account's SLA.
#    Raw input: per-account 2025 monthly on-time % (CLI id -> [m1..m12])
SLA = {"CLI-0007": 97.0, "CLI-0042": 97.0, "CLI-0155": 95.0, "CLI-0169": 95.0, "CLI-0201": 92.0}
NAME = {"CLI-0007": "Jaffle Storefronts", "CLI-0042": "Jaffle Equipment",
        "CLI-0155": "Jaffle Crew Outfitters", "CLI-0169": "Jaffle Beverage Co",
        "CLI-0201": "Jaffle Paper & Packaging"}
MONTHLY_2025 = {
    "CLI-0007": [86.21, 87.50, 93.55, 100.0, 97.14, 100.0, 100.0, 96.67, 100.0, 100.0, 97.62, 97.73],
    "CLI-0042": [76.32, 89.66, 94.12, 91.43, 90.91, 85.71, 84.38, 81.25, 81.82, 80.56, 78.38, 77.55],
    "CLI-0155": [83.87, 93.33, 100.0, 100.0, 93.33, 100.0, 97.78, 100.0, 100.0, 100.0, 97.83, 97.37],
    "CLI-0169": [78.43, 93.94, 100.0, 100.0, 95.00, 100.0, 100.0, 100.0, 94.12, 100.0, 92.31, 95.35],
    "CLI-0201": [91.18, 100.0, 96.43, 97.22, 87.88, 96.97, 100.0, 90.32, 100.0, 97.06, 92.31, 90.00],
}
CREDIT_RATE = 1.0    # % of monthly spend credited per full point below SLA
CAP_PER_MONTH = 10.0  # contract cap: 10% of monthly spend per month


def exposure():
    """Return [(name, uncapped_pct, capped_pct, months_in_breach)] ranked by uncapped."""
    rows = []
    for cid, months in MONTHLY_2025.items():
        sla = SLA[cid]
        pts = [max(0.0, sla - m) for m in months]
        uncapped = sum(CREDIT_RATE * p for p in pts)
        capped = sum(min(CREDIT_RATE * p, CAP_PER_MONTH) for p in pts)
        breach = sum(1 for p in pts if p > 0)
        rows.append((NAME[cid], uncapped, capped, breach))
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows


# 8. driver employment mix by hub (contractor vs employee) + weighted avg perf score
DRIVER_MIX = [
    # city, contractors, employees, avg_perf
    ("Chicago", 3, 7, 3.91),
    ("Cincinnati", 5, 8, 3.48),
    ("Columbus", 8, 9, 3.97),
    ("Detroit", 5, 2, 3.83),
    ("Indianapolis", 2, 7, 3.76),
]


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


def y_axis(parts, x0, y0, x1, y_top, y_bot, vmin, vmax, ticks, fmt):
    """Draw a left y-axis with horizontal gridlines. y_bot is the baseline."""
    for v in ticks:
        yy = y_bot - (v - vmin) / (vmax - vmin) * (y_bot - y_top)
        parts.append(line(x0, yy, x1, yy, GRID, 1))
        parts.append(text(x0 - 8, yy + 4, fmt(v), 11.5, GREY, "end"))


# ---------------------------------------------------------------- chart 1: line, quarterly
def chart_quarter():
    W, H = 960, 520
    x0, x1 = 90, 920
    y_top, y_bot = 80, 430
    vmin, vmax = 75, 100
    parts = canvas(W, H, "On-time delivery by quarter, 2023 \u2192 2025",
                   "Whole book vs Jaffle Equipment (CLI-0042). Dashed line = 97% contractual target.")
    ticks = [75, 80, 85, 90, 95, 100]
    y_axis(parts, x0, y_top, x1, y_top, y_bot, vmin, vmax, ticks, lambda v: f"{v}%")
    # reference line at target
    yt = y_bot - (TARGET - vmin) / (vmax - vmin) * (y_bot - y_top)
    parts.append(line(x0, yt, x1, yt, RED, 1.5, "6,4"))
    parts.append(text(x1, yt - 6, "97% contractual target", 11.5, RED, "end", "bold"))
    n = len(QUARTERS)
    step = (x1 - x0) / n
    xs = [x0 + step * (i + 0.5) for i in range(n)]

    def yy(v):
        return y_bot - (v - vmin) / (vmax - vmin) * (y_bot - y_top)

    for i, (q, _ov, _eq) in enumerate(QUARTERS):
        parts.append(line(xs[i], y_top, xs[i], y_bot, "#f0f0f0", 1))
        parts.append(text(xs[i], y_bot + 18, q, 10.5, GREY, "middle", rotate=45 if False else None))
    # x labels rotate for space
    # series: whole book (blue), equipment (red)
    for series_idx, (col, color, key) in enumerate([("whole book", BLUE, 1), ("Jaffle Equipment", RED, 2)]):
        pts = [(xs[i], yy(QUARTERS[i][key])) for i in range(n)]
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="2.6"/>')
        for (x, y) in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')
        # end label
        ex, ey = pts[-1]
        parts.append(text(ex + 6, ey + 4, f"{QUARTERS[-1][key]:.1f}%", 11.5, color, "start", "bold"))
    # legend
    parts.append(line(x0, 62, x0 + 24, 62, BLUE, 3))
    parts.append(text(x0 + 30, 66, "Whole book", 12, INK))
    parts.append(line(x0 + 160, 62, x0 + 184, 62, RED, 3))
    parts.append(text(x0 + 190, 66, "Jaffle Equipment", 12, INK))
    parts.append(text(W / 2, H - 12, "Quarter (shipment created date)", 12, GREY, "middle"))
    save("01-ontime-by-quarter.svg", parts)


# ---------------------------------------------------------------- chart 2: missed bars
def chart_missed():
    W, H = 960, 460
    x0, x1 = 230, 880
    top, bot = 80, 400
    vmax = 70
    parts = canvas(W, H, "Missed shipments by account, 2025",
                   "Ranked largest first. Bar = missed shipments; label = the account's 2025 on-time %.")
    for v in range(0, vmax + 1, 10):
        xx = x0 + v / vmax * (x1 - x0)
        parts.append(line(xx, top, xx, bot, GRID, 1))
        parts.append(text(xx, bot + 18, str(v), 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 40, "Missed shipments (units)", 12, GREY, "middle"))
    n = len(MISSED_2025)
    row_h = (bot - top) / n
    for i, (name, missed, rate) in enumerate(MISSED_2025):
        yy = top + i * row_h + row_h * 0.15
        h = row_h * 0.7
        color = RED if rate < TARGET else GREEN
        w = missed / vmax * (x1 - x0)
        parts.append(rect(x0, yy, w, h, color))
        parts.append(text(x0 - 10, yy + h * 0.72, name, 12.5, INK, "end"))
        parts.append(text(x0 + w + 8, yy + h * 0.72, f"{missed}  ({rate:.1f}% on time)", 12, INK))
    parts.append(text(x0, top - 12, "97% target = green bar; below = red", 11.5, GREY))
    save("02-missed-shipments-by-account.svg", parts)


# ---------------------------------------------------------------- chart 3: grouped 3yr
def chart_3yr_account():
    W, H = 960, 500
    x0, x1 = 90, 920
    top, bot = 80, 410
    vmin, vmax = 80, 100
    parts = canvas(W, H, "On-time rate by account, 2023 / 2024 / 2025",
                   "Grouped bars; dashed line = 97% contractual target. Red = below target.")
    y_axis(parts, x0, top, x1, top, bot, vmin, vmax, [80, 85, 90, 95, 100], lambda v: f"{v}%")
    yt = bot - (TARGET - vmin) / (vmax - vmin) * (bot - top)
    parts.append(line(x0, yt, x1, yt, RED, 1.5, "6,4"))
    n = len(ONTTIME_3YR)
    group_w = (x1 - x0) / n
    bar_w = group_w * 0.24
    cols = [("#9aa7b5", "2023"), ("#5b7fa6", "2024"), (BLUE, "2025")]

    def yy(v):
        return bot - (v - vmin) / (vmax - vmin) * (bot - top)

    for i, (name, y23, y24, y25) in enumerate(ONTTIME_3YR):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate((y23, y24, y25)):
            h = yy(val) - yy(vmax) if False else (bot - yy(val))
            bx = gx + j * (bar_w + 4)
            col = cols[j][0]
            if j == 2:
                col = RED if val < TARGET else GREEN
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), col))
            parts.append(text(bx + bar_w / 2, yy(val) - 4, f"{val:.1f}", 9.8, INK, "middle"))
        parts.append(text(x0 + i * group_w + group_w / 2, bot + 20, name.replace("Jaffle ", ""),
                          11.5, INK, "middle", rotate=0))
    # legend
    lx = x0
    for col, lab in cols:
        parts.append(rect(lx, 60, 14, 12, col))
        parts.append(text(lx + 20, 70, lab, 12, INK))
        lx += 90
    parts.append(line(lx, 66, lx + 24, 66, RED, 1.5, "6,4"))
    parts.append(text(lx + 30, 70, "97% contractual target", 12, RED, "start", "bold"))
    parts.append(text((x0 + x1) / 2, H - 10, "Account (grouped by year)", 12, GREY, "middle"))
    save("03-ontime-3yr-by-account.svg", parts)


# ---------------------------------------------------------------- chart 4: maintenance hub-year
def chart_maint_hub():
    W, H = 960, 500
    x0, x1 = 110, 920
    top, bot = 80, 410
    vmax = 80000
    parts = canvas(W, H, "Fleet maintenance spend by hub by year",
                   "Total fleet_work_orders.cost, USD. The only genuine cost record in this data.")
    for v in range(0, vmax + 1, 20000):
        gy = bot - v / vmax * (bot - top)
        parts.append(line(x0, gy, x1, gy, GRID, 1))
        parts.append(text(x0 - 8, gy + 4, f"${v//1000}k", 11.5, GREY, "end"))
    parts.append(text(x0 - 8, top - 12, "USD", 11.5, GREY, "end"))
    n = len(MAINT_HUB)
    group_w = (x1 - x0) / n
    bar_w = group_w * 0.24
    cols = [("#9aa7b5", "2023"), ("#5b7fa6", "2024"), (BLUE, "2025")]

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (city, a, b, c) in enumerate(MAINT_HUB):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate((a, b, c)):
            bx = gx + j * (bar_w + 4)
            col = cols[j][0]
            if j == 2 and val >= max(a, b):
                col = RED  # 2025 the highest of the three -> worsening
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), col))
            parts.append(text(bx + bar_w / 2, yy(val) - 4, f"${val/1000:.0f}k", 9.6, INK, "middle"))
        parts.append(text(x0 + i * group_w + group_w / 2, bot + 20, city, 12, INK, "middle"))
    lx = x0
    for col, lab in cols:
        parts.append(rect(lx, 60, 14, 12, col))
        parts.append(text(lx + 20, 70, lab, 12, INK))
        lx += 90
    parts.append(text((x0 + x1) / 2, H - 10, "Hub (city)", 12, GREY, "middle"))
    save("04-maintenance-by-hub-year.svg", parts)


# ---------------------------------------------------------------- chart 5: maintenance by month
def chart_maint_month():
    W, H = 960, 470
    x0, x1 = 100, 900
    top, bot = 80, 400
    vmax = 40000
    parts = canvas(W, H, "Maintenance spend by month, 2025",
                   "fleet_work_orders.cost, USD, by month opened. Shows cost creep and the summer/Jan peaks.")
    for v in range(0, vmax + 1, 10000):
        gy = bot - v / vmax * (bot - top)
        parts.append(line(x0, gy, x1, gy, GRID, 1))
        parts.append(text(x0 - 8, gy + 4, f"${v//1000}k", 11.5, GREY, "end"))
    n = len(MAINT_MONTH_2025)
    step = (x1 - x0) / n
    xs = [x0 + step * (i + 0.5) for i in range(n)]
    avg = sum(c for _, c in MAINT_MONTH_2025) / n
    ya = bot - avg / vmax * (bot - top)
    parts.append(line(x0, ya, x1, ya, GREY, 1.2, "5,4"))
    parts.append(text(x1, ya - 5, f"monthly avg ${avg/1000:.0f}k", 11, GREY, "end"))

    def yy(v):
        return bot - v / vmax * (bot - top)

    pts = [(xs[i], yy(c)) for i, (_, c) in enumerate(MAINT_MONTH_2025)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    parts.append(f'<polyline points="{d}" fill="none" stroke="{BLUE}" stroke-width="2.6"/>')
    for i, (m, c) in enumerate(MAINT_MONTH_2025):
        parts.append(f'<circle cx="{xs[i]:.1f}" cy="{yy(c):.1f}" r="3.2" fill="{BLUE}"/>')
        parts.append(text(xs[i], yy(c) - 8, f"${c/1000:.1f}k", 9.8, INK, "middle"))
        parts.append(text(xs[i], bot + 18, f"M{m}", 11, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, H - 10, "Month, 2025", 12, GREY, "middle"))
    save("05-maintenance-by-month-2025.svg", parts)


# ---------------------------------------------------------------- chart 6: tickets
def chart_tickets():
    W, H = 960, 500
    x0, x1 = 110, 920
    top, bot = 80, 410
    vmax = 80
    parts = canvas(W, H, "Support ticket volume by account by year",
                   "support_tickets count. The customer-pain trend.")
    for v in range(0, vmax + 1, 20):
        gy = bot - v / vmax * (bot - top)
        parts.append(line(x0, gy, x1, gy, GRID, 1))
        parts.append(text(x0 - 8, gy + 4, str(v), 11.5, GREY, "end"))
    parts.append(text(x0 - 8, top - 12, "Tickets", 11.5, GREY, "end"))
    n = len(TICKETS)
    group_w = (x1 - x0) / n
    bar_w = group_w * 0.24
    cols = [("#9aa7b5", "2023"), ("#5b7fa6", "2024"), (BLUE, "2025")]

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (name, a, b, c) in enumerate(TICKETS):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate((a, b, c)):
            bx = gx + j * (bar_w + 4)
            col = cols[j][0]
            if j == 2 and val > max(a, b):
                col = RED
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), col))
            parts.append(text(bx + bar_w / 2, yy(val) - 4, str(val), 10.5, INK, "middle"))
        parts.append(text(x0 + i * group_w + group_w / 2, bot + 20, name.replace("Jaffle ", ""),
                          11.5, INK, "middle"))
    lx = x0
    for col, lab in cols:
        parts.append(rect(lx, 60, 14, 12, col))
        parts.append(text(lx + 20, 70, lab, 12, INK))
        lx += 90
    parts.append(text((x0 + x1) / 2, H - 10, "Account", 12, GREY, "middle"))
    save("06-tickets-by-account-year.svg", parts)


# ---------------------------------------------------------------- chart 7: exposure
def chart_exposure():
    rows = exposure()
    W, H = 960, 460
    x0, x1 = 250, 830
    top, bot = 90, 400
    vmax = 160
    parts = canvas(W, H, "Contract credit exposure by account, 2025",
                   "Penalty exposure as % of one month's spend: \u03a3 over breach months of "
                   "1.0% \u00d7 points below SLA. Not a currency amount \u2014 no revenue table exists.")
    for v in range(0, vmax + 1, 20):
        xx = x0 + v / vmax * (x1 - x0)
        parts.append(line(xx, top, xx, bot, GRID, 1))
        parts.append(text(xx, bot + 18, f"{v}%", 11, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 40, "Exposure, % of monthly spend (summed over 2025)",
                      12, GREY, "middle"))
    n = len(rows)
    row_h = (bot - top) / n
    for i, (name, unc, capped, breach) in enumerate(rows):
        yy = top + i * row_h + row_h * 0.15
        h = row_h * 0.7
        w = unc / vmax * (x1 - x0)
        parts.append(rect(x0, yy, w, h, RED))
        parts.append(text(x0 - 10, yy + h * 0.72, name, 12.5, INK, "end"))
        parts.append(text(x0 + w + 8, yy + h * 0.72,
                          f"{unc:.1f}%   ({breach} months in breach; capped {capped:.1f}%)", 11.5, INK))
    save("07-credit-exposure-by-account.svg", parts)


# ---------------------------------------------------------------- chart 8: driver mix
def chart_driver_mix():
    W, H = 960, 500
    x0, x1 = 110, 920
    top, bot = 80, 410
    vmax = 18
    parts = canvas(W, H, "Driver employment mix by hub",
                   "Stacked: contractors + employees. Label = average driver performance score (1\u20135).")
    for v in range(0, vmax + 1, 3):
        gy = bot - v / vmax * (bot - top)
        parts.append(line(x0, gy, x1, gy, GRID, 1))
        parts.append(text(x0 - 8, gy + 4, str(v), 11.5, GREY, "end"))
    parts.append(text(x0 - 8, top - 12, "Drivers", 11.5, GREY, "end"))
    n = len(DRIVER_MIX)
    group_w = (x1 - x0) / n
    bar_w = group_w * 0.44

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (city, con, emp, perf) in enumerate(DRIVER_MIX):
        bx = x0 + i * group_w + (group_w - bar_w) / 2
        total = con + emp
        # contractor (bottom) then employee (stacked on top)
        parts.append(rect(bx, yy(con), bar_w, bot - yy(con), BLUE))
        parts.append(rect(bx, yy(total), bar_w, yy(con) - yy(total), "#9aa7b5"))
        parts.append(text(bx + bar_w / 2, yy(total) - 6, f"{total} drivers", 10.5, INK, "middle"))
        parts.append(text(bx + bar_w / 2, bot + 20, city, 12, INK, "middle"))
        parts.append(text(bx + bar_w / 2, bot + 38, f"perf {perf:.2f}", 11, GREY, "middle"))
        # inner labels (white, centred in each segment)
        parts.append(text(bx + bar_w / 2, (bot + yy(con)) / 2 + 3, f"{con}c", 10, "#ffffff", "middle", "bold"))
        parts.append(text(bx + bar_w / 2, (yy(con) + yy(total)) / 2 + 3, f"{emp}e", 10, "#ffffff", "middle", "bold"))
    lx = x0
    for col, lab in [(BLUE, "Contracted (contractor)"), ("#9aa7b5", "Employed (employee)")]:
        parts.append(rect(lx, 60, 14, 12, col))
        parts.append(text(lx + 20, 70, lab, 12, INK))
        lx += 220
    parts.append(text((x0 + x1) / 2, H - 10, "Hub (city)", 12, GREY, "middle"))
    save("08-driver-mix-by-hub.svg", parts)


if __name__ == "__main__":
    chart_quarter()
    chart_missed()
    chart_3yr_account()
    chart_maint_hub()
    chart_maint_month()
    chart_tickets()
    chart_exposure()
    chart_driver_mix()
    print("\nExposure ranking (uncapped % of monthly spend, capped %):")
    for name, unc, capped, breach in exposure():
        print(f"  {name:28s} {unc:7.1f}%  capped {capped:6.1f}%  ({breach} months in breach)")
