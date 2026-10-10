#!/usr/bin/env python3
"""Deterministically add a promised-delivery clock to seeds/shipments.csv: three new
columns, promised_delivery_at, hours_late and late_bucket, so lateness can be measured
in hours rather than only read off the status flag.

Enrichment, not a rebuild. The file is processed line by line on the raw text: each
data line is split on "," (no field in this file contains a comma or a quote), the three
new fields are appended, and the line is rejoined with its original CRLF ending. Every
existing field is byte-identical to the input, delivered_at included (empty for
failed/returned). Any pre-existing promised_delivery_at/hours_late/late_bucket columns
are dropped first, so running the script twice gives the same bytes. Reads
seeds/contracts.csv, seeds/clients.csv and seeds/hubs.csv (all read-only).

The promise. committed_transit (hours) is the account's contracted service window:
  SERVICE_BASE[service_level]            expedited 36, standard 60, freight 84
  + ACCOUNT_ADJ[client_id]               round((97.0 - sla_ontime_pct) * 6), from the
                                         client's current (latest-effective) contract:
                                         a higher SLA target is a tighter promise
  + HUB_PAIR_ADJ[origin hub state][client region]
                                         same state 0, neighbouring state 12, farther 24
  + jitter                               a seeded per-shipment draw in -6..+6

Rules, by status (lag = delivered_at - created_at, in hours):
  delivered          promised = created_at + max(committed_transit, lag): the promise was
                     met, so it lands at or after the actual delivery. hours_late null,
                     late_bucket 'on_time'.
  delayed            promised = delivered_at - overshoot: the promise was missed.
                     hours_late = overshoot, late_bucket = its bucket.
  failed / returned  promised = created_at + committed_transit (a promise was still
                     made). hours_late and late_bucket null.

The 2025 story. overshoot is drawn per delayed shipment:
  2023-2024 (quiet years)            2-10h   barely late
  January 2025 (the Chicago storm)   72-168h multi-day
  CLI-0042 in 2025 (the decline)     48-144h multi-day
  other 2025                         12-48h  1-2d
then clamped to [2, lag - SERVICE_BASE], so the reconstructed promise never falls
before the service base and always stays strictly before the delivery. A quiet-year
late shipment's reconstructed window is therefore close to its (long) actual transit:
deliberate, the healthy years' promise was a generous window missed by only hours.

late_bucket: on_time, <4h (2-3), 4-12h (4-12), 1-2d (13-48), >2d (over 48).

Run from the repo root:  python3 scripts/generate_promised_delivery.py
Verify without writing:  python3 scripts/generate_promised_delivery.py --check
(--check exits 1 if the seed on disk differs from what the script would write.)
"""
import collections
import csv
import os
import random
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")
SHIPMENTS = os.path.join(SEEDS, "shipments.csv")

SEED = 20251231
EQUIPMENT = "CLI-0042"
STORM_MONTH = "2025-01"
QUIET_YEARS = ("2023", "2024")

BASE_COLUMNS = ["shipment_id", "client_id", "origin_hub_id", "service_level",
                "created_at", "delivered_at", "status", "route_id"]
NEW_COLUMNS = ["promised_delivery_at", "hours_late", "late_bucket"]

# Committed transit before account/lane adjustments, in hours: tighter for faster service.
SERVICE_BASE = {"expedited": 36, "standard": 60, "freight": 84}

SLA_REFERENCE = 97.0      # the tightest SLA on the book: no extra hours
HOURS_PER_SLA_POINT = 6   # each point of SLA below the reference buys 6h of window

# Hub cities are not in hubs.csv as states; map them here.
HUB_STATE = {"Columbus": "OH", "Chicago": "IL", "Indianapolis": "IN",
             "Detroit": "MI", "Cincinnati": "OH"}

# Land borders among the states in play. Michigan/Illinois only share Lake Michigan,
# so they count as farther apart.
ADJACENT_STATES = {
    frozenset(p) for p in (("OH", "IN"), ("OH", "MI"), ("OH", "KY"), ("IN", "IL"),
                           ("IN", "MI"), ("IN", "KY"), ("IL", "KY"))
}
SAME_STATE_HOURS, NEIGHBOUR_HOURS, FARTHER_HOURS = 0, 12, 24

JITTER_HOURS = 6

# Delayed overshoot ranges (hours, inclusive).
OVERSHOOT_QUIET = (2, 10)
OVERSHOOT_STORM = (72, 168)
OVERSHOOT_EQUIPMENT_2025 = (48, 144)
OVERSHOOT_OTHER_2025 = (12, 48)
MIN_OVERSHOOT = 2

LATE_BUCKETS = ["on_time", "<4h", "4-12h", "1-2d", ">2d"]

TS_OUT = "%Y-%m-%dT%H:%M:%S"


def read(name):
    with open(os.path.join(SEEDS, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_ts(value):
    return datetime.fromisoformat(value)


def account_adjustments():
    """Hours added per client from its current contract's SLA target."""
    latest = {}
    for c in read("contracts.csv"):
        prior = latest.get(c["client_id"])
        if prior is None or c["effective_date"] > prior["effective_date"]:
            latest[c["client_id"]] = c
    return {cid: round((SLA_REFERENCE - float(c["sla_ontime_pct"])) * HOURS_PER_SLA_POINT)
            for cid, c in latest.items()}


def hub_pair_adjustments():
    """HUB_PAIR_ADJ[hub_id][client region] in hours."""
    hub_state = {h["hub_id"]: HUB_STATE[h["city"]] for h in read("hubs.csv")}
    regions = sorted({c["region"] for c in read("clients.csv")})
    matrix = {}
    for hub_id, state in hub_state.items():
        matrix[hub_id] = {}
        for region in regions:
            if region == state:
                hours = SAME_STATE_HOURS
            elif frozenset((state, region)) in ADJACENT_STATES:
                hours = NEIGHBOUR_HOURS
            else:
                hours = FARTHER_HOURS
            matrix[hub_id][region] = hours
    return matrix


def overshoot_range(created_at, client_id):
    year, month = created_at[:4], created_at[:7]
    if year in QUIET_YEARS:
        return OVERSHOOT_QUIET
    if month == STORM_MONTH:
        return OVERSHOOT_STORM
    if client_id == EQUIPMENT:
        return OVERSHOOT_EQUIPMENT_2025
    return OVERSHOOT_OTHER_2025


def bucket(overshoot):
    if overshoot < 4:
        return "<4h"
    if overshoot <= 12:
        return "4-12h"
    if overshoot <= 48:
        return "1-2d"
    return ">2d"


def hours_between(start, end):
    seconds = (end - start).total_seconds()
    assert seconds % 3600 == 0, (start, end)
    return int(seconds // 3600)


def build():
    with open(SHIPMENTS, "rb") as f:
        raw = f.read().decode("utf-8")
    assert raw.endswith("\r\n"), "shipments.csv must end with CRLF"
    lines = raw[:-2].split("\r\n")

    header = lines[0].split(",")
    keep = [i for i, col in enumerate(header) if col not in NEW_COLUMNS]
    assert [header[i] for i in keep] == BASE_COLUMNS, header

    account_adj = account_adjustments()
    hub_pair_adj = hub_pair_adjustments()
    client_region = {c["client_id"]: c["region"] for c in read("clients.csv")}
    rng = random.Random(SEED)

    out = [",".join(BASE_COLUMNS + NEW_COLUMNS)]
    rows = []
    for line in lines[1:]:
        fields = line.split(",")
        assert len(fields) == len(header), line
        fields = [fields[i] for i in keep]
        assert len(fields) == 8, line
        r = dict(zip(BASE_COLUMNS, fields))

        created = parse_ts(r["created_at"])
        base = SERVICE_BASE[r["service_level"]]
        committed = (base
                     + account_adj[r["client_id"]]
                     + hub_pair_adj[r["origin_hub_id"]][client_region[r["client_id"]]]
                     + rng.randint(-JITTER_HOURS, JITTER_HOURS))

        status = r["status"]
        if status == "delivered":
            lag = hours_between(created, parse_ts(r["delivered_at"]))
            promised = created + timedelta(hours=max(committed, lag))
            hours_late, late_bucket = "", "on_time"
        elif status == "delayed":
            delivered = parse_ts(r["delivered_at"])
            lag = hours_between(created, delivered)
            lo, hi = overshoot_range(r["created_at"], r["client_id"])
            overshoot = min(max(rng.randint(lo, hi), MIN_OVERSHOOT), lag - base)
            assert overshoot >= MIN_OVERSHOOT, line
            promised = delivered - timedelta(hours=overshoot)
            hours_late, late_bucket = str(overshoot), bucket(overshoot)
        else:
            assert status in ("failed", "returned"), line
            promised = created + timedelta(hours=committed)
            hours_late, late_bucket = "", ""

        new = [promised.strftime(TS_OUT), hours_late, late_bucket]
        out.append(",".join(fields + new))
        rows.append((r, new))

    return ("\r\n".join(out) + "\r\n").encode("utf-8"), rows


def summarise(rows):
    total = len(rows)
    print(f"rows: {total}")
    statuses = collections.Counter(r["status"] for r, _ in rows)
    for status, n in statuses.most_common():
        print(f"  {status:<10} {n:>5}  {100.0 * n / total:5.1f}%")

    print("late_bucket by year (delivered = on_time; failed/returned = null):")
    by_year = collections.defaultdict(collections.Counter)
    for r, (_, _, late_bucket) in rows:
        by_year[r["created_at"][:4]][late_bucket or "null"] += 1
    cols = LATE_BUCKETS + ["null"]
    print("  year  " + "".join(f"{c:>9}" for c in cols))
    for year in sorted(by_year):
        print(f"  {year}  " + "".join(f"{by_year[year][c]:>9}" for c in cols))

    print("delayed hours_late by year (min / median / max):")
    late = collections.defaultdict(list)
    for r, (_, hours_late, _) in rows:
        if hours_late:
            late[r["created_at"][:4]].append(int(hours_late))
    for year in sorted(late):
        v = sorted(late[year])
        print(f"  {year}  n={len(v):<4} {v[0]} / {v[len(v) // 2]} / {v[-1]}")

    promised = [p for _, (p, _, _) in rows]
    print(f"promised_delivery_at: min {min(promised)}  max {max(promised)}")


def main():
    check = "--check" in sys.argv[1:]
    data, rows = build()
    if check:
        with open(SHIPMENTS, "rb") as f:
            current = f.read()
        summarise(rows)
        if current != data:
            print("CHECK FAILED: seeds/shipments.csv differs from generator output")
            sys.exit(1)
        print("check ok: seeds/shipments.csv matches generator output")
        return
    with open(SHIPMENTS, "wb") as f:
        f.write(data)
    summarise(rows)


if __name__ == "__main__":
    main()
