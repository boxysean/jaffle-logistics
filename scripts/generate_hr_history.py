#!/usr/bin/env python3
"""Deterministic generator for rows appended to seeds/hr_docs.csv.

The HR file already spans 2018-2025, so this adds records across that whole window:
onboarding records for the drivers hired 2022-2024 who are missing one, plus annual
performance reviews, certifications, a few training and disciplinary notes, and one
exit. Voices/authors match the existing rows (X. Y (People Ops)); bodies use the same
'~~NL~~'-joined structure.

New doc_types (review, certification, exit) are added to the accepted_values test on
stg_hr_docs so the build stays green.

Appends only; continues the HR-6xxx block upward from HR-6059.

Run:  python3 scripts/generate_hr_history.py
"""
import csv
import datetime as dt
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, os.pardir, "seeds")
HR_PATH = os.path.join(SEEDS, "hr_docs.csv")
DRV_PATH = os.path.join(SEEDS, "drivers.csv")

SEED = 20231010
FIRST_HR_NUM = 6060          # continue HR-6xxx upward (existing 6xxx block ends HR-6059)
N_REVIEWS = 30
N_CERTS = 20
N_TRAINING = 6
N_DISCIPLINARY = 5
EXIT_DRIVER = "DRV-01188"    # the deactivated contractor -- the one natural exit

AUTHORS = [
    "R. Sandoval (People Ops)",
    "K. Ellsworth (People Ops)",
    "D. Marchetti (People Ops)",
]

CERTIFICATIONS = [
    "DOT medical examiner's certificate",
    "Defensive driving certification",
    "Air brake endorsement",
    "First aid / CPR certification",
    "Forklift operator certification",
    "Hazmat awareness certification",
]

TRAINING_MODULES = [
    "customer service basics",
    "defensive driving refresher",
    "winter operations module",
    "load securement refresher",
    "pre-trip inspection refresher",
]

REVIEW_NOTES = [
    "Consistent on-time performance and clean paperwork; a reliable route lead.",
    "Handles customer handoffs well; encouraged to tighten end-of-day POD filing.",
    "Steady year with no safety events; completed all assigned compliance modules.",
    "Good route discipline; noted a few late pre-trip starts to correct.",
    "Strong on disputed-delivery follow-through; a trusted escalation point.",
    "Meets route metrics; coaching offered on winter-approach following distance.",
]

REVIEW_RATING = [
    (lambda s: s >= 4.5, "exceeds expectations"),
    (lambda s: s >= 3.5, "meets expectations"),
    (lambda s: s >= 3.0, "meets most expectations"),
    (lambda s: True, "developing"),
]

DISCIPLINARY = [
    "Coaching session logged regarding POD compliance.",
    "Verbal warning for repeated late starts.",
    "Coaching session logged regarding pre-trip inspection completion.",
    "Coaching session logged regarding route-app stop confirmations.",
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def rating_word(score):
    for pred, word in REVIEW_RATING:
        if pred(score):
            return word
    return "developing"


def rand_date(rng, year, floor=None, ceil=None):
    """A date within `year`, clamped to be >= floor and <= ceil when given."""
    lo = dt.date(year, 1, 1)
    hi = dt.date(year, 12, 31)
    if floor:
        lo = max(lo, floor)
    if ceil:
        hi = min(hi, ceil)
    if hi < lo:
        return None
    span = (hi - lo).days
    return lo + dt.timedelta(days=rng.randint(0, span))


def drivers_sorted(drivers):
    return sorted(drivers, key=lambda d: d["driver_id"])


def pick(drivers, year, rng, used, min_days_after_hire=0):
    """A driver, distinct on (driver, year), whose hire date allows a doc in `year`.

    `used` accumulates the (driver_id, year) pairs already claimed for this doc type so
    no driver gets two same-year instances (reviews/certs are one-per-year by design).
    """
    for _ in range(600):
        d = rng.choice(drivers)
        key = (d["driver_id"], year)
        if key in used:
            continue
        floor = dt.date.fromisoformat(d["hire_date"]) + dt.timedelta(days=min_days_after_hire)
        date = rand_date(rng, year, floor=floor)
        if date is None:
            continue
        used.add(key)
        return d, date
    return None, None


def main():
    rng = random.Random(SEED)
    drivers = drivers_sorted(read_csv(DRV_PATH))
    drivers_by_id = {d["driver_id"]: d for d in drivers}

    existing = read_csv(HR_PATH)
    existing_ids = {r["hr_doc_id"] for r in existing}
    nums = [int(r["hr_doc_id"].split("-")[1]) for r in existing
            if r["hr_doc_id"].startswith("HR-6")]
    next_num = max(max(nums) + 1, FIRST_HR_NUM)

    have_onboarding = {r["driver_id"] for r in existing if r["doc_type"] == "onboarding"}

    new_rows = []

    # 1) onboarding for every driver hired 2022-2024 who is missing one
    missing = [d for d in drivers if d["driver_id"] not in have_onboarding]
    for d in missing:
        hy = dt.date.fromisoformat(d["hire_date"])
        created = hy + dt.timedelta(days=rng.randint(1, 6))
        kind = d["employment_type"]
        ack = "contractor agreement" if kind == "contractor" else "employee handbook"
        author = rng.choice(AUTHORS)
        body = "~~NL~~".join([
            "ONBOARDING RECORD \u2014 driver %s (%s), home hub %s." % (d["driver_id"], kind, d["hub_id"]),
            "Hire date %s. Completed orientation, safety briefing, and %s acknowledgment. "
            "Vehicle familiarization and route-app training complete. Filed by %s."
            % (d["hire_date"], ack, author),
        ])
        new_rows.append({
            "driver_id": d["driver_id"], "doc_type": "onboarding",
            "created_at": created.isoformat(), "author": author, "body": body,
        })

    # 2) annual performance reviews, spread across 2019-2025
    years_bag = [y for y in range(2019, 2025) for _ in range(5)]  # 30 slots
    rng.shuffle(years_bag)
    used_reviews = set()
    for year in years_bag:
        d, date = pick(drivers, year, rng, used_reviews, min_days_after_hire=365)
        if not d or date is None:
            continue
        author = rng.choice(AUTHORS)
        rw = rating_word(float(d["perf_score"]))
        body = "~~NL~~".join([
            "PERFORMANCE REVIEW \u2014 driver %s (%s), home hub %s."
            % (d["driver_id"], d["employment_type"], d["hub_id"]),
            "%d annual review completed %s. Overall rating %s." % (year, date.isoformat(), rw),
            "%s Filed by %s." % (rng.choice(REVIEW_NOTES), author),
        ])
        new_rows.append({
            "driver_id": d["driver_id"], "doc_type": "review",
            "created_at": date.isoformat(), "author": author, "body": body,
        })

    # 3) certifications, renewals spread across 2019-2025
    cert_years = [y for y in range(2019, 2025) for _ in range(4)][:N_CERTS]
    rng.shuffle(cert_years)
    used_certs = set()
    for year in cert_years:
        d, date = pick(drivers, year, rng, used_certs, min_days_after_hire=14)
        if not d or date is None:
            continue
        author = rng.choice(AUTHORS)
        cert = rng.choice(CERTIFICATIONS)
        valid_through = date + dt.timedelta(days=730)
        body = "~~NL~~".join([
            "CERTIFICATION RECORD \u2014 driver %s (%s), home hub %s."
            % (d["driver_id"], d["employment_type"], d["hub_id"]),
            "%s renewed %s; valid through %s." % (cert, date.isoformat(), valid_through.isoformat()),
            "Copy on file. Filed by %s." % author,
        ])
        new_rows.append({
            "driver_id": d["driver_id"], "doc_type": "certification",
            "created_at": date.isoformat(), "author": author, "body": body,
        })

    # 4) a few training records (2021-2024)
    train_years = [2021, 2022, 2022, 2023, 2023, 2024]
    rng.shuffle(train_years)
    used_training = set()
    for year in train_years:
        d, date = pick(drivers, year, rng, used_training, min_days_after_hire=14)
        if not d or date is None:
            continue
        author = rng.choice(AUTHORS)
        mod = rng.choice(TRAINING_MODULES)
        body = "TRAINING RECORD \u2014 driver %s. Completed %s on %s. Filed by %s." % (
            d["driver_id"], mod, date.isoformat(), author)
        new_rows.append({
            "driver_id": d["driver_id"], "doc_type": "training",
            "created_at": date.isoformat(), "author": author, "body": body,
        })

    # 5) a few disciplinary notes (2020-2024)
    disc_years = [2020, 2021, 2022, 2023, 2024]
    rng.shuffle(disc_years)
    used_disc = set()
    for year in disc_years:
        d, date = pick(drivers, year, rng, used_disc, min_days_after_hire=30)
        if not d or date is None:
            continue
        author = rng.choice(AUTHORS)
        reason = rng.choice(DISCIPLINARY)
        body = "DISCIPLINARY NOTE \u2014 driver %s (%s). %s Acknowledged and filed by %s on %s." % (
            d["driver_id"], d["employment_type"], reason, author, date.isoformat())
        new_rows.append({
            "driver_id": d["driver_id"], "doc_type": "disciplinary",
            "created_at": date.isoformat(), "author": author, "body": body,
        })

    # 6) one exit -- the deactivated contractor
    d = drivers_by_id[EXIT_DRIVER]
    exit_date = dt.date(2025, 9, 15)
    author = rng.choice(AUTHORS)
    body = "~~NL~~".join([
        "EXIT RECORD \u2014 driver %s (%s), home hub %s." % (d["driver_id"], d["employment_type"], d["hub_id"]),
        "Contractor relationship ended %s following the September deactivation. "
        "Equipment, fuel card and route-app access returned." % exit_date.isoformat(),
        "Final settlement processed by %s." % author,
    ])
    new_rows.append({
        "driver_id": d["driver_id"], "doc_type": "exit",
        "created_at": exit_date.isoformat(), "author": author, "body": body,
    })

    # assign ids and write
    for i, row in enumerate(new_rows):
        row["hr_doc_id"] = "HR-%d" % (next_num + i)
    new_rows.sort(key=lambda r: (r["created_at"], r["hr_doc_id"]))

    for row in new_rows:
        if row["hr_doc_id"] in existing_ids:
            sys.exit("refusing to overwrite existing %s" % row["hr_doc_id"])
        assert row["driver_id"] in drivers_by_id
        assert row["created_at"] >= drivers_by_id[row["driver_id"]]["hire_date"], row
        assert row["created_at"] <= "2025-12-31"

    header = ["hr_doc_id", "driver_id", "doc_type", "created_at", "author", "body"]
    with open(HR_PATH, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        for row in new_rows:
            w.writerow(row)

    print("appended %d rows: %s .. %s" % (len(new_rows), new_rows[0]["hr_doc_id"], new_rows[-1]["hr_doc_id"]))
    print("created_at range: %s .. %s" % (
        min(r["created_at"] for r in new_rows), max(r["created_at"] for r in new_rows)))
    print("by doc_type:", dict(Counter(r["doc_type"] for r in new_rows)))
    print("by year:", dict(sorted(Counter(r["created_at"][:4] for r in new_rows).items())))


if __name__ == "__main__":
    main()
