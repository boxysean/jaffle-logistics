#!/usr/bin/env python3
"""Deterministic generator for seeds/cost_ledger.csv (hub x month, non-labour).

One row per hub x month, 2020-01 .. 2025-12, with the non-labour cost lines the CFO
briefing said did not exist (fuel, maintenance, subcontractor, facility, technology).
Payroll is a separate card.

Design:

* ``maintenance_cost`` is NOT modelled -- it is the exact sum of ``seeds/fleet_work_orders.csv``
  cost for that hub and month. ``fleet_work_orders`` begins 2023-01, so maintenance ties out
  to zero for 2020-2022; the ledger deliberately does not invent maintenance it cannot root
  in a work order. This is the tie that makes the whole ledger defensible.
* ``fuel_cost`` tracks the hub's real route volume (``seeds/routes.csv`` where it exists,
  a modelled steady-state monthly volume for the 2020-2022 background) shaped by a seasonal
  diesel index (winter months higher) and a yearly diesel-price level (the 2022 spike).
* ``subcontractor_cost`` = a per-route cover base plus a premium that spikes in exactly the
  months the hub ran into exception trouble: the month's exception load is
  ``dispatch_notes`` count + 2x incidents + 4x *damage* incidents, less the hub's own
  2023-2024 baseline. The 4x weighting puts the 2025 HUB-CMH handling-damage cluster visibly
  on CMH while the other hubs stay near their 2024 run rate.
* ``facility_cost`` (rent, utilities, dock/door) scales with the hub's function and carries a
  winter utilities bump and a light annual escalation; ``technology_cost`` (telematics, TMS
  licence, handhelds) scales with the hub's fleet size. Both are quiet across 2023-2024.
* All costs scale with the hub's real size (route volume and fleet), so small hubs cost less.

Nothing is dated after 2025-12-31 and no 2025 signal (storm, CMH damage cluster, the
CLI-0042 decline) appears in 2023-2024.

Run:  python3 scripts/generate_cost_ledger.py
"""
import csv
import os
import statistics
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")

HUBS_PATH = os.path.join(SEEDS, "hubs.csv")
VEH_PATH = os.path.join(SEEDS, "vehicles.csv")
ROUTES_PATH = os.path.join(SEEDS, "routes.csv")
WO_PATH = os.path.join(SEEDS, "fleet_work_orders.csv")
DN_PATH = os.path.join(SEEDS, "dispatch_notes.csv")
INC_PATH = os.path.join(SEEDS, "incidents.csv")
OUT_PATH = os.path.join(SEEDS, "cost_ledger.csv")

FIRST_MONTH = (2020, 1)
LAST_MONTH = (2025, 12)

# --- cost shape parameters (USD) ------------------------------------------------------
FUEL_PER_ROUTE = 780          # baseline diesel for one route-day at the reference price
SUBCONTRACTOR_PER_ROUTE = 210  # baseline bought-in linehaul/cartage per route-day
COVER_RATE = 700              # $ of exception cover per unit of load above the hub baseline

# Exception load weights. Ordinary dispatch notes are the background; incidents weigh more
# and handling *damage* weighs most (and by severity), because damage is what forces rework
# and bought-in cover. This is what puts the 2025 HUB-CMH damage cluster visibly on CMH.
LOAD_DISPATCH = 0.25
LOAD_INCIDENT = 2
LOAD_DAMAGE_SEVERITY = {1: 1, 2: 2, 3: 4, 4: 6}  # multiplied by LOAD_DAMAGE
LOAD_DAMAGE = 10

FACILITY_BASE = {"HQ": 52000, "hub": 38000, "warehouse": 30000}
TECH_FIXED = 3500             # TMS licence / handhelds per hub per month
TECH_PER_VEHICLE = 85         # telematics per vehicle per month

# Year level effects. VOLUME is embedded in the real route counts for 2023-2025 and applied
# to the modelled steady-state volume for 2020-2022. DIESEL is the yearly diesel-price level.
VOLUME = {2020: 0.90, 2021: 0.93, 2022: 0.96, 2023: 0.98, 2024: 1.00, 2025: 1.03}
DIESEL = {2020: 0.85, 2021: 0.95, 2022: 1.20, 2023: 1.05, 2024: 1.00, 2025: 0.97}

# Seasonal indices (1.00 = annual mean). Winter fuel and utilities are higher.
FUEL_SEASON = {1: 1.14, 2: 1.12, 3: 1.04, 4: 0.99, 5: 0.97, 6: 0.99,
               7: 1.02, 8: 1.02, 9: 0.99, 10: 1.00, 11: 1.06, 12: 1.13}
UTIL_SEASON = {1: 1.08, 2: 1.08, 3: 1.03, 4: 1.00, 5: 0.99, 6: 1.00,
               7: 1.02, 8: 1.02, 9: 0.99, 10: 1.00, 11: 1.04, 12: 1.07}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def month_key(year, month):
    return "%04d-%02d" % (year, month)


def months_between(first, last):
    y, m = first
    while (y, m) <= last:
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


def load_monthly_counts(rows, hub_field, date_field):
    """(hub_id, 'YYYY-MM') -> row count, from any seed with a hub and a date/timestamp."""
    out = Counter()
    for r in rows:
        out[(r[hub_field], r[date_field][:7])] += 1
    return out


def main():
    hubs = read_csv(HUBS_PATH)

    vehicles = read_csv(VEH_PATH)
    routes = read_csv(ROUTES_PATH)
    wos = read_csv(WO_PATH)
    dispatch = read_csv(DN_PATH)
    incidents = read_csv(INC_PATH)

    fleet_size = Counter(v["hub_id"] for v in vehicles)
    routes_m = load_monthly_counts(routes, "hub_id", "service_date")
    dn_m = load_monthly_counts(dispatch, "hub_id", "timestamp")
    inc_m = load_monthly_counts(incidents, "hub_id", "occurred_at")
    dmg_sev_m = Counter()
    for i in incidents:
        if i["type"] == "damage":
            dmg_sev_m[(i["hub_id"], i["occurred_at"][:7])] += LOAD_DAMAGE_SEVERITY[int(i["severity"])]


    # maintenance ties exactly to the work orders, by hub and month.
    wo_m = Counter()
    for w in wos:
        wo_m[(w["hub_id"], w["opened_at"][:7])] += int(w["cost"])

    # Steady-state monthly route volume per hub (mean of the real 2023-2025 monthly counts);
    # used as the size scale for the 2020-2022 background, where no routes exist yet.
    base_routes = {}
    for h in hubs:
        vals = [v for (hh, _m), v in routes_m.items() if hh == h["hub_id"]]
        base_routes[h["hub_id"]] = statistics.mean(vals) if vals else 1.0

    # Exception load: dispatch notes + incidents + severity-weighted damage incidents.
    def load(hub, key):
        return (LOAD_DISPATCH * dn_m[(hub, key)] + LOAD_INCIDENT * inc_m[(hub, key)]
                + LOAD_DAMAGE * dmg_sev_m[(hub, key)])

    # Each hub's cover trigger is its own worst 2023-2024 month: 2023-2024 are unremarkable
    # (nothing exceeds this by construction), so cover only spikes when 2025 exceeds it.
    threshold = {}
    for h in hubs:
        threshold[h["hub_id"]] = max(
            load(h["hub_id"], "%04d-%02d" % (y, m))
            for y in (2023, 2024) for m in range(1, 13))

    rows = []
    for (year, month) in months_between(FIRST_MONTH, LAST_MONTH):
        key = month_key(year, month)
        for h in hubs:
            hub = h["hub_id"]

            # volume: real monthly routes where they exist, else the modelled steady state
            routes_used = routes_m.get((hub, key))
            if not routes_used:
                routes_used = base_routes[hub] * VOLUME[year]

            fuel = FUEL_PER_ROUTE * routes_used * FUEL_SEASON[month] * DIESEL[year]

            maintenance = wo_m.get((hub, key), 0)

            extra = max(0.0, load(hub, key) - threshold[hub])
            sub = SUBCONTRACTOR_PER_ROUTE * routes_used + COVER_RATE * extra

            esc = 1.0 + 0.015 * (year - 2020)
            facility = FACILITY_BASE[h["function"]] * UTIL_SEASON[month] * esc
            tech = (TECH_FIXED + TECH_PER_VEHICLE * fleet_size[hub]) * esc

            fuel, maintenance, sub = round(fuel), int(maintenance), round(sub)
            facility, tech = round(facility), round(tech)
            total = fuel + maintenance + sub + facility + tech
            rows.append({
                "cost_month": key + "-01",
                "hub_id": hub,
                "fuel_cost": fuel,
                "maintenance_cost": maintenance,
                "subcontractor_cost": sub,
                "facility_cost": facility,
                "technology_cost": tech,
                "total_cost": total,
            })

    rows.sort(key=lambda r: (r["cost_month"], r["hub_id"]))

    # guard rails
    assert len(rows) == 72 * len(hubs), len(rows)
    assert min(r["cost_month"] for r in rows) == "2020-01-01"
    assert max(r["cost_month"] for r in rows) == "2025-12-01"
    for r in rows:
        assert r["total_cost"] == (r["fuel_cost"] + r["maintenance_cost"]
                                   + r["subcontractor_cost"] + r["facility_cost"]
                                   + r["technology_cost"])
        assert r["cost_month"] <= "2025-12-31"

    header = ["cost_month", "hub_id", "fuel_cost", "maintenance_cost",
              "subcontractor_cost", "facility_cost", "technology_cost", "total_cost"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\r\n",
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    print("wrote %d rows to %s" % (len(rows), OUT_PATH))
    print("cost_month range: %s .. %s" % (rows[0]["cost_month"], rows[-1]["cost_month"]))
    print("maintenance total == WO total:",
          sum(r["maintenance_cost"] for r in rows), "==", sum(wo_m.values()))
    for y in range(2020, 2026):
        yr = [r for r in rows if r["cost_month"][:4] == str(y)]
        print("  %d total %12d  fuel %9d  maint %7d  sub %9d" % (
            y, sum(r["total_cost"] for r in yr), sum(r["fuel_cost"] for r in yr),
            sum(r["maintenance_cost"] for r in yr), sum(r["subcontractor_cost"] for r in yr)))
    print("HUB-CMH by year:")
    for y in range(2020, 2026):
        yr = [r for r in rows if r["cost_month"][:4] == str(y) and r["hub_id"] == "HUB-CMH"]
        print("  %d total %12d  maint %7d  sub %9d" % (
            y, sum(r["total_cost"] for r in yr), sum(r["maintenance_cost"] for r in yr),
            sum(r["subcontractor_cost"] for r in yr)))
    print("per-hub total 2024 vs 2025:")
    for h in sorted(r["hub_id"] for r in rows if r["cost_month"] == "2024-01-01"):
        t24 = sum(r["total_cost"] for r in rows if r["hub_id"] == h and r["cost_month"][:4] == "2024")
        t25 = sum(r["total_cost"] for r in rows if r["hub_id"] == h and r["cost_month"][:4] == "2025")
        s24 = sum(r["subcontractor_cost"] for r in rows if r["hub_id"] == h and r["cost_month"][:4] == "2024")
        s25 = sum(r["subcontractor_cost"] for r in rows if r["hub_id"] == h and r["cost_month"][:4] == "2025")
        print("  %s total %d -> %d (%+.1f%%)  sub %d -> %d (%+.1f%%)"
              % (h, t24, t25, 100.0 * (t25 - t24) / t24, s24, s25, 100.0 * (s25 - s24) / s24))



if __name__ == "__main__":
    main()
