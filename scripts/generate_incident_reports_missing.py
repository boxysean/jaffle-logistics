#!/usr/bin/env python3
"""Deterministic generator that fills the incident-report gaps in seeds/incident_reports.csv:

  * a report for every severity 1-2 incident in seeds/incidents.csv that has none, and
  * a report for every HUB-CMH damage incident that has none (the 2025 severity 3-4
    ones not already covered by the first rule).

APPEND ONLY: existing rows (IR-9003 and IR-7031 included) stay byte-identical. New
report_ids continue the IR-7xxx block above its current max. The template, author list,
filed_at rule and mundane root-cause/remediation pools are imported from
scripts/generate_incident_reports.py so the voice is identical.

The one departure from the mundane pools: the 2025 HUB-CMH damage reports carry a
dock-staging root cause consistent with IR-9003 and with seeds/dock_bay_events.csv
(bay 3 for the incidents whose dock record is at HUB-CMH-BAY-3, a generic Columbus
dock-staging cause for the rest). No 2023/2024 report gets a staging or bay-3 cause.

Refuses to double-append: once every target incident has a report it appends nothing,
and it aborts if any new report_id already exists.

Run:  python3 scripts/generate_incident_reports_missing.py
"""
import csv
import os
import random
import sys
from collections import Counter

from generate_incident_reports import (
    AUTHORS, INC_PATH, REMEDIATION, REP_PATH, ROOT_CAUSE, SHIP_PATH,
    build_body, filed_at, read_csv,
)
from generate_dock_bay_events import BAY3_2025

SEED = 20251231

CMH_BAY3_ROOT_CAUSE = [
    "Freight staged in the bay 3 forklift lane was struck during loading. Same bay 3 staging pattern as IR-9003; a recurring dock-staging problem, not a vehicle defect.",
    "Bay 3 staging area was over capacity, so pallets were double-stacked into the forklift path and damaged before loading. Recurring at bay 3 in 2025; the vehicle was not a factor.",
    "Damage traced to how freight is staged at bay 3: congested lane, pallets staged past the line and handled twice. Consistent with the bay 3 finding in IR-9003.",
]
CMH_DOCK_ROOT_CAUSE = [
    "Freight staged in an active forklift lane on the Columbus dock was struck before loading. Part of the same 2025 dock-staging problem under review at this hub, not a vehicle defect.",
    "Overflow staging on the Columbus dock left pallets in the forklift path; damaged during handling before the truck was loaded. Dock-staging process issue, not equipment.",
]
CMH_REMEDIATION = [
    "Bay 3 staging lane re-marked and forklift traffic separated from staged freight; supervisor signs off staging before loading.",
    "Staging capacity at bay 3 capped; overflow now routed to the next open bay. Hub supervisor auditing staging against SOP weekly.",
    "Dock staging audit against SOP; staged freight kept out of forklift lanes on every Columbus bay, bay 3 first.",
]

HEADER = ["report_id", "incident_id", "author", "filed_at", "severity", "shipment_id", "body"]


def main():
    rng = random.Random(SEED)
    incidents = read_csv(INC_PATH)
    shipments = {r["shipment_id"] for r in read_csv(SHIP_PATH)}

    with open(REP_PATH, "rb") as fh:
        original = fh.read()
    assert original.endswith(b"\r\n"), "incident_reports.csv does not end with CRLF"
    existing = read_csv(REP_PATH)
    existing_ids = {r["report_id"] for r in existing}
    reported = {r["incident_id"] for r in existing}
    max_num = max(int(r["report_id"].split("-")[1]) for r in existing if r["report_id"].startswith("IR-7"))

    targets = [
        i for i in incidents
        if i["incident_id"] not in reported
        and (int(i["severity"]) <= 2 or (i["hub_id"] == "HUB-CMH" and i["type"] == "damage"))
    ]
    if not targets:
        print("nothing to append: every severity 1-2 and HUB-CMH damage incident already has a report")
        return
    targets.sort(key=lambda r: (r["occurred_at"], r["incident_id"]))

    new_rows = []
    num = max_num + 1
    for inc in targets:
        report_id = "IR-%d" % num
        num += 1
        if report_id in existing_ids:
            sys.exit("refusing to overwrite existing %s" % report_id)
        author = rng.choice(AUTHORS)
        inc = dict(inc)
        year = inc["occurred_at"][:4]
        if inc["hub_id"] == "HUB-CMH" and inc["type"] == "damage" and year == "2025":
            pool = CMH_BAY3_ROOT_CAUSE if inc["incident_id"] in BAY3_2025 else CMH_DOCK_ROOT_CAUSE
            inc["_root_cause"] = rng.choice(pool)
            inc["_remediation"] = rng.choice(CMH_REMEDIATION)
        else:
            inc["_root_cause"] = rng.choice(ROOT_CAUSE[inc["type"]])
            inc["_remediation"] = rng.choice(REMEDIATION[inc["type"]])
        ts = filed_at(inc["occurred_at"], rng)
        assert ts[:4] == year and ts <= "2025-12-31T23:59:59", (report_id, ts)
        ship = inc["shipment_id"] if inc["shipment_id"] in shipments else ""
        body = build_body(inc, author, ts, ship)
        if year in ("2023", "2024"):
            assert "bay 3" not in body.lower() and "staging" not in body.lower(), report_id
        new_rows.append({
            "report_id": report_id,
            "incident_id": inc["incident_id"],
            "author": author,
            "filed_at": ts,
            "severity": inc["severity"],
            "shipment_id": ship,
            "body": body,
        })

    with open(REP_PATH, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        for row in new_rows:
            w.writerow(row)
    with open(REP_PATH, "rb") as fh:
        assert fh.read().startswith(original), "existing bytes changed"

    by_inc = {i["incident_id"]: i for i in incidents}
    print("appended %d rows: %s .. %s" % (len(new_rows), new_rows[0]["report_id"], new_rows[-1]["report_id"]))
    print("filed_at range: %s .. %s" % (min(r["filed_at"] for r in new_rows), max(r["filed_at"] for r in new_rows)))
    print("severity 1-2 by year:", dict(sorted(Counter(
        r["filed_at"][:4] for r in new_rows if int(r["severity"]) <= 2).items())))
    print("HUB-CMH damage by year:", dict(sorted(Counter(
        r["filed_at"][:4] for r in new_rows
        if by_inc[r["incident_id"]]["hub_id"] == "HUB-CMH" and by_inc[r["incident_id"]]["type"] == "damage").items())))
    print("severity 3-4 added:", sum(1 for r in new_rows if int(r["severity"]) >= 3))


if __name__ == "__main__":
    main()
