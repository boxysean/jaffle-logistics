#!/usr/bin/env python3
"""Generate the Chief Operating Officer persona-report charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible without the
warehouse. Every number comes from the data pack behind reports/persona-coo.md
(queries Q2-Q19, copied verbatim into that report's appendix).

Output: reports/assets/personas/coo-*.svg  (committed alongside the report).

Design rules (match scripts/cfo_charts.py, persona_people_charts.py, persona_cro_charts.py):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar;
  * reference lines (97% target, quiet-year band) drawn dashed and labelled;
  * consistent colour meaning: red = the problem cell (Chicago, BAY-3, severe incidents),
    grey ramp = years (2023 light -> 2025 dark), muted hues for the other hubs.

Run from the repo root:  python3 scripts/persona_coo_charts.py
"""
import os
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "personas")
TARGET = 97.0  # contractual on-time yardstick, %

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # the problem cell
INK = "#1a1a1a"
GREY = "#555555"
GRID = "#d9d9d9"
BAND = "#ececec"     # quiet-year reference band
G1 = "#c4c4c4"       # 2023
G2 = "#8c8c8c"       # 2024
G3 = "#3d3d3d"       # 2025
YEAR_COLS = [(G1, "2023"), (G2, "2024"), (G3, "2025")]
HUB_COLS = {"HUB-CHI": RED, "HUB-CIN": "#2c6fbb", "HUB-CMH": "#c58a1b",
            "HUB-DET": "#3d3d3d", "HUB-IND": "#6b8e23"}

FONT = "Helvetica, Arial, sans-serif"


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from the data pack)
HUBS = ["HUB-CHI", "HUB-CIN", "HUB-CMH", "HUB-DET", "HUB-IND"]
HUB_NAMES = {"HUB-CHI": "Chicago", "HUB-CIN": "Cincinnati", "HUB-CMH": "Columbus",
             "HUB-DET": "Detroit", "HUB-IND": "Indianapolis"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Q2 — routes and exceptions by hub by year (stg_routes): (routes, exceptions) for 2023, 2024, 2025
ROUTES = {
    "HUB-CHI": ((676, 532), (691, 491), (748, 931)),
    "HUB-CIN": ((652, 434), (715, 517), (712, 352)),
    "HUB-CMH": ((666, 387), (666, 434), (709, 369)),
    "HUB-DET": ((678, 467), (730, 465), (741, 382)),
    "HUB-IND": ((666, 463), (719, 513), (719, 387)),
}

# Q3 — on-time % by origin hub by year (stg_shipments, status = 'delivered')
ONTIME = {
    "HUB-CHI": (96.48, 96.90, 88.35),
    "HUB-CIN": (98.94, 96.73, 95.98),
    "HUB-CMH": (97.91, 95.93, 95.39),
    "HUB-DET": (95.48, 98.09, 93.68),
    "HUB-IND": (98.45, 98.66, 93.41),
}

# Q4 — exceptions per 100 routes by hub by month, 2025
MONTHLY_2025 = {
    "HUB-CHI": (700.00, 187.72, 16.92, 26.42, 14.55, 30.91, 18.18, 22.45, 26.39, 25.00, 112.90, 122.86),
    "HUB-CIN": (96.67, 125.00, 4.00, 21.54, 33.33, 24.36, 28.33, 30.16, 19.70, 11.76, 104.69, 108.33),
    "HUB-CMH": (132.31, 65.79, 17.65, 16.67, 16.22, 7.55, 30.43, 28.00, 23.08, 37.50, 127.42, 110.94),
    "HUB-DET": (90.00, 124.53, 30.00, 10.61, 31.82, 20.00, 23.33, 22.22, 26.47, 28.17, 96.36, 121.31),
    "HUB-IND": (82.76, 112.12, 28.13, 25.00, 13.73, 14.29, 17.65, 63.64, 45.65, 20.27, 122.00, 98.67),
}

# Q5 — network exceptions per 100 routes by month, 2023-2024 (the quiet-year reference band)
QUIET_MONTHLY = (77.78, 65.40, 71.91, 70.37, 73.91, 63.67, 62.29, 80.23, 65.41, 58.05, 76.21, 57.89,
                 66.67, 54.80, 80.43, 76.49, 80.15, 72.70, 57.01, 65.07, 77.27, 64.65, 57.39, 71.88)
QUIET_LO, QUIET_HI = min(QUIET_MONTHLY), max(QUIET_MONTHLY)
QUIET_MEAN = sum(QUIET_MONTHLY) / len(QUIET_MONTHLY)   # ~68.7

# Q6 — network exceptions per 100 routes by ISO week, 2025 (weeks 1..52)
WEEKLY_2025 = (94.9, 127.6, 662.8, 109.6, 72.9, 167.9, 95.4, 123.1, 96.8, 18.5, 23.1, 15.4, 18.9, 19.0,
               21.4, 20.6, 25.0, 17.6, 33.3, 14.7, 9.6, 24.7, 25.0, 26.0, 11.4, 24.3, 19.4, 31.0, 28.8,
               15.3, 13.2, 24.7, 56.1, 36.7, 24.1, 48.7, 31.1, 17.2, 12.3, 15.9, 25.7, 21.5, 30.0, 21.3,
               131.9, 126.1, 98.6, 102.7, 115.5, 151.5, 89.5, 100.0)

# Q7 — dispatch-note exception type by hub, 2025
NOTE_TYPES = ["weather", "traffic", "access", "customer_nsf", "mechanical", "volume", "address"]
NOTE_COLS = ["#1f4e79", "#5b7fa6", "#9aa7b5", "#c9d3de", "#c58a1b", "#8c8c8c", "#3d3d3d"]
NOTES_2025 = {
    "HUB-CHI": (30, 21, 19, 16, 15, 14, 12),
    "HUB-CIN": (28, 17, 16, 11, 19, 14, 5),
    "HUB-CMH": (30, 14, 13, 4, 10, 14, 15),
    "HUB-DET": (29, 22, 13, 12, 15, 10, 20),
    "HUB-IND": (31, 22, 19, 16, 14, 18, 21),
}

# Q12 — incidents by type x severity x year: type -> severity 1..4 -> (2023, 2024, 2025)
INC_TYPES = ["delay", "damage", "weather", "mispick", "accident", "dispute"]
INCIDENTS = {
    "accident": ((11, 5, 6), (3, 7, 3), (0, 0, 3), (1, 0, 2)),
    "damage": ((3, 3, 16), (4, 5, 10), (0, 0, 7), (0, 0, 7)),
    "delay": ((18, 21, 30), (9, 7, 20), (2, 3, 9), (0, 3, 2)),
    "dispute": ((5, 4, 1), (2, 3, 2), (1, 0, 2), (0, 1, 1)),
    "mispick": ((4, 9, 11), (3, 3, 3), (0, 0, 6), (1, 0, 1)),
    "weather": ((22, 27, 14), (11, 3, 10), (0, 6, 7), (0, 0, 1)),
}
SEV_COLS = ["#c9d3de", "#8fa3b8", "#e08a7e", RED]

# Q15 — Columbus damage_found dock events by bay x year (stg_dock_bay_events)
BAYS = ["HUB-CMH-BAY-1", "HUB-CMH-BAY-2", "HUB-CMH-BAY-3", "HUB-CMH-BAY-4", "HUB-CMH-BAY-5", "HUB-CMH-BAY-6"]
CMH_DAMAGE_BY_BAY = {
    "HUB-CMH-BAY-1": (0, 0, 1),
    "HUB-CMH-BAY-2": (1, 0, 1),
    "HUB-CMH-BAY-3": (0, 0, 11),
    "HUB-CMH-BAY-4": (0, 0, 1),
    "HUB-CMH-BAY-5": (1, 1, 1),
    "HUB-CMH-BAY-6": (0, 1, 0),
}

# Q16 — average minutes_at_bay on staging events, by hub x year
STAGING = {
    "HUB-CHI": (40.7, 41.2, 41.5),
    "HUB-CIN": (40.8, 41.2, 40.8),
    "HUB-CMH": (47.4, 47.1, 51.0),
    "HUB-DET": (41.3, 41.5, 41.1),
    "HUB-IND": (41.1, 41.1, 41.7),
}

# Q19 — route status by hub x year: (completed, partial, canceled) for 2023, 2024, 2025
ROUTE_STATUS = {
    "HUB-CHI": ((603, 65, 8), (616, 71, 4), (642, 90, 16)),
    "HUB-CIN": ((582, 66, 4), (637, 68, 10), (643, 68, 1)),
    "HUB-CMH": ((589, 72, 5), (584, 77, 5), (639, 65, 5)),
    "HUB-DET": ((597, 77, 4), (649, 73, 8), (668, 67, 6)),
    "HUB-IND": ((578, 84, 4), (646, 70, 3), (645, 74, 0)),
}


def exc_rate(hub, yi):
    r, e = ROUTES[hub][yi]
    return 100.0 * e / r


def incomplete_rate(hub, yi):
    c, p, x = ROUTE_STATUS[hub][yi]
    return 100.0 * (p + x) / (c + p + x)


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


def text(x, y, s, size=12, color=INK, anchor="start", weight="normal", rotate=None, halo=False):
    tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
    hl = ' stroke="#ffffff" stroke-width="3" paint-order="stroke"' if halo else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{tr}{hl}>{esc(s)}</text>')


def rect(x, y, w, h, fill, stroke="none", sw=1):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def polyline(pts, color, w=2):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round"/>'


def circle(cx, cy, r, fill):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"/>'


def save(name, parts):
    parts.append("</svg>")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write("\n".join(parts) + "\n")
    print("wrote", os.path.relpath(path, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))


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


def legend(parts, x, y, items, step=110):
    for col, lab in items:
        parts.append(rect(x, y - 10, 14, 12, col))
        parts.append(text(x + 20, y, lab, 12, INK))
        x += step
    return x


def quiet_band(parts, x0, x1, yy):
    """Shade the 2023-2024 monthly range and dash its mean."""
    parts.append(rect(x0, yy(QUIET_HI), x1 - x0, yy(QUIET_LO) - yy(QUIET_HI), BAND))
    parts.append(line(x0, yy(QUIET_MEAN), x1, yy(QUIET_MEAN), G3, 1.2, "6,4"))


def grouped_year_bars(parts, x0, x1, bot, yy, keys, values, fmt, highlight=None, labeller=hub_labels):
    """values[key] = (2023, 2024, 2025); highlight = (key, year index) drawn red."""
    group_w = (x1 - x0) / len(keys)
    bar_w = group_w * 0.24
    for i, k in enumerate(keys):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate(values[k]):
            bx = gx + j * (bar_w + 4)
            col = RED if highlight == (k, j) else YEAR_COLS[j][0]
            parts.append(rect(bx, yy(val), bar_w, max(yy(0) - yy(val), 0), col))
            parts.append(text(bx + bar_w / 2, yy(val) - 5, fmt(val), 10.5,
                              RED if highlight == (k, j) else INK, "middle",
                              "bold" if highlight == (k, j) else "normal"))
        labeller(parts, x0 + i * group_w + group_w / 2, bot, k)
    return group_w


# ---------------------------------------------------------------- coo-01: monthly exc/100 by hub, 2025
def chart_monthly_by_hub():
    W, H = 960, 540
    x0, x1 = 100, 900
    top, bot = 110, 440
    vmax = 220  # Chicago January (700) is drawn off-scale and labelled
    parts = canvas(W, H, "Exceptions per 100 routes, by hub, by month — 2025",
                   "stg_routes: sum(exceptions_count) / routes × 100. Grey band = 2023–2024 network monthly "
                   f"range ({QUIET_LO:.0f}–{QUIET_HI:.0f}); dashed = quiet-year mean ({QUIET_MEAN:.1f}).")

    def yy(v):
        return bot - min(v, vmax) / vmax * (bot - top)

    quiet_band(parts, x0, x1, yy)
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 40), str)
    y_title(parts, 45, top, bot, "Exceptions per 100 routes")
    step = (x1 - x0) / 12

    def xx(i):
        return x0 + (i + 0.5) * step

    for i, m in enumerate(MONTHS):
        parts.append(text(xx(i), bot + 20, m, 12, INK, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 42, "Month of service_date, 2025", 12, GREY, "middle"))
    for hub in ["HUB-CIN", "HUB-CMH", "HUB-DET", "HUB-IND", "HUB-CHI"]:  # Chicago drawn last, on top
        vals = MONTHLY_2025[hub]
        col = HUB_COLS[hub]
        w = 3 if hub == "HUB-CHI" else 1.8
        parts.append(polyline([(xx(i), yy(v)) for i, v in enumerate(vals)], col, w))
        for i, v in enumerate(vals):
            parts.append(circle(xx(i), yy(v), 3.2 if hub == "HUB-CHI" else 2.4, col))
    # the off-scale storm point
    parts.append(line(xx(0), top - 4, xx(0), top + 10, RED, 2))
    parts.append(f'<polygon points="{xx(0)-6:.1f},{top+2:.1f} {xx(0)+6:.1f},{top+2:.1f} {xx(0):.1f},{top-10:.1f}" '
                 f'fill="{RED}"/>')
    parts.append(text(xx(0) + 12, top + 4, "Chicago Jan = 700 (560 exceptions on 80 routes) — off scale",
                      12, RED, "start", "bold", halo=True))
    parts.append(text(xx(1) + 8, yy(187.72) + 4, "CHI Feb 188", 11, RED, "start", halo=True))
    parts.append(text(xx(6), yy(QUIET_HI) - 6, "2023–2024 quiet-year range", 11, GREY, "middle", halo=True))
    parts.append(text(xx(10) - 10, yy(132), "Nov–Dec: every hub 96–127", 11.5, INK, "end", "bold", halo=True))
    legend(parts, x0, 80, [(HUB_COLS[h], HUB_NAMES[h]) for h in HUBS], step=125)
    save("coo-01-exceptions-per-100-by-hub-monthly-2025.svg", parts)


# ---------------------------------------------------------------- coo-02: weekly network exc/100, 2025
def chart_weekly_network():
    W, H = 960, 500
    x0, x1 = 100, 920
    top, bot = 100, 400
    vmax = 200
    parts = canvas(W, H, "Network exceptions per 100 routes, by ISO week — 2025",
                   "stg_routes, all hubs, weekofyear(service_date). Grey band = 2023–2024 monthly range; "
                   f"dashed = quiet-year mean ({QUIET_MEAN:.1f}). Week 1 also holds 29–31 Dec 2025.")

    def yy(v):
        return bot - min(v, vmax) / vmax * (bot - top)

    quiet_band(parts, x0, x1, yy)
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 40), str)
    y_title(parts, 45, top, bot, "Exceptions per 100 routes")
    n = len(WEEKLY_2025)
    step = (x1 - x0) / n

    def xx(i):
        return x0 + (i + 0.5) * step

    for wk in (1, 5, 9, 13, 17, 22, 26, 31, 35, 40, 45, 48, 52):
        parts.append(line(xx(wk - 1), bot, xx(wk - 1), bot + 4, GREY, 1))
        parts.append(text(xx(wk - 1), bot + 18, str(wk), 11, INK, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 40, "ISO week of 2025 (week 3 = 13–19 Jan; week 45 = 3–9 Nov)",
                      12, GREY, "middle"))
    # shade the two waves lightly
    for a, b, lab in ((1, 9, "Wave 1: January storm, weeks 1–9"), (45, 52, "Wave 2: weeks 45–52")):
        parts.append(rect(xx(a - 1) - step / 2, top, (b - a + 1) * step, bot - top, RED).replace(
            'fill="#c0392b"', 'fill="#c0392b" fill-opacity="0.06"'))
        parts.append(text((xx(a - 1) + xx(b - 1)) / 2, top - 8, lab, 11.5, RED, "middle", "bold"))
    parts.append(polyline([(xx(i), yy(v)) for i, v in enumerate(WEEKLY_2025)], G3, 2))
    for i, v in enumerate(WEEKLY_2025):
        parts.append(circle(xx(i), yy(v), 2.6, RED if v > QUIET_HI else G3))
    parts.append(f'<polygon points="{xx(2)-6:.1f},{top+8:.1f} {xx(2)+6:.1f},{top+8:.1f} {xx(2):.1f},{top-2:.1f}" '
                 f'fill="{RED}"/>')
    parts.append(text(xx(2) + 10, top + 18, "wk 3 = 662.8 (570 exceptions on 86 routes) — off scale",
                      11.5, RED, "start", "bold", halo=True))
    parts.append(text(xx(5) + 6, yy(167.9) + 4, "167.9", 10.5, INK, "start", halo=True))
    parts.append(text(xx(49) , yy(151.5) - 8, "151.5", 10.5, INK, "middle", halo=True))
    parts.append(text(xx(26), yy(92), "weeks 10–44: 23.7 per 100 (570 exc / 2,405 routes)",
                      11.5, INK, "middle", "bold", halo=True))
    parts.append(text(x1, yy(QUIET_MEAN) - 6, f"quiet-year mean {QUIET_MEAN:.1f}", 11, G3, "end", halo=True))
    parts.append(text(x0, H - 12, "Red dot = week above the top of the quiet-year range (80.4).", 11, GREY))
    save("coo-02-network-weekly-exceptions-2025.svg", parts)


# ---------------------------------------------------------------- coo-03: hub league, 2025
def chart_hub_league():
    W, H = 960, 420
    ranked = sorted(HUBS, key=lambda h: -exc_rate(h, 2))
    parts = canvas(W, H, "Hub league, 2025: on-time rate and exceptions per 100 routes",
                   "Left: stg_shipments, delivered ÷ shipments (axis starts at 80%). "
                   "Right: stg_routes, exceptions per 100 routes. Ranked worst first.")
    top, bot = 100, 360
    row_h = (bot - top) / len(ranked)
    # left panel: on-time
    lx0, lx1, lmin, lmax = 200, 470, 80.0, 100.0

    def lxx(v):
        return lx0 + (v - lmin) / (lmax - lmin) * (lx1 - lx0)

    for v in (80, 85, 90, 95, 100):
        parts.append(line(lxx(v), top - 6, lxx(v), bot, GRID, 1))
        parts.append(text(lxx(v), bot + 18, f"{v}%", 11.5, GREY, "middle"))
    parts.append(text((lx0 + lx1) / 2, bot + 40, "2025 shipments delivered on time (%)", 12, GREY, "middle"))
    # right panel: exceptions per 100
    rx0, rx1, rmax = 560, 860, 160.0

    def rxx(v):
        return rx0 + v / rmax * (rx1 - rx0)

    for v in range(0, 161, 20):
        parts.append(line(rxx(v), top - 6, rxx(v), bot, GRID, 1))
        parts.append(text(rxx(v), bot + 18, str(v), 11.5, GREY, "middle"))
    parts.append(text((rx0 + rx1) / 2, bot + 40, "2025 exceptions per 100 routes", 12, GREY, "middle"))
    for i, hub in enumerate(ranked):
        y = top + i * row_h + row_h * 0.22
        h = row_h * 0.56
        col = RED if hub == "HUB-CHI" else G2
        ot = ONTIME[hub][2]
        parts.append(rect(lx0, y, lxx(ot) - lx0, h, col))
        parts.append(text(lxx(ot) + 6, y + h * 0.7, f"{ot:.2f}%", 11.5, INK, "start", "bold", halo=True))
        er = exc_rate(hub, 2)
        parts.append(rect(rx0, y, rxx(er) - rx0, h, col))
        parts.append(text(rxx(er) + 6, y + h * 0.7, f"{er:.1f}  ({ROUTES[hub][2][1]} / {ROUTES[hub][2][0]})",
                          11.5, INK, "start", "bold"))
        parts.append(text(lx0 - 10, y + h * 0.5, HUB_NAMES[hub], 12.5, INK, "end"))
        parts.append(text(lx0 - 10, y + h * 0.5 + 14, hub, 10.5, GREY, "end"))
    parts.append(line(lxx(TARGET), top - 14, lxx(TARGET), bot, RED, 1.5, "6,4"))
    parts.append(text(lxx(TARGET), top - 18, "97% target", 11.5, RED, "middle", "bold"))
    parts.append(line(rxx(QUIET_MEAN), top - 14, rxx(QUIET_MEAN), bot, G3, 1.2, "6,4"))
    parts.append(text(rxx(QUIET_MEAN), top - 18, f"2023–24 network mean {QUIET_MEAN:.1f}", 11, G3, "middle"))
    save("coo-03-hub-league-2025.svg", parts)


# ---------------------------------------------------------------- coo-04: dispatch-note type mix, 2025
def chart_note_mix():
    W, H = 960, 470
    x0, x1 = 200, 800
    top, bot = 110, 380
    vmax = 150
    total = sum(sum(v) for v in NOTES_2025.values())
    parts = canvas(W, H, "What the dispatch notes say went wrong, by hub — 2025",
                   f"stg_dispatch_notes.exception_type, 2025: {total} notes. A proxy: the notes narrate about "
                   "a quarter of the 2,421 route exceptions.")
    for v in range(0, vmax + 1, 25):
        xx = x0 + v / vmax * (x1 - x0)
        parts.append(line(xx, top - 6, xx, bot, GRID, 1))
        parts.append(text(xx, bot + 18, str(v), 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 40, "Dispatch notes, 2025 (count)", 12, GREY, "middle"))
    row_h = (bot - top) / len(HUBS)
    for i, hub in enumerate(HUBS):
        y = top + i * row_h + row_h * 0.2
        h = row_h * 0.6
        base = 0
        for col, val in zip(NOTE_COLS, NOTES_2025[hub]):
            bx = x0 + base / vmax * (x1 - x0)
            bw = val / vmax * (x1 - x0)
            parts.append(rect(bx, y, bw, h, col, "#ffffff"))
            if bw > 16:
                fill = INK if col in ("#9aa7b5", "#c9d3de") else "#ffffff"
                parts.append(text(bx + bw / 2, y + h * 0.65, str(val), 11, fill, "middle", "bold"))
            base += val
        rexc = ROUTES[hub][2][1]
        parts.append(text(x0 + base / vmax * (x1 - x0) + 6, y + h * 0.45, f"{base} notes", 11.5, INK, "start", "bold"))
        parts.append(text(x0 + base / vmax * (x1 - x0) + 6, y + h * 0.45 + 14,
                          f"vs {rexc} exceptions ({100 * base / rexc:.0f}%)", 10.5,
                          RED if hub == "HUB-CHI" else GREY))
        parts.append(text(x0 - 10, y + h * 0.5, HUB_NAMES[hub], 12.5, INK, "end"))
        parts.append(text(x0 - 10, y + h * 0.5 + 14, hub, 10.5, GREY, "end"))
    legend(parts, 80, 80, list(zip(NOTE_COLS, NOTE_TYPES)), step=118)
    save("coo-04-exception-type-mix-by-hub-2025.svg", parts)


# ---------------------------------------------------------------- coo-05: incidents by type, severity, year
def chart_incidents():
    W, H = 960, 520
    x0, x1 = 100, 920
    top, bot = 100, 420
    vmax = 70
    totals = [sum(INCIDENTS[t][s][y] for t in INC_TYPES for s in range(4)) for y in range(3)]
    parts = canvas(W, H, "Incidents by type and severity, 2023 / 2024 / 2025",
                   f"stg_incidents by year of occurred_at: {totals[0]} → {totals[1]} → {totals[2]}. "
                   "Each type shows three bars (2023, 2024, 2025), stacked by severity.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 10), str)
    y_title(parts, 45, top, bot, "Incidents (count)")

    def yy(v):
        return bot - v / vmax * (bot - top)

    group_w = (x1 - x0) / len(INC_TYPES)
    bar_w = group_w * 0.24
    for i, t in enumerate(INC_TYPES):
        gx = x0 + i * group_w + group_w * 0.12
        for j in range(3):
            bx = gx + j * (bar_w + 4)
            base = 0
            for s in range(4):
                val = INCIDENTS[t][s][j]
                if val:
                    parts.append(rect(bx, yy(base + val), bar_w, yy(base) - yy(base + val), SEV_COLS[s], "#ffffff"))
                    if yy(base) - yy(base + val) > 12:
                        parts.append(text(bx + bar_w / 2, (yy(base) + yy(base + val)) / 2 + 4, str(val), 10,
                                          INK if s < 2 else "#ffffff", "middle"))
                base += val
            parts.append(text(bx + bar_w / 2, yy(base) - 5, str(base), 11, INK, "middle", "bold"))
            parts.append(text(bx + bar_w / 2, bot + 14, ("'23", "'24", "'25")[j], 10, GREY, "middle"))
        parts.append(text(x0 + i * group_w + group_w / 2, bot + 32, t, 12.5, INK, "middle", "bold"))
    parts.append(text((x0 + x1) / 2, H - 12, "Incident type (stg_incidents.incident_type)", 12, GREY, "middle"))
    legend(parts, x0, 76, [(SEV_COLS[0], "severity 1"), (SEV_COLS[1], "severity 2"),
                           (SEV_COLS[2], "severity 3"), (SEV_COLS[3], "severity 4")], step=115)
    sev34 = [sum(INCIDENTS[t][s][y] for t in INC_TYPES for s in (2, 3)) for y in range(3)]
    parts.append(text(x1, 76, f"severity 3–4: {sev34[0]} → {sev34[1]} → {sev34[2]}", 12, RED, "end", "bold"))
    save("coo-05-incidents-by-type-severity-year.svg", parts)


# ---------------------------------------------------------------- coo-06: Columbus damage by bay
def chart_cmh_bays():
    W, H = 960, 460
    x0, x1 = 100, 920
    top, bot = 100, 380
    vmax = 12
    tots = [sum(CMH_DAMAGE_BY_BAY[b][y] for b in BAYS) for y in range(3)]
    parts = canvas(W, H, "Columbus: damage found at the dock, by bay — 2023 / 2024 / 2025",
                   f"stg_dock_bay_events, hub HUB-CMH, event_type 'damage_found'. Totals {tots[0]} / {tots[1]} / "
                   f"{tots[2]}.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 2), str)
    y_title(parts, 45, top, bot, "damage_found events (count)")

    def yy(v):
        return bot - v / vmax * (bot - top)

    def bay_label(parts_, cx, b, bay):
        parts_.append(text(cx, b + 20, bay.replace("HUB-CMH-", "").replace("BAY-", "Bay "), 12.5, INK, "middle",
                           "bold" if bay.endswith("3") else "normal"))
        parts_.append(text(cx, b + 36, bay, 10, GREY, "middle"))

    grouped_year_bars(parts, x0, x1, bot, yy, BAYS, CMH_DAMAGE_BY_BAY, str,
                      highlight=("HUB-CMH-BAY-3", 2), labeller=bay_label)
    legend(parts, x0, 76, YEAR_COLS, step=80)
    parts.append(text(x0 + 260, 76, "Bay 3, 2025 in red: 11 of the hub's 15", 12, RED, "start", "bold"))
    save("coo-06-columbus-damage-by-bay.svg", parts)


# ---------------------------------------------------------------- coo-07: dock staging minutes
def chart_staging():
    W, H = 960, 460
    x0, x1 = 100, 920
    top, bot = 100, 380
    vmax = 60
    parts = canvas(W, H, "Average dock staging time, by hub — 2023 / 2024 / 2025",
                   "stg_dock_bay_events, event_type 'staging': avg(minutes_at_bay). A throughput proxy, "
                   "not a measured dock cycle time.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 10), str)
    y_title(parts, 45, top, bot, "Minutes at bay per staging event")

    def yy(v):
        return bot - v / vmax * (bot - top)

    grouped_year_bars(parts, x0, x1, bot, yy, HUBS, STAGING, lambda v: f"{v:.1f}", highlight=("HUB-CMH", 2))
    legend(parts, x0, 76, YEAR_COLS, step=80)
    parts.append(text(x0 + 260, 76, "Columbus 2025 in red: slowest dock, and slower than its own 2023–24",
                      12, RED, "start", "bold"))
    save("coo-07-dock-staging-minutes-by-hub.svg", parts)


# ---------------------------------------------------------------- coo-08: incomplete routes per 100
def chart_incomplete():
    W, H = 960, 460
    x0, x1 = 100, 920
    top, bot = 100, 380
    vmax = 16
    rates = {h: tuple(incomplete_rate(h, y) for y in range(3)) for h in HUBS}
    others = [h for h in HUBS if h != "HUB-CHI"]
    o_inc = sum(ROUTE_STATUS[h][2][1] + ROUTE_STATUS[h][2][2] for h in others)
    o_rts = sum(sum(ROUTE_STATUS[h][2]) for h in others)
    ref = 100.0 * o_inc / o_rts
    parts = canvas(W, H, "Routes not completed (partial + canceled) per 100 routes, by hub",
                   "stg_routes.status by year of service_date. Dashed = the other four hubs in 2025 "
                   f"({o_inc} of {o_rts:,} routes).")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 4), str)
    y_title(parts, 45, top, bot, "Partial or canceled routes per 100 routes")

    def yy(v):
        return bot - v / vmax * (bot - top)

    grouped_year_bars(parts, x0, x1, bot, yy, HUBS, rates, lambda v: f"{v:.1f}", highlight=("HUB-CHI", 2))
    parts.append(line(x0, yy(ref), x1, yy(ref), G3, 1.2, "6,4"))
    lx = legend(parts, x0, 76, YEAR_COLS, step=80)
    parts.append(line(lx, 72, lx + 24, 72, G3, 1.2, "6,4"))
    parts.append(text(lx + 30, 76, f"other four hubs, 2025: {ref:.1f}", 12, G3))
    parts.append(text(lx + 230, 76, "Chicago 2025 (red): 90 + 16 = 106 of 748", 12, RED,
                      "start", "bold"))
    save("coo-08-incomplete-routes-per-100-by-hub.svg", parts)


if __name__ == "__main__":
    chart_monthly_by_hub()
    chart_weekly_network()
    chart_hub_league()
    chart_note_mix()
    chart_incidents()
    chart_cmh_bays()
    chart_staging()
    chart_incomplete()
