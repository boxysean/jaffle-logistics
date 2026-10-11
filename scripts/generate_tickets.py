#!/usr/bin/env python3
"""Deterministically extend the Jaffle Logistics support history backwards in
time, adding the quiet years 2023 and 2024 to seeds/support_tickets.csv and the
matching ground-truth labels to seeds/eval_ticket_triage.csv.

APPEND ONLY: existing bytes are read and re-written untouched; new rows are
appended after them. New ticket ids are pinned to TKT-200300 upward (they
continued the plain TKT-2NNNNN sequence after TKT-200299 when first written),
and every foreign key points at a row that exists (the client / shipment chosen
for the ticket).

Story the numbers tell:
  * 2023 and 2024 are the ordinary, healthy years: a late load, a POD request,
    an accessorial/contact question, the occasional missed delivery -- resolved
    without a systemic pattern.
  * No storm flood, no recurring Amsterdam (HUB-AMS) handling-damage cluster and
    no Jaffle Werke (CLI-0042) escalation trend: those belong to 2025 and
    are untouched here. New tickets simply continue the ordinary TKT-200xxx mix.

Every new ticket carries exactly one ground-truth label row (category +
sentiment) whose values come from the existing vocabulary and match the body.

Later revisions this script replays so a re-run reproduces the same rows:
  * scripts/generate_volume_variation.py later dropped unreferenced 2023-2024
    shipments. The shipment draws index into per-month pools, so the dropped rows
    are put back in their slots as placeholders that can never be drawn. Before
    that revision each 2023-2024 month ran SHP-YYYYMM-000001 ..
    ORIGINAL_MONTH_ROWS[month] in order, so a gap in the id sequence is a dropped
    row; all were delivered except DROPPED_STATUS.
  * scripts/generate_ticket_timestamps.py later added the response clock columns
    to every ticket. When the file has them, the new rows get the same clock that
    script gives them (its seeded stream run over the existing rows, then these).
"""
import csv, io, os, sys, random, datetime, collections

SEED = 20231002
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

FIRST_TICKET = 200300      # pinned: the block's ids run TKT-200300 upward

HUB_CITY = {"HUB-AMS": "Amsterdam", "HUB-PAR": "Paris", "HUB-BER": "Berlin",
            "HUB-VIE": "Vienna", "HUB-ZRH": "Zürich"}

# Pre-revision 2023-2024 shipments (see docstring). 2023 and 2024 had the same
# monthly row counts.
_MONTH_ROWS = (183, 143, 160, 145, 151, 139, 171, 162, 159, 169, 203, 224)
ORIGINAL_MONTH_ROWS = {(year, month): n
                       for year in (2023, 2024) for month, n in enumerate(_MONTH_ROWS, 1)}
DROPPED_STATUS = {"SHP-202306-000062": "delayed", "SHP-202306-000087": "delayed",
                  "SHP-202306-000118": "delayed", "SHP-202310-000147": "delayed",
                  "SHP-202403-000160": "delayed", "SHP-202412-000221": "returned"}
AGENTS = ["agent.mruiz", "agent.dfoster", "agent.tpatel",
          "agent.jbrooks", "agent.lchen", "agent.kobrien"]

CHANNELS = ["email", "phone", "chat", "portal"]
CHANNEL_W = [31, 31, 22, 16]
# Tickets per month: a touch below 2025's ordinary volume (the quiet years).
MONTH_TK = {1: 9, 2: 8, 3: 9, 4: 8, 5: 9, 6: 8,
            7: 9, 8: 9, 9: 8, 10: 9, 11: 10, 12: 11}      # 107 per year


def load(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="") as fh:
        return list(csv.DictReader(fh))


def build_block(rows):
    """Serialize csv rows (CRLF, matching the existing files) without writing."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerows(rows)
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
    with open(os.path.join(SEEDS, name + ".csv"), "ab") as fh:
        fh.write(block)


def weighted_choice(rng, items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


# --------------------------------------------------------------- body building
# Customer openers. Each maps to (category, sentiment) -- the body and the
# label are generated together so the eval set can never disagree with itself.
OPENERS = {
    "pod":        ("general_inquiry", "positive"),
    "window":     ("general_inquiry", "positive"),
    "ontrack":    ("general_inquiry", "positive"),
    "contact":    ("general_inquiry", "positive"),
    "eta_delayed":     ("delivery_delay", "neutral"),
    "eta_failed":      ("delivery_failed", "neutral"),
    "req_delayed":     ("delivery_delay", "neutral"),
    "req_failed":      ("delivery_failed", "neutral"),
    "followup_week":   ("delivery_delay", "neutral"),
    "polite_delay":    ("delivery_delay", "positive"),
    "morning_delayed": ("delivery_delay", "positive"),
    "morning_failed":  ("delivery_failed", "positive"),
    "second_time":     ("delivery_failed", "negative"),
    "disappointed_delayed":  ("delivery_delay", "negative"),
    "disappointed_returned": ("delivery_failed", "negative"),
    "where_is":        ("delivery_failed", "negative"),
    "wrong_item":      ("wrong_item", "negative"),
}

POSITIVE_CLOSERS = ["Perfect, thank you!", "Great, appreciate it.",
                    "Thanks for the quick help.", "Appreciate the quick turnaround."]


def opener_text(kind, sid):
    return {
        "pod": "[customer] Following up on %s — could you send the POD once it's delivered? Accounting needs it." % sid,
        "window": "[customer] Hi — quick question on %s. Can you confirm the delivery window?" % sid,
        "ontrack": "[customer] Can you confirm %s is still on track to arrive this week?" % sid,
        "contact": "[customer] Hello, I need to update the delivery contact for %s if it hasn't gone out yet." % sid,
        "eta_delayed": "[customer] Hi, I'm checking on shipment %s. The status shows delayed — can you tell me the latest ETA?" % sid,
        "eta_failed": "[customer] Hi, I'm checking on shipment %s. The status shows failed — can you tell me the latest ETA?" % sid,
        "req_delayed": "[customer] Requesting an update on %s. It appears to be delayed." % sid,
        "req_failed": "[customer] Requesting an update on %s. It appears to be failed." % sid,
        "followup_week": "[customer] Following up on %s. Could you confirm whether this will still be delivered this week?" % sid,
        "polite_delay": "[customer] Hello, hoping you can help with %s. I understand there may be delays — just need an updated delivery window when you have a moment. Thanks!" % sid,
        "morning_delayed": "[customer] Good morning! Quick question on %s, currently delayed. No rush, just planning around it." % sid,
        "morning_failed": "[customer] Good morning! Quick question on %s, currently failed. No rush, just planning around it." % sid,
        "second_time": "[customer] This is the second time I'm reaching out about %s. It was due days ago and I still have nothing. This is unacceptable for the rates we pay." % sid,
        "disappointed_delayed": "[customer] Extremely disappointed. %s was marked delayed with zero communication. Please escalate." % sid,
        "disappointed_returned": "[customer] Extremely disappointed. %s was marked returned with zero communication. Please escalate." % sid,
        "where_is": "[customer] Where is %s?? Your tracking hasn't updated and my customer is furious. I need answers today." % sid,
        "wrong_item": "[customer] We received the WRONG items for %s. This isn't what we ordered at all — looks like it was meant for someone else." % sid,
    }[kind]


def reply_locate(agent, sid, hub):
    return "[%s] Thank you for your patience. I've located %s in our system (origin %s). Checking with dispatch now." % (agent, sid, hub)


def reply_dispatch(agent, sid):
    return "[%s] Dispatch confirms %s will be reattempted next business day. I've flagged your account for a proactive follow-up." % (agent, sid)


def reply_exception(agent, sid, city):
    return "[%s] Thanks for reaching out — I'm sorry for the trouble with %s. I see it was affected by an exception at our %s hub. Let me pull the latest." % (agent, sid, city)


def reply_rerouted(agent, sid):
    return "[%s] Update: %s is re-routed and expected to deliver within 48 hours. I've added a note to prioritize it. Anything else I can do?" % (agent, sid)


def reply_backinmotion(agent, sid):
    return "[%s] Good news — %s is back in motion. I'll monitor it through delivery and confirm the POD with you." % (agent, sid)


def reply_investigation(agent, sid, city):
    return "[%s] Apologies for the delay on %s. I've opened an investigation and looped in the %s operations team." % (agent, sid, city)


def reply_onschedule(agent, sid, city):
    return "[%s] Happy to help — %s is on schedule out of our %s hub; delivery is within the next 1–2 business days." % (agent, sid, city)


def reply_pod(agent, sid):
    return "[%s] Attached the POD for %s. Let me know if there's anything else!" % (agent, sid)


def reply_noted(agent, sid, city):
    return "[%s] Sure thing. I've noted the update on %s and confirmed it with the %s team." % (agent, sid, city)


def reply_mispick(agent, city):
    return "[%s] Apologies — we've identified a fulfillment error at our %s warehouse and will arrange pickup of the wrong items and expedite the correct ones." % (agent, city)


def build_body(rng, kind, sid, hub, agent):
    city = HUB_CITY[hub]
    parts = [opener_text(kind, sid)]
    cat, sent = OPENERS[kind]
    if cat == "general_inquiry":
        parts.append(weighted_choice(rng, [
            reply_pod(agent, sid),
            reply_onschedule(agent, sid, city),
            reply_noted(agent, sid, city),
        ], [3, 3, 2]))
        parts.append("[customer] " + rng.choice(POSITIVE_CLOSERS))
    elif cat == "wrong_item":
        parts.append(reply_mispick(agent, city))
        parts.append("[customer] Thank you, please hurry.")
    else:
        first = weighted_choice(rng, [
            reply_exception(agent, sid, city),
            reply_locate(agent, sid, hub),
        ], [1, 1])
        parts.append(first)
        if rng.random() < 0.80:                      # most get a second agent line
            second = weighted_choice(rng, [
                reply_rerouted(agent, sid),
                reply_backinmotion(agent, sid),
                reply_dispatch(agent, sid),
                reply_investigation(agent, sid, city),
            ], [3, 3, 2, 2])
            parts.append(second)
        # optional customer closer
        r = rng.random()
        if r < 0.45 and sent == "positive":
            parts.append("[customer] " + rng.choice(POSITIVE_CLOSERS))
        elif sent == "neutral" and r < 0.55:
            parts.append("[customer] Okay, thank you. Please keep me posted.")
        elif sent == "negative" and r < 0.65:
            parts.append("[customer] That still isn't good enough but I'll wait for the update.")
    return "~~NL~~".join(parts), cat, sent


def choose_kind(rng, ship_status, cat):
    if cat == "general_inquiry":
        pool = ["pod", "window", "ontrack", "contact"]
        if ship_status == "delivered":
            return weighted_choice(rng, pool, [3, 4, 3, 2])
        return weighted_choice(rng, pool, [2, 3, 3, 2])
    if cat == "delivery_delay":
        return weighted_choice(rng, [
            "eta_delayed", "req_delayed", "followup_week", "polite_delay",
            "morning_delayed", "second_time", "disappointed_delayed",
        ], [4, 3, 3, 3, 2, 2, 1])
    if cat == "delivery_failed":
        pool = ["eta_failed", "req_failed", "where_is", "morning_failed",
                "second_time", "disappointed_returned"]
        w = [3, 3, 3, 2, 2, 2]
        if ship_status == "returned":
            pool.append("disappointed_returned")
            w.append(3)
        return weighted_choice(rng, pool, w)
    return "wrong_item"


def pick_csat(rng, status, sentiment):
    if status == "open":
        return ""
    if status == "pending" and rng.random() < 0.30:
        return ""
    if sentiment == "positive":
        return str(weighted_choice(rng, [5, 4, 3], [5, 3, 1]))
    if sentiment == "neutral":
        return str(weighted_choice(rng, [4, 3, 2], [3, 3, 1]))
    return str(weighted_choice(rng, [1, 2, 3], [5, 3, 1]))


def with_response_clock(existing_tk, new_tickets):
    """The new rows plus the clock columns scripts/generate_ticket_timestamps.py gives
    them: its seeded stream, run over the existing rows in file order, then these."""
    sys.path.insert(0, HERE)
    import generate_ticket_timestamps as tt
    hubs = tt.load_hubs()
    rng = random.Random(tt.SEED)
    own_ids = {values[0] for values in new_tickets}   # skip this block's rows on a re-run
    for row in existing_tk:
        if row["ticket_id"] not in own_ids:
            tt.clock(rng, row, hubs.get(row["shipment_id"]))
    cols = ["ticket_id", "client_id", "shipment_id", "opened_at", "channel", "status",
            "csat", "body"]
    out = []
    for values in new_tickets:
        row = dict(zip(cols, values))
        opened, first, resolved = tt.clock(rng, row, hubs.get(row["shipment_id"]))
        out.append(values + [first.strftime(tt.FMT),
                             resolved.strftime(tt.FMT) if resolved else "",
                             tt.fmt_h(tt.hours(opened, first)),
                             tt.fmt_h(tt.hours(opened, resolved)) if resolved else ""])
    return out


def main():
    rng = random.Random(SEED)

    existing_tk = load("support_tickets")
    shipments = load("shipments")

    next_id = FIRST_TICKET

    # shipments grouped by (year, month) and by status class, with parsed dates.
    # Category is chosen first (mirroring the ordinary 2025 mix), then a shipment
    # whose status fits that category is picked -- so a "currently delayed" body
    # always points at a shipment that really was delayed.
    def sclass(st):
        return "delivered" if st == "delivered" else ("delayed" if st == "delayed" else "failed")

    # The 2023-2024 shipments as they stood when the tickets were drawn: the surviving
    # rows, with each dropped row back in its slot as a placeholder (created None).
    by_id = {s["shipment_id"]: s for s in shipments if s["created_at"][:4] in ("2023", "2024")}
    ships_by_ym = collections.defaultdict(list)
    pool_month = collections.defaultdict(list)
    pool_year = collections.defaultdict(list)
    for (y, m), n in sorted(ORIGINAL_MONTH_ROWS.items()):
        for seq in range(1, n + 1):
            sid = "SHP-%04d%02d-%06d" % (y, m, seq)
            s = by_id.pop(sid, None)
            if s is None:
                entry = (None, {"shipment_id": sid,
                                "status": DROPPED_STATUS.get(sid, "delivered")})
            else:
                assert (int(s["created_at"][:4]), int(s["created_at"][5:7])) == (y, m), sid
                entry = (datetime.datetime.strptime(s["created_at"], "%Y-%m-%dT%H:%M:%S"), s)
            cls = sclass(entry[1]["status"])
            ships_by_ym[(y, m)].append(entry)
            pool_month[(y, m, cls)].append(entry)
            pool_year[(y, cls)].append(entry)
    assert not by_id, sorted(by_id)[:5]

    CAT_CLASS = {"general_inquiry": "delivered", "wrong_item": "delivered",
                 "delivery_delay": "delayed", "delivery_failed": "failed"}
    CAT_W = [53, 30, 13, 4]

    new_tickets = []
    new_labels = []
    last_body = None

    LAG_W = [3, 4, 3, 2, 2, 1]        # 0..5 days between shipment creation and ticket

    for year in (2023, 2024):
        for month in range(1, 13):
            for _ in range(MONTH_TK[month]):
                cat = weighted_choice(
                    rng, ["general_inquiry", "delivery_delay", "delivery_failed", "wrong_item"], CAT_W)
                cls = CAT_CLASS[cat]
                pool = (pool_month.get((year, month, cls))
                        or pool_year.get((year, cls))
                        or ships_by_ym[(year, month)])
                created, ship = rng.choice(pool)
                assert created is not None, "drew a dropped shipment %s" % ship["shipment_id"]
                sid = ship["shipment_id"]
                client = ship["client_id"]
                hub = ship["origin_hub_id"]
                agent = rng.choice(AGENTS)
                # open the ticket a few days after the shipment was created, but
                # always inside the shipment's own month (its "period").
                opened = created + datetime.timedelta(
                    days=weighted_choice(rng, range(6), LAG_W),
                    hours=rng.randint(0, 6), minutes=rng.randint(0, 59))
                if (opened.year, opened.month) != (created.year, created.month):
                    opened = created + datetime.timedelta(hours=rng.randint(1, 6))

                kind = choose_kind(rng, ship["status"], cat)
                body, cat, sent = build_body(rng, kind, sid, hub, agent)
                while body == last_body:            # never two identical rows back to back
                    kind = choose_kind(rng, ship["status"], cat)
                    body, cat, sent = build_body(rng, kind, sid, hub, agent)
                last_body = body

                channel = weighted_choice(rng, CHANNELS, CHANNEL_W)
                status = weighted_choice(rng, ["resolved", "pending", "open"], [80, 11, 9])
                csat = pick_csat(rng, status, sent)

                tid = "TKT-%d" % next_id
                next_id += 1
                new_tickets.append([tid, client, sid, opened.strftime("%Y-%m-%dT%H:%M:%S"),
                                    channel, status, csat, body])
                new_labels.append([tid, cat, sent])

    with open(os.path.join(SEEDS, "support_tickets.csv"), newline="") as fh:
        header = next(csv.reader(fh))
    if "first_response_at" in header:
        new_tickets = with_response_clock(existing_tk, new_tickets)

    tk_block = build_block(new_tickets)
    lb_block = build_block(new_labels)
    present = [block_present("support_tickets", new_tickets, tk_block),
               block_present("eval_ticket_triage", new_labels, lb_block)]
    if all(present):
        print("already present: each block is its file's tail, byte for byte; nothing written")
        return
    if any(present):
        raise RuntimeError("only one of support_tickets.csv / eval_ticket_triage.csv holds its "
                           "block; refusing to append")
    append_block("support_tickets", tk_block)
    append_block("eval_ticket_triage", lb_block)

    print("added tickets", len(new_tickets), "labels", len(new_labels))
    print("id range: TKT-%d .. TKT-%d" % (FIRST_TICKET, next_id - 1))
    print("date range:", new_tickets[0][3], "..", max(r[3] for r in new_tickets))
    print("category dist:", dict(collections.Counter(r[1] for r in new_labels)))
    print("sentiment dist:", dict(collections.Counter(r[2] for r in new_labels)))


if __name__ == "__main__":
    main()
