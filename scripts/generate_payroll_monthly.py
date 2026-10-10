#!/usr/bin/env python3
"""Deterministic generator for seeds/payroll_monthly.csv (driver x month, labour cost).

One row per driver x month, from the first day of the driver's hire month (a partial first
month) through 2025-12-01, for all 56 drivers in seeds/drivers.csv -- 2954 rows. This is the
payroll and headcount-cost data the reports named as missing: wages, hours and rates, so
cost-per-route and labour-productivity analysis become possible.

Pure arithmetic, no randomness: the same input seeds always give a byte-identical CSV.
Reads seeds/drivers.csv, seeds/routes.csv, seeds/shipments.csv and seeds/incidents.csv
(all read-only). Money is computed in Decimal with half-up rounding so every row ties to
the cent under the warehouse's own decimal round().

Design:

* ``hub_id`` is the driver's drivers.csv hub, constant for the driver. Every one of the
  10,887 routes.csv rows carries the driver's drivers.csv hub_id, so no driver moves hub
  anywhere in the record. The schema would support a mid-tenure move (a new hub_id from the
  month it happened), but the corpus records none, so none is modelled.
* ``hours_worked`` is NOT modelled for 2023-01 .. 2025-12, where the routes record exists:
  it is the driver's routes.csv row count for the month x HOURS_PER_ROUTE (9.0). Hours
  track routes exactly, which is the tie that makes payroll defensible and cost-per-route
  meaningful (enforced by tests/assert_payroll_hours_reconcile_routes.sql). A 2023-2025
  month with no routes carries zero hours and zero pay: the row exists (coverage is
  complete) but the driver is not paid.
* Before 2023 no routes are recorded at all, so the absence of a route is not evidence of
  no work. Those months are a modelled steady state: the driver's 2023 mean monthly routes
  (over 2023 months with >= 1 route) x HOURS_PER_ROUTE x a year factor (YEAR_FACTOR).
* ``hourly_rate`` is index-based: k = the driver's 0-based position in driver_id order.
  Employees: 31.00 + 0.90 x (k % 5). Contractors: 64.00 + 1.80 x (k % 5) -- roughly double,
  because the contractor rate is all-in (it embeds the contractor's own benefits and
  overhead), so contractors carry no benefits load and no overtime premium. Both escalate
  2.5% a year from 2018.
* ``gross_pay`` = hours_worked x hourly_rate. ``total_cost`` = gross_pay + overtime_hours x
  hourly_rate x 0.5 (the 50% overtime premium on hours already counted in hours_worked).
* ``overtime_hours`` (employees only; 0 for contractors and whenever hours are 0) =
  OT_BASE + ot_hub + ot_c42:
    - OT_BASE: a steady 4.0 hours for every employee-month with hours.
    - ot_hub: OT_DAMAGE_PER_INCIDENT x the hub-month's damage incidents above the hub's own
      worst 2023-2024 month. Zero in every 2023-2024 month by construction; it switches on
      only in 2025, and the HUB-CMH handling-damage cluster (2, 2 -> 15 damage incidents
      across 2023/2024/2025) is what lifts CMH overtime.
    - ot_c42: OT_PER_C42_EXCEPTION x the hub-month's CLI-0042 exceptions (shipments
      originating at the hub, created that month, status delayed or failed) above the hub's
      own worst 2023-2024 month, 2025 only -- the overtime pressure the CLI-0042 account's
      2025 decline puts on the hubs its freight runs through (see caveat 3).
  Overtime is a subset of hours worked, so it is capped at hours_worked: a thin month (one
  9-hour route) in a high-damage CMH month would otherwise carry more overtime than hours.
  The capped driver-months are listed in the review trail.

Data caveats (stated, not smoothed away):

1. Six drivers run no routes after 2024-12: DRV-01189, DRV-01190, DRV-01191, DRV-01192,
   DRV-01193 and DRV-01194 are 'active' in drivers.csv but have no routes.csv rows in 2025,
   so their 2025 rows carry zero hours and zero pay. This is a gap in the routes record,
   not modelled attrition.
2. DRV-01188 has an exit record (hr_docs) dated 2025-09-15 but runs routes through 2025-12.
   Payroll follows the routes record (hours must track routes), so the driver carries hours
   and pay through 2025-12. The discrepancy is flagged here, not resolved.
3. CLI-0042 overtime is hub-level, not route-level. None of the 416 CLI-0042 shipments
   created in 2025 carries a route_id (against 1588 of 1593 for every other client), so the
   account's 2025 pressure cannot be attached to individual drivers' routes without
   inventing route links. Instead the account's 2025 exception load (delayed + failed
   CLI-0042 shipments: 67 in 2025 vs 8 in 2023 and 8 in 2024, led by HUB-CHI's 8 in
   2025-01) is expressed as overtime for every employee working at the hub the freight
   originates from. 2023-2024 are steady: the term is exactly 0 there by construction.

Nothing is dated after 2025-12-31 and no 2025 signal (CMH damage cluster, the CLI-0042
decline) appears in 2023-2024.

Run:  python3 scripts/generate_payroll_monthly.py
"""
import csv
import os
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")

DRIVERS_PATH = os.path.join(SEEDS, "drivers.csv")
ROUTES_PATH = os.path.join(SEEDS, "routes.csv")
SHIP_PATH = os.path.join(SEEDS, "shipments.csv")
INC_PATH = os.path.join(SEEDS, "incidents.csv")
OUT_PATH = os.path.join(SEEDS, "payroll_monthly.csv")

LAST_MONTH = (2025, 12)
ROUTES_FROM = 2023            # first year of the routes record
EXPECTED_ROWS = 2954

# --- labour shape parameters ----------------------------------------------------------
HOURS_PER_ROUTE = Decimal("9.0")   # one route = one driver-day

# Pre-2023 steady-state hours relative to the driver's 2023 mean month.
YEAR_FACTOR = {2018: Decimal("0.90"), 2019: Decimal("0.93"), 2020: Decimal("0.95"),
               2021: Decimal("0.97"), 2022: Decimal("0.99")}

# Base hourly rates by employment type: base + step x (k % 5). Contractor rates are all-in.
EMPLOYEE_BASE, EMPLOYEE_STEP = Decimal("31.00"), Decimal("0.90")
CONTRACTOR_BASE, CONTRACTOR_STEP = Decimal("64.00"), Decimal("1.80")
ESCALATION = Decimal("1.025")      # annual, from RATE_BASE_YEAR
RATE_BASE_YEAR = 2018

OT_PREMIUM = Decimal("0.5")        # overtime paid at 1.5x; the 0.5 is the premium
OT_BASE = Decimal("4.0")
OT_DAMAGE_PER_INCIDENT = Decimal("6.0")
OT_PER_C42_EXCEPTION = Decimal("2.5")
C42 = "CLI-0042"
C42_EXCEPTION_STATUSES = ("delayed", "failed")

CENT = Decimal("0.01")
TENTH = Decimal("0.1")


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


def q(value, unit):
    return value.quantize(unit, rounding=ROUND_HALF_UP)


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / (sxx * syy) ** 0.5


def main():
    drivers = sorted(read_csv(DRIVERS_PATH), key=lambda d: d["driver_id"])
    routes = read_csv(ROUTES_PATH)
    shipments = read_csv(SHIP_PATH)
    incidents = read_csv(INC_PATH)

    # hub_id is constant per driver: verify the routes record never disagrees.
    driver_hub = {d["driver_id"]: d["hub_id"] for d in drivers}
    assert all(r["hub_id"] == driver_hub[r["driver_id"]] for r in routes)

    routes_m = Counter((r["driver_id"], r["service_date"][:7]) for r in routes)

    # CLI-0042 exception load by origin hub and creation month (caveat 3: the account's 2025
    # shipments carry no route_id, so its pressure is placed on the hub, not on routes).
    c42_exc_m = Counter((s["origin_hub_id"], s["created_at"][:7]) for s in shipments
                        if s["client_id"] == C42 and s["status"] in C42_EXCEPTION_STATUSES)
    # Same construction as damage_base: each hub's own worst 2023-2024 month, so ot_c42 is
    # 0 throughout 2023-2024 and only switches on when 2025 exceeds it.
    c42_exc_base = {
        hub: max(c42_exc_m[(hub, month_key(y, m))] for y in (2023, 2024) for m in range(1, 13))
        for hub in set(driver_hub.values())}

    damage_m = Counter((i["hub_id"], i["occurred_at"][:7]) for i in incidents
                       if i["type"] == "damage")
    # Each hub's damage baseline is its own worst 2023-2024 month, so ot_hub is 0 throughout
    # 2023-2024 by construction and only switches on when 2025 exceeds it.
    damage_base = {
        hub: max(damage_m[(hub, month_key(y, m))] for y in (2023, 2024) for m in range(1, 13))
        for hub in set(driver_hub.values())}

    rows = []
    ot_hub_terms = []   # (hub, year, ot_hub) for every employee-month with hours
    ot_c42_terms = []   # (hub, year, ot_c42) for every employee-month with hours
    capped = []         # (driver_id, month) where overtime was capped at hours_worked
    for k, d in enumerate(drivers):
        drv, hub, etype = d["driver_id"], d["hub_id"], d["employment_type"]
        is_employee = etype == "employee"
        if is_employee:
            base_rate = EMPLOYEE_BASE + EMPLOYEE_STEP * (k % 5)
        else:
            base_rate = CONTRACTOR_BASE + CONTRACTOR_STEP * (k % 5)

        # steady-state month for the pre-2023 background (only drivers hired before 2023)
        active_2023 = [routes_m[(drv, month_key(ROUTES_FROM, m))] for m in range(1, 13)
                       if routes_m[(drv, month_key(ROUTES_FROM, m))] > 0]
        mean_2023 = Decimal(sum(active_2023)) / len(active_2023) if active_2023 else None

        hire = (int(d["hire_date"][:4]), int(d["hire_date"][5:7]))
        for (year, month) in months_between(hire, LAST_MONTH):
            key = month_key(year, month)
            routes_run = routes_m[(drv, key)]

            if year >= ROUTES_FROM:
                hours = q(HOURS_PER_ROUTE * routes_run, TENTH)
            else:
                hours = q(mean_2023 * HOURS_PER_ROUTE * YEAR_FACTOR[year], TENTH)

            rate = q(base_rate * ESCALATION ** (year - RATE_BASE_YEAR), CENT)
            gross = q(hours * rate, CENT)

            if is_employee and hours > 0:
                ot_hub = OT_DAMAGE_PER_INCIDENT * max(0, damage_m[(hub, key)] - damage_base[hub])
                if year == 2025:
                    ot_c42 = OT_PER_C42_EXCEPTION * max(0, c42_exc_m[(hub, key)] - c42_exc_base[hub])
                else:
                    ot_c42 = Decimal(0)
                overtime = q(OT_BASE + ot_hub + ot_c42, TENTH)
                if overtime > hours:
                    # overtime is a subset of hours worked: a thin month (e.g. one 9-hour
                    # route) in a high-damage hub-month cannot carry more overtime than hours
                    overtime = hours
                    capped.append((drv, key))
                ot_hub_terms.append((hub, year, ot_hub))
                ot_c42_terms.append((hub, year, ot_c42))
            else:
                overtime = q(Decimal(0), TENTH)

            total = q(gross + overtime * rate * OT_PREMIUM, CENT)
            rows.append({
                "payroll_month": key + "-01",
                "driver_id": drv,
                "hub_id": hub,
                "employment_type": etype,
                "hours_worked": hours,
                "hourly_rate": rate,
                "gross_pay": gross,
                "overtime_hours": overtime,
                "total_cost": total,
                "_routes": routes_run,
            })

    rows.sort(key=lambda r: (r["payroll_month"], r["driver_id"]))

    # guard rails
    first_hire = min(d["hire_date"][:7] for d in drivers) + "-01"
    assert len(rows) == EXPECTED_ROWS, len(rows)
    assert min(r["payroll_month"] for r in rows) == first_hire
    assert max(r["payroll_month"] for r in rows) == "2025-12-01"
    for r in rows:
        assert r["payroll_month"] <= "2025-12-31"
        assert r["gross_pay"] == q(r["hours_worked"] * r["hourly_rate"], CENT)
        assert r["total_cost"] == q(r["gross_pay"]
                                    + r["overtime_hours"] * r["hourly_rate"] * OT_PREMIUM, CENT)
        if r["employment_type"] == "contractor":
            assert r["overtime_hours"] == 0 and r["total_cost"] == r["gross_pay"]
        assert r["overtime_hours"] <= r["hours_worked"], r
        if r["payroll_month"][:4] >= str(ROUTES_FROM):
            assert (r["hours_worked"] > 0) == (r["_routes"] >= 1), r

    def ot_total(pred):
        return sum(r["overtime_hours"] for r in rows if pred(r))

    cmh_ot = {y: ot_total(lambda r, y=y: r["hub_id"] == "HUB-CMH" and r["payroll_month"][:4] == str(y))
              for y in (2023, 2024, 2025)}
    assert cmh_ot[2025] > cmh_ot[2023] and cmh_ot[2025] > cmh_ot[2024], cmh_ot
    assert all(t == 0 for (hub, y, t) in ot_hub_terms if hub == "HUB-CMH" and y in (2023, 2024))

    # ot_c42 (term values, before any cap): 0 in 2023-2024, live in 2025, led by HUB-CHI.
    c42_ot = defaultdict(Decimal)   # (hub, year) -> ot_c42 total
    for (hub, y, t) in ot_c42_terms:
        c42_ot[(hub, y)] += t
    assert all(t == 0 for (_hub, y, t) in ot_c42_terms if y in (2023, 2024))
    assert sum(t for (_hub, y, t) in ot_c42_terms if y == 2025) > 0
    assert (c42_ot[("HUB-CHI", 2025)] > c42_ot[("HUB-CHI", 2023)]
            and c42_ot[("HUB-CHI", 2025)] > c42_ot[("HUB-CHI", 2024)])

    header = ["payroll_month", "driver_id", "hub_id", "employment_type", "hours_worked",
              "hourly_rate", "gross_pay", "overtime_hours", "total_cost"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\r\n",
                           quoting=csv.QUOTE_MINIMAL, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # review trail
    print("wrote %d rows to %s" % (len(rows), OUT_PATH))
    print("payroll_month range: %s .. %s" % (rows[0]["payroll_month"], rows[-1]["payroll_month"]))
    recorded = [r for r in rows if r["payroll_month"][:4] >= str(ROUTES_FROM)]
    print("hours vs routes, 2023-2025 driver-months: Pearson r = %.6f (n=%d)" % (
        pearson([float(r["hours_worked"]) for r in recorded], [r["_routes"] for r in recorded]),
        len(recorded)))
    print("overtime hours by hub, 2023 / 2024 / 2025:")
    for hub in sorted(set(driver_hub.values())):
        print("  %s  %8s %8s %8s" % ((hub,) + tuple(
            ot_total(lambda r, y=y: r["hub_id"] == hub and r["payroll_month"][:4] == str(y))
            for y in (2023, 2024, 2025))))
    print("overtime capped at hours_worked (%d): %s" % (
        len(capped), ", ".join("%s %s" % c for c in capped) or "none"))
    print("CLI-0042 exceptions (delayed+failed) by year: %s" % ", ".join(
        "%d %d" % (y, sum(n for (_h, key), n in c42_exc_m.items() if key[:4] == str(y)))
        for y in (2023, 2024, 2025)))
    print("CLI-0042 exception overtime term (ot_c42) by year: %s" % ", ".join(
        "%d %s" % (y, sum(t for (_h, yy, t) in ot_c42_terms if yy == y))
        for y in (2023, 2024, 2025)))
    print("2025 ot_c42 by hub (2023-2024 baseline = worst month):")
    for hub in sorted(set(driver_hub.values())):
        print("  %s  %7s hours  (exceptions 2025 %d, baseline %d)" % (
            hub, c42_ot[(hub, 2025)],
            sum(n for (h, key), n in c42_exc_m.items() if h == hub and key[:4] == "2025"),
            c42_exc_base[hub]))
    print("cost per route, 2023-2025 (total_cost / routes):")
    for etype in ("employee", "contractor"):
        sub = [r for r in recorded if r["employment_type"] == etype]
        cost, n = sum(r["total_cost"] for r in sub), sum(r["_routes"] for r in sub)
        print("  %-10s %12s over %5d routes = %8.2f" % (etype, cost, n, cost / n))
    print("whole-book labour cost by year:")
    by_year = defaultdict(lambda: [Decimal(0), Decimal(0), Decimal(0)])
    for r in rows:
        acc = by_year[r["payroll_month"][:4]]
        acc[0] += r["total_cost"]
        acc[1] += r["hours_worked"]
        acc[2] += r["overtime_hours"]
    for y in sorted(by_year):
        print("  %s total %13s  hours %9s  overtime %7s" % ((y,) + tuple(by_year[y])))
    idle_2025 = sorted({r["driver_id"] for r in rows if r["payroll_month"][:4] == "2025"}
                       - {drv for (drv, key) in routes_m if key[:4] == "2025"})
    print("drivers with no 2025 routes (zero 2025 pay):", ", ".join(idle_2025))


if __name__ == "__main__":
    main()
