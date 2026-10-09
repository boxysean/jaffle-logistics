#!/usr/bin/env python3
"""Deterministically extend the Jaffle Logistics CRM note history backwards in
time, adding the quiet years 2023 and 2024 to seeds/crm_notes.csv and their
labels to seeds/eval_crm_sentiment.csv.

APPEND ONLY: the existing CSV bytes are read untouched; new rows are appended
after them. Ids continue the existing CRM-5xxx scheme above the current max, and
every referenced shipment_id points at a shipment that exists for the same
client in the same month (account-level QBRs stay null, as they do today).

Story the notes tell:
  * 2023-2024 are the quiet, healthy years: on-time at or above the contractual
    target, praise for the Columbus and Cincinnati hubs, ordinary gripes about a
    specific late load. Jaffle Equipment (CLI-0042) is a good account (~98%).
  * No storm escalation, no Columbus bay-3 handling-damage pattern, no Jaffle
    Equipment deterioration: those belong to 2025 and are already written.
Nothing about 2025 is modified.
"""
import collections
import csv
import datetime
import io
import os
import random
import sys

SEED = 20231114
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

# client_id -> the account-voice facts the notes must stay consistent with
CLIENTS = {
    "CLI-0007": {
        "name": "Jaffle Storefronts", "owner": "Dana Whitfield",
        "sla": 97.0, "lob": "last-mile", "region": "OH",
        "contract": "CON-0007-01", "eff": "2022-04-16", "mean": 97.8,
    },
    "CLI-0042": {
        "name": "Jaffle Equipment", "owner": "Marcus Trent",
        "sla": 97.0, "lob": "LTL", "region": "IL",
        "contract": "CON-0042-01", "eff": "2023-11-14", "mean": 98.0,
    },
    "CLI-0155": {
        "name": "Jaffle Crew Outfitters", "owner": "Nora Behrevan",
        "sla": 95.0, "lob": "last-mile", "region": "IN",
        "contract": "CON-0155-01", "eff": "2023-07-28", "mean": 97.0,
    },
    "CLI-0169": {
        "name": "Jaffle Beverage Co", "owner": "Sam Calloway",
        "sla": 95.0, "lob": "warehousing", "region": "OH",
        "contract": "CON-0169-01", "eff": "2024-06-24", "mean": 96.0,
    },
    "CLI-0201": {
        "name": "Jaffle Paper & Packaging", "owner": "Priya Rao",
        "sla": 92.0, "lob": "LTL", "region": "KY",
        "contract": "CON-0201-01", "eff": "2024-06-14", "mean": 94.0,
    },
}

# Other reps who pick up calls on an account (matches the existing call notes).
SECONDARY_OWNERS = {
    "CLI-0007": ["Marcus Trent", "Dana Whitfield"],
    "CLI-0042": ["Marcus Trent"],
    "CLI-0155": ["Elaine Vasquez", "Nora Behrevan"],
    "CLI-0169": ["Priya Rao", "Sam Calloway"],
    "CLI-0201": ["Sam Calloway", "Priya Rao"],
}

# The schedule: (client_id, date, note_type). QBRs land at a real quarterly
# cadence; calls/reviews interleave; pre-contract notes (before a client's
# contract effective date) never cite the contract id.
SCHEDULE = [
    # ---- 2023 ----
    ("CLI-0007", "2023-03-16", "QBR"),
    ("CLI-0007", "2023-06-14", "QBR"),
    ("CLI-0155", "2023-03-09", "call"),
    ("CLI-0042", "2023-02-07", "plan"),
    ("CLI-0169", "2023-05-18", "QBR"),
    ("CLI-0201", "2023-05-04", "call"),
    ("CLI-0042", "2023-06-20", "call"),
    ("CLI-0007", "2023-08-09", "call"),
    ("CLI-0155", "2023-09-19", "QBR"),
    ("CLI-0169", "2023-09-07", "call"),
    ("CLI-0201", "2023-09-21", "QBR"),
    ("CLI-0007", "2023-09-13", "QBR"),
    ("CLI-0169", "2023-11-15", "QBR"),
    ("CLI-0042", "2023-12-05", "QBR"),
    ("CLI-0007", "2023-12-12", "QBR"),
    ("CLI-0155", "2023-12-14", "QBR"),
    # ---- 2024 ----
    ("CLI-0042", "2024-03-14", "QBR"),
    ("CLI-0007", "2024-03-19", "QBR"),
    ("CLI-0169", "2024-04-16", "QBR"),
    ("CLI-0201", "2024-05-15", "QBR"),
    ("CLI-0042", "2024-05-08", "call"),
    ("CLI-0007", "2024-06-11", "QBR"),
    ("CLI-0155", "2024-06-12", "QBR"),
    ("CLI-0042", "2024-06-18", "QBR"),
    ("CLI-0007", "2024-07-23", "call"),
    ("CLI-0169", "2024-07-19", "call"),
    ("CLI-0042", "2024-09-17", "QBR"),
    ("CLI-0155", "2024-09-11", "call"),
    ("CLI-0007", "2024-09-10", "QBR"),
    ("CLI-0169", "2024-10-08", "QBR"),
    ("CLI-0201", "2024-11-06", "QBR"),
    ("CLI-0042", "2024-12-03", "QBR"),
    ("CLI-0007", "2024-12-10", "QBR"),
    ("CLI-0155", "2024-12-12", "QBR"),
]

POSITIVE_CLOSINGS = [
    "Strong quarter. Discussed expanding volume into new lanes.",
    "Client happy with responsiveness; exploring expanded lanes next quarter.",
    "Client again praised the Columbus hub turnaround on recent pickups.",
    "Client complimented the Cincinnati hub team on a steady quarter.",
    "No escalations this quarter; client signed off on the lane plan.",
    "Client singled out the Columbus dock crew for a clean peak week.",
    "Volume steady. Client asked about peak-season capacity planning.",
]
NEUTRAL_CLOSINGS = [
    "A few isolated exceptions discussed; no systemic concerns raised.",
    "Volume steady. Client asked about peak-season capacity planning.",
    "One late load discussed; account owner to follow up with ops.",
    "Client flagged a single delayed pickup; no concerns about the quarter.",
    "Ordinary quarter. Client asked us to keep an eye on one lane.",
    "Nothing outstanding; client reviewed the plan without comment.",
]
CALL_TOPICS = [
    "Quick check-in, nothing outstanding.",
    "Covered upcoming seasonal volume; no action needed.",
    "Confirmed pickup windows for the quarter.",
    "Walked through the lane changes taking effect next month.",
    "A brief logistics touch-base; no issues raised.",
]
CALL_LATE_SHIPMENT = "Discussed a delayed shipment; account owner to follow up with ops."
PLAN_DETAILS = [
    "annual review of committed volumes, lane mix and the seasonal peak plan",
    "account plan refreshed: volume forecast, lane map and service commitments",
    "joint planning session on next year's volume and capacity",
]


def load(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="") as fh:
        return list(csv.DictReader(fh))


def append_rows(name, rows):
    """Append csv rows (CRLF, matching the existing files) after the existing bytes."""
    path = os.path.join(SEEDS, name + ".csv")
    with open(path, "rb") as fh:
        original = fh.read()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    for r in rows:
        w.writerow(r)
    with open(path, "ab") as fh:
        fh.write(buf.getvalue().encode())
    return len(original)


def quarter(datestr):
    m = int(datestr[5:7])
    return "Q%d" % ((m - 1) // 3 + 1)


def main():
    rng = random.Random(SEED)

    # ---- id continuation: start above the existing max CRM-5xxx ----
    existing = load("crm_notes")
    band = [int(r["note_id"].split("-")[1]) for r in existing
            if 5000 <= int(r["note_id"].split("-")[1]) < 6000]
    max_id = max(band)
    if any(n >= 5034 for n in band):
        sys.exit("crm_notes.csv already extended (found id >= CRM-5034); refusing to double-append.")

    # ---- real late shipments by (client, year-month), for call references ----
    late_by_client_month = collections.defaultdict(list)
    for s in load("shipments"):
        if s["status"] in ("delayed", "failed", "returned"):
            late_by_client_month[(s["client_id"], s["created_at"][:7])].append(s["shipment_id"])
    for k in late_by_client_month:
        late_by_client_month[k].sort()

    new_notes = []          # dict rows; ids assigned after the date sort
    next_id = max_id + 1

    for client_id, datestr, note_type in SCHEDULE:
        meta = CLIENTS[client_id]
        date = datetime.date.fromisoformat(datestr)
        assert date.year in (2023, 2024), datestr
        has_contract = datestr >= meta["eff"]
        cid = meta["contract"]

        if note_type == "QBR":
            pct = round(min(99.4, max(meta["sla"] - 0.2, rng.gauss(meta["mean"], 0.55))), 1)
            if pct >= meta["sla"] + 0.5:
                qualifier, sentiment = "above target", "positive"
                closing = rng.choice(POSITIVE_CLOSINGS)
            else:
                qualifier, sentiment = "roughly on target", "neutral"
                closing = rng.choice(NEUTRAL_CLOSINGS)
            owner = meta["owner"]
            body = ("QBR \u2014 {name} ({cid}), {q} {year}. Account owner: {owner}.~~NL~~"
                    "Reviewed service performance against the {sla:.1f}% SLA on-time target; "
                    "trailing-quarter on-time landed at {pct:.1f}% ({qual}). {contract}~~NL~~"
                    "Overall sentiment {sent}. {closing} Line of business: {lob}, region {region}."
                    ).format(name=meta["name"], cid=client_id, q=quarter(datestr), year=date.year,
                             owner=owner, sla=meta["sla"], pct=pct, qual=qualifier,
                             contract=("Contract %s." % cid) if has_contract
                             else "Contract renewal in progress.",
                             sent=sentiment, closing=closing, lob=meta["lob"], region=meta["region"])
            shipment_id = ""
            owner_col = owner

        elif note_type == "plan":
            sentiment = "neutral"
            owner = meta["owner"]
            body = ("Account plan \u2014 {name} ({cid}), {year}. Account owner: {owner}.~~NL~~"
                    "Annual account plan refreshed: {detail}. Contract renewal in progress; "
                    "terms not yet finalised. Sentiment {sent}."
                    ).format(name=meta["name"], cid=client_id, year=date.year, owner=owner,
                             detail=rng.choice(PLAN_DETAILS), sent=sentiment)
            shipment_id = ""
            owner_col = owner

        else:  # call
            owner = rng.choice(SECONDARY_OWNERS[client_id])
            late = late_by_client_month.get((client_id, datestr[:7]), [])
            if late and rng.random() < 0.9:
                shipment_id = rng.choice(late)
                topic = CALL_LATE_SHIPMENT
            else:
                shipment_id = ""
                topic = rng.choice(CALL_TOPICS)
            sentiment = rng.choice(["positive", "positive", "neutral"])
            body = ("Call note \u2014 {name} ({cid}). {owner} spoke with the account contact. "
                    "{topic} Sentiment {sent}."
                    ).format(name=meta["name"], cid=client_id, owner=owner, topic=topic, sent=sentiment)
            owner_col = owner

        new_notes.append({"client_id": client_id, "owner": owner_col, "call_date": datestr,
                          "note_type": note_type, "sentiment": sentiment,
                          "shipment_id": shipment_id, "body": body})

    # ids rise with the calendar and the file reads chronologically (as the
    # existing rows do), so a reviewer can follow the story year by year.
    new_notes.sort(key=lambda r: (r["call_date"], r["client_id"]))

    rows, labels = [], []
    for r in new_notes:
        note_id = "CRM-%d" % next_id
        next_id += 1
        rows.append([note_id, r["client_id"], r["owner"], r["call_date"], r["note_type"],
                     r["sentiment"], r["shipment_id"], r["body"]])
        labels.append([note_id, r["sentiment"]])

    earlier = len(existing)
    append_rows("crm_notes", rows)
    append_rows("eval_crm_sentiment", labels)

    print("appended %d notes (crm_notes %d -> %d) and %d labels"
          % (len(rows), earlier, earlier + len(rows), len(labels)))
    print("new id range: %s .. %s" % (rows[0][0], rows[-1][0]))
    print("date range added: %s .. %s" % (rows[0][3], rows[-1][3]))


if __name__ == "__main__":
    main()
