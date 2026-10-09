#!/usr/bin/env python3
"""Deterministic generator for 2023-2024 rows appended to seeds/fleet_work_orders.csv.

Extends the work-order history backwards two operating years, matching the voice and
format of the existing 2025 rows exactly. Bodies keep the '~~NL~~'-joined
'WORK ORDER - vehicle VEH-NNNN @ HUB-XXX' structure.

Prior years are ordinary: preventive maintenance, tyres, brakes, DEF/EGR/wiper faults
and a lift-gate fault, plus a handful of collision repairs each linked to a *real*
2023/2024 'accident' incident (same vehicle and hub as that incident). Deliberately no
storm narrative and no repeated handling-damage pattern at HUB-CMH -- nothing that
hints at a fleet-wide problem may start before 2025.

Appends only; never rewrites an existing row. Ids continue WO-3NNNNN upward from the
current max (WO-300079).

Run:  python3 scripts/generate_fleet_history.py
"""
import csv
import datetime as dt
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")
WO_PATH = os.path.join(SEEDS, "fleet_work_orders.csv")
INC_PATH = os.path.join(SEEDS, "incidents.csv")
VEH_PATH = os.path.join(SEEDS, "vehicles.csv")

SEED = 20231010
YEARS = ("2023", "2024")
TARGET_PER_YEAR = 41          # 41 + 41 = 82 new rows -> 163 total (>= 162 target)
N_LINKED_PER_YEAR = 8         # collision repairs tied to a real accident incident
FIRST_WO_NUM = 300080         # continue WO-3NNNNN upward (existing max is WO-300079)

# --- ordinary (unlinked) maintenance templates, mirroring the existing 2025 rows ---
ROUTINE = [
    {   # preventive maintenance
        "complaint": "Scheduled preventive maintenance (oil, filters, inspection).",
        "diagnosis": "Within normal wear; serviced per schedule.",
        "parts": "oil, filters, air filter",
        "labor": (1, 4), "cost": (285, 3100),
    },
    {   # tyres
        "complaint": "Tire wear flagged at pre-trip.",
        "diagnosis": "Two steer tires below tread minimum.",
        "parts": "2x steer tires",
        "labor": (1, 7), "cost": (360, 2800),
    },
    {   # DEF
        "complaint": "DEF system warning light.",
        "diagnosis": "DEF quality sensor fault.",
        "parts": "DEF sensor",
        "labor": (1, 5), "cost": (175, 2400),
    },
    {   # wiper / defrost
        "complaint": "Wiper/defrost fault ahead of winter.",
        "diagnosis": "Wiper motor linkage worn.",
        "parts": "wiper motor linkage",
        "labor": (1, 7), "cost": (345, 3200),
    },
    {   # check engine / EGR
        "complaint": "Check-engine light at startup.",
        "diagnosis": "EGR valve sticking; cleared and tested.",
        "parts": "EGR valve, gasket",
        "labor": (1, 7), "cost": (355, 2700),
    },
    {   # brakes
        "complaint": "Brake noise reported by driver.",
        "diagnosis": "Front pads at 3mm, rotors serviceable.",
        "parts": "front brake pads",
        "labor": (1, 8), "cost": (640, 2800),
    },
    {   # lift-gate fault (ordinary, one-off)
        "complaint": "Lift-gate not latching at the rear door.",
        "diagnosis": "Latch strike worn; hydraulic line weeping at the fitting.",
        "parts": "liftgate latch, hydraulic line, seal kit",
        "labor": (1, 4), "cost": (410, 1250),
    },
]

# --- collision templates, mirroring the existing 2025 collision repair bodies ---
COLLISION_DIAG = [
    "Body panel and liftgate damage; hydraulic line pinched.",
    "Bent tie rod and control arm following impact; alignment out of spec.",
    "Front-end damage, coolant leak, bumper and headlamp assembly compromised.",
]
COLLISION_PARTS = {
    0: "liftgate hydraulic line, panel, fasteners",
    1: "tie rod, control arm, alignment kit",
    2: "bumper assy, headlamp, coolant hose, clips",
}
COLLISION_DISPOSITION = ["returned to service.", "held for parts.", "road-tested and released."]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def spread_months(rng, n):
    """A balanced bag of month numbers so no month is over-loaded and none is empty."""
    bag = [m for m in range(1, 13) for _ in range(3)]  # 36 slots
    rng.shuffle(bag)
    return bag[:n]


def link_targets(incidents, year, rng):
    """Real accident incidents of that year that name a vehicle; spread across months."""
    cands = [
        r for r in incidents
        if r["incident_id"].startswith("INC-%s-" % year)
        and r["type"] == "accident" and r["vehicle_id"]
    ]
    # Highest severity first, then earliest -- deterministic; keep a month spread.
    cands.sort(key=lambda r: (-int(r["severity"]), r["occurred_at"], r["incident_id"]))
    picked, per_month = [], Counter()
    for r in cands:
        month = r["occurred_at"][:7]
        if per_month[month] >= 1:
            continue
        picked.append(r)
        per_month[month] += 1
        if len(picked) >= N_LINKED_PER_YEAR:
            break
    # top up if the month-spread rule left us short
    if len(picked) < N_LINKED_PER_YEAR:
        have = {r["incident_id"] for r in picked}
        for r in cands:
            if r["incident_id"] in have:
                continue
            picked.append(r)
            have.add(r["incident_id"])
            if len(picked) >= N_LINKED_PER_YEAR:
                break
    return picked


def opened_after(occurred_at, rng):
    """A day or two after the incident, plausible shop hours."""
    y, m, d = (int(x) for x in occurred_at[:10].split("-"))
    occ = dt.date(y, m, d)
    delta = rng.randint(0, 2)
    shop = occ + dt.timedelta(days=delta)
    return "%sT%02d:%02d:00" % (shop.isoformat(), rng.choice([7, 9, 10, 13, 16]), rng.choice([0, 0, 0, 30]))


def build_routine(year, vehicles, rng):
    months = spread_months(rng, TARGET_PER_YEAR - N_LINKED_PER_YEAR)
    rows = []
    for month in months:
        veh = rng.choice(vehicles)
        tpl = rng.choice(ROUTINE)
        day = rng.randint(1, 27)
        opened = "%04d-%02d-%02dT%02d:%02d:00" % (
            int(year), month, day, rng.choice([7, 8, 9, 10, 11, 12, 13, 14, 15, 16]), 0,
        )
        labor = rng.randint(*tpl["labor"])
        cost = rng.randrange(tpl["cost"][0], tpl["cost"][1] + 1, 7)  # vary, keep in range
        body = "~~NL~~".join([
            "WORK ORDER \u2014 vehicle %s @ %s" % (veh["vehicle_id"], veh["hub_id"]),
            "COMPLAINT: %s" % tpl["complaint"],
            "DIAGNOSIS: %s" % tpl["diagnosis"],
            "PARTS: %s" % tpl["parts"],
            "LABOR: %d hrs" % labor,
            "DISPOSITION: returned to service. Odometer %s. Total $%d." % (veh["odometer"], cost),
        ])
        rows.append({
            "vehicle_id": veh["vehicle_id"], "hub_id": veh["hub_id"],
            "opened_at": opened, "linked_incident_id": "", "cost": cost, "body": body,
        })
    return rows


def build_linked(year, incidents, vehicles_by_id, rng):
    rows = []
    for inc in link_targets(incidents, year, rng):
        veh = vehicles_by_id[inc["vehicle_id"]]
        idx = rng.randrange(len(COLLISION_DIAG))
        labor = rng.randint(4, 20)
        cost = rng.randrange(2050, 12050, 11)
        disp = rng.choice(COLLISION_DISPOSITION)
        body = "~~NL~~".join([
            "WORK ORDER \u2014 vehicle %s @ %s" % (veh["vehicle_id"], inc["hub_id"]),
            "Linked incident: %s." % inc["incident_id"],
            "COMPLAINT: Collision/accident damage reported by field.",
            "DIAGNOSIS: %s" % COLLISION_DIAG[idx],
            "PARTS: %s" % COLLISION_PARTS[idx],
            "LABOR: %d hrs" % labor,
            "DISPOSITION: %s Total $%d." % (disp, cost),
        ])
        rows.append({
            "vehicle_id": veh["vehicle_id"], "hub_id": inc["hub_id"],
            "opened_at": opened_after(inc["occurred_at"], rng),
            "linked_incident_id": inc["incident_id"], "cost": cost, "body": body,
        })
    return rows


def main():
    rng = random.Random(SEED)
    incidents = read_csv(INC_PATH)
    vehicles = read_csv(VEH_PATH)
    vehicles_by_id = {v["vehicle_id"]: v for v in vehicles}

    existing = read_csv(WO_PATH)
    nums = [int(r["wo_id"].split("-")[1]) for r in existing if r["wo_id"].startswith("WO-3")]
    existing_ids = {r["wo_id"] for r in existing}
    next_num = max(max(nums) + 1, FIRST_WO_NUM)

    new_rows = []
    for year in YEARS:
        new_rows.extend(build_linked(year, incidents, vehicles_by_id, rng))
        new_rows.extend(build_routine(year, vehicles, rng))

    # Ids are assigned in a deterministic shuffled order (like the existing block, where
    # id order does not track date), while the file itself is written in date order.
    id_order = list(range(len(new_rows)))
    rng.shuffle(id_order)
    for pos, row in enumerate(new_rows):
        row["wo_id"] = "WO-%06d" % (next_num + id_order[pos])
    new_rows.sort(key=lambda r: (r["opened_at"], r["wo_id"]))

    for row in new_rows:
        if row["wo_id"] in existing_ids:
            sys.exit("refusing to overwrite existing %s" % row["wo_id"])
        # guard rails
        assert row["opened_at"][:4] in YEARS
        assert row["opened_at"] <= "2025-12-31"
        if row["linked_incident_id"]:
            assert row["linked_incident_id"].startswith("INC-%s-" % row["opened_at"][:4]), row

    header = ["wo_id", "vehicle_id", "hub_id", "opened_at", "linked_incident_id", "cost", "body"]
    with open(WO_PATH, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        for row in new_rows:
            w.writerow(row)

    print("appended %d rows: %s .. %s" % (len(new_rows), new_rows[0]["wo_id"], new_rows[-1]["wo_id"]))
    print("opened_at range: %s .. %s" % (
        min(r["opened_at"] for r in new_rows), max(r["opened_at"] for r in new_rows)))
    print("by year:", dict(Counter(r["opened_at"][:4] for r in new_rows)))
    print("linked:", sum(1 for r in new_rows if r["linked_incident_id"]))
    print("per-month max:", max(Counter(r["opened_at"][:7] for r in new_rows).values()))


if __name__ == "__main__":
    main()
