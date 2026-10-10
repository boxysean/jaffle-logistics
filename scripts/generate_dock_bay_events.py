#!/usr/bin/env python3
"""Deterministic generator for seeds/dock_bay_events.csv: the bay-level dock record,
one row per event, every hub, every bay, every day of 2023-01-01 .. 2025-12-31.

Writes the whole file from scratch (same seed -> same bytes), so re-running it is
idempotent. Every route_id / driver_id / vehicle_id is a real row of seeds/routes.csv
(blank where the event is not tied to a route), every incident_id a real damage
incident from seeds/incidents.csv.

What the record holds:
  * Per route: a morning outbound staging + loading at one bay of the route's hub,
    an evening inbound unloading, and now and then a delay.
  * Per bay per day: an opening bay walk (inspection), so every named bay has a row
    every day. Plus linehaul unloading/staging the dock crew works with no route.
    Weekends are lighter.
  * damage_found: exactly one per damage incident in seeds/incidents.csv, at the
    incident's hub and occurred_at, route/driver/vehicle recovered from the
    incident's route_id via seeds/routes.csv. Reconciled by
    tests/assert_dock_damage_reconciles_incidents.sql.

Story the record tells:
  * 2023 and 2024 are quiet at every bay: flat dwell, damage scattered, and the
    Columbus damage of those years lands at bays other than 3.
  * 2025 at HUB-CMH: the damage cluster sits at HUB-CMH-BAY-3 (BAY3_2025, 11 of 15),
    and staging dwell at that bay drifts worse through the year, while every other
    bay and hub stays flat. This is consistent with IR-9003 (bay 3 forklift staging).

Dwell (minutes_at_bay) peaks at the morning outbound and evening inbound, runs longer
in December and at Columbus, and is longer for staging/inspection than for
loading/unloading. Never below 1.

Run:  python3 scripts/generate_dock_bay_events.py
"""
import csv
import datetime
import math
import os
import random
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")
OUT_PATH = os.path.join(SEEDS, "dock_bay_events.csv")

SEED = 20250303
START = datetime.date(2023, 1, 1)
END = datetime.date(2025, 12, 31)
FIRST_EVENT = 100000  # DBE-100000, mirrors DN-100000

BAYS = {"HUB-CMH": 6, "HUB-CHI": 6, "HUB-IND": 4, "HUB-DET": 4, "HUB-CIN": 4}

# The 2025 HUB-CMH damage incidents whose dock record is at bay 3 (11 of the 15).
# The other four (INC-2025-00020, -00041, -00046, -00226) land at other Columbus bays.
# Shared with scripts/generate_incident_reports_missing.py so the report narrative
# names the same bay the dock record does.
BAY3_2025 = (
    "INC-2025-00014", "INC-2025-00093", "INC-2025-00094", "INC-2025-00095",
    "INC-2025-00136", "INC-2025-00143", "INC-2025-00148", "INC-2025-00163",
    "INC-2025-00196", "INC-2025-00231", "INC-2025-00254",
)

BASE_DWELL = {
    "staging": 36, "inspection": 26, "loading": 20,
    "unloading": 23, "delay": 30, "damage_found": 44,
}

HEADER = ["event_id", "hub_id", "bay_id", "route_id", "vehicle_id", "driver_id",
          "event_at", "event_type", "minutes_at_bay", "incident_id", "detail"]


def read_csv(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def bay_id(hub, n):
    return "%s-BAY-%d" % (hub, n)


def ts(day, minute_of_day, second=0):
    minute_of_day = max(0, min(minute_of_day, 23 * 60 + 59))
    return "%sT%02d:%02d:%02d" % (day.isoformat(), minute_of_day // 60, minute_of_day % 60, second)


def bay3_drift(hub, bay, etype, day):
    """Columbus bay 3 staging gets slower through 2025; flat everywhere else, every year."""
    if hub == "HUB-CMH" and bay == 3 and etype == "staging" and day.year == 2025:
        return 1.0 + 0.95 * (day.timetuple().tm_yday / 365.0)
    return 1.0


def dwell(rng, hub, bay, etype, day, minute_of_day):
    h = minute_of_day / 60.0
    peak = 1.0 + 0.40 * math.exp(-((h - 7.0) ** 2) / 2.0) + 0.32 * math.exp(-((h - 18.0) ** 2) / 2.0)
    month = {12: 1.22, 11: 1.07}.get(day.month, 1.0)
    busy = 1.15 if hub == "HUB-CMH" else 1.0
    weekend = 0.9 if day.weekday() >= 5 else 1.0
    m = BASE_DWELL[etype] * peak * month * busy * weekend * bay3_drift(hub, bay, etype, day)
    m *= rng.lognormvariate(0.0, 0.22)
    return max(1, int(round(m)))


def staging_detail(rng, hub, bay, day, pallets, route_id):
    # Bay 3 at Columbus starts to show up in the floor log during 2025, more as the
    # year goes on. Never before 2025.
    if hub == "HUB-CMH" and bay == 3 and day.year == 2025:
        if rng.random() < 0.10 + 0.45 * (day.timetuple().tm_yday / 365.0):
            return rng.choice([
                "Bay 3 staging backed up, pallets in forklift lane.",
                "Bay 3 lane tight again. %d pallets double-stacked to clear door." % pallets,
                "Bay 3 staging slow, forklift working around staged freight.",
                "Bay 3 overflow, staged %d pallets past the line." % pallets,
            ])
    if route_id:
        return rng.choice([
            "Staged %d pallets for %s." % (pallets, route_id),
            "Outbound staged, %d pallets. Lane clear." % pallets,
            "%d pallets staged, waiting on driver." % pallets,
        ])
    return rng.choice([
        "Linehaul freight staged for AM sort, %d pallets." % pallets,
        "Cross-dock staged, %d pallets." % pallets,
    ])


def damage_detail(rng, hub, bay, inc):
    if hub == "HUB-CMH" and bay == 3 and inc["occurred_at"][:4] == "2025":
        return rng.choice([
            "Crushed pallet found at bay 3. Staged in forklift lane. %s filed." % inc["incident_id"],
            "Forked carton at bay 3 staging, again. Photos taken, %s." % inc["incident_id"],
            "Damage on freight staged at bay 3. Lane congested at the time. %s." % inc["incident_id"],
        ])
    return rng.choice([
        "Damaged freight found at bay %d on unload. Photos taken, %s." % (bay, inc["incident_id"]),
        "Torn wrap and crushed corner at bay %d. %s filed." % (bay, inc["incident_id"]),
        "Load shifted, damage found at bay %d door. %s." % (bay, inc["incident_id"]),
    ])


def main():
    rng = random.Random(SEED)
    routes = read_csv("routes")
    route_by_id = {r["route_id"]: r for r in routes}
    incidents = read_csv("incidents")

    routes_by_day = defaultdict(list)
    for r in routes:
        routes_by_day[r["service_date"]].append(r)

    events = []  # (event_at, hub, bay, route_id, vehicle_id, driver_id, type, minutes, incident_id, detail)

    def add(day, minute, hub, bay, etype, detail, route=None, incident_id="", second=0, at=None):
        events.append([
            at or ts(day, minute, second), hub, bay_id(hub, bay),
            route["route_id"] if route else "",
            route["vehicle_id"] if route else "",
            route["driver_id"] if route else "",
            etype, dwell(rng, hub, bay, etype, day, minute), incident_id, detail,
        ])

    day = START
    while day <= END:
        weekend = day.weekday() >= 5
        # Opening bay walk at every bay, every day.
        for hub, n in BAYS.items():
            for bay in range(1, n + 1):
                minute = rng.randint(4 * 60 + 30, 5 * 60 + 30)
                add(day, minute, hub, bay, "inspection", rng.choice([
                    "Bay walk, no issues.", "Dock plate and lights checked OK.",
                    "Forklift pre-shift check OK.", "Bay walk done, door seal fine.",
                ]))
            # Linehaul / cross-dock work with no route attached.
            for _ in range(rng.randint(1, 2) if weekend else rng.randint(3, 6)):
                bay = rng.randint(1, n)
                minute = rng.choice([rng.randint(9 * 60, 15 * 60), rng.randint(20 * 60, 22 * 60)])
                pallets = rng.randint(6, 26)
                add(day, minute, hub, bay, "unloading",
                    "Inbound linehaul unloaded, %d pallets." % pallets)
                add(day, minute + rng.randint(25, 60), hub, bay, "staging",
                    staging_detail(rng, hub, bay, day, pallets, ""))

        # Route outbound / inbound.
        for r in sorted(routes_by_day.get(day.isoformat(), []), key=lambda x: x["route_id"]):
            hub = r["hub_id"]
            bay = rng.randint(1, BAYS[hub])
            stops = int(r["stop_count"])
            pallets = max(2, stops // 4 + rng.randint(-2, 3))
            m_stage = rng.randint(5 * 60 + 15, 7 * 60 + 30)
            add(day, m_stage, hub, bay, "staging",
                staging_detail(rng, hub, bay, day, pallets, r["route_id"]), route=r)
            if rng.random() < 0.05:
                add(day, m_stage + rng.randint(10, 40), hub, bay, "delay", rng.choice([
                    "Dock queue, %d trailers ahead. ETA +%dm." % (rng.randint(1, 4), rng.randint(10, 45)),
                    "Forklift down, staging by pallet jack.",
                    "Door %d stuck, moved freight next bay over." % bay,
                    "Driver late to dock, load held.",
                ]), route=r)
            add(day, m_stage + rng.randint(30, 75), hub, bay, "loading", rng.choice([
                "Loaded %d stops, doors sealed." % stops,
                "Loaded, %d stops. Departed on time." % stops,
                "Loaded %d pallets, %d stops." % (pallets, stops),
            ]), route=r)
            if r["status"] != "canceled":
                in_bay = rng.randint(1, BAYS[hub])
                add(day, rng.randint(16 * 60, 20 * 60 + 30), hub, in_bay, "unloading", rng.choice([
                    "Returns unloaded, %d pallets." % rng.randint(0, 4),
                    "Truck back, empties and returns off.",
                    "Inbound unloaded, %d ATT returns." % rng.randint(0, 3),
                ]), route=r)
        day += datetime.timedelta(days=1)

    # damage_found: exactly one per damage incident.
    damage = sorted((i for i in incidents if i["type"] == "damage"), key=lambda i: i["incident_id"])
    for inc in damage:
        hub = inc["hub_id"]
        n = BAYS[hub]
        if inc["incident_id"] in BAY3_2025:
            bay = 3
        elif hub == "HUB-CMH":
            bay = rng.choice([b for b in range(1, n + 1) if b != 3])
        else:
            bay = rng.randint(1, n)
        route = route_by_id[inc["route_id"]] if inc["route_id"] else None
        occ = datetime.datetime.fromisoformat(inc["occurred_at"])
        add(occ.date(), occ.hour * 60 + occ.minute, hub, bay, "damage_found",
            damage_detail(rng, hub, bay, inc), route=route,
            incident_id=inc["incident_id"], at=inc["occurred_at"])

    events.sort(key=lambda e: (e[0], e[1], e[2], e[6], e[3]))
    assert all(e[0] <= "2025-12-31T23:59:59" and e[0] >= "2023-01-01" for e in events)
    assert all(e[7] >= 1 for e in events)

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(HEADER)
        for i, e in enumerate(events):
            at, hub, bay, route, veh, drv, etype, minutes, incident, detail = e
            w.writerow(["DBE-%06d" % (FIRST_EVENT + i), hub, bay, route, veh, drv,
                        at, etype, minutes, incident, detail])

    print("wrote %d events: DBE-%06d .. DBE-%06d" % (len(events), FIRST_EVENT, FIRST_EVENT + len(events) - 1))
    print("event_at range: %s .. %s" % (events[0][0], events[-1][0]))
    print("by type:", dict(sorted(Counter(e[6] for e in events).items())))
    dmg = [e for e in events if e[6] == "damage_found"]
    print("damage_found by year:", dict(sorted(Counter(e[0][:4] for e in dmg).items())))
    print("damage_found HUB-CMH by year:", dict(sorted(Counter(e[0][:4] for e in dmg if e[1] == "HUB-CMH").items())))
    print("damage_found HUB-CMH 2025 by bay:", dict(sorted(Counter(
        e[2] for e in dmg if e[1] == "HUB-CMH" and e[0][:4] == "2025").items())))
    for label, pred in (("HUB-CMH-BAY-3", lambda e: e[2] == "HUB-CMH-BAY-3"),
                        ("other CMH bays", lambda e: e[1] == "HUB-CMH" and e[2] != "HUB-CMH-BAY-3"),
                        ("other hubs", lambda e: e[1] != "HUB-CMH")):
        avg = {}
        for e in events:
            if e[6] == "staging" and pred(e):
                k = e[0][:4] + ("H1" if e[0][5:7] <= "06" else "H2")
                avg.setdefault(k, []).append(e[7])
        print("staging avg min, %s:" % label,
              {k: round(sum(v) / len(v), 1) for k, v in sorted(avg.items())})


if __name__ == "__main__":
    main()
