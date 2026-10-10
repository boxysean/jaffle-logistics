#!/usr/bin/env python3
"""Generate the CFO persona-report charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible without the
warehouse. Every number comes from an execute_sql query against
hive_metastore.dbt_smcintyre_jaffle_logistics_prod; the SQL is in the appendix of
reports/persona-cfo.md (query numbers are noted beside each data block).

Output: reports/assets/personas/cfo-*.svg  (committed alongside the report).

Design rules (match scripts/persona_fleet_charts.py):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar;
  * the 97% contractual on-time target drawn as a dashed, labelled reference line
    on every chart that shows an on-time rate;
  * consistent colour meaning: red = Jaffle Equipment / the failure,
    grey-blue ramp = years, neutral blue = a series with no judgement attached.

Run from the repo root:  python3 scripts/persona_cfo_charts.py
"""
import os
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "personas")

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # Jaffle Equipment / the failure
BLUE = "#2c6fbb"     # neutral series
GREY = "#555555"
GRID = "#d9d9d9"
INK = "#1a1a1a"
LIGHT = "#9aa7b5"
MID = "#5b7fa6"
BAND = "#eef1f5"
YEAR_COLS = [(LIGHT, "2023"), (MID, "2024"), (BLUE, "2025")]
CAT_COLS = {"fuel": BLUE, "maintenance": RED, "subcontractor": "#1a1a1a",
            "facility": LIGHT, "technology": "#7a9cc6"}

FONT = "Helvetica, Arial, sans-serif"
SLA = 97.0


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from execute_sql)
# Q7 — quarterly on-time %: (quarter, whole book %, whole-book missed, Equipment %, Equipment missed)
QUARTERLY = [
    ("2023-Q1", 96.87, 14, 96.43, 3), ("2023-Q2", 97.75, 9, 98.82, 1),
    ("2023-Q3", 97.79, 10, 98.90, 1), ("2023-Q4", 97.63, 13, 96.97, 3),
    ("2024-Q1", 97.03, 14, 99.11, 1), ("2024-Q2", 97.39, 11, 97.73, 2),
    ("2024-Q3", 97.48, 12, 97.26, 2), ("2024-Q4", 97.06, 17, 97.48, 3),
    ("2025-Q1", 90.33, 47, 86.14, 14), ("2025-Q2", 95.40, 20, 89.58, 10),
    ("2025-Q3", 95.12, 24, 82.47, 17), ("2025-Q4", 92.62, 44, 78.69, 26),
]

# Q4 — by account: name, (shipments, missed, on-time %) for 2023 / 2024 / 2025
BY_ACCOUNT = [
    ("CLI-0007", "Storefronts", [(354, 8, 97.74), (371, 11, 97.04), (387, 13, 96.64)]),
    ("CLI-0042", "Equipment", [(359, 8, 97.77), (392, 8, 97.96), (416, 67, 83.89)]),
    ("CLI-0155", "Crew Outfitters", [(382, 9, 97.64), (378, 11, 97.09), (398, 12, 96.98)]),
    ("CLI-0169", "Beverage Co", [(329, 9, 97.26), (398, 13, 96.73), (394, 21, 94.67)]),
    ("CLI-0201", "Paper & Packaging", [(424, 12, 97.17), (410, 11, 97.32), (414, 22, 94.69)]),
]

# Q19 — 2025 non-labour cost by category (company-wide, exact)
CAT_2025 = [("fuel", 2855968), ("maintenance", 267578), ("subcontractor", 1186640),
            ("facility", 2595832), ("technology", 273996)]
COST_2025_TOTAL = 7180014

# Q21 — 2025 non-labour cost by hub (exact), routes, shipments
COST_2025_BY_HUB = [
    ("HUB-CMH", "Columbus", 1745940, 709, 347),
    ("HUB-CHI", "Chicago", 1393529, 748, 412),
    ("HUB-DET", "Detroit", 1383006, 741, 427),
    ("HUB-CIN", "Cincinnati", 1372471, 712, 398),
    ("HUB-IND", "Indianapolis", 1285068, 719, 425),
]

# Q14, Q19, Q20 — year economics (USD)
YEAR_ECONOMICS = [
    # year, non-labour cost, driver labour, net revenue
    ("2023", 6424631, 1640713, 2641286.00),
    ("2024", 6529926, 1784067, 2754406.50),
    ("2025", 7180014, 1841275, 2826777.14),
]

# Q17 — 2025 credits actually issued, by account
CREDITS_2025 = [
    ("CLI-0042", "Equipment", 963695, 51269.00, 12),
    ("CLI-0007", "Storefronts", 445180, 1301.98, 12),
    ("CLI-0169", "Beverage Co", 487795, 383.88, 10),
    ("CLI-0155", "Crew Outfitters", 458802, 0.00, 0),
    ("CLI-0201", "Paper & Packaging", 524260, 0.00, 0),
]
CREDITS_TOTAL = 52954.86
GROSS_TOTAL = 2879732.00

# Q16 — Jaffle Equipment 2025 by month: (month, gross $, credit $, trailing-12m on-time %)
EQUIP_MONTHLY_2025 = [
    (1, 87925, 879.25, 95.9), (2, 67075, 1341.50, 95.0), (3, 78790, 1575.80, 94.5),
    (4, 81025, 1620.50, 94.1), (5, 76350, 2290.50, 93.3), (6, 64915, 2596.60, 92.5),
    (7, 74050, 3702.50, 91.5), (8, 74050, 4443.00, 90.5), (9, 76490, 5354.30, 89.3),
    (10, 83745, 7537.05, 87.9), (11, 85905, 8590.50, 86.4), (12, 113375, 11337.50, 83.9),
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Q24 — share of the 2,009 2025 shipments
CONC_ACCOUNT = [("Equipment", 416, 20.71), ("Paper & Packaging", 414, 20.61),
                ("Crew Outfitters", 398, 19.81), ("Beverage Co", 394, 19.61),
                ("Storefronts", 387, 19.26)]
CONC_HUB = [("Detroit", 427, 21.25), ("Indianapolis", 425, 21.15), ("Chicago", 412, 20.51),
            ("Cincinnati", 398, 19.81), ("Columbus", 347, 17.27)]


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


def polyline(points, color, w=2.5):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{w}"/>'


def dot(x, y, color, r=3.8):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}"/>'


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


def sla_line(parts, x0, x1, y, label_x=None, anchor="start"):
    parts.append(line(x0, y, x1, y, INK, 1.5, "6,4"))
    lx = x1 + 8 if label_x is None else label_x
    parts.append(text(lx, y + 4, "97% contract target", 11, INK, anchor, "bold"))


def money_m(v):
    return f"${v/1e6:.2f}m"


# ---------------------------------------------------------------- chart 1: quarterly on-time
def chart_ontime_by_quarter():
    W, H = 960, 500
    x0, x1 = 90, 800
    top, bot = 95, 410
    vmin, vmax = 75, 100
    parts = canvas(W, H, "On-time rate by quarter, 2023 Q1 to 2025 Q4",
                   "Share of shipments with status 'delivered' (stg_shipments). "
                   "Y axis starts at 75%. Whole book includes Jaffle Equipment.")
    y_gridlines(parts, x0, x1, top, bot, vmin, vmax, range(vmin, vmax + 1, 5), lambda v: f"{v}%")
    y_title(parts, 35, top, bot, "On-time rate (%)")

    def yy(v):
        return bot - (v - vmin) / (vmax - vmin) * (bot - top)

    step = (x1 - x0) / len(QUARTERLY)

    def xx(i):
        return x0 + step * (i + 0.5)

    for i, (q, *_rest) in enumerate(QUARTERLY):
        yr, qn = q.split("-")
        parts.append(text(xx(i), bot + 18, qn, 11, GREY, "middle"))
        if qn == "Q1":
            parts.append(text(xx(i) + step * 1.5, bot + 36, yr, 12, INK, "middle", "bold"))
            if i:
                parts.append(line(x0 + step * i, top, x0 + step * i, bot + 40, GRID, 1))
    sla_line(parts, x0, x1, yy(SLA))
    book = [(xx(i), yy(r[1])) for i, r in enumerate(QUARTERLY)]
    equip = [(xx(i), yy(r[3])) for i, r in enumerate(QUARTERLY)]
    parts.append(polyline(book, BLUE))
    parts.append(polyline(equip, RED))
    for i, r in enumerate(QUARTERLY):
        parts.append(dot(*book[i], BLUE))
        parts.append(dot(*equip[i], RED))
        if r[0].startswith("2025"):
            parts.append(halo(book[i][0], book[i][1] - 9, f"{r[1]:.1f}", 10.5, BLUE, "middle", "bold"))
            parts.append(halo(equip[i][0], equip[i][1] + 17, f"{r[3]:.1f}", 10.5, RED, "middle", "bold"))
    parts.append(text(x1 + 8, book[-1][1] + 4, "Whole book", 11.5, BLUE, "start", "bold"))
    parts.append(text(x1 + 8, equip[-1][1] + 4, "Jaffle Equipment", 11.5, RED, "start", "bold"))
    legend(parts, x0, 76, [(BLUE, "Whole book (all five accounts)"), (RED, "Jaffle Equipment (CLI-0042)")],
           step=260)
    save("cfo-01-ontime-by-quarter.svg", parts)


# ---------------------------------------------------------------- chart 2: missed shipments by account
def chart_missed_by_account():
    W, H = 900, 480
    x0, x1 = 90, 860
    top, bot = 95, 390
    vmax = 70
    tot24 = sum(a[2][1][1] for a in BY_ACCOUNT)
    tot25 = sum(a[2][2][1] for a in BY_ACCOUNT)
    parts = canvas(W, H, "Missed shipments by account, 2024 and 2025",
                   f"Count of shipments not 'delivered' (delayed + failed + returned). "
                   f"Totals {tot24} (2024) and {tot25} (2025).")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, range(0, vmax + 1, 10), str)
    y_title(parts, 40, top, bot, "Missed shipments (count)")

    def yy(v):
        return bot - v / vmax * (bot - top)

    slot = (x1 - x0) / len(BY_ACCOUNT)
    bw = slot * 0.3
    for i, (cid, name, yrs) in enumerate(BY_ACCOUNT):
        cx = x0 + i * slot + slot / 2
        m24, m25 = yrs[1][1], yrs[2][1]
        col25 = RED if cid == "CLI-0042" else BLUE
        parts.append(rect(cx - bw - 2, yy(m24), bw, bot - yy(m24), LIGHT))
        parts.append(rect(cx + 2, yy(m25), bw, bot - yy(m25), col25))
        parts.append(text(cx - bw / 2 - 2, yy(m24) - 5, str(m24), 11, GREY, "middle"))
        parts.append(text(cx + bw / 2 + 2, yy(m25) - 5, str(m25), 12.5, INK, "middle", "bold"))
        parts.append(text(cx, bot + 20, name, 12, RED if cid == "CLI-0042" else INK, "middle"))
        parts.append(text(cx, bot + 36, f"{cid} · {yrs[2][0]} shipped 2025", 10.5, GREY, "middle"))
    legend(parts, x0, 76, [(LIGHT, "2024 misses"), (BLUE, "2025 misses"),
                           (RED, "2025 misses, Jaffle Equipment")], step=170)
    parts.append(text((x0 + x1) / 2, H - 10, "2025: 13 + 67 + 12 + 21 + 22 = 135 misses; "
                      "Equipment's 67 is 50% of them", 11.5, GREY, "middle"))
    save("cfo-02-missed-shipments-by-account.svg", parts)


# ---------------------------------------------------------------- chart 3: on-time by account, 3 yrs
def chart_ontime_3yr_by_account():
    W, H = 960, 500
    x0, x1 = 90, 800
    top, bot = 95, 400
    vmin, vmax = 80, 100
    parts = canvas(W, H, "On-time rate by account, 2023 / 2024 / 2025",
                   "Share of each account's shipments delivered on time (stg_shipments). Y axis starts at 80%.")
    y_gridlines(parts, x0, x1, top, bot, vmin, vmax, range(vmin, vmax + 1, 5), lambda v: f"{v}%")
    y_title(parts, 35, top, bot, "On-time rate (%)")

    def yy(v):
        return bot - (v - vmin) / (vmax - vmin) * (bot - top)

    slot = (x1 - x0) / len(BY_ACCOUNT)
    bw = slot * 0.24
    for i, (cid, name, yrs) in enumerate(BY_ACCOUNT):
        gx = x0 + i * slot + slot * 0.12
        for j, (_n, _m, pct) in enumerate(yrs):
            bx = gx + j * (bw + 4)
            col = RED if (cid == "CLI-0042" and j == 2) else YEAR_COLS[j][0]
            parts.append(rect(bx, yy(pct), bw, bot - yy(pct), col))
            parts.append(halo(bx + bw / 2, yy(pct) - 5, f"{pct:.1f}", 10,
                              INK, "middle", "bold" if j == 2 else "normal"))
        cx = x0 + i * slot + slot / 2
        parts.append(text(cx, bot + 20, name, 12, RED if cid == "CLI-0042" else INK, "middle"))
        parts.append(text(cx, bot + 36, cid, 10.5, GREY, "middle"))
    sla_line(parts, x0, x1, yy(SLA))
    legend(parts, x0, 76, [(LIGHT, "2023"), (MID, "2024"), (BLUE, "2025"), (RED, "2025, Jaffle Equipment")],
           step=120)
    save("cfo-03-ontime-3yr-by-account.svg", parts)


# ---------------------------------------------------------------- chart 4: cost by hub and category
def chart_cost_by_hub_category():
    W, H = 960, 520
    x0, x1 = 100, 760
    top, bot = 100, 420
    vmax = 2.0e6
    shares = [(c, v / COST_2025_TOTAL) for c, v in CAT_2025]
    hub_sum = sum(h[2] for h in COST_2025_BY_HUB)
    parts = canvas(W, H, "2025 non-labour operating cost by hub",
                   "Category shares are the company-wide 2025 mix; hub totals are exact "
                   f"(stg_cost_ledger; hubs sum to ${hub_sum:,}).")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, [0, 0.5e6, 1.0e6, 1.5e6, 2.0e6], lambda v: f"${v/1e6:.1f}m")
    y_title(parts, 40, top, bot, "Non-labour cost (USD millions)")

    def yy(v):
        return bot - v / vmax * (bot - top)

    slot = (x1 - x0) / len(COST_2025_BY_HUB)
    bw = slot * 0.5
    for i, (hid, name, total, routes, ships) in enumerate(COST_2025_BY_HUB):
        bx = x0 + i * slot + (slot - bw) / 2
        cx = bx + bw / 2
        base = 0.0
        for cat, sh in shares:
            v = total * sh
            parts.append(rect(bx, yy(base + v), bw, yy(base) - yy(base + v), CAT_COLS[cat]))
            if cat in ("fuel", "facility"):
                parts.append(halo(cx, (yy(base) + yy(base + v)) / 2 + 4, money_m(v), 10, INK))
            base += v
        parts.append(text(cx, yy(total) - 6, money_m(total), 12, INK, "middle", "bold"))
        parts.append(text(cx, bot + 20, name, 12, INK, "middle"))
        parts.append(text(cx, bot + 36, f"${total/ships:,.0f} per shipment", 10.5, GREY, "middle"))
    ly = 120
    for cat, sh in reversed(shares):
        parts.append(rect(x1 + 30, ly - 10, 14, 12, CAT_COLS[cat]))
        parts.append(text(x1 + 50, ly, f"{cat} ({100*sh:.1f}%)", 12, INK))
        ly += 22
    parts.append(text(x1 + 30, ly + 10, "Company-wide 2025 mix,", 10.5, GREY))
    parts.append(text(x1 + 30, ly + 24, "applied to each hub.", 10.5, GREY))
    parts.append(text(x1 + 30, ly + 44, "Columbus: 17% of shipments,", 10.5, RED))
    parts.append(text(x1 + 30, ly + 58, "24% of non-labour cost.", 10.5, RED))
    parts.append(text((x0 + x1) / 2, H - 10, "Hub (cost-ledger hub_id)", 12, GREY, "middle"))
    save("cfo-04-cost-by-hub-category.svg", parts)


# ---------------------------------------------------------------- chart 5: cost vs revenue
def chart_cost_vs_revenue():
    W, H = 900, 500
    x0, x1 = 100, 860
    top, bot = 100, 410
    vmax = 8.0e6
    parts = canvas(W, H, "Recorded cost against recorded revenue, 2023 / 2024 / 2025",
                   "Cost ledger (non-labour) + payroll ledger (driver labour) vs revenue ledger (net of credits). "
                   "These do not form a P&L.")
    y_gridlines(parts, x0, x1, top, bot, 0, vmax, [i * 1e6 for i in range(0, 9, 2)], lambda v: f"${v/1e6:.0f}m")
    y_title(parts, 40, top, bot, "USD millions")

    def yy(v):
        return bot - v / vmax * (bot - top)

    cols = [MID, LIGHT, BLUE]
    slot = (x1 - x0) / len(YEAR_ECONOMICS)
    bw = slot * 0.24
    for i, (yr, nonlab, lab, rev) in enumerate(YEAR_ECONOMICS):
        gx = x0 + i * slot + slot * 0.12
        for j, v in enumerate((nonlab, lab, rev)):
            bx = gx + j * (bw + 4)
            parts.append(rect(bx, yy(v), bw, bot - yy(v), cols[j]))
            parts.append(text(bx + bw / 2, yy(v) - 5, money_m(v), 11, INK, "middle", "bold" if j == 2 else "normal"))
        cx = x0 + i * slot + slot / 2
        parts.append(text(cx, bot + 20, yr, 12.5, INK, "middle", "bold"))
        parts.append(text(cx, bot + 36, f"revenue = {100*rev/(nonlab+lab):.0f}% of the two costs", 10.5, GREY,
                          "middle"))
    legend(parts, x0, 76, [(MID, "Non-labour operating cost"), (LIGHT, "Driver labour"),
                           (BLUE, "Net revenue")], step=220)
    save("cfo-05-cost-vs-revenue.svg", parts)


# ---------------------------------------------------------------- chart 6: credits by account
def chart_credit_exposure():
    W, H = 960, 400
    x0, x1 = 220, 760
    top = 95
    row_h = 46
    bot = top + row_h * len(CREDITS_2025)
    vmax = 60000
    parts = canvas(W, H, "2025 contract credits actually issued, by account",
                   f"fct_account_revenue, 2025. Total ${CREDITS_TOTAL:,.2f} = "
                   f"{100*CREDITS_TOTAL/GROSS_TOTAL:.2f}% of ${GROSS_TOTAL:,.0f} gross revenue.")

    def xx(v):
        return x0 + v / vmax * (x1 - x0)

    for v in range(0, vmax + 1, 10000):
        parts.append(line(xx(v), top - 4, xx(v), bot, GRID, 1))
        parts.append(text(xx(v), bot + 16, f"${v//1000}k", 11, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 36, "Contract credits issued in 2025 (USD)", 12, GREY, "middle"))
    for i, (cid, name, gross, cred, breach) in enumerate(CREDITS_2025):
        y = top + i * row_h
        col = RED if cid == "CLI-0042" else BLUE
        parts.append(text(x0 - 10, y + 20, name, 12.5, RED if cid == "CLI-0042" else INK, "end",
                          "bold" if cid == "CLI-0042" else "normal"))
        parts.append(text(x0 - 10, y + 35, f"{cid} · {breach} of 12 months in breach", 10.5, GREY, "end"))
        if cred > 0:
            parts.append(rect(x0, y + 8, max(xx(cred) - x0, 2), row_h - 18, col))
        pct = 100 * cred / gross
        lab = f"${cred:,.2f}  ({pct:.2f}% of gross)" if cred > 0 else "$0.00  (no credit)"
        parts.append(text(max(xx(cred), x0 + 2) + 8, y + 27, lab, 12, INK, "start", "bold" if cred > 0 else "normal"))
    parts.append(text(W / 2, H - 14, "51,269.00 + 1,301.98 + 383.88 + 0 + 0 = 52,954.86", 11.5, GREY, "middle"))
    save("cfo-06-credit-exposure-by-account.svg", parts)


# ---------------------------------------------------------------- chart 7: Equipment credit accrual
def chart_equipment_accrual():
    W, H = 960, 500
    x0, x1 = 90, 830
    top, bot = 100, 410
    pmin, pmax = 80, 100
    cmax = 12000
    total = sum(r[2] for r in EQUIP_MONTHLY_2025)
    parts = canvas(W, H, "Jaffle Equipment 2025: trailing on-time rate and the credit it triggers",
                   f"stg_revenue_ledger. Line: trailing-12-month on-time % (left axis). "
                   f"Bars: monthly contract credit $ (right axis), total ${total:,.2f}.")

    def yp(v):
        return bot - (v - pmin) / (pmax - pmin) * (bot - top)

    def yc(v):
        return bot - v / cmax * (bot - top)

    for v in range(pmin, pmax + 1, 5):
        parts.append(line(x0, yp(v), x1, yp(v), GRID, 1))
        parts.append(text(x0 - 8, yp(v) + 4, f"{v}%", 11.5, RED, "end"))
    for v in range(0, cmax + 1, 3000):
        parts.append(text(x1 + 8, yc(v) + 4, f"${v//1000}k", 11.5, MID, "start"))
    y_title(parts, 35, top, bot, "Trailing-12-month on-time rate (%)")
    parts.append(text(x1 + 62, (top + bot) / 2, "Monthly contract credit (USD)", 12, GREY, "middle", rotate=90))
    step = (x1 - x0) / 12
    bw = step * 0.55
    pts = []
    for i, (m, gross, cred, trail) in enumerate(EQUIP_MONTHLY_2025):
        cx = x0 + step * (i + 0.5)
        parts.append(rect(cx - bw / 2, yc(cred), bw, bot - yc(cred), LIGHT))
        parts.append(text(cx, yc(cred) - 5, f"${cred/1000:.1f}k", 10, MID, "middle"))
        parts.append(text(cx, bot + 18, MONTHS[i], 11.5, INK, "middle"))
        pts.append((cx, yp(trail)))
    parts.append(line(x0, yp(SLA), x1, yp(SLA), INK, 1.5, "6,4"))
    parts.append(text(x0 + 6, yp(SLA) - 6, "97% contract target (SLA)", 11, INK, "start", "bold"))
    parts.append(polyline(pts, RED))
    for i, (cx, cy) in enumerate(pts):
        parts.append(dot(cx, cy, RED))
        parts.append(halo(cx, cy - 9, f"{EQUIP_MONTHLY_2025[i][3]:.1f}", 10, RED, "middle", "bold"))
    legend(parts, x0, 76, [(RED, "Trailing-12-month on-time %"), (LIGHT, "Monthly credit issued ($)")], step=240)
    parts.append(text((x0 + x1) / 2, H - 14, "Credit = 1.0% of monthly spend per full point below 97%, "
                      "capped at 10%. December: 11,337.50 on 113,375 gross = 10%.", 11, GREY, "middle"))
    save("cfo-07-equipment-credit-accrual.svg", parts)


# ---------------------------------------------------------------- chart 8: concentration
def chart_concentration():
    W, H = 1000, 380
    parts = canvas(W, H, "Where the 2,009 shipments of 2025 came from",
                   "Share of 2025 shipments (stg_shipments). Volume is spread evenly by design; "
                   "revenue is not (Equipment 33.5% of gross).")
    vmax = 25

    def panel(px0, px1, rows, heading, red_first):
        top = 105
        row_h = 40
        bot = top + row_h * len(rows)
        parts.append(text((px0 + px1) / 2, 82, heading, 13.5, INK, "middle", "bold"))

        def xx(v):
            return px0 + v / vmax * (px1 - px0)

        for v in range(0, vmax + 1, 5):
            parts.append(line(xx(v), top - 4, xx(v), bot, GRID, 1))
            parts.append(text(xx(v), bot + 16, f"{v}%", 11, GREY, "middle"))
        parts.append(line(xx(20), top - 4, xx(20), bot, GREY, 1.2, "2,3"))
        parts.append(text(xx(20), top - 8, "even split 20%", 10, GREY, "middle"))
        for i, (name, n, pct) in enumerate(rows):
            y = top + i * row_h
            col = RED if (red_first and i == 0) else BLUE
            parts.append(rect(px0, y + 8, xx(pct) - px0, row_h - 16, col))
            parts.append(text(px0 - 8, y + row_h / 2 + 4, name, 12, INK, "end"))
            parts.append(text(xx(pct) + 6, y + row_h / 2 + 4, f"{pct:.2f}%  ({n})", 11.5, INK, "start", "bold"))
        parts.append(text((px0 + px1) / 2, bot + 36, f"Share of 2025 shipments; counts sum to "
                          f"{sum(r[1] for r in rows):,}", 11.5, GREY, "middle"))

    panel(150, 440, CONC_ACCOUNT, "By account", True)
    panel(640, 930, CONC_HUB, "By origin hub", False)
    save("cfo-08-concentration.svg", parts)


if __name__ == "__main__":
    chart_ontime_by_quarter()
    chart_missed_by_account()
    chart_ontime_3yr_by_account()
    chart_cost_by_hub_category()
    chart_cost_vs_revenue()
    chart_credit_exposure()
    chart_equipment_accrual()
    chart_concentration()
