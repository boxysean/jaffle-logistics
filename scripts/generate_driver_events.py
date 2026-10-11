#!/usr/bin/env python3
"""Deterministic generator for seeds/driver_events.csv: the driver employment-event log,
one row per employment event, every driver, 2018-01-01 .. 2025-12-31.

Writes the whole file from scratch (same seed -> same bytes), so re-running it is
idempotent. Every driver_id is a real row of seeds/drivers.csv, every hub_id a real hub
of seeds/hubs.csv. drivers.csv, hubs.csv, hr_docs.csv, payroll_monthly.csv and
routes.csv are read, never written: the roster stays fixed.

What the log holds:
  * hire           exactly one per driver, on the roster hire_date at the roster hub,
                   so the 56 hire rows rebuild seeds/drivers.csv (and nothing for a
                   driver predates them).
  * certification  one per hr_docs row with doc_type = 'certification', on that doc's
                   created_at, at the driver's roster hub. None invented.
  * leave_start /  absence spells of 2-14 days, paired (leave_end is the last day off).
    leave_end      Seasonal: most in Dec-Feb, a smaller Jul-Aug peak. From 2023, when
                   routes.csv exists, a spell only sits where the driver ran no route,
                   so leave never contradicts the route record.
  * termination    seven, all in 2025 (see below).
  * transfer       none. Every driver has exactly one hub_id across payroll_monthly.csv
                   and routes.csv, and it is the roster hub; a hub move would contradict
                   both. The generator asserts this and stops if it ever stops holding.

Story the log tells:
  * 2023 and 2024 are quiet: no termination, ordinary seasonal leave.
  * 2025 has seven departures. DRV-01188 (HUB-BER, roster status 'disputed') is
    deactivated for cause on 2025-09-15, which the driver disputes (the exit record in
    hr_docs.csv). The six silent leavers DRV-01189 .. DRV-01194 ran no route in 2025
    and drew no pay, yet the roster still calls them active: this log records their
    resignations, January-March 2025, voluntary. Two are at HUB-AMS, so the strained
    hub carries the most voluntary leavers.
  * HUB-AMS takes a modest 2025 rise in leave: a little more often and a little longer
    than its own other years. Not a cliff.
  * Nothing for a driver after their termination or before their hire.

Run:  python3 scripts/generate_driver_events.py
"""
import csv
import datetime
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")
OUT_PATH = os.path.join(SEEDS, "driver_events.csv")

SEED = 20251231
START = datetime.date(2018, 1, 1)
END = datetime.date(2025, 12, 31)
FIRST_EVENT = 100001  # EVT-100001, assigned in file order
ROUTES_FROM = datetime.date(2023, 1, 1)  # routes.csv begins here

HEADER = ["event_id", "driver_id", "hub_id", "event_date", "event_type", "reason", "voluntary"]
EVENT_ORDER = {"hire": 0, "certification": 1, "transfer": 2, "leave_end": 3,
               "leave_start": 4, "termination": 5}

# The recorded exit: matches the 2025-09-15 EXIT RECORD in hr_docs.csv.
DISPUTED = ("DRV-01188", datetime.date(2025, 9, 15),
            "deactivated for cause — repeated route failures, driver disputes")

# The six silent leavers: (driver, termination date, reason). January-March 2025.
SILENT_LEAVERS = [
    ("DRV-01189", datetime.date(2025, 1, 17), "resigned — competing offer"),
    ("DRV-01190", datetime.date(2025, 2, 7), "resigned — relocation"),
    ("DRV-01191", datetime.date(2025, 1, 31), "resigned — personal reasons"),
    ("DRV-01192", datetime.date(2025, 3, 14), "resigned — relocation"),
    ("DRV-01193", datetime.date(2025, 2, 21), "resigned — personal reasons"),
    ("DRV-01194", datetime.date(2025, 3, 7), "resigned — competing offer"),
]

# Leave spells per driver-year at full-year employment, and spell length (days).
LEAVE_RATE = 1.6
LEAVE_RATE_AMS_2025 = 2.15
LENGTH = (2, 14, 4)            # triangular(low, high, mode)
LENGTH_AMS_2025 = (3, 14, 6)
FIRST_LEAVE_AFTER_HIRE = 30    # no leave in a driver's first month
LEAVE_GAP_DAYS = 14            # min days between two spells for a driver

MONTH_WEIGHTS = {1: 3.0, 2: 2.6, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.1,
                 7: 1.9, 8: 2.1, 9: 1.0, 10: 1.0, 11: 1.1, 12: 3.0}
REASONS = {
    "winter": [("sick leave", 0.50), ("annual leave", 0.38), ("family leave", 0.12)],
    "summer": [("annual leave", 0.76), ("sick leave", 0.14), ("family leave", 0.10)],
    "other": [("annual leave", 0.44), ("sick leave", 0.42), ("family leave", 0.14)],
}


def read_csv(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def parse_date(s):
    y, m, d = (int(x) for x in s[:10].split("-"))
    return datetime.date(y, m, d)


def weighted_choice(rng, pairs):
    x = rng.random() * sum(w for _, w in pairs)
    for value, w in pairs:
        x -= w
        if x < 0:
            return value
    return pairs[-1][0]


def season(month):
    if month in (12, 1, 2):
        return "winter"
    if month in (7, 8):
        return "summer"
    return "other"


def assert_one_hub_per_driver(drivers, payroll, routes):
    """No transfers: every driver has one hub in payroll and routes, the roster hub."""
    hubs = defaultdict(set)
    for r in payroll + routes:
        hubs[r["driver_id"]].add(r["hub_id"])
    for did, seen in sorted(hubs.items()):
        if len(seen) > 1:
            sys.exit("%s spans hubs %s in payroll/routes: a transfer would be needed" % (did, sorted(seen)))
        if did in drivers and seen != {drivers[did]["hub_id"]}:
            sys.exit("%s runs from %s but the roster says %s" % (did, sorted(seen), drivers[did]["hub_id"]))


def place_leave(rng, did, hub, year, lo, hi, route_days, taken):
    """One leave spell in [lo, hi] for a driver-year, or None. From 2023 the spell must
    not touch a route day; spells keep LEAVE_GAP_DAYS apart."""
    strained = hub == "HUB-AMS" and year == 2025
    months = [m for m in range(1, 13)
              if datetime.date(year, m, 1) <= hi
              and (datetime.date(year + 1, 1, 1) if m == 12 else datetime.date(year, m + 1, 1)) > lo]
    if not months:
        return None
    for _ in range(80):
        month = weighted_choice(rng, [(m, MONTH_WEIGHTS[m]) for m in months])
        start = datetime.date(year, month, 1) + datetime.timedelta(days=rng.randint(0, 27))
        length = int(round(rng.triangular(*(LENGTH_AMS_2025 if strained else LENGTH))))
        end = start + datetime.timedelta(days=length - 1)
        if start < lo or end > hi:
            continue
        if any(start <= d <= end for d in route_days):
            continue
        gap = datetime.timedelta(days=LEAVE_GAP_DAYS)
        if any(start <= e + gap and s <= end + gap for s, e in taken):
            continue
        return start, end
    return None


def main():
    rng = random.Random(SEED)
    roster = read_csv("drivers")
    roster.sort(key=lambda d: d["driver_id"])
    drivers = {d["driver_id"]: d for d in roster}
    hub_ids = {h["hub_id"] for h in read_csv("hubs")}
    hr_docs = read_csv("hr_docs")
    payroll = read_csv("payroll_monthly")
    routes = read_csv("routes")

    assert len(drivers) == 56, len(drivers)
    assert_one_hub_per_driver(drivers, payroll, routes)

    route_days = defaultdict(set)
    for r in routes:
        route_days[r["driver_id"]].add(parse_date(r["service_date"]))

    terminations = {DISPUTED[0]: (DISPUTED[1], DISPUTED[2], "false")}
    for did, day, reason in SILENT_LEAVERS:
        terminations[did] = (day, reason, "true")
    for did in drivers:
        if drivers[did]["status"] != "active":
            assert did in terminations, did
    for did, _, _ in SILENT_LEAVERS:
        last = max(route_days[did])
        assert last.year == 2024 and last.month == 12, (did, last)

    rows = []

    def add(did, day, etype, reason="", voluntary=""):
        rows.append({"driver_id": did, "hub_id": drivers[did]["hub_id"], "event_date": day.isoformat(),
                     "event_type": etype, "reason": reason, "voluntary": voluntary})

    # --- hire: one per driver, the roster rebuilt ---
    for d in roster:
        add(d["driver_id"], parse_date(d["hire_date"]), "hire")

    # --- certification: one per hr_docs certification row ---
    for doc in sorted(hr_docs, key=lambda r: (r["created_at"], r["hr_doc_id"])):
        if doc["doc_type"] == "certification":
            add(doc["driver_id"], parse_date(doc["created_at"]), "certification")

    # --- leave: seasonal spells, driver by driver, year by year ---
    for d in roster:
        did, hub = d["driver_id"], d["hub_id"]
        hire = parse_date(d["hire_date"])
        first = hire + datetime.timedelta(days=FIRST_LEAVE_AFTER_HIRE)
        if did in terminations:
            # the silent leavers did no work in 2025; DRV-01188's leave stops before
            # the August warnings
            last = datetime.date(2024, 12, 31) if did != DISPUTED[0] else datetime.date(2025, 7, 31)
        else:
            last = END
        taken = []
        for year in range(first.year, last.year + 1):
            lo = max(first, datetime.date(year, 1, 1))
            hi = min(last, datetime.date(year, 12, 31))
            if lo > hi:
                continue
            rate = LEAVE_RATE_AMS_2025 if (hub == "HUB-AMS" and year == 2025) else LEAVE_RATE
            expected = rate * ((hi - lo).days + 1) / 365.0
            n = int(expected) + (1 if rng.random() < expected - int(expected) else 0)
            days = route_days[did] if year >= ROUTES_FROM.year else set()
            for _ in range(n):
                spell = place_leave(rng, did, hub, year, lo, hi, days, taken)
                if spell is None:
                    continue
                taken.append(spell)
                reason = weighted_choice(rng, REASONS[season(spell[0].month)])
                add(did, spell[0], "leave_start", reason)
                add(did, spell[1], "leave_end", reason)

    # --- termination: the seven 2025 departures ---
    for did in sorted(terminations):
        day, reason, voluntary = terminations[did]
        add(did, day, "termination", reason, voluntary)

    rows.sort(key=lambda r: (r["event_date"], r["driver_id"], EVENT_ORDER[r["event_type"]]))
    for i, row in enumerate(rows):
        row["event_id"] = "EVT-%06d" % (FIRST_EVENT + i)

    # guard rails
    hires = {d["driver_id"]: d["hire_date"] for d in roster}
    by_driver = defaultdict(list)
    for row in rows:
        assert START.isoformat() <= row["event_date"] <= END.isoformat(), row
        assert row["hub_id"] in hub_ids and row["hub_id"] == drivers[row["driver_id"]]["hub_id"], row
        assert row["event_date"] >= hires[row["driver_id"]], row
        assert bool(row["reason"]) == (row["event_type"] in ("leave_start", "leave_end", "termination")), row
        assert bool(row["voluntary"]) == (row["event_type"] == "termination"), row
        by_driver[row["driver_id"]].append(row)
    for did, evs in by_driver.items():
        types = [e["event_type"] for e in evs]
        assert types[0] == "hire" and types.count("hire") == 1, did
        assert evs[0]["event_date"] == hires[did], did
        assert types.count("transfer") == 0, did
        if "termination" in types:
            assert types[-1] == "termination" and types.count("termination") == 1, did
        open_leave = None
        for e in evs:
            if e["event_type"] == "leave_start":
                assert open_leave is None, did
                open_leave = e
            elif e["event_type"] == "leave_end":
                assert open_leave is not None and e["event_date"] > open_leave["event_date"], did
                open_leave = None
        assert open_leave is None, did
    terms = [r for r in rows if r["event_type"] == "termination"]
    assert len(terms) == 7 and all(r["event_date"][:4] == "2025" for r in terms), terms
    assert len([r for r in rows if r["event_type"] == "certification"]) == \
        sum(1 for r in hr_docs if r["doc_type"] == "certification")

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for row in rows:
            w.writerow(row)

    print("wrote %d rows: %s" % (len(rows), os.path.relpath(OUT_PATH)))
    print("by type:", dict(sorted(Counter(r["event_type"] for r in rows).items())))
    print("by year:", dict(sorted(Counter(r["event_date"][:4] for r in rows).items())))
    print("event_date range: %s .. %s" % (rows[0]["event_date"], rows[-1]["event_date"]))
    starts = [r for r in rows if r["event_type"] == "leave_start"]
    print("leave starts by month:", dict(sorted(Counter(int(r["event_date"][5:7]) for r in starts).items())))
    print("terminations by hub:", dict(sorted(Counter(r["hub_id"] for r in terms).items())))

    # leave per driver-year and mean spell length, HUB-AMS 2025 against its other years
    ends = {}
    for did, evs in by_driver.items():
        s = None
        for e in evs:
            if e["event_type"] == "leave_start":
                s = e
            elif e["event_type"] == "leave_end":
                ends[id(s)] = (parse_date(e["event_date"]) - parse_date(s["event_date"])).days + 1
    for hub in sorted(hub_ids):
        stats = []
        for band in ("2023-2024", "2025"):
            yrs = (2023, 2024) if band == "2023-2024" else (2025,)
            sp = [r for r in starts if r["hub_id"] == hub and int(r["event_date"][:4]) in yrs]
            n_dy = sum(1 for d in roster if d["hub_id"] == hub for y in yrs
                       if d["hire_date"][:4] <= str(y) and not (d["driver_id"] in terminations and y == 2025))
            mean = sum(ends[id(r)] for r in sp) / len(sp) if sp else 0.0
            stats.append("%s %.2f spells/driver-yr, %.1f days" % (band, len(sp) / n_dy, mean))
        print("%s leave: %s" % (hub, "; ".join(stats)))


if __name__ == "__main__":
    main()
