#!/usr/bin/env python3
"""Deterministically extend Jaffle Logistics' legal history backwards in time.

Adds a 2020-2024 paper trail behind the existing 2022-2025 rows in
seeds/legal_docs.csv and seeds/contracts.csv, so the operating years now sit on
top of a visible contract history (superseded original agreements, renewals,
addenda, a side letter, driver agreements).

APPEND ONLY: the existing CSV bytes are read and re-written untouched; new rows
are appended after them. Every id continues the existing scheme (LGL-4xxx for
legal docs, CON-<client>-NN for contracts) and every foreign key points at a row
that exists (the five clients and two long-tenured drivers).

Story the numbers tell:
  * Each client's `-00` contract is the superseded ORIGINAL agreement (a slightly
    lower service level than the current `-01`); `-01` is the standing agreement;
    `-02` (CLI-0042, 2025) is a mid-term amendment.
  * CLI-0042 goes 95.5% (2021) -> 97.0% (2023) -> 97.0% (2025 amendment), so the
    97.0% target the 2025 analysis depends on is still the standing figure at the
    end of 2025.
Nothing about 2025 operations is modified.

Deterministic: fixed content, no randomness beyond a seeded author rotation.
"""
import csv
import io
import os
import random

SEED = 20200416
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

CREDIT_TERMS = ("1.0% of monthly spend credited per full percentage point below "
                "the SLA on-time target, capped at 10% of monthly spend.")
AUTHORS = ["N. Brightwater", "S. Ackerman", "T. Ramachandran", "M. Osei"]

# client -> (display name, line of business, region) — mirrors seeds/clients.csv
CLIENT = {
    "CLI-0007": ("Jaffle Storefronts",   "last-mile",   "OH"),
    "CLI-0042": ("Jaffle Equipment",     "LTL",         "IL"),
    "CLI-0155": ("Jaffle Crew Outfitters", "last-mile", "IN"),
    "CLI-0169": ("Jaffle Beverage Co",   "warehousing", "OH"),
    "CLI-0201": ("Jaffle Paper & Packaging", "LTL",     "KY"),
}

# ---------------------------------------------------------------- contracts
# (contract_id, client_id, effective_date, sla_ontime_pct)
NEW_CONTRACTS = [
    ("CON-0007-00", "CLI-0007", "2020-04-16", "96.0"),
    ("CON-0155-00", "CLI-0155", "2021-07-28", "94.0"),
    ("CON-0042-00", "CLI-0042", "2021-11-14", "95.5"),
    ("CON-0201-00", "CLI-0201", "2022-06-14", "91.0"),
    ("CON-0169-00", "CLI-0169", "2022-06-24", "94.0"),
    ("CON-0042-02", "CLI-0042", "2025-05-12", "97.0"),
]

# -------------------------------------------------------------- legal docs
# (doc_id, client_id, driver_id, effective_date, doc_type, body)
NEW_DOCS = []


def msa(doc_id, client_id, date, contract_id, sla, author):
    name, lob, region = CLIENT[client_id]
    body = (
        "MASTER SERVICES AGREEMENT \u2014 Jaffle Logistics and %s (%s).~~NL~~"
        "Effective %s. Referenced contract: %s.~~NL~~"
        "1. SERVICES. Jaffle Logistics shall provide %s logistics services in the "
        "%s region.~~NL~~"
        "2. SERVICE LEVELS. Target on-time delivery of %s%% measured monthly.~~NL~~"
        "3. CREDITS. %s~~NL~~"
        "4. TERM. Initial term of twenty-four (24) months, auto-renewing for "
        "successive twelve (12) month terms.~~NL~~"
        "Prepared by %s (Legal)."
    ) % (name, client_id, date, contract_id, lob, region, sla, CREDIT_TERMS, author)
    return (doc_id, client_id, "", date, "MSA", body)


# Superseded original agreements (the predecessors of each client's current -01).
NEW_DOCS.append(msa("LGL-4014", "CLI-0007", "2020-04-16", "CON-0007-00", "96.0", "S. Ackerman"))
NEW_DOCS.append(msa("LGL-4015", "CLI-0155", "2021-07-28", "CON-0155-00", "94.0", "T. Ramachandran"))
NEW_DOCS.append(msa("LGL-4016", "CLI-0042", "2021-11-14", "CON-0042-00", "95.5", "N. Brightwater"))
NEW_DOCS.append(msa("LGL-4017", "CLI-0201", "2022-06-14", "CON-0201-00", "91.0", "M. Osei"))
NEW_DOCS.append(msa("LGL-4018", "CLI-0169", "2022-06-24", "CON-0169-00", "94.0", "N. Brightwater"))

# Mid-term addenda / a side letter — one per client plus a measurement-clause note.
NEW_DOCS.append((
    "LGL-4019", "CLI-0155", "", "2022-11-08", "SLA_addendum",
    "SLA ADDENDUM to CON-0155-00 \u2014 Jaffle Crew Outfitters (CLI-0155). Effective 2022-11-08.~~NL~~"
    "The parties agree to clarify that on-time delivery is measured against the contracted "
    "service window using the hub scan-out timestamp as the origin event. All other terms of "
    "the Master Services Agreement remain in effect. Credit mechanics per the MSA are unchanged."
))
NEW_DOCS.append((
    "LGL-4020", "CLI-0169", "", "2023-04-11", "SLA_addendum",
    "SIDE LETTER \u2014 Jaffle Beverage Co (CLI-0169), contract CON-0169-00. Effective 2023-04-11.~~NL~~"
    "The parties acknowledge a one-time carry-over of an unused service credit from the prior "
    "measurement period, to be applied against the next qualifying shortfall. This letter is "
    "administrative only and does not amend the Master Services Agreement."
))
NEW_DOCS.append((
    "LGL-4021", "CLI-0042", "", "2024-01-30", "SLA_addendum",
    "SLA ADDENDUM to CON-0042-01 \u2014 Jaffle Equipment (CLI-0042). Effective 2024-01-30.~~NL~~"
    "The parties agree that, for shipments tendered during the peak-season window (November 15 "
    "to December 24), the on-time measurement window is extended by one (1) business day. All "
    "other terms of the Master Services Agreement remain in effect. Credit mechanics per the MSA "
    "are unchanged."
))
NEW_DOCS.append((
    "LGL-4022", "CLI-0007", "", "2024-03-15", "SLA_addendum",
    "SLA ADDENDUM to CON-0007-01 \u2014 Jaffle Storefronts (CLI-0007). Effective 2024-03-15.~~NL~~"
    "The parties confirm the renewal of CON-0007-01 for a further twelve (12) month term and "
    "restate the target on-time delivery of 97.0% measured monthly. No other terms of the Master "
    "Services Agreement are modified."
))
NEW_DOCS.append((
    "LGL-4023", "CLI-0201", "", "2024-11-05", "SLA_addendum",
    "SLA ADDENDUM to CON-0201-01 \u2014 Jaffle Paper & Packaging (CLI-0201). Effective 2024-11-05.~~NL~~"
    "The parties agree to adjust the on-time measurement window to exclude documented force-majeure "
    "weather events at the origin hub. All other terms of the Master Services Agreement remain in "
    "effect. Credit mechanics per the MSA are unchanged."
))


def driver_agreement(doc_id, driver_id, date):
    body = (
        "INDEPENDENT CONTRACTOR DRIVER AGREEMENT \u2014 %s. Effective %s.~~NL~~"
        "1. RELATIONSHIP. Contractor operates as an independent contractor, not an employee.~~NL~~"
        "2. PERFORMANCE. Contractor shall complete assigned routes within service windows and "
        "promptly notify dispatch of any inability to perform.~~NL~~"
        "3. TERMINATION FOR CAUSE. Jaffle Logistics may deactivate the contractor for repeated "
        "failure to perform or failure to notify, including no-call/no-show events.~~NL~~"
        "4. DISPUTE. Disputes shall first be raised with People Ops and Legal before external remedies."
    ) % (driver_id, date)
    return (doc_id, "", driver_id, date, "driver_agreement", body)


NEW_DOCS.append(driver_agreement("LGL-4024", "DRV-01001", "2020-06-02"))
NEW_DOCS.append(driver_agreement("LGL-4025", "DRV-01005", "2023-01-19"))


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


def main():
    rng = random.Random(SEED)  # kept for parity with the other generators
    assert {r[4] for r in NEW_DOCS} <= {"MSA", "SLA_addendum", "driver_agreement"}
    assert len(NEW_CONTRACTS) == len({r[0] for r in NEW_CONTRACTS})
    assert len(NEW_DOCS) == len({r[0] for r in NEW_DOCS})

    n_docs = append_rows("legal_docs", NEW_DOCS)
    n_con = append_rows("contracts", [
        [cid, client, date, sla, CREDIT_TERMS] for cid, client, date, sla in NEW_CONTRACTS
    ])
    print("legal_docs: +%d rows (was %d bytes)  contracts: +%d rows"
          % (len(NEW_DOCS), n_docs, len(NEW_CONTRACTS)))
    _ = rng  # deterministic; author list is fixed for reproducibility


if __name__ == "__main__":
    main()
