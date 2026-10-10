#!/usr/bin/env python3
"""Generate the company-profile charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible without the
warehouse. Every number comes from an execute_sql query against
hive_metastore.dbt_smcintyre_jaffle_logistics_prod; the SQL is in the appendix of
reports/company-profile.md (query numbers are noted beside each data block).

Output: reports/assets/company/company-*.svg  (committed alongside the report).

Design rules (match scripts/persona_fleet_charts.py):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar;
  * the 97% contractual on-time target drawn as a dashed, labelled reference line;
  * consistent colour meaning: red = the concentration / the account in trouble,
    grey-blue ramp = years, neutral blue = a series with no judgement attached.

Run from the repo root:  python3 scripts/company_profile_charts.py
"""
import os
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "company")

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # the largest account / the account in trouble
BLUE = "#2c6fbb"     # neutral series
GREY = "#555555"
GRID = "#d9d9d9"
INK = "#1a1a1a"
LIGHT = "#9aa7b5"
MID = "#5b7fa6"
BAND = "#eef1f5"
YEAR_COLS = [(LIGHT, "2023"), (MID, "2024"), (BLUE, "2025")]

FONT = "Helvetica, Arial, sans-serif"

SLA_TARGET = 97.0    # Q2 — contractual on-time target for the two strategic accounts


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from execute_sql)
# Q7 — CONCENTRATION_2025: client, name, gross revenue $, credits $, shipments, $ per shipment
CONCENTRATION_2025 = [
    ("CLI-0042", "Jaffle Equipment", 963695.00, 51269.00, 416, 2316.57),
    ("CLI-0201", "Jaffle Paper & Packaging", 524260.00, 0.00, 414, 1266.33),
    ("CLI-0169", "Jaffle Beverage Co", 487795.00, 383.88, 394, 1238.06),
    ("CLI-0155", "Jaffle Crew Outfitters", 458802.00, 0.00, 398, 1152.77),
    ("CLI-0007", "Jaffle Storefronts", 445180.00, 1301.98, 387, 1150.34),
]

# Q8 — BY_ACCOUNT: client, name, (on-time % 2023, 2024, 2025), (shipments 2023, 2024, 2025)
BY_ACCOUNT = [
    ("CLI-0007", "Jaffle Storefronts", (97.74, 97.04, 96.64), (354, 371, 387)),
    ("CLI-0042", "Jaffle Equipment", (97.77, 97.96, 83.89), (359, 392, 416)),
    ("CLI-0155", "Jaffle Crew Outfitters", (97.64, 97.09, 96.98), (382, 378, 398)),
    ("CLI-0169", "Jaffle Beverage Co", (97.26, 96.73, 94.67), (329, 398, 394)),
    ("CLI-0201", "Jaffle Paper & Packaging", (97.17, 97.32, 94.69), (424, 410, 414)),
]
BOOK_ONTIME = (97.51, 97.23, 93.28)


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


# ---------------------------------------------------------------- chart 1: 2025 revenue concentration
def chart_concentration():
    rows = sorted(CONCENTRATION_2025, key=lambda r: -r[2])
    total = sum(r[2] for r in rows)
    W, H = 960, 430
    x0, x1 = 260, 820
    top = 95
    row_h = 50
    bot = top + row_h * len(rows)
    vmax = 1000000
    parts = canvas(W, H, "2025 gross revenue by account: one account is a third of the book",
                   f"fct_account_revenue, 2025. Five accounts sum to ${total:,.0f}. "
                   "Label at bar end = share of the 2025 book.")

    def xx(v):
        return x0 + v / vmax * (x1 - x0)

    for v in range(0, vmax + 1, 200000):
        parts.append(line(xx(v), top - 6, xx(v), bot, GRID, 1))
        parts.append(text(xx(v), bot + 16, f"${v//1000}k", 11, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 36, "2025 gross revenue (USD)", 12, GREY, "middle"))
    for i, (cid, name, gross, cred, ships, per) in enumerate(rows):
        y = top + i * row_h
        col = RED if i == 0 else MID
        parts.append(rect(x0, y + 10, xx(gross) - x0, row_h - 20, col))
        parts.append(text(x0 - 10, y + row_h / 2, name, 12.5, RED if i == 0 else INK, "end",
                          "bold" if i == 0 else "normal"))
        parts.append(text(x0 - 10, y + row_h / 2 + 14, cid, 10.5, GREY, "end"))
        parts.append(halo(x0 + 8, y + row_h / 2 + 4, f"${gross:,.0f}", 11, INK, "start"))
        parts.append(text(xx(gross) + 8, y + row_h / 2 + 5, f"{100 * gross / total:.2f}%", 13,
                          RED if i == 0 else INK, "start", "bold"))
    rest = total - rows[0][2]
    parts.append(text(x0, H - 14, f"Other four accounts together: ${rest:,.0f} "
                      f"({100 * rest / total:.2f}%). Gross revenue, not profit: no margin exists in the data.",
                      11, GREY))
    save("company-01-concentration.svg", parts)


# ---------------------------------------------------------------- chart 2: on-time by account, 3 years
def chart_ontime_3yr():
    W, H = 980, 520
    x0, x1 = 90, 860
    top, bot = 100, 420
    vmin, vmax = 80, 100
    parts = canvas(W, H, "On-time delivery by account, 2023 / 2024 / 2025",
                   "stg_shipments: delivered ÷ all shipments created that year. "
                   "Axis starts at 80% so the gaps are visible.")
    y_gridlines(parts, x0, x1, top, bot, vmin, vmax, range(vmin, vmax + 1, 5), lambda v: f"{v}%")
    y_title(parts, 40, top, bot, "On-time (% of shipments)")

    def yy(v):
        return bot - (v - vmin) / (vmax - vmin) * (bot - top)

    group_w = (x1 - x0) / len(BY_ACCOUNT)
    bar_w = group_w * 0.24
    for i, (cid, name, pcts, ships) in enumerate(BY_ACCOUNT):
        gx = x0 + i * group_w + group_w * 0.12
        for j, val in enumerate(pcts):
            bx = gx + j * (bar_w + 4)
            col = RED if (j == 2 and val < 90) else YEAR_COLS[j][0]
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), col))
            parts.append(halo(bx + bar_w / 2, yy(val) - 5, f"{val:.2f}", 10, RED if col == RED else INK,
                              "middle", "bold" if col == RED else "normal"))
        cx = x0 + i * group_w + group_w / 2
        parts.append(text(cx, bot + 20, name, 12, INK, "middle"))
        parts.append(text(cx, bot + 36, f"{cid} · {ships[2]} ships in 2025", 10.5, GREY, "middle"))
    parts.append(line(x0, yy(SLA_TARGET), x1, yy(SLA_TARGET), INK, 1.5, "6,4"))
    parts.append(text(x1 + 8, yy(SLA_TARGET) - 2, "97% target", 11, INK, "start", "bold"))
    parts.append(text(x1 + 8, yy(SLA_TARGET) + 12, "(strategic SLA)", 10.5, GREY))
    legend(parts, x0, 76, [(LIGHT, "2023"), (MID, "2024"), (BLUE, "2025"), (RED, "2025, below 90%")], step=130)
    parts.append(text((x0 + x1) / 2, H - 30,
                      f"Whole book: {BOOK_ONTIME[0]:.2f}% / {BOOK_ONTIME[1]:.2f}% / {BOOK_ONTIME[2]:.2f}%.",
                      11, INK, "middle", "bold"))
    parts.append(text((x0 + x1) / 2, H - 12,
                      "Contract targets differ: 97% (CLI-0042, CLI-0007), 95% (CLI-0155, CLI-0169), 92% (CLI-0201).",
                      11, GREY, "middle"))
    save("company-02-ontime-3yr.svg", parts)


# ---------------------------------------------------------------- chart 3: value per shipment
def chart_value_per_shipment():
    rows = sorted(CONCENTRATION_2025, key=lambda r: -r[5])
    tot_rev = sum(r[2] for r in rows)
    tot_ship = sum(r[4] for r in rows)
    rest_per = (tot_rev - rows[0][2]) / (tot_ship - rows[0][4])
    W, H = 1000, 450
    row_h = 52
    top = 125
    bot = top + row_h * len(rows)
    parts = canvas(W, H, "2025: the largest account pays about twice as much per shipment",
                   "fct_account_revenue, 2025. Left: gross revenue ÷ shipments. "
                   "Right: the same account's share of shipments vs share of revenue.")
    # left panel — $ per shipment
    x0, x1 = 230, 560
    vmax = 2500

    def xx(v):
        return x0 + v / vmax * (x1 - x0)

    for v in range(0, vmax + 1, 500):
        parts.append(line(xx(v), top - 6, xx(v), bot, GRID, 1))
        parts.append(text(xx(v), bot + 16, f"${v:,}", 11, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 36, "Gross revenue per shipment (USD)", 12, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, top - 22, "Revenue per shipment", 13, INK, "middle", "bold"))
    for i, (cid, name, gross, cred, ships, per) in enumerate(rows):
        y = top + i * row_h
        col = RED if i == 0 else MID
        parts.append(rect(x0, y + 12, xx(per) - x0, row_h - 24, col))
        parts.append(text(x0 - 10, y + row_h / 2, name, 12, RED if i == 0 else INK, "end",
                          "bold" if i == 0 else "normal"))
        parts.append(text(x0 - 10, y + row_h / 2 + 14, f"{cid} · {ships} ships", 10.5, GREY, "end"))
        parts.append(text(xx(per) + 6, y + row_h / 2 + 4, f"${per:,.2f}", 11.5,
                          RED if i == 0 else INK, "start", "bold"))
    parts.append(line(xx(rest_per), top - 8, xx(rest_per), bot, INK, 1.5, "6,4"))
    parts.append(text(xx(rest_per) + 4, bot - 4, f"other four: ${rest_per:,.2f}", 10.5, INK, "start", "bold"))
    # right panel — share of shipments vs share of revenue
    px0, px1 = 660, 940
    smax = 40

    def sx_(v):
        return px0 + v / smax * (px1 - px0)

    for v in range(0, smax + 1, 10):
        parts.append(line(sx_(v), top - 6, sx_(v), bot, GRID, 1))
        parts.append(text(sx_(v), bot + 16, f"{v}%", 11, GREY, "middle"))
    parts.append(text((px0 + px1) / 2, bot + 36, "Share of 2025 total (%)", 12, GREY, "middle"))
    parts.append(text((px0 + px1) / 2, top - 22, "Share of shipments vs revenue", 13, INK, "middle", "bold"))
    for i, (cid, name, gross, cred, ships, per) in enumerate(rows):
        y = top + i * row_h
        s_ship = 100 * ships / tot_ship
        s_rev = 100 * gross / tot_rev
        parts.append(text(px0 - 8, y + row_h / 2 + 4, cid[4:], 10.5, GREY, "end"))
        parts.append(rect(px0, y + 10, sx_(s_ship) - px0, 13, LIGHT))
        parts.append(text(sx_(s_ship) + 5, y + 21, f"{s_ship:.2f}%", 10.5, GREY))
        parts.append(rect(px0, y + 26, sx_(s_rev) - px0, 13, RED if i == 0 else MID))
        parts.append(text(sx_(s_rev) + 5, y + 37, f"{s_rev:.2f}%", 10.5, RED if i == 0 else INK,
                          "start", "bold" if i == 0 else "normal"))
    legend(parts, px0, 78, [(LIGHT, "shipments"), (MID, "revenue")], step=110)
    parts.append(text(x0, H - 12, f"Five accounts: ${tot_rev:,.0f} on {tot_ship:,} shipments. "
                      "Gross revenue, not profit: there is no per-account cost or margin.", 11, GREY))
    save("company-03-value-per-shipment.svg", parts)


if __name__ == "__main__":
    chart_concentration()
    chart_ontime_3yr()
    chart_value_per_shipment()
