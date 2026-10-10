#!/usr/bin/env python3
"""Generate the Fleet / Maintenance persona-report charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible without the
warehouse. Every number comes from an execute_sql query against
hive_metastore.dbt_smcintyre_jaffle_logistics_prod; the SQL is in the appendix of
reports/persona-fleet.md (query numbers are noted beside each data block).

Output: reports/assets/personas/fleet-*.svg  (committed alongside the report).

Design rules (match scripts/cfo_charts.py and scripts/persona_cx_charts.py):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar;
  * fleet averages drawn as dashed, labelled reference lines;
  * consistent colour meaning: red = collision repair / outside the chance band,
    grey-blue ramp = years, neutral blue = a series with no judgement attached.

Run from the repo root:  python3 scripts/persona_fleet_charts.py
"""
import math
import os
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "personas")

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # collision repair / outside chance band
BLUE = "#2c6fbb"     # neutral series
GREY = "#555555"
GRID = "#d9d9d9"
INK = "#1a1a1a"
LIGHT = "#9aa7b5"
MID = "#5b7fa6"
BAND = "#eef1f5"
YEAR_COLS = [(LIGHT, "2023"), (MID, "2024"), (BLUE, "2025")]
TYPE_COLS = {"van": BLUE, "box_truck": MID, "semi": LIGHT}
HUB_COLS = {"HUB-CHI": "#2c6fbb", "HUB-CIN": "#7a9cc6", "HUB-CMH": "#c0392b",
            "HUB-DET": "#1a1a1a", "HUB-IND": "#9aa7b5"}

FONT = "Helvetica, Arial, sans-serif"


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from execute_sql)
HUBS = [("HUB-CHI", "Chicago"), ("HUB-CIN", "Cincinnati"), ("HUB-CMH", "Columbus"),
        ("HUB-DET", "Detroit"), ("HUB-IND", "Indianapolis")]

# Q6 — maintenance spend ($) by hub by year, and 2025 collision-repair spend ($) by hub
MAINT = {
    "HUB-CHI": (12576, 17588, 64456),
    "HUB-CIN": (17423, 437, 31362),
    "HUB-CMH": (15538, 48044, 78083),
    "HUB-DET": (27990, 19829, 46581),
    "HUB-IND": (16828, 18203, 47096),
}
ACC_2025 = {"HUB-CHI": 49405, "HUB-CIN": 10030, "HUB-CMH": 54635, "HUB-DET": 37468, "HUB-IND": 18261}

# Q9 — 2025 by vehicle type: routes, WOs, WO $, collision WOs, collision $
TYPES_2025 = [
    # type, label, routes, wos, cost, acc_wos, acc_cost
    ("box_truck", "Box truck", 1935, 37, 138683, 14, 102295),
    ("van", "Van", 1694, 35, 101707, 7, 53304),
    ("semi", "Semi", 0, 9, 27188, 1, 14200),
]
FLEET_ROUTES_2025 = 3629
FLEET_COST_2025 = 267578
FLEET_COST_ROUTE_RUNNING = 240390   # spend on the 36 vehicles that ran routes
FLEET_WOS_ROUTE_RUNNING = 72

# Q8 — 2025 exposure-normalised league: vehicle, type, hub, routes, attributable incidents
LEAGUE = [
    ("VEH-0040", "van", "HUB-CHI", 84, 8), ("VEH-0010", "box_truck", "HUB-IND", 97, 6),
    ("VEH-0003", "box_truck", "HUB-CMH", 84, 5), ("VEH-0029", "box_truck", "HUB-DET", 155, 9),
    ("VEH-0018", "box_truck", "HUB-CIN", 93, 5), ("VEH-0038", "box_truck", "HUB-CMH", 81, 4),
    ("VEH-0019", "van", "HUB-CHI", 102, 5), ("VEH-0005", "box_truck", "HUB-CHI", 82, 4),
    ("VEH-0011", "box_truck", "HUB-DET", 155, 7), ("VEH-0032", "box_truck", "HUB-CIN", 90, 4),
    ("VEH-0031", "box_truck", "HUB-CMH", 71, 3), ("VEH-0028", "van", "HUB-CMH", 72, 3),
    ("VEH-0007", "box_truck", "HUB-CMH", 73, 3), ("VEH-0016", "van", "HUB-IND", 98, 4),
    ("VEH-0020", "van", "HUB-CIN", 106, 4), ("VEH-0013", "box_truck", "HUB-IND", 107, 4),
    ("VEH-0025", "box_truck", "HUB-CIN", 112, 4), ("VEH-0017", "box_truck", "HUB-IND", 115, 4),
    ("VEH-0021", "van", "HUB-CMH", 87, 3), ("VEH-0001", "van", "HUB-CMH", 90, 3),
    ("VEH-0027", "van", "HUB-CIN", 97, 3), ("VEH-0022", "van", "HUB-DET", 132, 4),
    ("VEH-0009", "van", "HUB-IND", 105, 3), ("VEH-0030", "box_truck", "HUB-DET", 141, 3),
    ("VEH-0023", "van", "HUB-IND", 97, 2), ("VEH-0004", "van", "HUB-CHI", 99, 2),
    ("VEH-0037", "box_truck", "HUB-CHI", 103, 2), ("VEH-0036", "box_truck", "HUB-CIN", 104, 2),
    ("VEH-0033", "van", "HUB-CMH", 71, 1), ("VEH-0024", "van", "HUB-DET", 158, 2),
    ("VEH-0012", "box_truck", "HUB-CMH", 80, 1), ("VEH-0006", "van", "HUB-CHI", 86, 1),
    ("VEH-0008", "van", "HUB-IND", 100, 1), ("VEH-0002", "box_truck", "HUB-CHI", 111, 1),
    ("VEH-0026", "van", "HUB-CIN", 110, 0), ("VEH-0014", "box_truck", "HUB-CHI", 81, 0),
]
IDLE_2025 = [("VEH-0015", "semi", "HUB-CHI"), ("VEH-0034", "semi", "HUB-IND"),
             ("VEH-0035", "semi", "HUB-CMH"), ("VEH-0039", "semi", "HUB-IND"),
             ("VEH-0041", "van", "HUB-CMH"), ("VEH-0042", "box_truck", "HUB-CHI"),
             ("VEH-0043", "box_truck", "HUB-IND"), ("VEH-0044", "van", "HUB-DET")]

# Q2 — odometer histogram, 25k-mile bins: (bin start, van, box_truck, semi)
ODO_BINS = [(0, 1, 1, 0), (25000, 3, 4, 0), (50000, 2, 1, 0), (75000, 1, 2, 1),
            (100000, 1, 4, 0), (125000, 0, 1, 2), (150000, 2, 3, 0), (175000, 3, 1, 1),
            (200000, 3, 1, 0), (225000, 3, 3, 0)]

# Q14 — Columbus 2025 damage per 100 loadings, by bay group
BAYS = [("Columbus bay 3", "HUB-CMH-BAY-3", 11, 111),
        ("Columbus, other 5 bays", "HUB-CMH-BAY-1,2,4,5,6", 4, 598),
        ("Other four hubs", "CHI, CIN, DET, IND", 25, 2920)]
FLEET_DMG_2025 = (40, 3629)


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
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}" stroke="#ffffff" stroke-width="3" paint-order="stroke">{esc(s)}</text>')


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


def legend(parts, x, y, items, step=130):
    for col, lab in items:
        parts.append(rect(x, y - 10, 14, 12, col))
        parts.append(text(x + 20, y, lab, 12, INK))
        x += step
    return x


def money_k(v):
    return f"${v/1000:.1f}k" if v < 10000 else f"${v/1000:.0f}k"


# ---------------------------------------------------------------- chart 1: maintenance by hub by year
def chart_maintenance_by_hub_year():
    W, H = 960, 520
    x0, x1 = 100, 920
    top, bot = 100, 420
    vmax = 80000
    total = [sum(MAINT[h][j] for h, _ in HUBS) for j in range(3)]
    acc_total = sum(ACC_2025.values())
    parts = canvas(W, H, "Fleet maintenance spend by hub, 2023 / 2024 / 2025",
                   f"Work-order cost (stg_fleet_work_orders). Totals ${total[0]:,} / ${total[1]:,} / "
                   f"${total[2]:,}. 2025 bar split: red = collision repair (${acc_total:,}).")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 20000), lambda v: f"${v//1000}k")
    y_title(parts, 40, top, bot, "Maintenance spend (USD)")
    group_w = (x1 - x0) / len(HUBS)
    bar_w = group_w * 0.24

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (hid, name) in enumerate(HUBS):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate(MAINT[hid]):
            bx = gx + j * (bar_w + 4)
            if j == 2:
                acc = ACC_2025[hid]
                parts.append(rect(bx, yy(val), bar_w, yy(acc) - yy(val), BLUE))
                parts.append(rect(bx, yy(acc), bar_w, bot - yy(acc), RED))
                parts.append(halo(bx + bar_w / 2, (yy(acc) + bot) / 2 + 4, money_k(acc), 9.5, INK))
            else:
                parts.append(rect(bx, yy(val), bar_w, bot - yy(val), YEAR_COLS[j][0]))
            parts.append(text(bx + bar_w / 2, yy(val) - 5, money_k(val), 10.5, INK, "middle"))
        cx = x0 + i * group_w + group_w / 2
        parts.append(text(cx, bot + 20, name, 12, INK, "middle"))
        parts.append(text(cx, bot + 36, hid, 10.5, GREY, "middle"))
    legend(parts, x0, 76, [(LIGHT, "2023"), (MID, "2024"), (BLUE, "2025 other repair & service"),
                           (RED, "2025 collision repair")], step=200)
    parts.append(text((x0 + x1) / 2, H - 10, "Hub (vehicle's home hub)", 12, GREY, "middle"))
    save("fleet-01-maintenance-by-hub-year.svg", parts)


# ---------------------------------------------------------------- chart 2: 2025 $/route by type
def chart_cost_per_route_by_type():
    W, H = 900, 500
    x0, x1 = 110, 700
    top, bot = 100, 410
    vmax = 90
    fleet = FLEET_COST_2025 / FLEET_ROUTES_2025
    fleet_running = FLEET_COST_ROUTE_RUNNING / FLEET_ROUTES_2025
    parts = canvas(W, H, "2025 maintenance cost per route, by vehicle type",
                   "Work-order $ ÷ routes run by that type. Red = collision repair, blue = everything else.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 15), lambda v: f"${v}")
    y_title(parts, 45, top, bot, "Maintenance cost per route (USD)")

    def yy(v):
        return bot - v / vmax * (bot - top)

    slot = (x1 - x0) / len(TYPES_2025)
    bar_w = slot * 0.42
    for i, (t, lab, routes, wos, cost, acc_wos, acc_cost) in enumerate(TYPES_2025):
        bx = x0 + i * slot + (slot - bar_w) / 2
        cx = bx + bar_w / 2
        parts.append(text(cx, bot + 20, lab, 12.5, INK, "middle"))
        parts.append(text(cx, bot + 36, f"{routes:,} routes · {wos} WOs", 10.5, GREY, "middle"))
        if routes == 0:
            parts.append(rect(bx, bot - 70, bar_w, 70, "none", GRID))
            parts.append(text(cx, bot - 48, "no routes in 2025", 11, GREY, "middle", "bold"))
            parts.append(text(cx, bot - 32, f"${cost:,} spent", 11, RED, "middle"))
            parts.append(text(cx, bot - 17, "on 4 idle semis", 11, GREY, "middle"))
            continue
        per = cost / routes
        acc = acc_cost / routes
        parts.append(rect(bx, yy(acc), bar_w, bot - yy(acc), RED))
        parts.append(rect(bx, yy(per), bar_w, yy(acc) - yy(per), BLUE))
        parts.append(halo(cx, (yy(acc) + bot) / 2 + 4, f"${acc:.2f}", 11, INK))
        parts.append(halo(cx, (yy(per) + yy(acc)) / 2 + 4, f"${per - acc:.2f}", 11, INK))
        parts.append(text(cx, yy(per) - 6, f"${per:.2f}", 12.5, INK, "middle", "bold"))
    # reference lines
    parts.append(line(x0, yy(fleet), x1, yy(fleet), INK, 1.5, "6,4"))
    parts.append(text(x1 + 8, yy(fleet) - 2, f"fleet average ${fleet:.2f}", 11, INK, "start", "bold"))
    parts.append(text(x1 + 8, yy(fleet) + 12, "(all spend ÷ all routes)", 10.5, GREY))
    parts.append(line(x0, yy(fleet_running), x1, yy(fleet_running), GREY, 1.2, "2,3"))
    parts.append(text(x1 + 8, yy(fleet_running) + 14, f"${fleet_running:.2f} excl. idle-semi spend", 10.5, GREY))
    legend(parts, x0, 76, [(RED, "collision repair"), (BLUE, "wear/fault repair + preventive")], step=160)
    parts.append(text((x0 + x1) / 2, H - 10, "Vehicle type", 12, GREY, "middle"))
    save("fleet-02-cost-per-route-by-type.svg", parts)


# ---------------------------------------------------------------- chart 3: league with chance band
def chart_incident_league():
    rows = LEAGUE
    k_tot = sum(r[4] for r in rows)
    n_tot = sum(r[3] for r in rows)
    p = k_tot / n_tot
    row_h = 17
    W = 960
    x0, x1 = 230, 860
    top = 105
    bot = top + row_h * len(rows)
    H = bot + 80
    vmax = 12
    parts = canvas(W, H, "2025 incidents per 100 routes, by vehicle (ranked)",
                   f"{k_tot} attributable incidents on {n_tot:,} routes; fleet average {100*p:.2f}. "
                   "Shaded = chance band for each vehicle's route count (fleet rate ± 2σ).")

    def xx(v):
        return x0 + v / vmax * (x1 - x0)

    for v in range(0, vmax + 1, 2):
        parts.append(line(xx(v), top - 4, xx(v), bot, GRID, 1))
        parts.append(text(xx(v), bot + 16, str(v), 11, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 36, "Incidents per 100 routes (attributable incidents ÷ routes run, 2025)",
                      12, GREY, "middle"))
    for i, (veh, t, hub, n, k) in enumerate(rows):
        y = top + i * row_h
        sd = math.sqrt(p * n) / n
        lo, hi = max(0.0, 100 * (p - 2 * sd)), 100 * (p + 2 * sd)
        parts.append(rect(xx(lo), y + 1, xx(hi) - xx(lo), row_h - 2, BAND))
        rate = 100 * k / n
        outside = rate > hi
        col = RED if outside else BLUE
        parts.append(rect(x0, y + 4, xx(rate) - x0, row_h - 8, col))
        parts.append(text(x0 - 8, y + row_h - 5, f"{veh}  {t.replace('_', ' ')} · {hub[4:]}", 10.5,
                          RED if outside else INK, "end", "bold" if outside else "normal"))
        parts.append(text(xx(rate) + 5, y + row_h - 5, f"{rate:.2f}  ({k}/{n})", 10,
                          RED if outside else GREY, "start", "bold" if outside else "normal"))
    xf = xx(100 * p)
    parts.append(line(xf, top - 18, xf, bot, INK, 1.5, "6,4"))
    parts.append(text(xf + 4, top - 8, f"fleet average {100*p:.2f}", 11, INK, "start", "bold"))
    parts.append(text(x1, top - 22, "VEH-0040: only bar outside its band; p≈0.008 alone,", 10.5, RED, "end"))
    parts.append(text(x1, top - 8, "but ≈25% chance one of 36 vehicles does this by luck", 10.5, RED, "end"))
    parts.append(rect(x0, H - 26, 14, 10, BAND))
    parts.append(text(x0 + 20, H - 17, "chance band (±2σ)", 11, GREY))
    parts.append(text(x0 + 170, H - 17, f"8 idle vehicles (0 routes) not shown: "
                      + ", ".join(v for v, _, _ in IDLE_2025[:4]) + ", …", 10.5, GREY))
    save("fleet-03-incidents-per-100-routes-by-vehicle.svg", parts)


# ---------------------------------------------------------------- chart 4: odometer + utilisation
def chart_odometer_utilisation():
    W, H = 1000, 520
    parts = canvas(W, H, "The fleet on paper vs the fleet at work",
                   "Left: odometer snapshot (stg_vehicles), 44 vehicles. "
                   "Right: routes run per vehicle in 2025 (stg_routes), one dot per vehicle.")
    # left panel — stacked histogram
    x0, x1, top, bot = 80, 470, 95, 410
    vmax = 8
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 2), str)
    y_title(parts, 35, top, bot, "Vehicles (count)")
    bw = (x1 - x0) / len(ODO_BINS)

    def yy(v):
        return bot - v / vmax * (bot - top)

    for i, (b, van, box, semi) in enumerate(ODO_BINS):
        bx = x0 + i * bw + 3
        base = 0
        for val, t in [(box, "box_truck"), (van, "van"), (semi, "semi")]:
            if val:
                parts.append(rect(bx, yy(base + val), bw - 6, yy(base) - yy(base + val), TYPE_COLS[t]))
            base += val
        parts.append(text(bx + (bw - 6) / 2, yy(base) - 5, str(base), 11, INK, "middle", "bold"))
        parts.append(text(bx + (bw - 6) / 2, bot + 15, f"{b//1000}", 10.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 34, "Odometer reading, 25k-mile bins (thousand miles, bin start)",
                      11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 52, "Snapshot only: corr. with 3-yr routes 0.14, with repair cost −0.08",
                      10.5, RED, "middle"))
    legend(parts, x0, 80, [(MID, "box truck"), (BLUE, "van"), (LIGHT, "semi")], step=100)
    # right panel — dot plot by hub
    px0, px1, ptop, pbot = 580, 960, 95, 410
    rmax = 170
    hubs = [h for h, _ in HUBS]
    for v in range(0, rmax + 1, 25):
        xv = px0 + v / rmax * (px1 - px0)
        parts.append(line(xv, ptop, xv, pbot, GRID, 1))
        parts.append(text(xv, pbot + 15, str(v), 10.5, GREY, "middle"))
    parts.append(text((px0 + px1) / 2, pbot + 34, "Routes run in 2025 (count)", 11.5, GREY, "middle"))
    lane = (pbot - ptop) / len(hubs)
    by_hub = {h: [(n, v) for v, t, hh, n, k in LEAGUE if hh == h] for h in hubs}
    for h, v, in [(hh, vv) for vv, _t, hh in IDLE_2025]:
        by_hub[h].append((0, v))
    for i, (h, name) in enumerate(HUBS):
        cy = ptop + i * lane + lane / 2
        parts.append(text(px0 - 8, cy + 4, name, 11.5, INK, "end"))
        vals = sorted(by_hub[h])
        seen = {}
        for n, v in vals:
            bucket = round(n / 4)
            k = seen.get(bucket, 0)
            seen[bucket] = k + 1
            cx = px0 + n / rmax * (px1 - px0)
            col = RED if n == 0 else HUB_COLS[h]
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy - 6 + k * 9:.1f}" r="4.2" fill="{col}" fill-opacity="0.85"/>')
        running = [n for n, _ in vals if n > 0]
        idle = len(vals) - len(running)
        parts.append(text(px1 - 2, cy - 14, f"{len(vals)} owned · {idle} idle · mean {sum(running)/len(running):.0f}",
                          10, GREY, "end"))
    parts.append(f'<circle cx="{px0+6}" cy="{H-22}" r="4.2" fill="{RED}"/>')
    parts.append(text(px0 + 16, H - 18, "idle all year (0 routes): all 4 semis + VEH-0041, 0042, 0043, 0044",
                      10.5, GREY))
    save("fleet-04-odometer-utilisation.svg", parts)


# ---------------------------------------------------------------- chart 5: WOs per 100 routes by type
def chart_wos_per_100_by_type():
    W, H = 900, 500
    x0, x1 = 110, 700
    top, bot = 100, 410
    vmax = 2.5
    fleet = 100 * FLEET_WOS_ROUTE_RUNNING / FLEET_ROUTES_2025
    parts = canvas(W, H, "2025 work orders per 100 routes, by vehicle type",
                   "Count of work orders ÷ routes run by that type. Red = collision repair, blue = everything else.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, [0, 0.5, 1.0, 1.5, 2.0, 2.5], lambda v: f"{v:.1f}")
    y_title(parts, 45, top, bot, "Work orders per 100 routes")

    def yy(v):
        return bot - v / vmax * (bot - top)

    slot = (x1 - x0) / len(TYPES_2025)
    bar_w = slot * 0.42
    for i, (t, lab, routes, wos, cost, acc_wos, acc_cost) in enumerate(TYPES_2025):
        bx = x0 + i * slot + (slot - bar_w) / 2
        cx = bx + bar_w / 2
        parts.append(text(cx, bot + 20, lab, 12.5, INK, "middle"))
        parts.append(text(cx, bot + 36, f"{wos} WOs on {routes:,} routes", 10.5, GREY, "middle"))
        if routes == 0:
            parts.append(rect(bx, bot - 70, bar_w, 70, "none", GRID))
            parts.append(text(cx, bot - 48, "no routes in 2025", 11, GREY, "middle", "bold"))
            parts.append(text(cx, bot - 32, f"{wos} work orders anyway", 11, RED, "middle"))
            continue
        per = 100 * wos / routes
        acc = 100 * acc_wos / routes
        parts.append(rect(bx, yy(acc), bar_w, bot - yy(acc), RED))
        parts.append(rect(bx, yy(per), bar_w, yy(acc) - yy(per), BLUE))
        parts.append(halo(cx, (yy(acc) + bot) / 2 + 4, f"{acc:.2f}  ({acc_wos})", 11, INK))
        parts.append(halo(cx, (yy(per) + yy(acc)) / 2 + 4, f"{per - acc:.2f}  ({wos - acc_wos})", 11, INK))
        parts.append(text(cx, yy(per) - 6, f"{per:.2f}", 12.5, INK, "middle", "bold"))
    parts.append(line(x0, yy(fleet), x1, yy(fleet), INK, 1.5, "6,4"))
    parts.append(text(x1 + 8, yy(fleet) + 4, f"fleet average {fleet:.2f}", 11, INK, "start", "bold"))
    parts.append(text(x1 + 8, yy(fleet) + 18, f"({FLEET_WOS_ROUTE_RUNNING} WOs ÷ {FLEET_ROUTES_2025:,} routes)",
                      10.5, GREY))
    legend(parts, x0, 76, [(RED, "collision repair"), (BLUE, "wear/fault repair + preventive")], step=160)
    parts.append(text((x0 + x1) / 2, H - 10, "Vehicle type", 12, GREY, "middle"))
    save("fleet-05-work-orders-per-100-routes-by-type.svg", parts)


# ---------------------------------------------------------------- chart 6: Columbus bay 3
def chart_bay3():
    W, H = 960, 440
    x0, x1 = 110, 700
    top, bot = 95, 350
    vmax = 12
    fleet = 100 * FLEET_DMG_2025[0] / FLEET_DMG_2025[1]
    parts = canvas(W, H, "2025 freight damage per 100 loadings: the bay, not the truck",
                   "stg_dock_bay_events: damage_found events ÷ loading events. 11 + 4 + 25 = 40 damage events; "
                   "111 + 598 + 2,920 = 3,629 loadings.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 2), str)
    y_title(parts, 45, top, bot, "Damage events per 100 loadings")

    def yy(v):
        return bot - v / vmax * (bot - top)

    slot = (x1 - x0) / len(BAYS)
    bar_w = slot * 0.42
    for i, (lab, sub, d, n) in enumerate(BAYS):
        bx = x0 + i * slot + (slot - bar_w) / 2
        cx = bx + bar_w / 2
        rate = 100 * d / n
        parts.append(rect(bx, yy(rate), bar_w, bot - yy(rate), RED if i == 0 else BLUE))
        parts.append(text(cx, yy(rate) - 6, f"{rate:.2f}  ({d}/{n:,})", 12, INK, "middle", "bold"))
        parts.append(text(cx, bot + 20, lab, 12, INK, "middle"))
        parts.append(text(cx, bot + 36, sub, 10.5, GREY, "middle"))
    parts.append(line(x0, yy(fleet), x1, yy(fleet), INK, 1.5, "6,4"))
    parts.append(text(x1 + 8, yy(fleet) + 4, f"fleet {fleet:.2f}", 11, INK, "start", "bold"))
    parts.append(text(x1 + 8, yy(fleet) + 18, f"({FLEET_DMG_2025[0]} ÷ {FLEET_DMG_2025[1]:,})", 10.5, GREY))
    parts.append(text(x1 + 8, yy(9.91) + 4, "Every Columbus vehicle", 10.5, GREY))
    parts.append(text(x1 + 8, yy(9.91) + 18, "loaded at bay 3 (7–18 times);", 10.5, GREY))
    parts.append(text(x1 + 8, yy(9.91) + 32, "VEH-0012 most often (18), 0 damage", 10.5, GREY))
    save("fleet-06-columbus-damage-by-bay.svg", parts)


if __name__ == "__main__":
    chart_maintenance_by_hub_year()
    chart_cost_per_route_by_type()
    chart_incident_league()
    chart_odometer_utilisation()
    chart_wos_per_100_by_type()
    chart_bay3()
