#!/usr/bin/env python3
"""Deterministic generator for seeds/vehicle_inspections.csv: the vehicle inspection log,
one row per inspection, every vehicle, 2023-01-01 .. 2025-12-31, each carrying the
odometer reading at the time of inspection.

Writes the whole file from scratch (same seed -> same bytes), so re-running it is
idempotent. Every vehicle_id is a real row of seeds/vehicles.csv, every hub_id a real
hub, every incident id a real accident in seeds/incidents.csv. seeds/vehicles.csv is
read, never written: its odometer stays the 2025-12-31 snapshot.

The odometer series (one per vehicle, odometer_at(vehicle, date)):
  * travel = min(routes run x 300 km, half the snapshot) is what the vehicle drove in
    the window; gap = max(200, 2% of the snapshot) is the tail between the last 2025
    reading and the snapshot; start = snapshot - travel - gap.
  * travel is spread over the vehicle's routes in (service_date, route_id) order with
    weights 1 +/- 0.3. The reading on a date is start plus every route on or before
    it: a step function, never decreasing, always below the snapshot.

What the log holds:
  * pre_trip       one per route in seeds/routes.csv (the driver's walkaround).
  * periodic       the scheduled service, planned from the odometer forward: due every
                   20,000 km or 365 days, whichever comes first, on the last route day
                   before the next day's running would carry it past 20,000 km.
  * annual         one statutory roadworthiness check per vehicle per year, on a fixed
                   day per vehicle, every status (retired and maintenance included).
  * post_incident  one per 2023-2025 accident incident that names a vehicle (13/10/14),
                   the day after, at the incident's hub. Notes carry
                   'Linked incident: INC-YYYY-NNNNN.', reconciled by
                   tests/assert_post_incident_inspections_reconcile_accidents.sql.

Story the log tells:
  * 2023 and 2024 are orderly: every periodic on time, steady intervals, mostly pass.
  * 2025 shows mild strain, not a fleet collapse: a handful of periodics served late
    (LATE_PER_HUB, spread over four hubs, HUB-AMS no worse than any other), and a few
    more defects at every hub. HUB-AMS sits slightly below the fleet's 2025 defect
    rate, so nothing here points at the fleet for the Amsterdam handling damage.

Run:  python3 scripts/generate_vehicle_inspections.py
"""
import csv
import datetime
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")
OUT_PATH = os.path.join(SEEDS, "vehicle_inspections.csv")

SEED = 20251101
START = datetime.date(2023, 1, 1)
END = datetime.date(2025, 12, 31)
FIRST_INSPECTION = 100000  # INS-100000, mirrors DBE-100000

KM_PER_ROUTE = 300
SERVICE_INTERVAL_KM = 20000
SERVICE_INTERVAL_DAYS = 365
BOOKING_WINDOW_DAYS = 14   # a time-due service is booked into the last two weeks

# Accident incidents that name a vehicle, per year. Checked, not assumed.
EXPECTED_ACCIDENTS = {"2023": 13, "2024": 10, "2025": 14}

# 2025 late periodics per hub (8 in all). HUB-AMS is never the worst.
LATE_PER_HUB = {"HUB-AMS": 1, "HUB-PAR": 2, "HUB-BER": 2, "HUB-ZRH": 2, "HUB-VIE": 1}
LATE_FACTOR = (1.15, 1.6)

# Non-pass share per type and year band; fail share is of all rows, not of non-pass.
NON_PASS = {
    "pre_trip": {"2023-2024": 0.040, "2025": 0.068},
    "periodic": {"2023-2024": 0.10, "2025": 0.18},
    "annual": {"2023-2024": 0.07, "2025": 0.14},
}
FAIL = {
    "pre_trip": {"2023-2024": 0.002, "2025": 0.006},
    "periodic": {"2023-2024": 0.0, "2025": 0.025},
    "annual": {"2023-2024": 0.0, "2025": 0.03},
}
# 2025 strain is fleet-wide, a touch heavier outside Amsterdam. 2023-2024 are flat.
HUB_STRAIN_2025 = {"HUB-AMS": 0.88, "HUB-PAR": 1.06, "HUB-BER": 1.04, "HUB-VIE": 1.00, "HUB-ZRH": 1.02}

DEFECT_WEIGHTS = [
    ("lights", 0.24), ("brakes", 0.22), ("tyres", 0.18), ("body_door", 0.12),
    ("electrical", 0.09), ("refrigeration", 0.06), ("fluids", 0.06), ("other", 0.03),
]
POST_INCIDENT_WEIGHTS = [
    ("body_door", 0.42), ("lights", 0.20), ("tyres", 0.14), ("brakes", 0.10),
    ("electrical", 0.08), ("other", 0.06),
]

HEADER = ["inspection_id", "vehicle_id", "hub_id", "inspected_at", "inspection_type",
          "odometer_reading", "result", "defect_area", "notes"]

# --- notes: pass templates per type and year band ---
PASS_NOTES = {
    ("pre_trip", "2023-2024"): [
        "Pre-trip walkaround complete — no defects found.",
        "Pre-trip check — lights, tyres and mirrors OK.",
        "Walkaround done before departure — tyres, lights and load restraints OK.",
        "Pre-trip complete — fluid levels and tyre pressures within spec.",
        "Daily check complete — no faults reported by driver.",
        "Pre-trip walkaround — all lamps working, no leaks under the vehicle.",
    ],
    ("pre_trip", "2025"): [
        "Pre-trip walkaround complete — no defects found.",
        "Pre-trip check — lights, tyres and mirrors OK.",
        "Walkaround done before departure — tyres, lights and load restraints OK.",
        "Pre-trip complete — fluid levels and tyre pressures within spec.",
        "Daily check complete — no faults reported by driver.",
        "Pre-trip walkaround — all lamps working, no leaks under the vehicle.",
    ],
    ("periodic", "2023-2024"): [
        "Scheduled periodic service — oil and filters, brakes and fluids checked.",
        "Periodic service complete — filters changed, brakes within limits.",
        "Scheduled service — oil change, tyre rotation and brake check, no findings.",
        "Periodic service — fluids topped up, pads and discs within limits.",
        "Scheduled periodic inspection — no defects, returned to service the same day.",
    ],
    ("periodic", "2025"): [
        "Scheduled periodic service — oil and filters, brakes and fluids checked.",
        "Periodic service complete — filters changed, brakes within limits.",
        "Scheduled service — oil change, tyre rotation and brake check, no findings.",
        "Periodic service — fluids topped up, pads and discs within limits.",
        "Scheduled periodic service — slot rebooked once for workshop load, no findings.",
    ],
    ("annual", "2023-2024"): [
        "Annual roadworthiness inspection — passed, certificate renewed.",
        "Annual statutory check — passed first time, certificate renewed.",
        "Annual roadworthiness test — no advisories, certificate renewed.",
        "Annual inspection complete — emissions and brakes within limits, certificate renewed.",
        "Statutory annual test — passed, next test booked for the same month.",
    ],
    ("annual", "2025"): [
        "Annual roadworthiness inspection — passed, certificate renewed.",
        "Annual statutory check — passed first time, certificate renewed.",
        "Annual roadworthiness test — no advisories, certificate renewed.",
        "Annual inspection complete — emissions and brakes within limits, certificate renewed.",
        "Statutory annual test — passed, next test booked for the same month.",
    ],
}
LATE_NOTES = [
    "Periodic service over interval — workshop slot backlog, oil and filters changed.",
    "Periodic service carried out late — slot moved twice, brakes and fluids checked.",
    "Overdue periodic service — rebooked for workshop load, serviced and returned.",
]

# --- notes: defect findings per area and result, as (finding, action) ---
DEFECT_NOTES = {
    "brakes": {
        "pass_with_defects": [
            ("Front pads at 4mm", "within limit, monitor at next service"),
            ("Slight brake judder reported", "discs within limit, re-check at next service"),
        ],
        "fail": [
            ("Rear brake pads below minimum", "vehicle held, work order raised at the hub"),
            ("Air leak at the nearside brake chamber", "vehicle off road, work order raised at the hub"),
        ],
    },
    "tyres": {
        "pass_with_defects": [
            ("Nearside rear tyre tread at 3mm", "within limit, monitor at next service"),
            ("Offside rear tyre pressure low", "inflated to spec, valve checked"),
        ],
        "fail": [
            ("Steer tyre below tread minimum", "vehicle held, work order raised at the hub"),
            ("Sidewall bulge on the offside steer tyre", "vehicle held, work order raised at the hub"),
        ],
    },
    "lights": {
        "pass_with_defects": [
            ("Offside rear marker light inoperative", "noted, bulb replaced at the hub"),
            ("Number plate lamp out", "bulb replaced at the hub"),
            ("Nearside indicator lens cracked", "noted, lens replaced at the hub"),
        ],
        "fail": [
            ("Both brake lights inoperative", "vehicle held, work order raised at the hub"),
        ],
    },
    "body_door": {
        "pass_with_defects": [
            ("Rear roller door slow to latch", "noted, latch lubricated at the hub"),
            ("Side door seal torn", "noted, repair booked at next service"),
        ],
        "fail": [
            ("Rear door will not secure", "vehicle held, work order raised at the hub"),
        ],
    },
    "refrigeration": {
        "pass_with_defects": [
            ("Reefer unit slow to pull down", "set point checked, monitor"),
        ],
        "fail": [
            ("Reefer unit not holding temperature", "vehicle held, work order raised at the hub"),
        ],
    },
    "electrical": {
        "pass_with_defects": [
            ("Dashboard warning light intermittent", "fault code logged, monitor"),
            ("Reversing alarm weak", "noted, connector cleaned at the hub"),
        ],
        "fail": [
            ("Battery not holding charge", "vehicle held, work order raised at the hub"),
        ],
    },
    "fluids": {
        "pass_with_defects": [
            ("Coolant level low", "topped up, no leak found"),
            ("Minor oil weep at the sump", "noted, monitor at next service"),
        ],
        "fail": [
            ("Fuel weep at the tank strap", "vehicle held, work order raised at the hub"),
        ],
    },
    "other": {
        "pass_with_defects": [
            ("Nearside mirror glass cracked", "noted, replacement ordered"),
        ],
        "fail": [
            ("Windscreen crack in the driver's line of sight", "vehicle held, work order raised at the hub"),
        ],
    },
}

# --- post-incident: type of impact by severity ---
IMPACTS = {
    4: ["a front-end collision", "a heavy side impact at a junction"],
    3: ["a side-swipe at a junction", "a rear-end impact in traffic"],
    2: ["a reversing contact in the yard", "a kerb strike on a tight turn"],
    1: ["a low-speed yard contact", "a mirror strike on a narrow street", "a kerb strike on a tight turn"],
}


def read_csv(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def parse_date(s):
    y, m, d = (int(x) for x in s[:10].split("-"))
    return datetime.date(y, m, d)


def band(day):
    return "2025" if day.year == 2025 else "2023-2024"


def weighted_choice(rng, pairs):
    x = rng.random() * sum(w for _, w in pairs)
    for value, w in pairs:
        x -= w
        if x < 0:
            return value
    return pairs[-1][0]


def lower_first(s):
    return s[0].lower() + s[1:]


class Odometer:
    """The odometer series for one vehicle: a step function over its route dates."""

    def __init__(self, rng, vehicle, routes):
        current = int(vehicle["odometer"])
        travel = min(len(routes) * KM_PER_ROUTE, current // 2)
        gap = max(200, int(round(0.02 * current)))
        self.current = current
        self.start = current - travel - gap
        assert self.start >= 0, vehicle

        weights = [1.0 + rng.uniform(-0.3, 0.3) for _ in routes]
        total = sum(weights)
        cum, running = {}, 0.0
        for r, w in zip(routes, weights):
            running += w
            # rounded cumulative, so the last reading is exactly start + travel
            cum[parse_date(r["service_date"])] = int(round(travel * running / total))
        self.dates = sorted(cum)                       # unique route dates
        self.reading_on = {d: self.start + cum[d] for d in self.dates}
        if self.dates:
            assert self.reading_on[self.dates[-1]] == self.start + travel

    def at(self, day):
        """Last known reading on or before day (start before the first route)."""
        reading = self.start
        for d in self.dates:
            if d > day:
                break
            reading = self.reading_on[d]
        return reading

    def route_dates_between(self, lo, hi):
        return [d for d in self.dates if lo <= d <= hi]


def next_periodic(odo, prev_day, prev_reading, limit_km):
    """Next periodic after (prev_day, prev_reading): due at limit_km or 365 days, first.

    km: the last route day before the next route day's reading would pass the limit.
    days: the first route day in the last two weeks of the year, else the due day itself
    (a vehicle with no running is serviced in the yard on the day).
    """
    km_day, last_within = None, None
    for d in odo.dates:
        if d <= prev_day:
            continue
        if odo.reading_on[d] - prev_reading > limit_km:
            km_day = last_within or d
            break
        last_within = d

    due = prev_day + datetime.timedelta(days=SERVICE_INTERVAL_DAYS)
    window = odo.route_dates_between(due - datetime.timedelta(days=BOOKING_WINDOW_DAYS), due)
    days_day = window[0] if window else due

    return min(km_day, days_day) if km_day else days_day


def periodic_schedule(odo, anchor, late_factor=None):
    """[(day, reading, is_late)] from the anchor forward, while on or before END.

    With late_factor, the first periodic falling due in 2025 is served late: its km
    trigger is multiplied by late_factor.
    """
    window = odo.route_dates_between(anchor, anchor + datetime.timedelta(days=BOOKING_WINDOW_DAYS))
    first = window[0] if window else anchor
    out = [(first, odo.at(first), False)]
    strained = False
    while True:
        prev_day, prev_reading, _ = out[-1]
        day = next_periodic(odo, prev_day, prev_reading, SERVICE_INTERVAL_KM)
        is_late = False
        if late_factor and not strained and day.year == 2025:
            day = next_periodic(odo, prev_day, prev_reading, SERVICE_INTERVAL_KM * late_factor)
            strained = is_late = True
        if day > END:
            break
        out.append((day, odo.at(day), is_late))
    return out


def over_interval(schedule):
    """[(day, km, days)] for each interval over 20,000 km or 365 days."""
    over = []
    for (d0, r0, _), (d1, r1, _) in zip(schedule, schedule[1:]):
        if r1 - r0 > SERVICE_INTERVAL_KM or (d1 - d0).days > SERVICE_INTERVAL_DAYS:
            over.append((d1, r1 - r0, (d1 - d0).days))
    return over


def pick_late(rng, vehicles, odos, anchors):
    """Per hub, LATE_PER_HUB vehicles whose strained schedule has exactly one late
    interval, in 2025, and none before."""
    late = {}
    for hub in sorted(LATE_PER_HUB):
        cands = sorted(v["vehicle_id"] for v in vehicles if v["hub_id"] == hub)
        rng.shuffle(cands)
        for vid in cands:
            if sum(1 for v in late if odos[v].hub == hub) >= LATE_PER_HUB[hub]:
                break
            factor = round(rng.uniform(*LATE_FACTOR), 2)
            sched = periodic_schedule(odos[vid], anchors[vid], factor)
            over = over_interval(sched)
            if len(over) == 1 and over[0][0].year == 2025 and over[0][1] > SERVICE_INTERVAL_KM:
                late[vid] = factor
        if sum(1 for v in late if odos[v].hub == hub) != LATE_PER_HUB[hub]:
            sys.exit("could not place %d late periodics at %s" % (LATE_PER_HUB[hub], hub))
    return late


def assign_results(rng, rows, itype):
    """Seeded result mix for one inspection type, per year (pre_trip: per hub-year quota,
    so hub rates are exact; periodic/annual: weighted draw over the year's rows)."""
    by_year = defaultdict(list)
    for row in rows:
        by_year[row["inspected_at"][:4]].append(row)
    for year in sorted(by_year):
        yrows = by_year[year]
        b = "2025" if year == "2025" else "2023-2024"
        strain = HUB_STRAIN_2025 if year == "2025" else {}
        if itype == "pre_trip":
            groups = defaultdict(list)
            for row in yrows:
                groups[row["hub_id"]].append(row)
            for hub in sorted(groups):
                g = groups[hub]
                mult = strain.get(hub, 1.0)
                n_bad = int(round(NON_PASS[itype][b] * mult * len(g)))
                n_fail = int(round(FAIL[itype][b] * mult * len(g)))
                order = list(range(len(g)))
                rng.shuffle(order)
                for k, i in enumerate(order[:n_bad]):
                    g[i]["result"] = "fail" if k < n_fail else "pass_with_defects"
        else:
            n_bad = int(round(NON_PASS[itype][b] * len(yrows)))
            n_fail = int(round(FAIL[itype][b] * len(yrows)))
            if itype == "annual" and year == "2024":
                n_fail = 1  # the single statutory fail of the orderly years
            # Efraimidis-Spirakis weighted sample without replacement; a late periodic
            # is three times as likely to turn something up.
            keyed = []
            for i, row in enumerate(yrows):
                w = strain.get(row["hub_id"], 1.0) * (3.0 if row.get("_late") else 1.0)
                keyed.append((rng.random() ** (1.0 / w), i))
            keyed.sort(reverse=True)
            for k, (_, i) in enumerate(keyed[:n_bad]):
                yrows[i]["result"] = "fail" if k < n_fail else "pass_with_defects"


def write_notes(rng, row):
    itype, result = row["inspection_type"], row["result"]
    day = parse_date(row["inspected_at"])
    if result == "pass":
        row["defect_area"] = "none"
        if row.get("_late"):
            row["notes"] = rng.choice(LATE_NOTES)
        else:
            row["notes"] = rng.choice(PASS_NOTES[(itype, band(day))])
        return
    area = weighted_choice(rng, DEFECT_WEIGHTS)
    row["defect_area"] = area
    finding, action = rng.choice(DEFECT_NOTES[area][result])
    if itype == "pre_trip":
        row["notes"] = "%s — %s." % (finding, action)
    elif itype == "periodic":
        prefix = "Overdue periodic service" if row.get("_late") else "Periodic service"
        row["notes"] = "%s: %s — %s." % (prefix, lower_first(finding), action)
    else:
        if result == "fail":
            action = action.replace("vehicle held", "certificate withheld")
        row["notes"] = "Annual inspection: %s — %s." % (lower_first(finding), action)


def main():
    rng = random.Random(SEED)
    vehicles = read_csv("vehicles")
    vehicles.sort(key=lambda v: v["vehicle_id"])
    routes = read_csv("routes")
    incidents = read_csv("incidents")

    routes_by_vehicle = defaultdict(list)
    for r in routes:
        routes_by_vehicle[r["vehicle_id"]].append(r)
    for vid in routes_by_vehicle:
        routes_by_vehicle[vid].sort(key=lambda r: (r["service_date"], r["route_id"]))

    odos = {}
    for v in vehicles:
        odo = Odometer(rng, v, routes_by_vehicle.get(v["vehicle_id"], []))
        odo.hub = v["hub_id"]
        odos[v["vehicle_id"]] = odo

    rows = []

    # --- pre_trip: one per route ---
    for r in sorted(routes, key=lambda r: (r["service_date"], r["route_id"])):
        day = parse_date(r["service_date"])
        rows.append({
            "vehicle_id": r["vehicle_id"], "hub_id": r["hub_id"],
            "inspected_at": day.isoformat(), "inspection_type": "pre_trip",
            "odometer_reading": odos[r["vehicle_id"]].at(day), "result": "pass",
        })

    # --- periodic: from the odometer forward, staggered first service in Q1 2023 ---
    anchors = {v["vehicle_id"]: START + datetime.timedelta(days=rng.randint(1, 89)) for v in vehicles}
    late = pick_late(rng, vehicles, odos, anchors)
    for v in vehicles:
        vid = v["vehicle_id"]
        for day, reading, is_late in periodic_schedule(odos[vid], anchors[vid], late.get(vid)):
            rows.append({
                "vehicle_id": vid, "hub_id": v["hub_id"],
                "inspected_at": day.isoformat(), "inspection_type": "periodic",
                "odometer_reading": reading, "result": "pass", "_late": is_late,
            })

    # --- annual: a fixed day per vehicle, spread over the year in vehicle_id order ---
    for i, v in enumerate(vehicles):
        doy = 8 + i * 8 + rng.randint(-3, 3)
        md = datetime.date(2023, 1, 1) + datetime.timedelta(days=doy - 1)
        for year in (2023, 2024, 2025):
            day = datetime.date(year, md.month, md.day)
            rows.append({
                "vehicle_id": v["vehicle_id"], "hub_id": v["hub_id"],
                "inspected_at": day.isoformat(), "inspection_type": "annual",
                "odometer_reading": odos[v["vehicle_id"]].at(day), "result": "pass",
            })

    for itype in ("pre_trip", "periodic", "annual"):
        assign_results(rng, [r for r in rows if r["inspection_type"] == itype], itype)
    for row in rows:
        write_notes(rng, row)

    # --- post_incident: one per 2023-2025 accident that names a vehicle ---
    accidents = sorted(
        (r for r in incidents
         if r["type"] == "accident" and r["vehicle_id"]
         and START <= parse_date(r["occurred_at"]) <= END),
        key=lambda r: (r["occurred_at"], r["incident_id"]),
    )
    got = Counter(r["occurred_at"][:4] for r in accidents)
    if dict(got) != EXPECTED_ACCIDENTS:
        print("accident incidents per year %s, expected %s" % (dict(got), EXPECTED_ACCIDENTS))
        sys.exit(1)
    for inc in accidents:
        day = parse_date(inc["occurred_at"]) + datetime.timedelta(days=1)
        severity = int(inc["severity"])
        x = rng.random()
        if severity == 4:
            result = "fail" if x < 0.8 else "pass_with_defects"
        elif severity == 3:
            result = "pass_with_defects" if x < 0.75 else ("fail" if x < 0.9 else "pass")
        else:
            result = "pass_with_defects" if x < 0.5 else "pass"
        lead = "Linked incident: %s. Post-incident inspection after %s" % (
            inc["incident_id"], rng.choice(IMPACTS[severity]))
        if result == "pass":
            area, tail = "none", "no damage beyond cosmetic scuffing, returned to service."
        else:
            area = weighted_choice(rng, POST_INCIDENT_WEIGHTS)
            finding, action = rng.choice(DEFECT_NOTES[area][result])
            tail = "%s, %s." % (lower_first(finding), action)
        rows.append({
            "vehicle_id": inc["vehicle_id"], "hub_id": inc["hub_id"],
            "inspected_at": day.isoformat(), "inspection_type": "post_incident",
            "odometer_reading": odos[inc["vehicle_id"]].at(day), "result": result,
            "defect_area": area, "notes": "%s — %s" % (lead, tail),
        })

    # Ids are assigned in a deterministic shuffled order (id order does not track date),
    # while the file itself is written in date order.
    id_order = list(range(len(rows)))
    rng.shuffle(id_order)
    for pos, row in enumerate(rows):
        row["inspection_id"] = "INS-%06d" % (FIRST_INSPECTION + id_order[pos])
    rows.sort(key=lambda r: (r["inspected_at"], r["vehicle_id"], r["inspection_id"]))

    # guard rails
    odometer_cap = {v["vehicle_id"]: int(v["odometer"]) for v in vehicles}
    last_reading = {}
    for row in rows:
        assert START.isoformat() <= row["inspected_at"] <= END.isoformat(), row
        assert row["vehicle_id"] in odometer_cap, row
        assert len(row["hub_id"]) == 7 and row["hub_id"].startswith("HUB-"), row
        assert row["odometer_reading"] >= last_reading.get(row["vehicle_id"], 0), row
        assert row["odometer_reading"] <= odometer_cap[row["vehicle_id"]], row
        assert (row["result"] == "pass") == (row["defect_area"] == "none"), row
        assert "~~NL~~" not in row["notes"] and "WO-" not in row["notes"], row
        last_reading[row["vehicle_id"]] = row["odometer_reading"]
    for vid in sorted(odos):
        sched = [(parse_date(r["inspected_at"]), r["odometer_reading"], False)
                 for r in rows if r["vehicle_id"] == vid and r["inspection_type"] == "periodic"]
        for day, _, _ in over_interval(sched):
            assert day.year == 2025, (vid, day)
    for row in rows:
        row.pop("_late", None)

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for row in rows:
            w.writerow(row)

    print("wrote %d rows: %s" % (len(rows), os.path.relpath(OUT_PATH)))
    print("by type:", dict(sorted(Counter(r["inspection_type"] for r in rows).items())))
    print("by year:", dict(sorted(Counter(r["inspected_at"][:4] for r in rows).items())))
    print("odometer range: %d .. %d" % (
        min(r["odometer_reading"] for r in rows), max(r["odometer_reading"] for r in rows)))
    late_hubs = Counter(odos[v].hub for v in late)
    print("2025 late periodics: %d %s" % (len(late), dict(sorted(late_hubs.items()))))
    for year in ("2023", "2024", "2025"):
        yr = [r for r in rows if r["inspected_at"][:4] == year]
        bad = sum(1 for r in yr if r["result"] != "pass")
        print("%s non-pass: %d / %d = %.1f%%" % (year, bad, len(yr), 100.0 * bad / len(yr)))
    rates = {}
    for hub in sorted(LATE_PER_HUB):
        hr = [r for r in rows if r["inspected_at"][:4] == "2025" and r["hub_id"] == hub]
        rates[hub] = 100.0 * sum(1 for r in hr if r["result"] != "pass") / len(hr)
    print("2025 non-pass by hub:", ", ".join("%s %.1f%%" % (h, rates[h]) for h in sorted(rates)))
    if max(rates, key=rates.get) == "HUB-AMS" or late_hubs["HUB-AMS"] >= max(late_hubs.values()):
        sys.exit("HUB-AMS must not be the worst hub in 2025")


if __name__ == "__main__":
    main()
