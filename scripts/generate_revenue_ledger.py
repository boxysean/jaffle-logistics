#!/usr/bin/env python3
"""Deterministically generate seeds/revenue_ledger.csv: the revenue and cost ledger,
one row per account x month, 2020-01 through 2025-12 (5 accounts x 72 months).

Pure arithmetic, no randomness: the same input seeds always give byte-identical output.
Reads seeds/clients.csv, seeds/shipments.csv and seeds/contracts.csv (all read-only).

Revenue model:
  * 2023-01 onward (the shipment record exists): derived from that month's shipments
    for the client (created_at month).
      base         = sum of rate(service_level) x client contract factor
      accessorials = $85 per expedited shipment
                   + $75 per liftgate/waiting-time shipment (every 5th shipment of the
                     month, in shipment_id order, for that client)
                   + $140 per failed or returned shipment
      invoices     = distinct ISO weeks with >= 1 shipment (weekly consolidated billing)
  * 2020-01 .. 2022-12 (no shipment record): imputed from the client's 2023 same-month
    volume x a growth factor, at the client's 2023 average base per shipment x a price
    factor, with accessorials at the client's 2023 accessorial-to-base ratio. Invoices =
    Mondays in the month (4 or 5). No credits; no on-time measurement.

Credits (the point of the dataset): the contract's credit_terms ("X% of monthly spend
per full percentage point below the SLA on-time target, capped at Y%") are assessed on
the TRAILING-12-MONTH on-time rate ending on the billing month. A month is assessed
only once 12 months of shipment record exist (2024-01 onward). Only full points count.
credited_amount is positive and subtracted in net_revenue.

SLA in force: the contract in seeds/contracts.csv with the latest effective_date month
on or before the billing month. Before an account's earliest recorded contract, the
account was on a predecessor agreement the register does not record; the earliest
recorded contract's SLA is applied backwards as the predecessor term.

Run from the repo root:  python3 scripts/generate_revenue_ledger.py
"""
import collections
import csv
import datetime
import math
import os
import re
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")
OUT = os.path.join(SEEDS, "revenue_ledger.csv")

START = datetime.date(2020, 1, 1)
END = datetime.date(2025, 12, 1)
RECORD_START = datetime.date(2023, 1, 1)   # first month of the shipment record
ASSESS_START = datetime.date(2024, 1, 1)   # first month with a full trailing-12m window

BASE_RATE = {"standard": Decimal("950"), "expedited": Decimal("1450"), "freight": Decimal("2300")}
CONTRACT_FACTOR = {
    "CLI-0007": Decimal("0.95"),
    "CLI-0042": Decimal("1.00"),
    "CLI-0155": Decimal("1.02"),
    "CLI-0169": Decimal("1.05"),
    "CLI-0201": Decimal("1.10"),
}
EXPEDITED_PREMIUM = Decimal("85")
LIFTGATE_WAITING_FEE = Decimal("75")
LIFTGATE_EVERY_NTH = 5
EXCEPTION_FEE = Decimal("140")   # redelivery / return handling on failed or returned

# Pre-record imputation, keyed by year.
GROWTH_FACTOR = {2020: Decimal("0.88"), 2021: Decimal("0.92"), 2022: Decimal("0.96")}
PRICE_FACTOR = {2020: Decimal("0.94"), 2021: Decimal("0.96"), 2022: Decimal("0.98")}

# Fallbacks only if credit_terms ever stops parsing; asserted below that it does parse.
DEFAULT_CREDIT_RATE_PCT = Decimal("1.0")
DEFAULT_CREDIT_CAP_PCT = Decimal("10.0")
RATE_RE = re.compile(r"([\d.]+)% of monthly spend credited per full percentage point")
CAP_RE = re.compile(r"capped at ([\d.]+)% of monthly spend")

CENT = Decimal("0.01")
TENTH = Decimal("0.1")

COLUMNS = [
    "revenue_month", "client_id", "contracted_base_revenue", "accessorial_revenue",
    "credited_amount", "net_revenue", "invoice_count", "shipment_count", "ontime_pct",
    "trailing_12m_ontime_pct", "sla_ontime_pct", "measurement_basis",
]


def money(x):
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


def pct1(num, den):
    return (Decimal(100) * num / den).quantize(TENTH, rounding=ROUND_HALF_UP)


def months(start, end):
    d = start
    while d <= end:
        yield d
        d = datetime.date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def add_months(d, n):
    k = d.year * 12 + d.month - 1 + n
    return datetime.date(k // 12, k % 12 + 1, 1)


def mondays_in(month):
    nxt = add_months(month, 1)
    return sum(1 for i in range((nxt - month).days)
               if (month + datetime.timedelta(days=i)).weekday() == 0)


def read(name):
    with open(os.path.join(SEEDS, name), newline="") as f:
        return list(csv.DictReader(f))


def parse_terms(text):
    rate, cap = RATE_RE.search(text), CAP_RE.search(text)
    parsed = bool(rate and cap)
    return (Decimal(rate.group(1)) if rate else DEFAULT_CREDIT_RATE_PCT,
            Decimal(cap.group(1)) if cap else DEFAULT_CREDIT_CAP_PCT,
            parsed)


def main():
    clients = sorted(r["client_id"] for r in read("clients.csv"))
    assert set(clients) == set(CONTRACT_FACTOR), clients

    # Contracts per client, sorted by effective month (tie-broken by contract_id).
    contracts = collections.defaultdict(list)
    for r in read("contracts.csv"):
        eff = datetime.date.fromisoformat(r["effective_date"])
        rate_pct, cap_pct, parsed = parse_terms(r["credit_terms"])
        assert parsed, f"credit_terms did not parse for {r['contract_id']}: {r['credit_terms']!r}"
        contracts[r["client_id"]].append({
            "contract_id": r["contract_id"],
            "effective_month": eff.replace(day=1),
            "sla": Decimal(r["sla_ontime_pct"]).quantize(TENTH),
            "rate_pct": rate_pct,
            "cap_pct": cap_pct,
        })
    for cid in clients:
        assert contracts[cid], f"no contract for {cid}"
        contracts[cid].sort(key=lambda c: (c["effective_month"], c["contract_id"]))

    def contract_in_force(cid, month):
        in_force = [c for c in contracts[cid] if c["effective_month"] <= month]
        # Before the earliest recorded contract: predecessor term = earliest recorded.
        return in_force[-1] if in_force else contracts[cid][0]

    # Shipments bucketed by (client, month), in shipment_id order.
    by_cm = collections.defaultdict(list)
    for r in read("shipments.csv"):
        created = datetime.datetime.fromisoformat(r["created_at"])
        by_cm[(r["client_id"], created.date().replace(day=1))].append(
            (r["shipment_id"], r["service_level"], r["status"], created.date()))
    for v in by_cm.values():
        v.sort()
    assert max(m for _, m in by_cm) <= END, "shipment record runs past the ledger window"
    assert min(m for _, m in by_cm) == RECORD_START

    def observed(cid, month):
        ships = by_cm.get((cid, month), [])
        factor = CONTRACT_FACTOR[cid]
        base = sum((BASE_RATE[s[1]] * factor for s in ships), Decimal(0))
        acc = Decimal(0)
        for i, (_, level, status, _) in enumerate(ships, start=1):
            if level == "expedited":
                acc += EXPEDITED_PREMIUM
            if i % LIFTGATE_EVERY_NTH == 0:
                acc += LIFTGATE_WAITING_FEE
            if status in ("failed", "returned"):
                acc += EXCEPTION_FEE
        delivered = sum(1 for s in ships if s[2] == "delivered")
        weeks = {s[3].isocalendar()[:2] for s in ships}
        return {"base": money(base), "acc": money(acc), "n": len(ships),
                "delivered": delivered, "invoices": len(weeks)}

    # 2023 per-client baselines for the imputation.
    obs = {(cid, m): observed(cid, m) for cid in clients for m in months(RECORD_START, END)}
    baseline = {}
    for cid in clients:
        y23 = [obs[(cid, m)] for m in months(RECORD_START, datetime.date(2023, 12, 1))]
        n23 = sum(o["n"] for o in y23)
        base23 = sum(o["base"] for o in y23)
        acc23 = sum(o["acc"] for o in y23)
        baseline[cid] = {"base_per_shipment": base23 / n23, "acc_ratio": acc23 / base23}

    rows = []
    for cid in clients:
        for month in months(START, END):
            con = contract_in_force(cid, month)
            row = {"revenue_month": month, "client_id": cid, "sla_ontime_pct": con["sla"]}
            if month < RECORD_START:
                same_2023 = obs[(cid, month.replace(year=2023))]
                volume = (same_2023["n"] * GROWTH_FACTOR[month.year]).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP)
                base = money(volume * baseline[cid]["base_per_shipment"] * PRICE_FACTOR[month.year])
                row.update(
                    contracted_base_revenue=base,
                    accessorial_revenue=money(base * baseline[cid]["acc_ratio"]),
                    credited_amount=money(0),
                    invoice_count=mondays_in(month),
                    shipment_count=None, ontime_pct=None, trailing_12m_ontime_pct=None,
                    measurement_basis="no_shipment_record",
                )
            else:
                o = obs[(cid, month)]
                assert o["n"] > 0, f"no shipments for {cid} {month}"
                # Assessed from 2024-01: the first billing year with a full trailing window
                # behind every month. All of 2023 stays partial_history.
                window = [obs[(cid, add_months(month, -k))] for k in range(12)] \
                    if month >= ASSESS_START else None
                t12 = pct1(sum(w["delivered"] for w in window), sum(w["n"] for w in window)) \
                    if window else None
                gross = o["base"] + o["acc"]
                credit = money(0)
                if t12 is not None:
                    shortfall = con["sla"] - t12
                    if shortfall >= 1:
                        credit = money(min(math.floor(shortfall) * con["rate_pct"] / 100 * gross,
                                           con["cap_pct"] / 100 * gross))
                row.update(
                    contracted_base_revenue=o["base"],
                    accessorial_revenue=o["acc"],
                    credited_amount=credit,
                    invoice_count=o["invoices"],
                    shipment_count=o["n"],
                    ontime_pct=pct1(o["delivered"], o["n"]),
                    trailing_12m_ontime_pct=t12,
                    measurement_basis="trailing_12m" if t12 is not None else "partial_history",
                )
            row["net_revenue"] = (row["contracted_base_revenue"] + row["accessorial_revenue"]
                                  - row["credited_amount"])
            rows.append(row)

    rows.sort(key=lambda r: (r["client_id"], r["revenue_month"]))

    # ---- story constraints --------------------------------------------------------
    assert len(rows) == len(clients) * 72 == 360
    # 1. no credits before 2024-01 (nothing assessable without a full window)
    assert all(r["credited_amount"] == 0 for r in rows if r["revenue_month"] < ASSESS_START)
    # 2. healthy accounts: a 2025 credit only where the trailing window genuinely misses
    healthy = [c for c in clients if c != "CLI-0042"]
    for r in rows:
        if r["client_id"] in healthy and r["revenue_month"].year == 2025 and r["credited_amount"] > 0:
            assert r["sla_ontime_pct"] - r["trailing_12m_ontime_pct"] >= 1
    # 3. CLI-0042 credits material in 2025, peaking in Q4
    c42 = {r["revenue_month"]: r["credited_amount"] for r in rows
           if r["client_id"] == "CLI-0042" and r["revenue_month"].year == 2025}
    assert sum(c42.values()) > 0, "CLI-0042 carries no 2025 credits"
    peak = max(c42.values())
    assert any(c42[m] == peak for m in c42 if m.month >= 10), "CLI-0042 credits do not peak in Q4"
    # 4. healthy-book gross revenue grows year over year 2023 -> 2025. Reported, not
    # asserted: revenue is derived from the ops record. Healthy-book volume grows
    # 2023 -> 2025 (scripts/generate_volume_variation.py), but in 2025 only CLI-0007 and
    # CLI-0169 ship any freight, and only ~8% of their book, against roughly a fifth of
    # every account's book in 2023-24. At the rate card the thinner freight mix can
    # outweigh the volume growth; the ledger shows it rather than smoothing it away.
    healthy_gross = collections.Counter()
    for r in rows:
        if r["client_id"] in healthy:
            healthy_gross[r["revenue_month"].year] += r["contracted_base_revenue"] + r["accessorial_revenue"]
    healthy_grows = healthy_gross[2023] < healthy_gross[2024] < healthy_gross[2025]
    # 5. nothing after 2025-12-01
    assert max(r["revenue_month"] for r in rows) == END
    # 6. signed-credit convention and exact reconciliation
    for r in rows:
        assert r["credited_amount"] >= 0
        assert r["net_revenue"] == r["contracted_base_revenue"] + r["accessorial_revenue"] - r["credited_amount"]

    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, datetime.date):
            return v.isoformat()
        return str(v)

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([fmt(r[c]) for c in COLUMNS])

    # ---- review trail -------------------------------------------------------------
    print(f"wrote {os.path.relpath(OUT)}: {len(rows)} rows")
    print(f"revenue_month range: {rows[0]['revenue_month']} .. {max(r['revenue_month'] for r in rows)}")
    print("\n2025 credits by client:")
    total_2025 = Decimal(0)
    for cid in clients:
        amt = sum(r["credited_amount"] for r in rows
                  if r["client_id"] == cid and r["revenue_month"].year == 2025)
        months_credited = [r["revenue_month"].strftime("%b") for r in rows
                           if r["client_id"] == cid and r["revenue_month"].year == 2025
                           and r["credited_amount"] > 0]
        total_2025 += amt
        print(f"  {cid}  ${amt:>12,.2f}  months credited: {', '.join(months_credited) or 'none'}")
    print(f"  total     ${total_2025:>12,.2f}")
    print("\nCLI-0042 2025 by month (trailing-12m vs SLA -> credit):")
    for r in rows:
        if r["client_id"] == "CLI-0042" and r["revenue_month"].year == 2025:
            gross = r["contracted_base_revenue"] + r["accessorial_revenue"]
            print(f"  {r['revenue_month']}  t12m {r['trailing_12m_ontime_pct']:>5}  "
                  f"SLA {r['sla_ontime_pct']}  gross ${gross:>11,.2f}  credit ${r['credited_amount']:>10,.2f}")
    print(f"  CLI-0042 2025 total credits: ${sum(c42.values()):,.2f}")
    print("\nwhole-book revenue by year (gross / credits / net):")
    for year in range(START.year, END.year + 1):
        yr = [r for r in rows if r["revenue_month"].year == year]
        gross = sum(r["contracted_base_revenue"] + r["accessorial_revenue"] for r in yr)
        cred = sum(r["credited_amount"] for r in yr)
        net = sum(r["net_revenue"] for r in yr)
        print(f"  {year}  ${gross:>14,.2f}  ${cred:>11,.2f}  ${net:>14,.2f}")
    print("\nhealthy-book (excl. CLI-0042) gross by year:")
    for year in (2023, 2024, 2025):
        n = sum(r["shipment_count"] for r in rows
                if r["client_id"] in healthy and r["revenue_month"].year == year)
        print(f"  {year}  ${healthy_gross[year]:>14,.2f}  ({n} shipments)")
    if not healthy_grows:
        print("  CHECK NOT MET (constraint 4): healthy-book revenue does not grow 2023 -> 2025."
              " Volume grows, but these accounts' 2025 freight mix is far thinner than in 2023-24"
              " (freight only on CLI-0007 and CLI-0169, ~8% of their book).")
    print("\nmax trailing-12m shortfall (SLA - t12m, pts) by year:")
    for year in (2023, 2024, 2025):
        assessed = [r for r in rows if r["revenue_month"].year == year
                    and r["trailing_12m_ontime_pct"] is not None]
        if not assessed:
            print(f"  {year}  n/a (no full trailing-12m window)")
            continue
        worst = max(assessed, key=lambda r: r["sla_ontime_pct"] - r["trailing_12m_ontime_pct"])
        gap = worst["sla_ontime_pct"] - worst["trailing_12m_ontime_pct"]
        print(f"  {year}  {gap:+.1f}  ({worst['client_id']} {worst['revenue_month']})")
    # 2023 has no full window; 2024 must stay under one full point.
    y24 = [r["sla_ontime_pct"] - r["trailing_12m_ontime_pct"] for r in rows
           if r["revenue_month"].year == 2024]
    assert max(y24) < 1, "a 2024 trailing-12m window misses SLA by a full point"
    # 2023 partial-history windows (months so far), for the record only: never credited.
    worst23 = Decimal(-100)
    for cid in clients:
        for m in months(RECORD_START, datetime.date(2023, 12, 1)):
            ws = [obs[(cid, x)] for x in months(RECORD_START, m)]
            gap = contract_in_force(cid, m)["sla"] - pct1(sum(w["delivered"] for w in ws),
                                                         sum(w["n"] for w in ws))
            worst23 = max(worst23, gap)
    print(f"  2023 (partial-history, year-to-date windows): max shortfall {worst23:+.1f}")
    assert worst23 < 1, "a 2023 partial window misses SLA by a full point"


if __name__ == "__main__":
    main()
