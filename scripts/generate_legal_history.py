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

Texture is the European network's: each MSA names both parties with VAT id and postcode
and carries a CMR / EU cabotage documentation clause; contractor driver agreements bind the
driver to EC 561/2006 driving-time limits (tachograph), ADR and CMR, and record the
contractor's VAT id.

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
    "CLI-0007": ("Jaffle Warenhuis", "last-mile",   "Noord-Holland"),
    "CLI-0042": ("Jaffle Werke",     "LTL",         "Île-de-France"),
    "CLI-0155": ("Jaffle Maison",    "last-mile",   "Berlin"),
    "CLI-0169": ("Jaffle Getränke",  "warehousing", "Noord-Holland"),
    "CLI-0201": ("Jaffle Papier",    "LTL",         "Wien"),
}

# Contracting parties: VAT id and registered city + postcode.
CARRIER_PARTY = "Jaffle Logistics (VAT NL859312746B01), Amsterdam 1234 AB"
CLIENT_PARTY = {
    "CLI-0007": ("NL587509310B01", "Amsterdam 1234 AB"),
    "CLI-0042": ("FR82231150582", "Paris 75001"),
    "CLI-0155": ("DE867590058", "Berlin 10115"),
    "CLI-0169": ("NL506678284B01", "Amsterdam 1234 AB"),
    "CLI-0201": ("ATU84505343", "Wien 1010"),
}

# Contractor drivers' VAT ids (as on their onboarding records in seeds/hr_docs.csv).
CONTRACTOR_VAT = {"DRV-01001": "NL100813255B01", "DRV-01005": "FR82897691482"}

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
    vat, place = CLIENT_PARTY[client_id]
    body = (
        "MASTER SERVICES AGREEMENT \u2014 Jaffle Logistics and %s (%s).~~NL~~"
        "Effective %s. Parties: %s; %s (VAT %s), %s.~~NL~~"
        "Referenced contract: %s.~~NL~~"
        "1. SERVICES. Jaffle Logistics shall provide %s logistics services in the "
        "%s region.~~NL~~"
        "2. SERVICE LEVELS. Target on-time delivery of %s%% measured monthly.~~NL~~"
        "3. CREDITS. %s~~NL~~"
        "4. TERM. Initial term of twenty-four (24) months, auto-renewing for "
        "successive twelve (12) month terms.~~NL~~"
        "5. DOCUMENTATION. Every consignment travels under a CMR consignment note; domestic "
        "legs performed outside the Netherlands observe EU cabotage limits.~~NL~~"
        "Prepared by %s (Legal)."
    ) % (name, client_id, date, CARRIER_PARTY, name, vat, place, contract_id, lob, region, sla,
         CREDIT_TERMS, author)
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
    "SLA ADDENDUM to CON-0155-00 \u2014 Jaffle Maison (CLI-0155). Effective 2022-11-08.~~NL~~"
    "The parties agree to clarify that on-time delivery is measured against the contracted "
    "service window using the hub scan-out timestamp as the origin event. All other terms of "
    "the Master Services Agreement remain in effect. Credit mechanics per the MSA are unchanged."
))
NEW_DOCS.append((
    "LGL-4020", "CLI-0169", "", "2023-04-11", "SLA_addendum",
    "SIDE LETTER \u2014 Jaffle Getränke (CLI-0169), contract CON-0169-00. Effective 2023-04-11.~~NL~~"
    "The parties acknowledge a one-time carry-over of an unused service credit from the prior "
    "measurement period, to be applied against the next qualifying shortfall. This letter is "
    "administrative only and does not amend the Master Services Agreement."
))
NEW_DOCS.append((
    "LGL-4021", "CLI-0042", "", "2024-01-30", "SLA_addendum",
    "SLA ADDENDUM to CON-0042-01 \u2014 Jaffle Werke (CLI-0042). Effective 2024-01-30.~~NL~~"
    "The parties agree that, for shipments tendered during the peak-season window (November 15 "
    "to December 24), the on-time measurement window is extended by one (1) business day. All "
    "other terms of the Master Services Agreement remain in effect. Credit mechanics per the MSA "
    "are unchanged."
))
NEW_DOCS.append((
    "LGL-4022", "CLI-0007", "", "2024-03-15", "SLA_addendum",
    "SLA ADDENDUM to CON-0007-01 \u2014 Jaffle Warenhuis (CLI-0007). Effective 2024-03-15.~~NL~~"
    "The parties confirm the renewal of CON-0007-01 for a further twelve (12) month term and "
    "restate the target on-time delivery of 97.0% measured monthly. No other terms of the Master "
    "Services Agreement are modified."
))
NEW_DOCS.append((
    "LGL-4023", "CLI-0201", "", "2024-11-05", "SLA_addendum",
    "SLA ADDENDUM to CON-0201-01 \u2014 Jaffle Papier (CLI-0201). Effective 2024-11-05.~~NL~~"
    "The parties agree to adjust the on-time measurement window to exclude documented force-majeure "
    "weather events at the origin hub. All other terms of the Master Services Agreement remain in "
    "effect. Credit mechanics per the MSA are unchanged."
))


def driver_agreement(doc_id, driver_id, date):
    body = (
        "INDEPENDENT CONTRACTOR DRIVER AGREEMENT \u2014 %s. Effective %s.~~NL~~"
        "1. RELATIONSHIP. Contractor operates as an independent contractor, not an employee.~~NL~~"
        "2. PERFORMANCE. Contractor shall complete assigned routes within service windows and "
        "within the driving-time and rest limits of Regulation (EC) No 561/2006 as recorded by "
        "the tachograph, and promptly notify dispatch of any inability to perform.~~NL~~"
        "2a. COMPLIANCE. Contractor shall carry a valid ADR certificate before accepting any "
        "dangerous-goods consignment, and shall hand over a signed CMR consignment note at every "
        "delivery. Contractor VAT id: %s.~~NL~~"
        "3. TERMINATION FOR CAUSE. Jaffle Logistics may deactivate the contractor for repeated "
        "failure to perform or failure to notify, including no-call/no-show events.~~NL~~"
        "4. DISPUTE. Disputes shall first be raised with People Ops and Legal before external remedies."
    ) % (driver_id, date, CONTRACTOR_VAT[driver_id])
    return (doc_id, "", driver_id, date, "driver_agreement", body)


NEW_DOCS.append(driver_agreement("LGL-4024", "DRV-01001", "2020-06-02"))
NEW_DOCS.append(driver_agreement("LGL-4025", "DRV-01005", "2023-01-19"))


def build_block(rows):
    """Serialize csv rows (CRLF, matching the existing files) without writing."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode()


def block_present(name, rows, block):
    """True if the block is already the file's tail, byte for byte; False if none of its
    ids are on file yet. Any other collision with an existing id is an error."""
    with open(os.path.join(SEEDS, name + ".csv"), newline="") as fh:
        existing_ids = {r[0] for r in csv.reader(fh)}
    if not any(r[0] in existing_ids for r in rows):
        return False
    with open(os.path.join(SEEDS, name + ".csv"), "rb") as fh:
        if fh.read().endswith(block):
            return True
    raise RuntimeError("%s.csv already holds %s.. but not this block; refusing to append"
                       % (name, rows[0][0]))


def append_block(name, block):
    """Append the block after the existing bytes; returns the file's prior size."""
    path = os.path.join(SEEDS, name + ".csv")
    n = os.path.getsize(path)
    with open(path, "ab") as fh:
        fh.write(block)
    return n


def main():
    rng = random.Random(SEED)  # kept for parity with the other generators
    assert {r[4] for r in NEW_DOCS} <= {"MSA", "SLA_addendum", "driver_agreement"}
    assert len(NEW_CONTRACTS) == len({r[0] for r in NEW_CONTRACTS})
    assert len(NEW_DOCS) == len({r[0] for r in NEW_DOCS})

    con_rows = [[cid, client, date, sla, CREDIT_TERMS] for cid, client, date, sla in NEW_CONTRACTS]
    docs_block = build_block(NEW_DOCS)
    con_block = build_block(con_rows)
    present = [block_present("legal_docs", NEW_DOCS, docs_block),
               block_present("contracts", con_rows, con_block)]
    if all(present):
        print("already present: each block is its file's tail, byte for byte; nothing written")
        return
    if any(present):
        raise RuntimeError("only one of legal_docs.csv / contracts.csv holds its block; "
                           "refusing to append")

    n_docs = append_block("legal_docs", docs_block)
    n_con = append_block("contracts", con_block)
    print("legal_docs: +%d rows (was %d bytes)  contracts: +%d rows"
          % (len(NEW_DOCS), n_docs, len(NEW_CONTRACTS)))
    _ = rng  # deterministic; author list is fixed for reproducibility


if __name__ == "__main__":
    main()
