#!/usr/bin/env python3
"""Generate the Head of People persona-report charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible without the
warehouse. Every number comes from the data pack behind
reports/persona-people.md (queries Q2-Q19, copied into that report's appendix).

Output: reports/assets/personas/p*.svg  (committed alongside the report).

Design rules (match scripts/cfo_charts.py and scripts/persona_cx_charts.py):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar;
  * reference lines (fleet average, thresholds) drawn dashed and labelled;
  * consistent colour meaning: red = the problem cell / gap, neutral blue = employees /
    a series with no target, grey-blue ramp = ordered bands, amber = contractors.

Run from the repo root:  python3 scripts/persona_people_charts.py
"""
import os
import statistics
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "personas")

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # the problem cell / gap
BLUE = "#2c6fbb"     # employees / neutral series
AMBER = "#c58a1b"    # contractors
GREY = "#555555"
GRID = "#d9d9d9"
INK = "#1a1a1a"
PALE = "#c9d3de"
LIGHT = "#9aa7b5"
MID = "#5b7fa6"
DARK = "#1f4e79"
BAND_COLS = [PALE, LIGHT, MID, DARK]   # ordered bands, light -> dark

FONT = "Helvetica, Arial, sans-serif"


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from the data pack)
HUBS = ["HUB-CHI", "HUB-CIN", "HUB-CMH", "HUB-DET", "HUB-IND"]
HUB_NAMES = {"HUB-CHI": "Chicago", "HUB-CIN": "Cincinnati", "HUB-CMH": "Columbus",
             "HUB-DET": "Detroit", "HUB-IND": "Indianapolis"}

# Q6 / Q7 / Q11 / Q12 / Q13 — one row per driver (all 56):
# driver_id: (hub, employment type c/e, perf_score,
#             docs (onboarding, review, certification, training, disciplinary, exit),
#             routes 2025, exceptions 2025, attributed incidents all-time, attributed incidents 2025)
DRIVERS = {
    "DRV-01005": ("HUB-CHI", "c", 4.89, (1, 0, 0, 0, 0, 0), 76, 78, 1, 0),
    "DRV-01007": ("HUB-CHI", "e", 2.84, (1, 0, 0, 0, 0, 0), 78, 154, 3, 1),
    "DRV-01011": ("HUB-CHI", "e", 4.01, (1, 0, 0, 0, 0, 0), 97, 98, 1, 1),
    "DRV-01012": ("HUB-CHI", "c", 3.20, (1, 1, 0, 0, 0, 0), 90, 86, 6, 3),
    "DRV-01017": ("HUB-CHI", "e", 3.77, (1, 0, 1, 0, 0, 0), 80, 108, 4, 3),
    "DRV-01020": ("HUB-CHI", "e", 3.81, (1, 1, 0, 1, 0, 0), 78, 135, 3, 1),
    "DRV-01035": ("HUB-CHI", "e", 4.76, (1, 0, 1, 0, 0, 0), 79, 105, 2, 1),
    "DRV-01047": ("HUB-CHI", "e", 4.02, (1, 0, 0, 1, 1, 0), 98, 114, 5, 2),
    "DRV-01048": ("HUB-CHI", "e", 3.45, (1, 1, 0, 1, 0, 0), 72, 53, 3, 0),
    "DRV-01190": ("HUB-CHI", "c", 4.35, (1, 0, 0, 0, 0, 0), 0, 0, 2, 0),
    "DRV-01002": ("HUB-CIN", "c", 4.19, (1, 0, 1, 0, 0, 0), 64, 40, 3, 1),
    "DRV-01003": ("HUB-CIN", "e", 4.63, (1, 0, 0, 0, 0, 0), 60, 24, 2, 1),
    "DRV-01008": ("HUB-CIN", "e", 2.82, (1, 1, 0, 1, 0, 0), 50, 36, 4, 2),
    "DRV-01019": ("HUB-CIN", "c", 4.75, (1, 0, 1, 0, 0, 0), 54, 24, 7, 2),
    "DRV-01023": ("HUB-CIN", "c", 3.13, (1, 0, 0, 0, 1, 0), 77, 50, 4, 1),
    "DRV-01025": ("HUB-CIN", "e", 2.92, (1, 0, 0, 0, 0, 0), 43, 29, 3, 0),
    "DRV-01026": ("HUB-CIN", "e", 3.13, (1, 0, 0, 0, 0, 0), 51, 28, 1, 0),
    "DRV-01027": ("HUB-CIN", "e", 2.94, (1, 1, 0, 0, 0, 0), 70, 23, 7, 1),
    "DRV-01029": ("HUB-CIN", "e", 2.88, (1, 0, 0, 0, 0, 0), 63, 24, 3, 3),
    "DRV-01034": ("HUB-CIN", "c", 2.95, (1, 1, 1, 0, 1, 0), 51, 28, 6, 3),
    "DRV-01038": ("HUB-CIN", "e", 3.43, (1, 0, 0, 0, 0, 0), 60, 12, 0, 0),
    "DRV-01041": ("HUB-CIN", "e", 3.23, (1, 0, 0, 1, 0, 0), 69, 34, 4, 0),
    "DRV-01192": ("HUB-CIN", "c", 4.28, (1, 0, 0, 0, 0, 0), 0, 0, 0, 0),
    "DRV-01001": ("HUB-CMH", "c", 4.85, (1, 1, 1, 0, 0, 0), 37, 26, 1, 0),
    "DRV-01009": ("HUB-CMH", "e", 4.61, (1, 1, 1, 0, 0, 0), 62, 25, 2, 1),
    "DRV-01010": ("HUB-CMH", "e", 4.20, (1, 0, 0, 0, 0, 0), 41, 30, 3, 2),
    "DRV-01013": ("HUB-CMH", "c", 3.69, (1, 0, 0, 0, 0, 0), 47, 34, 5, 0),
    "DRV-01015": ("HUB-CMH", "e", 4.48, (1, 1, 0, 1, 0, 0), 44, 34, 5, 2),
    "DRV-01016": ("HUB-CMH", "e", 3.93, (1, 0, 0, 0, 0, 0), 50, 33, 5, 1),
    "DRV-01018": ("HUB-CMH", "e", 3.01, (1, 0, 0, 1, 0, 0), 34, 12, 2, 1),
    "DRV-01028": ("HUB-CMH", "c", 3.65, (1, 0, 1, 0, 0, 0), 49, 30, 4, 1),
    "DRV-01030": ("HUB-CMH", "e", 3.99, (1, 0, 0, 0, 0, 0), 53, 18, 0, 0),
    "DRV-01036": ("HUB-CMH", "c", 3.40, (1, 1, 0, 0, 0, 0), 44, 26, 4, 2),
    "DRV-01039": ("HUB-CMH", "c", 3.36, (1, 1, 1, 0, 0, 0), 58, 24, 6, 2),
    "DRV-01040": ("HUB-CMH", "c", 3.37, (1, 1, 0, 0, 0, 0), 37, 7, 4, 2),
    "DRV-01043": ("HUB-CMH", "e", 4.54, (1, 0, 0, 0, 0, 0), 55, 27, 5, 1),
    "DRV-01044": ("HUB-CMH", "e", 4.14, (1, 1, 0, 0, 0, 0), 50, 30, 3, 0),
    "DRV-01049": ("HUB-CMH", "c", 4.23, (1, 0, 0, 0, 1, 0), 48, 13, 5, 2),
    "DRV-01189": ("HUB-CMH", "c", 4.10, (1, 1, 0, 0, 0, 0), 0, 0, 0, 0),
    "DRV-01194": ("HUB-CMH", "e", 3.88, (1, 0, 0, 0, 0, 0), 0, 0, 0, 0),
    "DRV-01004": ("HUB-DET", "c", 4.39, (1, 0, 0, 0, 1, 0), 116, 42, 7, 3),
    "DRV-01014": ("HUB-DET", "c", 4.21, (1, 1, 1, 0, 0, 0), 115, 73, 11, 5),
    "DRV-01021": ("HUB-DET", "c", 3.60, (1, 1, 1, 0, 1, 0), 132, 83, 7, 1),
    "DRV-01022": ("HUB-DET", "e", 3.40, (1, 0, 0, 0, 0, 0), 143, 67, 8, 5),
    "DRV-01037": ("HUB-DET", "c", 4.08, (1, 1, 1, 1, 0, 0), 123, 58, 9, 3),
    "DRV-01046": ("HUB-DET", "e", 2.96, (1, 1, 0, 0, 1, 0), 112, 59, 5, 1),
    "DRV-01193": ("HUB-DET", "c", 4.16, (1, 0, 0, 0, 0, 0), 0, 0, 1, 0),
    "DRV-01006": ("HUB-IND", "e", 3.75, (1, 0, 0, 1, 0, 0), 84, 36, 4, 1),
    "DRV-01024": ("HUB-IND", "e", 4.02, (1, 0, 1, 1, 0, 0), 100, 38, 8, 3),
    "DRV-01031": ("HUB-IND", "c", 4.21, (1, 0, 1, 1, 1, 0), 89, 49, 10, 2),
    "DRV-01032": ("HUB-IND", "e", 3.07, (1, 0, 0, 0, 0, 0), 101, 52, 6, 4),
    "DRV-01033": ("HUB-IND", "e", 2.82, (1, 1, 0, 1, 0, 0), 78, 49, 4, 0),
    "DRV-01042": ("HUB-IND", "e", 4.70, (1, 0, 0, 0, 0, 0), 74, 22, 3, 1),
    "DRV-01045": ("HUB-IND", "e", 3.96, (1, 0, 0, 0, 0, 0), 93, 47, 7, 3),
    "DRV-01188": ("HUB-IND", "c", 3.30, (1, 0, 1, 0, 1, 1), 100, 94, 5, 1),
    "DRV-01191": ("HUB-IND", "e", 4.02, (1, 0, 0, 0, 0, 0), 0, 0, 1, 0),
}

# Q4 — tenure bands as of 2025-12-31: (<2y, 2-4y, 4-6y, 6y+)
TENURE = {
    "HUB-CHI": (1, 5, 2, 2),
    "HUB-CIN": (3, 3, 4, 3),
    "HUB-CMH": (3, 3, 6, 5),
    "HUB-DET": (2, 1, 1, 3),
    "HUB-IND": (0, 5, 2, 2),
}

# Q10 — 2025 routes by hub
ROUTES_2025 = {"HUB-CHI": 748, "HUB-CIN": 712, "HUB-CMH": 709, "HUB-DET": 741, "HUB-IND": 719}

# Q15 — 2025 payroll by employment type: (cost $, hours, overtime hours, routes, cost per route $)
PAY_2025 = {
    "contractor": (1017289.35, 12663, 0, 1407, 723.02),
    "employee": (823985.72, 19998, 2485, 2222, 370.83),
}
# Q16 — range of per-driver 2025 cost per route, $ (min, max) by type
CPR_RANGE = {"contractor": (684, 762), "employee": (344, 412)}
# Q19 — 2025 exceptions per 100 routes by type
EXC_RATE_2025 = {"contractor": 61.48, "employee": 70.03}
FLEET_CPR_2025 = 1841275.07 / 3629  # Q14: 2025 payroll / routes run (~$507 per route)


def hub_of(d):
    return DRIVERS[d][0]


def working(d):
    return DRIVERS[d][4] > 0


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


def halo(x, y, s, size=11, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}" stroke="#ffffff" stroke-width="3" '
            f'paint-order="stroke">{esc(s)}</text>')


def rect(x, y, w, h, fill, stroke="none"):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}"/>')


def circle(cx, cy, r, fill, stroke="none", opacity=0.9):
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
            f'fill-opacity="{opacity}" stroke="{stroke}"/>')


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


def hub_labels(parts, cx, bot, hub):
    parts.append(text(cx, bot + 20, HUB_NAMES[hub], 12, INK, "middle"))
    parts.append(text(cx, bot + 36, hub, 10.5, GREY, "middle"))


def legend(parts, x, y, items, step=130):
    for col, lab in items:
        parts.append(rect(x, y - 10, 14, 12, col))
        parts.append(text(x + 20, y, lab, 12, INK))
        x += step
    return x


def stacked_bars(parts, x0, x1, top, bot, vmax, rows, cols, totals_fmt="{} total"):
    """rows: list of (hub, tuple of segment values); segments drawn bottom-up in cols order."""
    group_w = (x1 - x0) / len(rows)
    bar_w = group_w * 0.42

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (hub, vals) in enumerate(rows):
        bx = x0 + i * group_w + (group_w - bar_w) / 2
        base = 0
        for col, val in zip(cols, vals):
            if val:
                parts.append(rect(bx, yy(base + val), bar_w, yy(base) - yy(base + val), col, "#ffffff"))
                fill = INK if col in (PALE, LIGHT) else "#ffffff"
                parts.append(text(bx + bar_w / 2, (yy(base) + yy(base + val)) / 2 + 4, str(val),
                                  11, fill, "middle", "bold"))
            base += val
        parts.append(text(bx + bar_w / 2, yy(base) - 6, totals_fmt.format(base), 11, INK, "middle"))
        hub_labels(parts, bx + bar_w / 2, bot, hub)
    return group_w, bar_w


# ---------------------------------------------------------------- p1: headcount by hub and type
def chart_headcount():
    W, H = 960, 500
    x0, x1 = 100, 920
    top, bot = 100, 410
    vmax = 20
    rows = []
    for hub in HUBS:
        c = sum(1 for d in DRIVERS if hub_of(d) == hub and DRIVERS[d][1] == "c")
        e = sum(1 for d in DRIVERS if hub_of(d) == hub and DRIVERS[d][1] == "e")
        rows.append((hub, (e, c)))
    tot_c = sum(r[1][1] for r in rows)
    tot_e = sum(r[1][0] for r in rows)
    parts = canvas(W, H, "Driver headcount by hub and employment type",
                   f"All {tot_c + tot_e} drivers on stg_drivers: {tot_e} employees + {tot_c} contractors. "
                   "Headcount, not who worked in 2025.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 5), str)
    y_title(parts, 40, top, bot, "Drivers (headcount)")
    group_w, bar_w = stacked_bars(parts, x0, x1, top, bot, vmax, rows, [BLUE, AMBER], "{} drivers")
    # DET is the only contractor-majority hub
    i = HUBS.index("HUB-DET")
    bx = x0 + i * group_w + (group_w - bar_w) / 2
    parts.append(text(bx + bar_w + 6, bot - 7 / vmax * (bot - top) + 4, "5 of 7 contractors",
                      11, RED, "start", "bold"))
    i = HUBS.index("HUB-IND")
    bx = x0 + i * group_w + (group_w - bar_w) / 2
    parts.append(text(bx + bar_w + 6, bot - 9 / vmax * (bot - top) + 18, "incl. DRV-01188", 10.5, GREY))
    parts.append(text(bx + bar_w + 6, bot - 9 / vmax * (bot - top) + 31, "(status: disputed)", 10.5, GREY))
    legend(parts, x0, 80, [(BLUE, "employee"), (AMBER, "contractor")])
    parts.append(text((x0 + x1) / 2, H - 10, "Hub", 12, GREY, "middle"))
    save("p1-headcount-by-hub-type.svg", parts)


# ---------------------------------------------------------------- p2: tenure bands
def chart_tenure():
    W, H = 960, 500
    x0, x1 = 100, 920
    top, bot = 100, 410
    vmax = 20
    labels = ["under 2 years", "2–4 years", "4–6 years", "6 years +"]
    rows = [(hub, TENURE[hub]) for hub in HUBS]
    totals = [sum(col) for col in zip(*TENURE.values())]
    parts = canvas(W, H, "Driver tenure by hub, as of 2025-12-31",
                   f"Bands by hire_date. Fleet: {totals[0]} / {totals[1]} / {totals[2]} / {totals[3]} "
                   f"= {sum(totals)} drivers. Nobody was hired in 2025 (latest hire 2024-09-01).")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 5), str)
    y_title(parts, 40, top, bot, "Drivers (headcount)")
    stacked_bars(parts, x0, x1, top, bot, vmax, rows, BAND_COLS, "{} drivers")
    legend(parts, x0, 80, list(zip(BAND_COLS, labels)), 150)
    parts.append(text((x0 + x1) / 2, H - 10, "Hub", 12, GREY, "middle"))
    save("p2-tenure-distribution.svg", parts)


# ---------------------------------------------------------------- p3: performance by hub (dot plot)
def chart_perf():
    W, H = 960, 470
    x0, x1 = 170, 850
    top, bot = 90, 400
    vmin, vmax = 2.5, 5.0
    all_scores = [v[2] for v in DRIVERS.values()]
    fleet_avg = statistics.mean(all_scores)
    parts = canvas(W, H, "Performance score by hub, one dot per driver",
                   "stg_drivers.perf_score (scale as recorded). Bar = hub average. "
                   "Dashed = fleet average; red line = 3.0.")

    def xx(v):
        return x0 + (v - vmin) / (vmax - vmin) * (x1 - x0)

    for v in [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]:
        parts.append(line(xx(v), top, xx(v), bot, GRID, 1))
        parts.append(text(xx(v), bot + 18, f"{v:.1f}", 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 42, "Performance score (perf_score)", 12, GREY, "middle"))
    parts.append(line(xx(3.0), top - 8, xx(3.0), bot, RED, 1.2, "4,3"))
    parts.append(line(xx(fleet_avg), top - 8, xx(fleet_avg), bot, INK, 1.2, "6,4"))
    parts.append(text(xx(fleet_avg) + 4, top - 12, f"fleet average {fleet_avg:.2f}", 11, INK))
    row_h = (bot - top) / len(HUBS)
    for i, hub in enumerate(HUBS):
        cy = top + i * row_h + row_h / 2
        scores = sorted((v[2], v[1]) for v in DRIVERS.values() if v[0] == hub)
        n = len(scores)
        below = sum(1 for s, _ in scores if s < 3.0)
        avg = statistics.mean(s for s, _ in scores)
        parts.append(text(x0 - 14, cy - 2, HUB_NAMES[hub], 12.5, INK, "end"))
        parts.append(text(x0 - 14, cy + 13, f"{hub}  n={n}", 10.5, GREY, "end"))
        parts.append(line(xx(avg), cy - 16, xx(avg), cy + 16, INK, 2.5))
        # jitter equal-ish scores vertically so they do not hide one another
        placed = []
        for s, t in scores:
            k = sum(1 for p in placed if abs(p - s) < 0.04)
            placed.append(s)
            off = (-1) ** k * ((k + 1) // 2) * 7
            parts.append(circle(xx(s), cy + off, 5, AMBER if t == "c" else BLUE, "#ffffff"))
        lab_col = RED if below >= 3 else GREY
        parts.append(text(x1 + 6, cy + 4, f"{below} below 3.0", 11, lab_col, "start",
                          "bold" if below >= 3 else "normal"))
    lx = x0
    for col, lab in [(BLUE, "employee"), (AMBER, "contractor")]:
        parts.append(circle(lx + 7, 70, 5, col))
        parts.append(text(lx + 18, 74, lab, 12, INK))
        lx += 120
    save("p3-perf-by-hub.svg", parts)


# ---------------------------------------------------------------- p4: documentation completeness
def chart_docs():
    W, H = 960, 520
    x0, x1 = 100, 920
    top, bot = 110, 420
    vmax = 20
    labels = ["onboarding only", "1 further doc type", "2 or more further doc types"]
    cols = [RED, LIGHT, MID]
    rows = []
    fleet = [0, 0, 0]
    for hub in HUBS:
        b = [0, 0, 0]
        for d, v in DRIVERS.items():
            if v[0] != hub:
                continue
            # review, certification, training: the development record beyond the onboarding file
            k = sum(v[3][1:4])
            b[min(k, 2)] += 1
        rows.append((hub, tuple(b)))
        fleet = [a + c for a, c in zip(fleet, b)]
    parts = canvas(W, H, "HR file completeness by hub: drivers with nothing beyond onboarding",
                   "Further doc types counted: review, certification, training (stg_hr_docs). "
                   f"Fleet: {fleet[0]} / {fleet[1]} / {fleet[2]} = {sum(fleet)} drivers.")
    parts.append(text(W / 2, 68, "No driver holds a certification valid after 2025-08-26 — "
                      "current certifications at 2025-12-31: 0 of 56.", 12.5, RED, "middle", "bold"))
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 5), str)
    y_title(parts, 40, top, bot, "Drivers (headcount)")
    stacked_bars(parts, x0, x1, top, bot, vmax, rows, cols, "{} drivers")
    legend(parts, x0, 95, list(zip(cols, labels)), 190)
    parts.append(text((x0 + x1) / 2, H - 10, "Hub", 12, GREY, "middle"))
    save("p4-doc-completeness-by-hub.svg", parts)


# ---------------------------------------------------------------- p5: cost per route by type
def chart_cost_per_route():
    W, H = 960, 420
    x0, x1 = 190, 880
    top, bot = 90, 320
    vmax = 800
    parts = canvas(W, H, "2025 labour cost per route: contractor vs employee",
                   "stg_payroll_monthly, 2025. Bar = type total cost ÷ routes run; "
                   "whisker = range of per-driver cost per route.")

    def xx(v):
        return x0 + v / vmax * (x1 - x0)

    for v in range(0, vmax + 1, 100):
        parts.append(line(xx(v), top, xx(v), bot, GRID, 1))
        parts.append(text(xx(v), bot + 18, f"${v}", 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 42, "Labour cost per route run, 2025 (US$)", 12, GREY, "middle"))
    row_h = (bot - top) / 2
    for i, (typ, col) in enumerate([("contractor", AMBER), ("employee", BLUE)]):
        cost, hrs, ot, routes, cpr = PAY_2025[typ]
        yy = top + i * row_h + row_h * 0.22
        h = row_h * 0.5
        parts.append(rect(x0, yy, xx(cpr) - x0, h, col))
        lo, hi = CPR_RANGE[typ]
        cy = yy + h / 2
        parts.append(line(xx(lo), cy, xx(hi), cy, INK, 1.5))
        parts.append(line(xx(lo), cy - 7, xx(lo), cy + 7, INK, 1.5))
        parts.append(line(xx(hi), cy - 7, xx(hi), cy + 7, INK, 1.5))
        parts.append(halo(xx(hi) + 8, cy + 5, f"${cpr:,.2f}", 13, INK, "start", "bold"))
        parts.append(text(x0 - 12, cy - 4, typ, 13, INK, "end", "bold"))
        parts.append(text(x0 - 12, cy + 12, f"{routes:,} routes · ${cost:,.0f}", 10.5, GREY, "end"))
        parts.append(text(x0 - 12, cy + 26, f"{ot:,} OT hrs · {EXC_RATE_2025[typ]} exc/100", 10.5, GREY, "end"))
    parts.append(line(xx(FLEET_CPR_2025), top - 10, xx(FLEET_CPR_2025), bot, GREY, 1.2, "6,4"))
    parts.append(text(xx(FLEET_CPR_2025) + 4, top - 12, f"fleet ${FLEET_CPR_2025:,.0f}", 11, GREY))
    save("p5-cost-per-route-by-type.svg", parts)


# ---------------------------------------------------------------- p6: routes per working driver
def chart_routes_per_driver():
    W, H = 960, 500
    x0, x1 = 100, 920
    top, bot = 100, 410
    vmax = 140
    fleet_working = sum(1 for d in DRIVERS if working(d))
    fleet_rpd = sum(ROUTES_2025.values()) / fleet_working
    parts = canvas(W, H, "2025 routes per working driver, by hub",
                   "Routes run in 2025 ÷ drivers who ran at least one 2025 route. "
                   "Dashed = fleet average.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 20), str)
    y_title(parts, 40, top, bot, "Routes per working driver, 2025")
    group_w = (x1 - x0) / len(HUBS)
    bar_w = group_w * 0.42

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, hub in enumerate(HUBS):
        heads = sum(1 for d in DRIVERS if hub_of(d) == hub)
        work = sum(1 for d in DRIVERS if hub_of(d) == hub and working(d))
        rpd = ROUTES_2025[hub] / work
        bx = x0 + i * group_w + (group_w - bar_w) / 2
        parts.append(rect(bx, yy(rpd), bar_w, bot - yy(rpd), RED if rpd > 110 else BLUE))
        parts.append(halo(bx + bar_w / 2, yy(rpd) - 6, f"{rpd:.1f}", 12, INK, "middle", "bold"))
        parts.append(text(bx + bar_w / 2, bot - 22, f"{ROUTES_2025[hub]} routes", 10.5, "#ffffff", "middle"))
        parts.append(text(bx + bar_w / 2, bot - 8, f"{work} of {heads} drivers", 10.5, "#ffffff", "middle"))
        hub_labels(parts, bx + bar_w / 2, bot, hub)
    parts.append(line(x0, yy(fleet_rpd), x1, yy(fleet_rpd), INK, 1.2, "6,4"))
    parts.append(halo(x1, yy(fleet_rpd) - 6, f"fleet {fleet_rpd:.1f} "
                      f"({sum(ROUTES_2025.values()):,} ÷ {fleet_working})", 11, INK, "end"))
    parts.append(text((x0 + x1) / 2, H - 10, "Hub", 12, GREY, "middle"))
    save("p6-routes-per-driver-by-hub.svg", parts)


# ---------------------------------------------------------------- p7: does performance travel?
def hub_exc_rate(hub):
    r = sum(v[4] for v in DRIVERS.values() if v[0] == hub)
    e = sum(v[5] for v in DRIVERS.values() if v[0] == hub)
    return e / r


def chart_perf_vs_normalised():
    W, H = 960, 540
    x0, x1 = 110, 900
    top, bot = 90, 450
    xmin, xmax = 2.5, 5.0
    ymin, ymax = 0.0, 2.0
    parts = canvas(W, H, "Score vs 2025 exceptions, after normalising for the driver's hub",
                   "One dot per driver who ran 2025 routes (50). y = driver's exceptions per route ÷ "
                   "own hub's rate; 1.0 = hub average.")

    def xx(v):
        return x0 + (v - xmin) / (xmax - xmin) * (x1 - x0)

    def yy(v):
        return bot - (v - ymin) / (ymax - ymin) * (bot - top)

    for v in [0.0, 0.5, 1.0, 1.5, 2.0]:
        parts.append(line(x0, yy(v), x1, yy(v), GRID, 1))
        parts.append(text(x0 - 8, yy(v) + 4, f"{v:.1f}×", 11.5, GREY, "end"))
    for v in [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]:
        parts.append(line(xx(v), bot, xx(v), bot + 5, GREY, 1))
        parts.append(text(xx(v), bot + 20, f"{v:.1f}", 11.5, GREY, "middle"))
    parts.append(line(x0, bot, x1, bot, GREY, 1))
    parts.append(line(x0, yy(1.0), x1, yy(1.0), INK, 1.2, "6,4"))
    parts.append(line(xx(3.0), top, xx(3.0), bot, RED, 1.2, "4,3"))
    y_title(parts, 45, top, bot, "Exceptions per route vs own hub (×)")
    parts.append(text((x0 + x1) / 2, bot + 44, "Performance score (perf_score)", 12, GREY, "middle"))
    rates = {h: hub_exc_rate(h) for h in HUBS}
    for d, v in DRIVERS.items():
        if v[4] == 0:
            continue
        ratio = (v[5] / v[4]) / rates[v[0]]
        parts.append(circle(xx(v[2]), yy(ratio), 5, AMBER if v[1] == "c" else BLUE, "#ffffff"))
        if ratio > 1.5 or ratio < 0.4:
            parts.append(halo(xx(v[2]) + 8, yy(ratio) + 4, f"{d} ({HUB_NAMES[v[0]]})", 10.5, INK, "start"))
    lx = x0
    for col, lab in [(BLUE, "employee"), (AMBER, "contractor")]:
        parts.append(circle(lx + 7, 70, 5, col))
        parts.append(text(lx + 18, 74, lab, 12, INK))
        lx += 120
    parts.append(text(lx + 10, 74, "dashed = own-hub average · red = score 3.0", 11.5, GREY))
    save("p7-perf-vs-normalised-exceptions.svg", parts)


if __name__ == "__main__":
    chart_headcount()
    chart_tenure()
    chart_perf()
    chart_docs()
    chart_cost_per_route()
    chart_routes_per_driver()
    chart_perf_vs_normalised()
