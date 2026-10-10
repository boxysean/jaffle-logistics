#!/usr/bin/env python3
"""Deterministically generate seeds/route_client_attribution.csv: the route-to-client
attribution bridge, one row per route x client the route serves (every route in
seeds/routes.csv, 2023-01-01 .. 2025-12-31, one to four clients each).

No randomness: every "draw" is a SHA-256 hash of the route_id and a salt, so the same
input seeds always give byte-identical output. Reads seeds/routes.csv,
seeds/shipments.csv, seeds/clients.csv and seeds/incidents.csv (all read-only).

What it answers: which accounts a route carried, so route-level cost (exceptions, fleet
maintenance) can be allocated to clients. It is a mix, not a cause: an allocation by
share is an approximation.

Client mix:
  * Evidence first. shipments.route_id is the only recorded route->client link; every
    client with a shipment on the route is kept. Shipments are a sample of the route's
    stops (a 40-stop route typically has one or two recorded shipments), so the mix is
    topped up to a drawn client count (1-4) from the remaining accounts.
  * Top-up draws are weighted by each account's shipments from the route's hub in the
    route's month (+1 so no account is ever impossible), so the larger accounts appear
    on more routes and an account's footprint follows its own volume over time. All
    shipments count, not only the route-linked ones: none of CLI-0042's 2025 freight
    carries a route_id, and weighting by routed shipments alone would wrongly drop
    Jaffle Equipment from 2025 routes.
  * Stop weight per client = (1 + 2 x its shipments on the route) x a 0.5-1.5 jitter.
    stop_share is the normalised stop weight.
  * revenue_share = stop weight x the account's revenue per stop (LTL freight earns more
    per stop than last-mile parcels) x a 0.85-1.15 jitter, normalised. It can differ
    from stop_share; both sum to one.
  * exception_attributed splits the route's exceptions_count by stop share with a
    largest-remainder allocation, so the integers sum to exceptions_count exactly.

Rounding: shares are rounded to 4 dp and the largest-share row absorbs the remainder,
so each route's stop_share and revenue_share sum to exactly 1.0000.

The 2025 Columbus story: on every route carrying a 2025 damage incident (type =
'damage', the HUB-CMH bay-3 handling-damage cluster and the scattered damage elsewhere),
Jaffle Equipment (CLI-0042) is on the route with the largest stop share, and its
exception weight is tripled, so it holds the largest exception_attributed. On the
2023-2024 damage routes CLI-0042 is held below the route's leading account, so the
2025 concentration has no earlier analogue. Nothing else is year-dependent.

Run from the repo root:  python3 scripts/generate_route_client_attribution.py
"""
import collections
import csv
import hashlib
import os
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")
OUT = os.path.join(SEEDS, "route_client_attribution.csv")

EQUIPMENT = "CLI-0042"
STORY_YEAR = "2025"
QUIET_YEARS = ("2023", "2024")

# Drawn client count before evidence: u < cut -> that many clients.
CLIENT_COUNT_CUTS = ((0.22, 1), (0.58, 2), (0.86, 3), (1.00, 4))
MAX_CLIENTS = 4

# Revenue per stop relative to a warehousing stop (contract factor x line of business).
REVENUE_PER_STOP = {
    "CLI-0007": Decimal("0.80"),   # last-mile, strategic rate
    "CLI-0042": Decimal("1.35"),   # LTL freight
    "CLI-0155": Decimal("0.85"),   # last-mile
    "CLI-0169": Decimal("1.05"),   # warehousing
    "CLI-0201": Decimal("1.30"),   # LTL
}

EQUIPMENT_LEAD = Decimal("1.6")         # 2025 damage routes: CLI-0042 stop weight vs next
EQUIPMENT_DAMAGE_WEIGHT = Decimal("3")  # 2025 damage routes: CLI-0042 exception weight x
QUIET_EQUIPMENT_CAP = Decimal("0.5")    # 2023-24 damage routes: CLI-0042 vs route leader

SHARE = Decimal("0.0001")
COLUMNS = ["route_id", "client_id", "stop_share", "revenue_share", "exception_attributed"]


def read(name):
    with open(os.path.join(SEEDS, name), newline="") as f:
        return list(csv.DictReader(f))


def unit(*parts):
    """A deterministic draw in [0, 1) from the given key parts."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:15], 16) / float(16 ** 15)


def jitter(lo, hi, *parts):
    return Decimal(lo) + (Decimal(hi) - Decimal(lo)) * Decimal(repr(unit(*parts)))


def client_count(route_id):
    u = unit(route_id, "n_clients")
    return next(n for cut, n in CLIENT_COUNT_CUTS if u < cut)


def leader(weights):
    """Largest weight, tie-broken by client_id: the row that absorbs rounding."""
    return max(sorted(weights), key=lambda c: weights[c])


def shares_4dp(weights):
    total = sum(weights.values())
    out = {c: (w / total).quantize(SHARE, rounding=ROUND_HALF_UP) for c, w in weights.items()}
    out[leader(weights)] += Decimal(1) - sum(out.values())
    return out


def largest_remainder(total, weights):
    wsum = sum(weights.values())
    exact = {c: Decimal(total) * w / wsum for c, w in weights.items()}
    out = {c: int(x) for c, x in exact.items()}
    order = sorted(weights, key=lambda c: (-(exact[c] - out[c]), -weights[c], c))
    for c in order[: total - sum(out.values())]:
        out[c] += 1
    return out


def dominant(rows):
    """The test's dominant client: exception_attributed desc, then stop_share desc."""
    return max(rows, key=lambda r: (r["exception_attributed"], r["stop_share"]))["client_id"]


def main():
    clients = sorted(r["client_id"] for r in read("clients.csv"))
    assert set(clients) == set(REVENUE_PER_STOP), clients
    routes = sorted(read("routes.csv"), key=lambda r: r["route_id"])
    route_ids = {r["route_id"] for r in routes}

    on_route = collections.defaultdict(collections.Counter)
    hub_month = collections.defaultdict(collections.Counter)
    for s in read("shipments.csv"):
        hub_month[(s["origin_hub_id"], s["created_at"][:7])][s["client_id"]] += 1
        if s["route_id"]:
            assert s["route_id"] in route_ids, s["shipment_id"]
            on_route[s["route_id"]][s["client_id"]] += 1

    damage_routes = collections.defaultdict(set)   # year -> route_ids
    damage_incidents = collections.defaultdict(list)
    for i in read("incidents.csv"):
        if i["type"] == "damage" and i["route_id"]:
            assert i["route_id"] in route_ids, i["incident_id"]
            damage_routes[i["occurred_at"][:4]].add(i["route_id"])
            damage_incidents[i["occurred_at"][:4]].append(i)
    story_routes = damage_routes[STORY_YEAR]
    quiet_routes = set().union(*(damage_routes[y] for y in QUIET_YEARS))
    assert not story_routes & quiet_routes

    out_rows = []
    by_route = {}
    for r in routes:
        rid = r["route_id"]
        observed = on_route.get(rid, collections.Counter())
        assert len(observed) <= MAX_CLIENTS, rid
        n = max(client_count(rid), len(observed))

        # Top up from the remaining accounts, weighted by hub-month volume (+1).
        volume = hub_month[(r["hub_id"], r["service_date"][:7])]
        chosen = sorted(observed)
        pool = [c for c in clients if c not in observed]
        while len(chosen) < n:
            # Weighted draw without replacement: smallest -log(u)/w wins (exponential race).
            pick = min(pool, key=lambda c: (Decimal(1) - Decimal(repr(unit(rid, "pick", c))))
                       .ln() / -(volume[c] + 1))
            chosen.append(pick)
            pool.remove(pick)

        if rid in story_routes and EQUIPMENT not in chosen:
            if len(chosen) == MAX_CLIENTS:
                # Swap out the drawn (unobserved) account with the least volume.
                drop = min((c for c in chosen if c not in observed),
                           key=lambda c: (volume[c], c))
                chosen.remove(drop)
            chosen.append(EQUIPMENT)
        if rid in quiet_routes and chosen == [EQUIPMENT]:
            # A sole-client route would make CLI-0042 dominant by default; add the
            # hub-month's largest other account as the route's leader.
            chosen.append(max(sorted(c for c in clients if c != EQUIPMENT),
                              key=lambda c: volume[c]))

        stop_w = {c: (1 + 2 * observed[c]) * jitter("0.5", "1.5", rid, "stops", c)
                  for c in sorted(chosen)}
        if rid in story_routes and len(stop_w) > 1:
            stop_w[EQUIPMENT] = EQUIPMENT_LEAD * max(w for c, w in stop_w.items()
                                                     if c != EQUIPMENT)
        if rid in quiet_routes and EQUIPMENT in stop_w:
            others = max(w for c, w in stop_w.items() if c != EQUIPMENT)
            stop_w[EQUIPMENT] = min(stop_w[EQUIPMENT], QUIET_EQUIPMENT_CAP * others)

        rev_w = {c: w * REVENUE_PER_STOP[c] * jitter("0.85", "1.15", rid, "revenue", c)
                 for c, w in stop_w.items()}
        exc_w = dict(stop_w)
        if rid in story_routes:
            exc_w[EQUIPMENT] *= EQUIPMENT_DAMAGE_WEIGHT

        stop_share = shares_4dp(stop_w)
        revenue_share = shares_4dp(rev_w)
        exceptions = largest_remainder(int(r["exceptions_count"]), exc_w)

        rows = [{"route_id": rid, "client_id": c, "stop_share": stop_share[c],
                 "revenue_share": revenue_share[c], "exception_attributed": exceptions[c]}
                for c in sorted(stop_w)]
        assert 1 <= len(rows) <= MAX_CLIENTS, rid
        assert sum(x["stop_share"] for x in rows) == 1, rid
        assert sum(x["revenue_share"] for x in rows) == 1, rid
        assert all(x["stop_share"] > 0 and x["revenue_share"] > 0 for x in rows), rid
        assert sum(x["exception_attributed"] for x in rows) == int(r["exceptions_count"]), rid
        by_route[rid] = rows
        out_rows.extend(rows)

    # The story checks the singular test repeats in dbt.
    for rid in story_routes:
        rows = by_route[rid]
        assert dominant(rows) == EQUIPMENT, rid
        lead = max(x["stop_share"] for x in rows)
        assert sum(x["stop_share"] == lead for x in rows) == 1, rid
    for rid in quiet_routes:
        assert dominant(by_route[rid]) != EQUIPMENT, rid

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNS)
        for x in out_rows:
            w.writerow([x["route_id"], x["client_id"], f"{x['stop_share']:.4f}",
                        f"{x['revenue_share']:.4f}", x["exception_attributed"]])

    # ---- summary -------------------------------------------------------------------
    print(f"wrote {OUT}: {len(out_rows)} rows, {len(by_route)} routes "
          f"({min(r['service_date'] for r in routes)} .. {max(r['service_date'] for r in routes)})")
    sizes = collections.Counter(len(v) for v in by_route.values())
    print("clients per route: " + ", ".join(f"{k}: {sizes[k]}" for k in sorted(sizes)))
    print("\nroute participation by account and year:")
    for c in clients:
        per_year = collections.Counter(r["service_date"][:4] for r in routes
                                       if any(x["client_id"] == c for x in by_route[r["route_id"]]))
        print(f"  {c}  " + "  ".join(f"{y} {per_year[y]:>5}" for y in sorted(per_year)))
    print("\ndamage routes where CLI-0042 is the dominant account:")
    for y in sorted(damage_routes):
        rids = damage_routes[y]
        n42 = sum(dominant(by_route[rid]) == EQUIPMENT for rid in rids)
        cmh = sum(1 for i in damage_incidents[y] if i["hub_id"] == "HUB-CMH")
        print(f"  {y}  {n42:>2} of {len(rids):>2} routes  "
              f"({len(damage_incidents[y])} incidents, {cmh} at HUB-CMH)")


if __name__ == "__main__":
    main()
