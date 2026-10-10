#!/usr/bin/env python3
"""Assert the cost ledger's one defensible tie: for every hub-month row,
maintenance_cost equals the sum of seeds/fleet_work_orders.csv for that hub and month.
Also checks total_cost is the sum of the five lines and prints the head/date range.

Run:  python3 scripts/verify_cost_ledger.py
"""
import collections
import csv
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    ledger = read_csv(os.path.join(SEEDS, "cost_ledger.csv"))
    work_orders = read_csv(os.path.join(SEEDS, "fleet_work_orders.csv"))
    routes = read_csv(os.path.join(SEEDS, "routes.csv"))

    wo_sum = collections.Counter()
    for w in work_orders:
        wo_sum[(w["hub_id"], w["opened_at"][:7])] += int(w["cost"])

    route_count = collections.Counter()
    for rr in routes:
        route_count[(rr["hub_id"], rr["service_date"][:7])] += 1

    bad = 0
    for r in ledger:
        key = (r["hub_id"], r["cost_month"][:7])
        if int(r["maintenance_cost"]) != wo_sum.get(key, 0):
            bad += 1
            if bad <= 5:
                print("MISMATCH", key, r["maintenance_cost"], wo_sum.get(key, 0))
        total = sum(int(r[c]) for c in ("fuel_cost", "maintenance_cost", "subcontractor_cost",
                                        "facility_cost", "technology_cost"))
        assert total == int(r["total_cost"]), r

    months = sorted(r["cost_month"] for r in ledger)
    print("rows:", len(ledger))
    print("hubs:", sorted({r["hub_id"] for r in ledger}))
    print("cost_month range:", months[0], "..", months[-1])
    print("maintenance reconciliation mismatches:", bad)
    print("ledger maintenance total:", sum(int(r["maintenance_cost"]) for r in ledger),
          " work-order total:", sum(wo_sum.values()))

    cpr = collections.defaultdict(list)
    for r in ledger:
        n = route_count.get((r["hub_id"], r["cost_month"][:7]))
        if n:
            cpr[r["hub_id"]].append(int(r["total_cost"]) / n)
    print("cost_per_route (mean across 2023-2025) by hub:",
          {h: round(statistics.mean(v)) for h, v in sorted(cpr.items())})
    assert bad == 0, "maintenance does not reconcile"



if __name__ == "__main__":
    main()
