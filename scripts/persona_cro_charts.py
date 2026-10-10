#!/usr/bin/env python3
"""Generate the Chief Revenue Officer persona-report charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results embedded below, so each figure is reproducible without the
warehouse. Every literal comes from an execute_sql query whose SQL is copied
into the appendix of reports/persona-cro.md (labels Q3, Q4, Q5d, Q6, Q7).

Output: reports/assets/personas/cro-*.svg  (committed alongside the report).

Design rules (match scripts/persona_cx_charts.py, but sober: greys + one accent):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every bar or dot;
  * reference lines labelled where they are drawn;
  * one accent colour (red) for the contractual line and for money lost to credits.

Run from the repo root:  python3 scripts/persona_cro_charts.py
"""
import os
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "personas")
TARGET = 97.0  # whole-book contractual on-time yardstick, %

# ---------------------------------------------------------------- colours
ACCENT = "#c0392b"   # the one accent: contractual line, credited money
INK = "#1a1a1a"
GREY = "#555555"
GRID = "#d9d9d9"
G1 = "#c4c4c4"       # 2023
G2 = "#8c8c8c"       # 2024
G3 = "#3d3d3d"       # 2025
YEAR_COLS = [(G1, "2023"), (G2, "2024"), (G3, "2025")]

FONT = "Helvetica, Arial, sans-serif"


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data (from the queries)
# (client_id, short name) in client-id order
ACCOUNTS = [
    ("CLI-0007", "Storefronts"),
    ("CLI-0042", "Equipment"),
    ("CLI-0155", "Crew Outfitters"),
    ("CLI-0169", "Beverage Co"),
    ("CLI-0201", "Paper & Packaging"),
]
NAME = dict(ACCOUNTS)

# Q3 — on-time % by account by year (stg_shipments, status = 'delivered')
ONTIME = {
    "CLI-0007": (97.74, 97.04, 96.64),
    "CLI-0042": (97.77, 97.96, 83.89),
    "CLI-0155": (97.64, 97.09, 96.98),
    "CLI-0169": (97.26, 96.73, 94.67),
    "CLI-0201": (97.17, 97.32, 94.69),
}
# Q2 — SLA on-time target in force through 2025 (stg_contracts)
SLA = {"CLI-0007": 97.0, "CLI-0042": 97.0, "CLI-0155": 95.0, "CLI-0169": 95.0, "CLI-0201": 92.0}

# Q5d — 2025 gross revenue, credited amount as recorded in the ledger (trailing-12-month basis),
# and the calendar-month cross-check credit (fct_account_revenue)
GROSS_2025 = {"CLI-0007": 445180.00, "CLI-0042": 963695.00, "CLI-0155": 458802.00,
              "CLI-0169": 487795.00, "CLI-0201": 524260.00}
CREDITED_2025 = {"CLI-0007": 1301.98, "CLI-0042": 51269.00, "CLI-0155": 0.00,
                 "CLI-0169": 383.88, "CLI-0201": 0.00}
CALENDAR_XCHECK_2025 = {"CLI-0007": 6081.00, "CLI-0042": 80948.80, "CLI-0155": 4397.75,
                        "CLI-0169": 7768.98, "CLI-0201": 3402.35}
BOOK_GROSS_2025 = 2879732.00
BOOK_CREDITED_2025 = 52954.86

# Q6 — 2025 share of shipments (stg_shipments)
SHIP_SHARE_2025 = {"CLI-0007": 19.26, "CLI-0042": 20.71, "CLI-0155": 19.81,
                   "CLI-0169": 19.61, "CLI-0201": 20.61}

# Q7 — tickets by account by year (stg_support_tickets joined to eval_ticket_triage)
TICKETS = {
    "CLI-0007": (29, 16, 23),
    "CLI-0042": (17, 17, 72),
    "CLI-0155": (19, 17, 24),
    "CLI-0169": (19, 30, 35),
    "CLI-0201": (23, 27, 35),
}

# Q7 — 2025 CSAT distribution: counts of score 1..5, then no score (null)
CSAT_2025 = {
    "CLI-0007": (4, 1, 0, 5, 11, 2),
    "CLI-0042": (19, 16, 4, 6, 20, 7),
    "CLI-0155": (0, 2, 2, 8, 9, 3),
    "CLI-0169": (2, 2, 5, 6, 19, 1),
    "CLI-0201": (2, 3, 5, 4, 18, 3),
}
CSAT_AVG_2025 = {"CLI-0007": 3.86, "CLI-0042": 2.88, "CLI-0155": 4.14, "CLI-0169": 4.12, "CLI-0201": 4.03}


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


def account_labels(parts, cx, bot, cid, name):
    parts.append(text(cx, bot + 20, name, 12, INK, "middle"))
    parts.append(text(cx, bot + 36, cid, 10.5, GREY, "middle"))


def year_legend(parts, x, y):
    for col, lab in YEAR_COLS:
        parts.append(rect(x, y - 10, 14, 12, col))
        parts.append(text(x + 20, y, lab, 12, INK))
        x += 80
    return x


def money(v):
    return f"${v:,.0f}"


# ---------------------------------------------------------------- chart 1: on-time, 3 years, vs SLA
def chart_ontime():
    W, H = 960, 540
    x0, x1 = 100, 920
    top, bot = 100, 420
    vmin, vmax = 80, 100
    parts = canvas(W, H, "On-time rate by account, 2023 / 2024 / 2025, against contract",
                   "stg_shipments, on time = status 'delivered'. Red dashed = 97% whole-book yardstick; "
                   "black bar = the account's own SLA.")
    y_gridlines(parts, x0, x1, top, bot, vmin, vmax, [80, 85, 90, 95, 100], lambda v: f"{v}%")
    y_title(parts, 40, top, bot, "Shipments delivered on time (%)")
    parts.append(text(x0 - 8, bot + 14, "(axis starts at 80%)", 9.5, GREY, "end"))

    def yy(v):
        return bot - (v - vmin) / (vmax - vmin) * (bot - top)

    group_w = (x1 - x0) / len(ACCOUNTS)
    bar_w = group_w * 0.22
    labels = []
    for i, (cid, name) in enumerate(ACCOUNTS):
        gx = x0 + i * group_w + group_w * 0.14
        for j, val in enumerate(ONTIME[cid]):
            bx = gx + j * (bar_w + 4)
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), YEAR_COLS[j][0]))
            labels.append((bx + bar_w / 2, yy(val) - 5, f"{val:.1f}"))
        # the account's own SLA, drawn across its group
        sx0, sx1 = gx - 6, gx + 3 * bar_w + 8 + 6
        parts.append(line(sx0, yy(SLA[cid]), sx1, yy(SLA[cid]), INK, 3))
        account_labels(parts, x0 + i * group_w + group_w / 2, bot, cid, name)
        parts.append(text(x0 + i * group_w + group_w / 2, bot + 52, f"SLA {SLA[cid]:.0f}%", 11, INK,
                          "middle", "bold"))
    yt = yy(TARGET)
    parts.append(line(x0, yt, x1, yt, ACCENT, 1.5, "6,4"))
    for lx_, ly_, s in labels:
        parts.append(text(lx_, ly_, s, 10, INK, "middle", halo=True))
    lx = year_legend(parts, x0, 76)
    parts.append(line(lx, 72, lx + 24, 72, ACCENT, 1.5, "6,4"))
    parts.append(text(lx + 30, 76, "97% whole-book yardstick", 12, ACCENT, "start", "bold"))
    parts.append(line(lx + 220, 72, lx + 244, 72, INK, 3))
    parts.append(text(lx + 250, 76, "account's own SLA (2025)", 12, INK))
    parts.append(text((x0 + x1) / 2, H - 10, "Account (Jaffle Logistics)", 12, GREY, "middle"))
    save("cro-01-ontime-3yr-by-account.svg", parts)


# ---------------------------------------------------------------- chart 2: % of spend credited, ranked
def chart_spend_at_risk():
    W, H = 960, 440
    x0, x1 = 230, 860
    top, bot = 100, 360
    vmax = 10.0
    rows = sorted(ACCOUNTS, key=lambda a: (-CREDITED_2025[a[0]] / GROSS_2025[a[0]], a[0]))
    parts = canvas(W, H, "2025 service credits as % of each account's gross revenue",
                   "Solid = credited_amount recorded in fct_account_revenue (trailing-12-month basis). "
                   "Open = calendar-month cross-check.")
    for v in range(0, 11, 2):
        xx = x0 + v / vmax * (x1 - x0)
        parts.append(line(xx, top - 6, xx, bot, GRID, 1))
        parts.append(text(xx, bot + 18, f"{v}%", 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 42, "Credited as % of 2025 gross revenue", 12, GREY, "middle"))
    row_h = (bot - top) / len(rows)
    for i, (cid, name) in enumerate(rows):
        y = top + i * row_h
        pct = 100 * CREDITED_2025[cid] / GROSS_2025[cid]
        xpct = 100 * CALENDAR_XCHECK_2025[cid] / GROSS_2025[cid]
        h = row_h * 0.36
        parts.append(rect(x0, y + row_h * 0.12, max(pct / vmax * (x1 - x0), 1.5), h, ACCENT))
        parts.append(text(x0 + max(pct / vmax * (x1 - x0), 1.5) + 8, y + row_h * 0.12 + h * 0.75,
                          f"{pct:.2f}%  ·  {money(CREDITED_2025[cid])} recorded", 12, INK, "start", "bold"))
        yb = y + row_h * 0.12 + h + 3
        hb = row_h * 0.24
        parts.append(rect(x0, yb, xpct / vmax * (x1 - x0), hb, "none", G2, 1.2))
        parts.append(text(x0 + xpct / vmax * (x1 - x0) + 8, yb + hb * 0.8,
                          f"{xpct:.2f}%  ·  {money(CALENDAR_XCHECK_2025[cid])} cross-check", 10.5, GREY))
        parts.append(text(x0 - 10, y + row_h * 0.42, name, 12.5, INK, "end"))
        parts.append(text(x0 - 10, y + row_h * 0.42 + 15, cid, 10.5, GREY, "end"))
    book = 100 * BOOK_CREDITED_2025 / BOOK_GROSS_2025
    xb = x0 + book / vmax * (x1 - x0)
    parts.append(line(xb, top - 12, xb, bot, INK, 1.2, "3,3"))
    parts.append(text(xb + 4, top - 14, f"whole book {book:.2f}% ({money(BOOK_CREDITED_2025)})", 11, INK))
    save("cro-02-spend-at-risk-by-account.svg", parts)


# ---------------------------------------------------------------- chart 3: tickets by account by year
def chart_tickets():
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
            col = ACCENT if (cid == "CLI-0042" and j == 2) else YEAR_COLS[j][0]
            parts.append(rect(bx, yy(val), bar_w, bot - yy(val), col))
            parts.append(text(bx + bar_w / 2, yy(val) - 5, str(val), 11, INK, "middle"))
        account_labels(parts, x0 + i * group_w + group_w / 2, bot, cid, name)
    year_legend(parts, x0, 72)
    parts.append(text(x0 + 250, 72, "(Equipment 2025 in red: the only year-on-year break)", 11.5, ACCENT))
    parts.append(text((x0 + x1) / 2, H - 10, "Account (Jaffle Logistics)", 12, GREY, "middle"))
    save("cro-03-ticket-volume-by-account-year.svg", parts)


# ---------------------------------------------------------------- chart 4: CSAT dot plot, 2025
def chart_csat():
    W, H = 960, 470
    x0, x1 = 230, 820
    top, bot = 110, 390
    cols = ["1", "2", "3", "4", "5", "no score"]
    parts = canvas(W, H, "2025 CSAT by account: how many tickets got each score",
                   "stg_support_tickets.csat, tickets opened in 2025. Dot area is proportional to the count; "
                   "'no score' = CSAT null.")
    col_w = (x1 - x0) / len(cols)
    row_h = (bot - top) / len(ACCOUNTS)
    for k, c in enumerate(cols):
        cx = x0 + (k + 0.5) * col_w
        parts.append(text(cx, top - 14, c, 12.5, INK if k < 5 else GREY, "middle", "bold"))
        parts.append(line(cx, top - 4, cx, bot, GRID, 1))
    parts.append(text((x0 + x0 + 5 * col_w) / 2, top - 34, "CSAT score (1 = worst, 5 = best)", 12, GREY, "middle"))
    parts.append(line(x0 + 5 * col_w, top - 30, x0 + 5 * col_w, bot, G2, 1, "3,3"))
    parts.append(text(x1 + 70, top - 14, "avg", 12.5, INK, "middle", "bold"))
    vmax = 20
    rmax = row_h * 0.46
    for i, (cid, name) in enumerate(ACCOUNTS):
        cy = top + (i + 0.5) * row_h
        parts.append(line(x0, cy, x1, cy, GRID, 1))
        parts.append(text(x0 - 10, cy, name, 12.5, INK, "end"))
        parts.append(text(x0 - 10, cy + 15, f"{cid} · {sum(CSAT_2025[cid])} tickets", 10.5, GREY, "end"))
        for k, n in enumerate(CSAT_2025[cid]):
            cx = x0 + (k + 0.5) * col_w
            if n == 0:
                parts.append(text(cx, cy + 4, "0", 11, G2, "middle"))
                continue
            r = rmax * (n / vmax) ** 0.5
            fill = "none" if k == 5 else (ACCENT if k < 2 else G3)
            stroke = G2 if k == 5 else "none"
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" '
                         f'fill-opacity="0.85" stroke="{stroke}" stroke-width="1.2"/>')
            parts.append(text(cx + r + 4, cy + 4, str(n), 11, INK, "start", "bold", halo=True))
        parts.append(text(x1 + 70, cy + 4, f"{CSAT_AVG_2025[cid]:.2f}", 12.5,
                          ACCENT if CSAT_AVG_2025[cid] < 3.5 else INK, "middle", "bold"))
    parts.append(text(x0, H - 14, "Red = scores 1–2 (dissatisfied). Grey = 3–5. Open circle = ticket with no score.",
                      11, GREY))
    save("cro-04-csat-by-account.svg", parts)


# ---------------------------------------------------------------- chart 5: revenue and credit
def chart_revenue_and_credit():
    W, H = 960, 440
    x0, x1 = 230, 820
    top, bot = 90, 360
    vmax = 1000000
    rows = sorted(ACCOUNTS, key=lambda a: -GROSS_2025[a[0]])
    parts = canvas(W, H, "2025 gross revenue by account, with the service credits taken out of it",
                   "fct_account_revenue, 2025. Grey = net revenue kept; red = credited_amount. "
                   "Right column = share of 2025 shipments.")
    for v in range(0, vmax + 1, 200000):
        xx = x0 + v / vmax * (x1 - x0)
        parts.append(line(xx, top - 6, xx, bot, GRID, 1))
        parts.append(text(xx, bot + 18, f"${v // 1000:,}k", 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 42, "2025 gross revenue (USD)", 12, GREY, "middle"))
    parts.append(text(x1 + 70, top - 12, "ship share", 11.5, GREY, "middle", "bold"))
    row_h = (bot - top) / len(rows)
    for i, (cid, name) in enumerate(rows):
        y = top + i * row_h + row_h * 0.2
        h = row_h * 0.6
        g, c = GROSS_2025[cid], CREDITED_2025[cid]
        wn = (g - c) / vmax * (x1 - x0)
        wc = c / vmax * (x1 - x0)
        parts.append(rect(x0, y, wn, h, G2))
        if c > 0:
            parts.append(rect(x0 + wn, y, max(wc, 1.5), h, ACCENT))
        share = 100 * g / BOOK_GROSS_2025
        lab = f"{money(g)} · {share:.1f}% of revenue"
        if c > 0:
            lab += f" · {money(c)} credited"
        if wn > 0.6 * (x1 - x0):  # long bar: label inside it, so it does not run into the share column
            parts.append(text(x0 + wn - 8, y + h * 0.65, lab, 11.5, "#ffffff", "end", "bold"))
        else:
            parts.append(text(x0 + wn + wc + 6, y + h * 0.65, lab, 11.5, INK, "start", "bold"))
        parts.append(text(x0 - 10, y + h * 0.45, name, 12.5, INK, "end"))
        parts.append(text(x0 - 10, y + h * 0.45 + 15, cid, 10.5, GREY, "end"))
        parts.append(text(x1 + 70, y + h * 0.65, f"{SHIP_SHARE_2025[cid]:.1f}%", 12, INK, "middle"))
    save("cro-05-revenue-and-credit-by-account.svg", parts)


if __name__ == "__main__":
    chart_ontime()
    chart_spend_at_risk()
    chart_tickets()
    chart_csat()
    chart_revenue_and_credit()
