#!/usr/bin/env python3
"""Deterministically revise seeds/shipments.csv and seeds/routes.csv so the years differ
in volume and the service_level dimension stops being an alias for one account.

THIS IS A REVISION OF EXISTING ROWS, NOT AN APPEND. It rewrites both files in place:
  * 2023 and 2024 lose rows. No row is added, renumbered or re-drawn; every surviving
    row keeps every value it had. 2023 shrinks to ~8% below 2025 (1,848 shipments) and
    2024 to ~3% below (1,949); 2025 stays at 2,009.
  * 2025 shipments keep every row and every value except service_level: a small seeded
    share of CLI-0007's and CLI-0169's expedited shipments are re-labelled freight, so
    freight is carried by three accounts in every year rather than by CLI-0042 alone.
  * 2025 routes are byte-identical.
  * The promised-delivery columns (promised_delivery_at, hours_late, late_bucket, from
    scripts/generate_promised_delivery.py) are carried through untouched on every
    surviving row, the relabelled 2025 rows included. Do not re-run that generator
    afterwards: its seeded stream is drawn row by row and would redraw every promise.

Why: before this revision 2023, 2024 and 2025 each held exactly 2,009 shipments and
3,629 routes, so no analysis could separate a volume effect from a reliability effect,
and every 2025 freight shipment was CLI-0042's.

How rows are chosen (seeded, byte-reproducible):
  * Shipments: only rows no other seed mentions (incidents, support_tickets, crm_notes,
    incident_reports, dispatch_notes, slack_threads, call_transcripts, ...) may be
    dropped. Drops meet three quotas at once: per month (each month scaled by the
    year's factor, so the January trough and Q4 peak survive), per account (CLI-0042's
    share rises 2023 -> 2024 -> 2025; the other four scale together), and per status
    (the year's missed count scales with the year, so the on-time rate holds). CLI-0042
    exceptions are never dropped, so its 2023-2024 exception baseline is unchanged.
  * Routes: each month is scaled by the same annual factor. Only a route no surviving
    shipment, incident, dispatch note or other seed text references may be dropped, and
    never a driver's last route of a month. Driver-months and vehicle-months above the
    2025 maximum are thinned first, so 2023-2024 never load a driver or vehicle harder
    than 2025 does.

Guard: the script aborts unless the input is still the pre-revision shape (equal
per-year totals), so a second run cannot silently shrink already-revised data.

Run from the repo root:  python3 scripts/generate_volume_variation.py
"""
import collections
import csv
import glob
import io
import os
import random
import re
import sys

SEED = 20251231
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")
SHIP_PATH = os.path.join(SEEDS, "shipments.csv")
ROUTE_PATH = os.path.join(SEEDS, "routes.csv")

YEARS = ("2023", "2024", "2025")
EQUIPMENT = "CLI-0042"
TARGET_SHIPMENTS = {"2023": 1848, "2024": 1949}       # 2025 = 2,009, unchanged
TARGET_EQUIPMENT_SHARE = {"2023": 0.194, "2024": 0.201}  # 2025 = 416/2009 = 20.7%
# 2025 service-level revision: share of the account's 2025 shipments moved expedited -> freight.
FREIGHT_RELABEL_SHARE = {"CLI-0007": 0.08, "CLI-0169": 0.08}

SHP_RE = re.compile(r"SHP-\d{6}-\d{6}")
RTE_RE = re.compile(r"RTE-[A-Z]{3}-\d{8}-\d{3}")
# Derived from shipments/routes and regenerated afterwards; not a source of references.
DERIVED = {"shipments.csv", "routes.csv", "route_client_attribution.csv",
           "revenue_ledger.csv", "payroll_monthly.csv", "cost_ledger.csv"}


def read_raw(path):
    """Header + rows, asserting the csv round-trip reproduces the file byte for byte."""
    with open(path, "rb") as fh:
        raw = fh.read()
    rows = list(csv.reader(io.StringIO(raw.decode(), newline="")))
    assert serialize(rows) == raw, f"{path}: csv round-trip is not lossless"
    return rows[0], rows[1:]


def serialize(rows):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows(rows)
    return buf.getvalue().encode()


def largest_remainder(total, weights):
    """Integer split of total proportional to weights (dict), ties broken by key."""
    s = sum(weights.values())
    exact = {k: total * w / s for k, w in weights.items()}
    out = {k: int(v) for k, v in exact.items()}
    for k in sorted(exact, key=lambda k: (-(exact[k] - out[k]), k))[:total - sum(out.values())]:
        out[k] += 1
    return out


def referenced_ids():
    shp, rte = set(), set()
    for path in sorted(glob.glob(os.path.join(SEEDS, "*.csv"))):
        if os.path.basename(path) in DERIVED:
            continue
        with open(path, newline="") as fh:
            text = fh.read()
        shp.update(SHP_RE.findall(text))
        rte.update(RTE_RE.findall(text))
    return shp, rte


def summarize(label, ships, routes, sc, rc):
    print(f"\n{label}")
    for y in YEARS:
        s = [r for r in ships if r[sc["created_at"]][:4] == y]
        n_rte = sum(1 for r in routes if r[rc["service_date"]][:4] == y)
        ontime = sum(r[sc["status"]] == "delivered" for r in s)
        acct = collections.Counter(r[sc["client_id"]] for r in s)
        lvl = collections.Counter(r[sc["service_level"]] for r in s)
        frt = collections.Counter(r[sc["client_id"]] for r in s if r[sc["service_level"]] == "freight")
        print(f"  {y}  shipments {len(s):>5}  routes {n_rte:>5}  on-time {100 * ontime / len(s):6.2f}%"
              f"  {EQUIPMENT} share {100 * acct[EQUIPMENT] / len(s):5.2f}%")
        print("        accounts  " + "  ".join(f"{c} {acct[c]:>3}" for c in sorted(acct)))
        print("        levels    " + "  ".join(f"{k} {lvl[k]:>4}" for k in ("standard", "expedited", "freight")))
        print("        freight   " + "  ".join(f"{c} {frt[c]:>3}" for c in sorted(frt)))


def main():
    rng = random.Random(SEED)
    s_header, ships = read_raw(SHIP_PATH)
    r_header, routes = read_raw(ROUTE_PATH)
    sc = {c: i for i, c in enumerate(s_header)}
    rc = {c: i for i, c in enumerate(r_header)}
    s_year = lambda r: r[sc["created_at"]][:4]
    r_year = lambda r: r[rc["service_date"]][:4]

    s_tot = collections.Counter(s_year(r) for r in ships)
    r_tot = collections.Counter(r_year(r) for r in routes)
    if not (len(set(s_tot[y] for y in YEARS)) == 1 and len(set(r_tot[y] for y in YEARS)) == 1
            and set(s_tot) == set(YEARS) and set(r_tot) == set(YEARS)):
        sys.exit("ABORT: shipments/routes are not in the pre-revision shape (equal per-year "
                 f"totals); shipments {dict(sorted(s_tot.items()))}, routes "
                 f"{dict(sorted(r_tot.items()))}. The revision has already been applied.")
    n_year = s_tot["2025"]
    summarize("BEFORE", ships, routes, sc, rc)

    ref_shp, ref_rte = referenced_ids()
    assert ref_shp <= {r[sc["shipment_id"]] for r in ships}
    assert ref_rte <= {r[rc["route_id"]] for r in routes}

    # ---- 2023 / 2024 shipments: choose drops against month, account and status quotas ----
    drop_shp = set()
    for y, target in TARGET_SHIPMENTS.items():
        rows = sorted((r for r in ships if s_year(r) == y), key=lambda r: r[sc["shipment_id"]])
        month_n = collections.Counter(r[sc["created_at"]][5:7] for r in rows)
        acct_n = collections.Counter(r[sc["client_id"]] for r in rows)
        missed_n = sum(r[sc["status"]] != "delivered" for r in rows)

        month_keep = largest_remainder(target, month_n)
        eq_keep = round(TARGET_EQUIPMENT_SHARE[y] * target)
        acct_keep = largest_remainder(target - eq_keep,
                                      {c: n for c, n in acct_n.items() if c != EQUIPMENT})
        acct_keep[EQUIPMENT] = eq_keep
        need_month = {m: month_n[m] - month_keep[m] for m in month_n}
        need_acct = {c: acct_n[c] - acct_keep[c] for c in acct_n}
        need_missed = missed_n - round(missed_n * target / len(rows))
        assert all(v >= 0 for v in list(need_month.values()) + list(need_acct.values()))

        droppable = [r for r in rows if r[sc["shipment_id"]] not in ref_shp]
        missed = [r for r in droppable if r[sc["status"]] != "delivered"
                  and r[sc["client_id"]] != EQUIPMENT]
        delivered = [r for r in droppable if r[sc["status"]] == "delivered"]
        rng.shuffle(missed)
        rng.shuffle(delivered)
        chosen = []

        def take(pool, limit):
            taken = 0
            for _ in range(len(pool) + 1):        # repeated passes until no progress
                progress = False
                for r in pool:
                    if taken == limit:
                        return
                    m, c = r[sc["created_at"]][5:7], r[sc["client_id"]]
                    if id(r) not in picked and need_month[m] > 0 and need_acct[c] > 0:
                        picked.add(id(r))
                        chosen.append(r)
                        need_month[m] -= 1
                        need_acct[c] -= 1
                        taken += 1
                        progress = True
                if not progress:
                    return

        picked = set()
        take(missed, need_missed)
        assert sum(r[sc["status"]] != "delivered" for r in chosen) == need_missed, y
        take(delivered, sum(need_month.values()))
        assert not any(need_month.values()) and not any(need_acct.values()), (y, need_month, need_acct)
        drop_shp.update(r[sc["shipment_id"]] for r in chosen)

    kept_ships = [r for r in ships if r[sc["shipment_id"]] not in drop_shp]

    # ---- 2025 service-level revision: expedited -> freight for two healthy accounts ----
    relabel = set()
    for cid, share in sorted(FREIGHT_RELABEL_SHARE.items()):
        acct25 = [r for r in kept_ships if s_year(r) == "2025" and r[sc["client_id"]] == cid]
        pool = sorted(r[sc["shipment_id"]] for r in acct25
                      if r[sc["service_level"]] == "expedited" and r[sc["shipment_id"]] not in ref_shp)
        relabel.update(rng.sample(pool, round(share * len(acct25))))
    for r in kept_ships:
        if r[sc["shipment_id"]] in relabel:
            r[sc["service_level"]] = "freight"

    # ---- 2023 / 2024 routes: same annual factor, per month, only unreferenced routes ----
    protected = set(ref_rte) | {r[sc["route_id"]] for r in kept_ships if r[sc["route_id"]]}
    cap = {}
    for key in ("driver_id", "vehicle_id"):
        load25 = collections.Counter((r[rc[key]], r[rc["service_date"]][:7])
                                     for r in routes if r_year(r) == "2025")
        cap[key] = max(load25.values())
    load = {key: collections.Counter((r[rc[key]], r[rc["service_date"]][:7]) for r in routes)
            for key in cap}
    drop_rte = set()
    for y, target in TARGET_SHIPMENTS.items():
        rows = sorted((r for r in routes if r_year(r) == y), key=lambda r: r[rc["route_id"]])
        month_n = collections.Counter(r[rc["service_date"]][:7] for r in rows)
        month_keep = largest_remainder(round(len(rows) * target / n_year), month_n)
        need = {m: month_n[m] - month_keep[m] for m in month_n}
        droppable = [r for r in rows if r[rc["route_id"]] not in protected]
        rng.shuffle(droppable)

        def drop(r):
            m = r[rc["service_date"]][:7]
            drop_rte.add(r[rc["route_id"]])
            need[m] -= 1
            for key in cap:
                load[key][(r[rc[key]], m)] -= 1

        # First thin any driver-/vehicle-month loaded above the 2025 maximum.
        for key in cap:
            for r in droppable:
                m = r[rc["service_date"]][:7]
                if (r[rc["route_id"]] not in drop_rte and need[m] > 0
                        and load[key][(r[rc[key]], m)] > cap[key]):
                    drop(r)
        # Then fill each month's quota, never removing a driver's last route of the month.
        for r in droppable:
            m = r[rc["service_date"]][:7]
            if (r[rc["route_id"]] not in drop_rte and need[m] > 0
                    and load["driver_id"][(r[rc["driver_id"]], m)] > 1):
                drop(r)
        assert not any(need.values()), (y, need)

    kept_routes = [r for r in routes if r[rc["route_id"]] not in drop_rte]

    # ---- hard constraints ---------------------------------------------------------
    orig_ship = {r[sc["shipment_id"]]: r for r in read_raw(SHIP_PATH)[1]}
    for r in kept_ships:
        o = orig_ship[r[sc["shipment_id"]]]
        diff = [h for h, a, b in zip(s_header, o, r) if a != b]
        assert diff == ([] if r[sc["shipment_id"]] not in relabel else ["service_level"]), diff
    assert {s_year(r) for r in ships if r[sc["shipment_id"]] in drop_shp} <= set(TARGET_SHIPMENTS)
    assert not drop_shp & ref_shp
    assert not drop_rte & protected
    assert {r_year(r) for r in routes if r[rc["route_id"]] in drop_rte} <= set(TARGET_SHIPMENTS)
    assert [r for r in kept_routes if r_year(r) == "2025"] == [r for r in routes if r_year(r) == "2025"]
    kept_route_ids = {r[rc["route_id"]] for r in kept_routes}
    assert all(r[sc["route_id"]] in kept_route_ids for r in kept_ships if r[sc["route_id"]])
    for key in cap:
        final = collections.Counter((r[rc[key]], r[rc["service_date"]][:7]) for r in kept_routes)
        worst = max(v for (_, m), v in final.items() if m[:4] in TARGET_SHIPMENTS)
        assert worst <= cap[key], f"{key}-month load {worst} exceeds the 2025 maximum {cap[key]}"
        print(f"max routes per {key.split('_')[0]}-month: 2023-24 {worst}, 2025 {cap[key]}")

    def year_stats(y):
        s = [r for r in kept_ships if s_year(r) == y]
        acct = collections.Counter(r[sc["client_id"]] for r in s)
        frt = collections.Counter(r[sc["client_id"]] for r in s if r[sc["service_level"]] == "freight")
        return s, acct, frt

    shares = []
    for y in YEARS:
        s, acct, frt = year_stats(y)
        assert len(s) == TARGET_SHIPMENTS.get(y, n_year), (y, len(s))
        months = [sum(r[sc["created_at"]][5:7] == "%02d" % m for r in s) for m in range(1, 13)]
        assert max(months) in months[10:] and months[0] > months[1], ("monthly shape lost", y, months)
        carriers = [c for c in frt if frt[c] >= 0.05 * acct[c]]
        assert len(carriers) >= 3 and EQUIPMENT in carriers, (y, frt)
        if y == "2025":
            # CLI-0042 keeps the largest 2025 freight book. (In 2023-24 freight was already
            # spread across all five accounts and CLI-0042 was never the largest carrier.)
            assert all(frt[c] < frt[EQUIPMENT] for c in frt if c != EQUIPMENT), (y, frt)
        shares.append(acct[EQUIPMENT] / len(s))
    assert shares[0] < shares[1] < shares[2], shares
    for y in YEARS:
        before = [r for r in ships if s_year(r) == y]
        after = year_stats(y)[0]
        rate = lambda rs: sum(r[sc["status"]] == "delivered" for r in rs) / len(rs)
        assert abs(rate(after) - rate(before)) < 0.0005, (y, rate(before), rate(after))

    with open(SHIP_PATH, "wb") as fh:
        fh.write(serialize([s_header] + kept_ships))
    with open(ROUTE_PATH, "wb") as fh:
        fh.write(serialize([r_header] + kept_routes))

    summarize("AFTER", kept_ships, kept_routes, sc, rc)
    print(f"\nshipments dropped: {len(drop_shp)}  routes dropped: {len(drop_rte)}  "
          f"2025 shipments re-labelled expedited -> freight: {len(relabel)}")
    print(f"wrote {os.path.relpath(SHIP_PATH)} ({len(kept_ships)} rows) and "
          f"{os.path.relpath(ROUTE_PATH)} ({len(kept_routes)} rows)")


if __name__ == "__main__":
    main()
