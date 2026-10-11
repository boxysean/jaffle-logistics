#!/usr/bin/env python3
"""Generate the Head of Data persona report charts as dependency-free SVG.

No charting library is used (none is installed and package installation is
blocked on this box). Every chart is emitted as plain SVG text markup built from
the query results and repository counts embedded below, so each figure is
reproducible from reports/persona-data.md's appendix queries.

Output: reports/assets/personas/data-*.svg  (committed alongside the report).

Design rules (house style, as scripts/cfo_charts.py and scripts/persona_fleet_charts.py):
  * no 3-D, no gradients, no chart junk;
  * every axis labelled with its unit;
  * value printed on or beside every mark;
  * the 97% contractual on-time target drawn as a dashed reference line on any rate chart;
  * consistent colour meaning: red = below target / stale / broken, green = at or above
    target, neutral blue = a series with no target of its own.

Source of every warehouse number: hive_metastore.dbt_smcintyre_jaffle_logistics_prod,
via the dbt Platform remote MCP `execute_sql` tool (production still holds the pre-pivot
labels; quantities are identical to main's re-skinned seeds). Repository counts (seeds,
tests, models) were read from the files on main. The dataset's present is 2025-12-31.

Run from the repo root:  python3 scripts/persona_data_charts.py
"""
import math
import os
import xml.sax.saxutils as sx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "assets", "personas")
TARGET = 97.0  # whole-book contractual on-time reference line, %

# ---------------------------------------------------------------- colours
RED = "#c0392b"      # below target / stale / broken
GREEN = "#2e7d32"    # at or above target
BLUE = "#2c6fbb"     # neutral series
LIGHT_BLUE = "#a9c4e6"
GREY = "#555555"
LIGHT_GREY = "#bdbdbd"
GRID = "#d9d9d9"
INK = "#1a1a1a"

FONT = "Helvetica, Arial, sans-serif"


def esc(s):
    return sx.escape(str(s))


# ---------------------------------------------------------------- data
# Q1 (E1) whole-book on-time by year, and Q2 (E2) CLI-0042 on-time by year
YEARS = ["2023", "2024", "2025"]
BOOK = {"2023": (1848, 46, 97.51), "2024": (1949, 54, 97.23), "2025": (2009, 135, 93.28)}  # n, missed, %
EQUIPMENT = {"2023": 97.77, "2024": 97.96, "2025": 83.89}

# The volume artefact: shipments per year as published (pre-revision seed) vs the warehouse now (Q1)
PUBLISHED_SHIPMENTS = {"2023": 2009, "2024": 2009, "2025": 2009}
# Q3 (E3) shipments per quarter, warehouse now; the published reports gave 486/435/492/596 for every year
QUARTERS_NOW = {"2023": [447, 400, 452, 549], "2024": [472, 422, 477, 578], "2025": [486, 435, 492, 596]}

# Source coverage: the 24 seeds (repository) x staged / semantic layer / search corpus.
#   semantic: 2 = measured grain of a semantic model, 1 = reaches it only as a joined
#             attribute or touchpoint count, 0 = never
#   corpus:   rows in knowledge_base (Q8), or "key" = supplies the account key only, or None
COVERAGE = [
    # seed, staged, semantic, corpus
    ("call_transcripts", True, 1, 69),
    ("clients", True, 1, None),
    ("contracts", True, 1, None),
    ("cost_ledger", True, 0, None),
    ("crm_notes", True, 1, 58),
    ("dispatch_notes", True, 1, 1299),
    ("dock_bay_events", True, 0, None),
    ("drivers", True, 0, None),
    ("eval_crm_sentiment", False, 0, None),
    ("eval_ticket_triage", False, 0, None),
    ("fleet_work_orders", True, 0, None),
    ("hr_docs", True, 0, None),
    ("hubs", True, 1, None),
    ("incident_reports", True, 1, 716),
    ("incidents", True, 1, "key"),
    ("legal_docs", True, 0, 35),
    ("payroll_monthly", True, 0, None),
    ("revenue_ledger", True, 2, None),
    ("route_client_attribution", True, 0, "key"),
    ("routes", True, 0, None),
    ("shipments", True, 2, "key"),
    ("slack_threads", True, 0, 116),
    ("support_tickets", True, 1, 403),
    ("vehicles", True, 0, None),
]

# Test coverage by model layer (counted from models/**/_*.yml and tests/*.sql on main)
#   layer, model files, generic (YAML) tests, singular tests, gated by ai_functions_enabled
TESTS = [
    ("staging", 22, 158, 9, False),
    ("intermediate", 2, 6, 0, False),
    ("marts", 8, 31, 0, False),
    ("context (pre-AI)", 25, 45, 2, False),
    ("context / ai", 23, 23, 1, True),
    ("utilities", 1, 2, 0, False),
]

# AI layer lineage: the seven per-source chains (models/context/ai/_context_ai.yml, knowledge_base.sql)
#   seed, prep chain (models/context/), knowledge_base rows (Q8)
CHAINS = [
    ("legal_docs", "int_legal_docs_documents → split → chunk → chunks_meta", 35),
    ("incident_reports", "int_incident_reports_documents → split → chunk → chunks_meta", 716),
    ("crm_notes", "int_crm_notes_documents → split → chunk → chunks_meta", 58),
    ("call_transcripts", "int_transcript_turns → chunk_transcripts → transcript_chunks_meta", 69),
    ("support_tickets", "ticket_records_meta (whole record)", 403),
    ("dispatch_notes", "dispatch_notes_records_meta (whole record)", 1299),
    ("slack_threads", "slack_threads_records_meta (whole record)", 116),
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


def rect(x, y, w, h, fill, stroke="none", sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def arrow(x1, y1, x2, y2, color=GREY, w=1.2):
    """Straight connector with a small filled arrowhead at (x2, y2)."""
    ang = math.atan2(y2 - y1, x2 - x1)
    hx1 = x2 - 7 * math.cos(ang - 0.4)
    hy1 = y2 - 7 * math.sin(ang - 0.4)
    hx2 = x2 - 7 * math.cos(ang + 0.4)
    hy2 = y2 - 7 * math.sin(ang + 0.4)
    return (line(x1, y1, x2, y2, color, w) +
            f'<polygon points="{x2:.1f},{y2:.1f} {hx1:.1f},{hy1:.1f} {hx2:.1f},{hy2:.1f}" fill="{color}"/>')


def box(x, y, w, h, label, fill="#ffffff", stroke=GREY, size=11, color=INK, weight="normal", dash=None):
    return (rect(x, y, w, h, fill, stroke, 1.2, dash) +
            text(x + w / 2, y + h / 2 + size * 0.36, label, size, color, "middle", weight))


def save(name, parts):
    parts.append("</svg>")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print("wrote", os.path.relpath(path, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))


# ---------------------------------------------------------------- chart 1: on-time by year
def chart_ontime_by_year():
    W, H = 860, 500
    x0, x1 = 90, 700
    y_top, y_bot = 80, 400
    vmin, vmax = 80, 100
    parts = canvas(W, H, "On-time delivery by year, 2023 → 2025",
                   "Whole book vs CLI-0042 (Jaffle Werke). Dashed line = 97% contractual target.")

    def yy(v):
        return y_bot - (v - vmin) / (vmax - vmin) * (y_bot - y_top)

    for v in range(vmin, vmax + 1, 5):
        parts.append(line(x0, yy(v), x1, yy(v), GRID, 1))
        parts.append(text(x0 - 8, yy(v) + 4, f"{v}%", 11.5, GREY, "end"))
    parts.append(text(28, (y_top + y_bot) / 2, "On-time shipments (% delivered)", 12, GREY,
                      "middle", rotate=-90))
    parts.append(line(x0, yy(TARGET), x1, yy(TARGET), RED, 1.5, "6,4"))
    parts.append(text(x1 + 6, yy(TARGET) + 4, "97% target", 11.5, RED, "start", "bold"))

    step = (x1 - x0) / len(YEARS)
    xs = [x0 + step * (i + 0.5) for i in range(len(YEARS))]
    for i, y in enumerate(YEARS):
        n, missed, _pct = BOOK[y]
        parts.append(text(xs[i], y_bot + 22, y, 13, INK, "middle", "bold"))
        parts.append(text(xs[i], y_bot + 40, f"book: {n:,} shipped, {missed} missed", 11, GREY, "middle"))

    # book labels above its points, Werke labels below (the two sit ~4 px apart in 2023-24)
    series = [("Whole book", BLUE, [BOOK[y][2] for y in YEARS], -12),
              ("Jaffle Werke (CLI-0042)", RED, [EQUIPMENT[y] for y in YEARS], 28)]
    for name, color, vals, dy in series:
        pts = [(xs[i], yy(v)) for i, v in enumerate(vals)]
        parts.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
                     f'fill="none" stroke="{color}" stroke-width="2.6"/>')
        for (x, y), v in zip(pts, vals):
            dot = GREEN if v >= TARGET else RED
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{dot}" stroke="{color}" stroke-width="1.5"/>')
            parts.append(text(x, y + dy, f"{v:.2f}%", 12, color, "middle", "bold"))
    parts.append(line(x0, 64, x0 + 24, 64, BLUE, 3))
    parts.append(text(x0 + 30, 68, "Whole book", 12, INK))
    parts.append(line(x0 + 150, 64, x0 + 174, 64, RED, 3))
    parts.append(text(x0 + 180, 68, "Jaffle Werke (CLI-0042)", 12, INK))
    parts.append(text(x0 + 400, 68, "dot: green = at/above 97%, red = below", 11, GREY))
    parts.append(text(W / 2, H - 14, "Year of shipment created_at (stg_shipments, production)", 12, GREY, "middle"))
    save("data-01-ontime-by-year.svg", parts)


# ---------------------------------------------------------------- chart 2: coverage matrix
def chart_coverage():
    W = 900
    top = 110
    row_h = 22
    H = top + row_h * len(COVERAGE) + 140
    name_x = 250
    cols = [("Staged (stg_*)", 330), ("Semantic layer", 500), ("Search corpus (knowledge_base)", 700)]
    cw = 130
    parts = canvas(W, H, "Where each of the 24 seeds reaches",
                   "Staging model, dbt Semantic Layer, and the AI search corpus. Corpus cells print the row count in production.")
    for label, cx in cols:
        parts.append(text(cx, top - 14, label, 12.5, INK, "middle", "bold"))
    for i, (seed, staged, sem, corp) in enumerate(COVERAGE):
        y = top + i * row_h
        if i % 2 == 0:
            parts.append(rect(20, y, W - 40, row_h, "#f6f6f6"))
        parts.append(text(name_x, y + 15, seed, 12, INK, "end"))
        # staged
        cx = cols[0][1]
        if staged:
            parts.append(rect(cx - cw / 2 + 20, y + 3, cw - 40, row_h - 6, BLUE))
            parts.append(text(cx, y + 15, "yes", 11, "#ffffff", "middle", "bold"))
        else:
            parts.append(rect(cx - cw / 2 + 20, y + 3, cw - 40, row_h - 6, "#ffffff", RED, 1.2))
            parts.append(text(cx, y + 15, "no model", 11, RED, "middle", "bold"))
        # semantic
        cx = cols[1][1]
        if sem == 2:
            parts.append(rect(cx - cw / 2, y + 3, cw, row_h - 6, BLUE))
            parts.append(text(cx, y + 15, "measured (grain)", 11, "#ffffff", "middle", "bold"))
        elif sem == 1:
            parts.append(rect(cx - cw / 2, y + 3, cw, row_h - 6, LIGHT_BLUE))
            parts.append(text(cx, y + 15, "joined upstream", 11, INK, "middle"))
        else:
            parts.append(text(cx, y + 15, "—", 12, LIGHT_GREY, "middle"))
        # corpus
        cx = cols[2][1]
        if isinstance(corp, int):
            parts.append(rect(cx - cw / 2, y + 3, cw, row_h - 6, BLUE))
            parts.append(text(cx, y + 15, f"{corp:,} rows", 11, "#ffffff", "middle", "bold"))
        elif corp == "key":
            parts.append(rect(cx - cw / 2, y + 3, cw, row_h - 6, LIGHT_BLUE))
            parts.append(text(cx, y + 15, "account key only", 11, INK, "middle"))
        else:
            parts.append(text(cx, y + 15, "—", 12, LIGHT_GREY, "middle"))
        if seed.startswith("eval_"):
            parts.append(text(cols[2][1] + cw / 2 + 8, y + 15, "eval set only", 10.5, RED, "start"))
    yb = top + row_h * len(COVERAGE)
    staged_n = sum(1 for r in COVERAGE if r[1])
    grain_n = sum(1 for r in COVERAGE if r[2] == 2)
    joined_n = sum(1 for r in COVERAGE if r[2] == 1)
    corpus_n = sum(1 for r in COVERAGE if isinstance(r[3], int))
    key_n = sum(1 for r in COVERAGE if r[3] == "key")
    neither_n = sum(1 for r in COVERAGE if r[2] == 0 and r[3] is None)
    corpus_rows = sum(r[3] for r in COVERAGE if isinstance(r[3], int))
    parts.append(line(20, yb + 4, W - 20, yb + 4, GREY, 1))
    parts.append(text(name_x, yb + 24, "Totals (of 24)", 12, INK, "end", "bold"))
    parts.append(text(cols[0][1], yb + 24, f"{staged_n} staged", 12, INK, "middle", "bold"))
    parts.append(text(cols[1][1], yb + 24, f"{grain_n} measured + {joined_n} joined", 12, INK, "middle", "bold"))
    parts.append(text(cols[2][1], yb + 24, f"{corpus_n} text + {key_n} key ({corpus_rows:,} rows)", 12, INK, "middle", "bold"))
    parts.append(text(40, yb + 50, f"{neither_n} seeds reach neither the semantic layer nor the corpus "
                      "(cost ledger, payroll, drivers, vehicles, fleet work orders, HR docs, routes, dock events, two eval sets).", 11.5, INK))
    parts.append(text(40, yb + 70, "Dispatch notes and Slack threads ARE in the corpus: 1,299 + 116 rows. "
                      "The ‘known hole’ is closed.", 12, GREEN, weight="bold"))
    parts.append(text(40, yb + 90, "No seed is declared as a dbt source, so none has source freshness "
                      "monitoring (get_all_sources is empty).", 12, RED))
    parts.append(text(40, yb + 112, "Dark blue = yes / measured / text in corpus. Light blue = partial "
                      "(joined attribute, or account key only). — = not reached.", 11, GREY))
    save("data-02-source-coverage-matrix.svg", parts)


# ---------------------------------------------------------------- chart 3: tests by layer
def chart_tests():
    W, H = 960, 440
    x0, x1 = 210, 600
    top, bot = 80, 360
    vmax = 180
    parts = canvas(W, H, "Data tests by model layer",
                   "Generic (YAML) tests plus singular SQL tests in tests/, counted on main. Dashed outline = gated by ai_functions_enabled.")
    for v in range(0, vmax + 1, 30):
        xx = x0 + v / vmax * (x1 - x0)
        parts.append(line(xx, top, xx, bot, GRID, 1))
        parts.append(text(xx, bot + 18, str(v), 11.5, GREY, "middle"))
    parts.append(text((x0 + x1) / 2, bot + 40, "Number of tests (count)", 12, GREY, "middle"))
    n = len(TESTS)
    rh = (bot - top) / n
    for i, (layer, models, gen, sing, gated) in enumerate(TESTS):
        y = top + i * rh + rh * 0.18
        h = rh * 0.64
        wg = gen / vmax * (x1 - x0)
        ws = sing / vmax * (x1 - x0)
        if gated:
            parts.append(rect(x0, y, wg, h, "#ffffff", BLUE, 1.6, "5,3"))
        else:
            parts.append(rect(x0, y, wg, h, BLUE))
        if sing:
            parts.append(rect(x0 + wg, y, ws, h, "#173f6e"))
        parts.append(text(x0 - 10, y + h * 0.45, layer, 12.5, INK, "end", "bold"))
        parts.append(text(x0 - 10, y + h * 0.45 + 14, f"{models} model files", 10.5, GREY, "end"))
        total = gen + sing
        per = total / models
        label = f"{gen} generic + {sing} singular = {total}  ({per:.1f} per model)"
        if gated:
            label += "  — the 23 YAML tests run only with the AI gate on"
        parts.append(text(x0 + wg + ws + 8, y + h * 0.68, label, 11.5, RED if gated else INK))
    parts.append(rect(x0, 60, 14, 12, BLUE))
    parts.append(text(x0 + 20, 70, "generic (YAML)", 11.5, INK))
    parts.append(rect(x0 + 130, 60, 14, 12, "#173f6e"))
    parts.append(text(x0 + 150, 70, "singular (tests/*.sql)", 11.5, INK))
    total_all = sum(g + s for _l, _m, g, s, _x in TESTS)
    parts.append(text(W - 20, 70, f"Total: {total_all} tests", 12, INK, "end", "bold"))
    parts.append(text(40, H - 14, "Zero unit tests, zero model contracts, zero exposures anywhere in the project "
                      "(see dbt-best-practices-audit.md H1, M1).", 11.5, GREY))
    save("data-03-test-coverage-by-layer.svg", parts)


# ---------------------------------------------------------------- chart 4: AI layer lineage
def chart_lineage():
    W, H = 1320, 760
    top, rh = 120, 62
    parts = canvas(W, H, "The context / AI layer: seven chains into one search corpus",
                   "Seed → staging → prep → hash → (classify ‖ embed) → embedded_classified "
                   "→ knowledge_base. Dashed region is disabled unless ai_functions_enabled = true.")
    X = {"seed": 20, "stg": 165, "prep": 330, "hash": 650, "cls": 830, "emb": 830, "ec": 990, "kb": 1170}
    Wd = {"seed": 125, "stg": 140, "prep": 300, "hash": 150, "cls": 120, "emb": 120, "ec": 150, "kb": 130}
    heads = [("seed", "seeds/*.csv"), ("stg", "staging (view)"), ("prep", "models/context/ (view/table)"),
             ("hash", "*_hashed"), ("cls", "classify / embed"), ("ec", "*_embedded_classified"),
             ("kb", "corpus")]
    for k, label in heads:
        parts.append(text(X[k] + Wd[k] / 2, top - 22, label, 11.5, GREY, "middle", "bold"))
    # gate region
    gate_x0 = X["cls"] - 14
    gate_x1 = X["kb"] + Wd["kb"] + 14
    gate_y0 = top - 12
    gate_y1 = top + rh * len(CHAINS) + 70
    parts.append(rect(gate_x0, gate_y0, gate_x1 - gate_x0, gate_y1 - gate_y0, "#f5f9fd", BLUE, 1.4, "7,4"))
    parts.append(text(gate_x0 + 6, gate_y1 - 8, "gated: +enabled: var('ai_functions_enabled', false) "
                      "— real embed()/classify() spend; 23 YAML tests live here", 11, BLUE, "start", "bold"))
    bh = 22
    for i, (seed, prep, kb_rows) in enumerate(CHAINS):
        y = top + i * rh
        yc = y + bh / 2
        parts.append(box(X["seed"], y, Wd["seed"], bh, seed, "#eef5ee", "#7FA37F", 11))
        parts.append(box(X["stg"], y, Wd["stg"], bh, f"stg_{seed}", "#fbf2ea", "#D2955C", 11))
        parts.append(box(X["prep"], y, Wd["prep"], bh, prep, "#eef1f6", "#7C93B0", 10))
        parts.append(box(X["hash"], y, Wd["hash"], bh, f"{seed}_hashed", "#eef1f6", "#7C93B0", 10.5))
        parts.append(box(X["cls"], y - 6, Wd["cls"], 17, "_classify (table)", "#e9f3f3", "#7FAFAF", 9.5))
        parts.append(box(X["emb"], y + 15, Wd["emb"], 17, "_embed (incremental)", "#e9f3f3", "#7FAFAF", 9.5))
        parts.append(box(X["ec"], y, Wd["ec"], bh, "_embedded_classified", "#e9f3f3", "#7FAFAF", 10))
        parts.append(arrow(X["seed"] + Wd["seed"], yc, X["stg"] - 2, yc))
        parts.append(arrow(X["stg"] + Wd["stg"], yc, X["prep"] - 2, yc))
        parts.append(arrow(X["prep"] + Wd["prep"], yc, X["hash"] - 2, yc))
        parts.append(arrow(X["hash"] + Wd["hash"], yc, X["cls"] - 2, y + 2.5))
        parts.append(arrow(X["hash"] + Wd["hash"], yc, X["emb"] - 2, y + 23.5))
        parts.append(arrow(X["cls"] + Wd["cls"], y + 2.5, X["ec"] - 2, yc - 3))
        parts.append(arrow(X["emb"] + Wd["emb"], y + 23.5, X["ec"] - 2, yc + 3))
        # into knowledge_base
        kb_y = top + 2 * rh
        parts.append(arrow(X["ec"] + Wd["ec"], yc, X["kb"] - 2, kb_y + 40 + (i - 3) * 9, LIGHT_GREY, 1.1))
        parts.append(text(X["ec"] + Wd["ec"] + 4, yc - 4, f"{kb_rows:,}", 10, GREY, "start", "bold"))
    # knowledge_base box
    kb_y = top + 2 * rh
    parts.append(rect(X["kb"], kb_y, Wd["kb"], 80, "#f1ecf5", "#9E85AC", 1.8))
    parts.append(text(X["kb"] + Wd["kb"] / 2, kb_y + 22, "knowledge_base", 12.5, INK, "middle", "bold"))
    parts.append(text(X["kb"] + Wd["kb"] / 2, kb_y + 40, "table · 2,696 rows", 10.5, GREY, "middle"))
    parts.append(text(X["kb"] + Wd["kb"] / 2, kb_y + 55, "7 source_types", 10.5, GREY, "middle"))
    parts.append(text(X["kb"] + Wd["kb"] / 2, kb_y + 70, "catalog: 0 parents", 10.5, RED, "middle", "bold"))
    # search + consumers
    s_y = kb_y + 130
    parts.append(box(X["kb"], s_y, Wd["kb"], 26, "search (demo queries)", "#ffffff", GREY, 10.5))
    parts.append(arrow(X["kb"] + Wd["kb"] / 2, kb_y + 80, X["kb"] + Wd["kb"] / 2, s_y - 2))
    c_y = s_y + 70
    parts.append(box(X["kb"] - 20, c_y, Wd["kb"] + 40, 40, "", "#ffffff", GREY, 10.5, "3,3"))
    parts.append(text(X["kb"] + Wd["kb"] / 2, c_y + 16, "agents: knowledge-base-", 10, INK, "middle"))
    parts.append(text(X["kb"] + Wd["kb"] / 2, c_y + 30, "search skill (no exposure)", 10, INK, "middle"))
    parts.append(arrow(X["kb"] + Wd["kb"] + 8, kb_y + 60, X["kb"] + Wd["kb"] + 8, c_y - 2, GREY, 1.0))
    # account-key helpers
    hy = top + rh * len(CHAINS) + 90
    parts.append(box(X["stg"], hy, 470, 26,
                     "account-key helpers: stg_route_client_attribution · stg_shipments · stg_incidents",
                     "#fbf2ea", "#D2955C", 10.5))
    parts.append(arrow(X["stg"] + 470, hy + 13, X["prep"] + Wd["prep"] / 2 + 160, top + 6 * rh + bh + 2, LIGHT_GREY, 1.1))
    parts.append(text(X["stg"], hy + 46, "dispatch notes and Slack threads carry no client_id; *_records_meta derives it "
                      "through these (null where it cannot).", 10.5, GREY))
    # prod-state callout
    parts.append(rect(X["hash"], hy, 600, 54, "#fdf0ee", RED, 1.2))
    parts.append(text(X["hash"] + 10, hy + 20, "Production today: corpus text is still the pre-pivot geography "
                      "(‘amsterdam’ in 0 rows)", 11, RED, "start", "bold"))
    parts.append(text(X["hash"] + 10, hy + 38, "main’s seeds were re-labelled to Europe (a00d85b); the gated "
                      "layer was not rebuilt in production.", 11, RED))
    save("data-04-ai-layer-lineage.svg", parts)


# ---------------------------------------------------------------- chart 5: the volume artefact
def chart_volume():
    W, H = 900, 480
    x0, x1 = 90, 840
    top, bot = 90, 380
    vmax = 2200
    parts = canvas(W, H, "Shipments per year: what the reports say vs what the warehouse holds",
                   "Grey = the figure published before scripts/generate_volume_variation.py; blue = stg_shipments in production today.")

    def yy(v):
        return bot - v / vmax * (bot - top)

    for v in range(0, vmax + 1, 500):
        parts.append(line(x0, yy(v), x1, yy(v), GRID, 1))
        parts.append(text(x0 - 8, yy(v) + 4, f"{v:,}", 11.5, GREY, "end"))
    parts.append(text(28, (top + bot) / 2, "Shipments (count)", 12, GREY, "middle", rotate=-90))
    step = (x1 - x0) / len(YEARS)
    bw = 70
    for i, y in enumerate(YEARS):
        cx = x0 + step * (i + 0.5)
        pub = PUBLISHED_SHIPMENTS[y]
        now = BOOK[y][0]
        parts.append(rect(cx - bw - 4, yy(pub), bw, bot - yy(pub), LIGHT_GREY))
        parts.append(text(cx - bw / 2 - 4, yy(pub) - 6, f"{pub:,}", 12, GREY, "middle", "bold"))
        parts.append(rect(cx + 4, yy(now), bw, bot - yy(now), BLUE))
        parts.append(text(cx + bw / 2 + 4, yy(now) - 6, f"{now:,}", 12, BLUE, "middle", "bold"))
        parts.append(text(cx, bot + 20, y, 13, INK, "middle", "bold"))
        d = now - pub
        note = "unchanged" if d == 0 else f"{d:+,} ({100.0 * d / pub:+.1f}%)"
        parts.append(text(cx, bot + 38, note, 11.5, RED if d else GREY, "middle"))
        q = QUARTERS_NOW[y]
        parts.append(text(cx, bot + 56, "Q1–Q4: " + " / ".join(str(v) for v in q), 10.5, GREY, "middle"))
    parts.append(rect(x0, 60, 14, 12, LIGHT_GREY))
    parts.append(text(x0 + 20, 70, "published (pre-revision seed): 2,009 every year, 486/435/492/596 every quarter", 11.5, INK))
    parts.append(rect(x0 + 520, 60, 14, 12, BLUE))
    parts.append(text(x0 + 540, 70, "production warehouse now", 11.5, INK))
    parts.append(text(W / 2, H - 12, "Year of shipment created_at", 12, GREY, "middle"))
    save("data-05-volume-artefact.svg", parts)


if __name__ == "__main__":
    chart_ontime_by_year()
    chart_coverage()
    chart_tests()
    chart_lineage()
    chart_volume()
