#!/usr/bin/env python3
"""Deterministic generator for 2023-2024 rows appended to seeds/incident_reports.csv.

Extends the narrative incident-report history backwards two operating years, matching
the voice/format of the existing 2025 rows exactly. Reports are the *escalated subset*
of seeds/incidents.csv: one report for a significant incident (severity >= 3, or any
accident/dispute), spread across months, filed a few days after the event.

Idempotent-ish: refuses to run if a row whose report_id is already present would be
written (it appends only new IR-7xxx ids above the current max).

Run:  python3 scripts/generate_incident_reports.py
"""
import csv
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")
INC_PATH = os.path.join(SEEDS, "incidents.csv")
REP_PATH = os.path.join(SEEDS, "incident_reports.csv")
SHIP_PATH = os.path.join(SEEDS, "shipments.csv")

SEED = 20231010
YEARS = ("2023", "2024")
TARGET_PER_YEAR = 16
FIRST_REPORT_NUM = 7035  # continue IR-7xxx upward (existing max in the 7xxx block is IR-7034)

CITY = {
    "HUB-CMH": "Columbus",
    "HUB-CHI": "Chicago",
    "HUB-IND": "Indianapolis",
    "HUB-DET": "Detroit",
    "HUB-CIN": "Cincinnati",
}

# Name + function, matching the existing convention. Existing authors first, plus two
# added in the same style.
AUTHORS = [
    "M. Vieira (Safety)",
    "P. Grantham (Safety)",
    "L. Okonkwo (Safety)",
    "R. Kowalski (Safety)",
    "T. Nakamura (Safety)",
    "Frank Deluca",
    "Gordon Reyes",
    "Yolanda Pierce",
    "Alicia Munro",
    "J. Alvarez (Ops)",
]

# Mundane, closed-out root causes only. Deliberately NO storm narrative, no systemic
# handling-damage finding at HUB-CMH, no bay-3 pattern — none of that may start early.
ROOT_CAUSE = {
    "accident": [
        "Loss of traction on an unsalted approach; contributing factor was reduced following distance.",
        "Driver misjudged stopping distance on a wet grade; the approach hadn't been salted yet.",
        "Icy on-ramp combined with following too closely; standard winter-approach protocol wasn't followed.",
        "Braking distance was insufficient for road conditions; the approach hadn't been treated for ice.",
        "A patch of black ice on an untreated ramp caught the driver off guard; following distance made it worse.",
    ],
    "damage": [
        "Improper load securement allowed shifting in transit.",
        "Straps weren't re-tensioned after the first stop, letting the load shift on the next turn.",
        "Load was secured for the manifest weight but not for the actual pallet mix, so it shifted en route.",
    ],
    "mispick": [
        "Item pulled from a mislabeled bin during a high-volume pick wave.",
        "A relabel during reslotting didn't match the WMS location, so pickers pulled the wrong SKU.",
        "Two adjacent bins were confused during a rush pick; the scan-to-confirm step was skipped.",
    ],
    "delay": [
        "Cascading ETA slippage from an upstream hub exception.",
        "A delay at the previous hub pushed this leg past its dispatch window, and the next truck had already left.",
        "An upstream exception ate the buffer this leg needed; there was no next available departure until the next day.",
    ],
    "weather": [
        "Severe weather at the hub exceeded the safe-dispatch threshold.",
    ],
    "dispute": [
        "Conflicting POD records between the driver app and the consignee.",
    ],
}

REMEDIATION = {
    "accident": [
        "Vehicle pulled for inspection; see linked work order.",
        "Unit taken out of rotation pending a full brake and suspension inspection.",
        "Vehicle held for inspection; findings folded into the fleet's quarterly maintenance review.",
        "Retraining scheduled; process checklist updated.",
        "Refresher training booked for the shift; checklist now requires a supervisor sign-off.",
    ],
    "damage": [
        "Loading crew walked back through the securement checklist; a load-check step added before departure.",
        "Retraining scheduled; process checklist updated.",
        "Refresher training booked for the shift; checklist now requires a supervisor sign-off.",
    ],
    "mispick": [
        "Every bin label in the affected zone re-verified against the WMS; two more mismatches found and corrected.",
        "Scan-to-confirm made mandatory at pick for this hub; manual label overrides disabled.",
        "Bin labeling audit initiated across the hub.",
    ],
    "delay": [
        "Dispatch threshold adjusted for the affected conditions.",
        "Added a manual weather check to the dispatch board for this hub before morning departures.",
        "Dispatch now holds this route when conditions cross the same threshold that was missed here.",
    ],
    "weather": [
        "Dispatch now holds this route when conditions cross the same threshold that was missed here.",
        "Dispatch threshold adjusted for the affected conditions.",
        "Added a manual weather check to the dispatch board for this hub before morning departures.",
    ],
    "dispute": [
        "POD records reconciled between the driver app and the consignee; documentation steps reviewed with the crew.",
        "Signed POD now required at handover for this account; the discrepancy was closed out the same week.",
    ],
}

# Lower rank = preferred when severities tie.
TYPE_RANK = {"accident": 0, "dispute": 1, "damage": 2, "mispick": 3, "weather": 4, "delay": 5}

# Cap how many reports any one incident type can contribute per year, so the escalated
# subset reads like the existing 2025 block (accident-heavy but not accident-only).
TYPE_CAP = {"accident": 8, "dispute": 6, "damage": 4, "mispick": 5, "weather": 5, "delay": 5}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def select_incidents(incidents, year, rng):
    cands = [
        r
        for r in incidents
        if r["incident_id"].startswith("INC-%s-" % year)
        and (int(r["severity"]) >= 3 or r["type"] in ("accident", "dispute", "damage"))
    ]
    # Highest severity first; type preference; then earliest. Deterministic.
    cands.sort(key=lambda r: (-int(r["severity"]), TYPE_RANK[r["type"]], r["occurred_at"]))
    for cap in (2, 3, 4):
        picked, per_month, per_type = [], Counter(), Counter()
        for r in cands:
            month = r["occurred_at"][:7]
            if per_month[month] >= cap:
                continue
            if per_type[r["type"]] >= TYPE_CAP[r["type"]]:
                continue
            picked.append(r)
            per_month[month] += 1
            per_type[r["type"]] += 1
            if len(picked) >= TARGET_PER_YEAR:
                break
        if len(picked) >= TARGET_PER_YEAR:
            return picked
    return picked


def filed_at(occurred_at, rng):
    """A few days after the event, same clock time, never rolling past the year end."""
    date, time = occurred_at[:10], occurred_at[11:]
    y, m, d = (int(x) for x in date.split("-"))
    import datetime

    occ = datetime.date(y, m, d)
    year_end = datetime.date(y, 12, 31)
    max_delta = (year_end - occ).days
    delta = min(rng.randint(1, 6), max_delta)
    return (occ + datetime.timedelta(days=delta)).isoformat() + "T" + time


def build_body(inc, author, filed_ts, report_shipment):
    sev = inc["severity"]
    typ = inc["type"]
    city = CITY[inc["hub_id"]]
    linked = []
    if inc["route_id"]:
        linked.append("route %s" % inc["route_id"])
    if inc["driver_id"]:
        linked.append("driver %s" % inc["driver_id"])
    if inc["vehicle_id"]:
        linked.append("vehicle %s" % inc["vehicle_id"])
    linked_txt = ", ".join(linked) if linked else "no linked entities"
    occ_date, occ_time = inc["occurred_at"][:10], inc["occurred_at"][11:16]
    lines = [
        "INCIDENT REPORT %s \u2014 %s (severity %s)" % (inc["incident_id"], typ.upper(), sev),
        "Hub: %s (%s). Filed by %s on %s." % (inc["hub_id"], city, author, filed_ts[:10]),
        "",
        "SUMMARY",
        "%s event (severity %s) at %s. Linked entities: %s." % (typ.title(), sev, city, linked_txt),
        "",
        "TIMELINE",
        "- %s %s event reported." % (occ_date, occ_time),
        "- +00:20 supervisor on scene; area secured.",
        "- +01:30 impact assessed and affected shipments identified.",
        "",
        "ROOT CAUSE",
        inc["_root_cause"],
        "",
        "REMEDIATION",
        inc["_remediation"],
    ]
    return "~~NL~~".join(lines)


def main():
    rng = random.Random(SEED)
    incidents = read_csv(INC_PATH)
    shipments = {r["shipment_id"] for r in read_csv(SHIP_PATH)}

    existing = read_csv(REP_PATH)
    existing_ids = {r["report_id"] for r in existing}
    max_num = max(
        int(r["report_id"].split("-")[1]) for r in existing if r["report_id"].startswith("IR-7")
    )

    selected = []
    for year in YEARS:
        selected.extend(select_incidents(incidents, year, rng))
    selected.sort(key=lambda r: (r["occurred_at"], r["incident_id"]))

    new_rows = []
    num = max(max_num + 1, FIRST_REPORT_NUM)
    for inc in selected:
        report_id = "IR-%d" % num
        num += 1
        if report_id in existing_ids:
            sys.exit("refusing to overwrite existing %s" % report_id)
        author = rng.choice(AUTHORS)
        inc = dict(inc)
        inc["_root_cause"] = rng.choice(ROOT_CAUSE[inc["type"]])
        inc["_remediation"] = rng.choice(REMEDIATION[inc["type"]])
        ts = filed_at(inc["occurred_at"], rng)
        assert ts[:4] == inc["incident_id"].split("-")[1], (report_id, ts, inc["incident_id"])
        ship = inc["shipment_id"] if inc["shipment_id"] in shipments else ""
        body = build_body(inc, author, ts, ship)
        new_rows.append(
            {
                "report_id": report_id,
                "incident_id": inc["incident_id"],
                "author": author,
                "filed_at": ts,
                "severity": inc["severity"],
                "shipment_id": ship,
                "body": body,
            }
        )

    header = ["report_id", "incident_id", "author", "filed_at", "severity", "shipment_id", "body"]
    with open(REP_PATH, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        for row in new_rows:
            w.writerow(row)

    print("appended %d rows: %s .. %s" % (len(new_rows), new_rows[0]["report_id"], new_rows[-1]["report_id"]))
    print("filed_at range: %s .. %s" % (min(r["filed_at"] for r in new_rows), max(r["filed_at"] for r in new_rows)))
    by_year = Counter(r["filed_at"][:4] for r in new_rows)
    print("by year:", dict(by_year))
    by_type = Counter(r["body"].split("\u2014 ")[1].split(" (")[0] for r in new_rows)
    print("by type:", dict(by_type))
    by_month = Counter(r["filed_at"][:7] for r in new_rows)
    print("per-month max:", max(by_month.values()))


if __name__ == "__main__":
    main()
