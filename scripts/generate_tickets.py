#!/usr/bin/env python3
"""Deterministically extend the Jaffle Logistics support history backwards in
time, adding the quiet years 2023 and 2024 to seeds/support_tickets.csv and the
matching ground-truth labels to seeds/eval_ticket_triage.csv.

APPEND ONLY: existing bytes are read and re-written untouched; new rows are
appended after them. New ticket ids continue the plain TKT-2NNNNN sequence
upward from TKT-200299 (the last existing plain id), and every foreign key
points at a row that exists (the client / shipment chosen for the ticket).

Story the numbers tell:
  * 2023 and 2024 are the ordinary, healthy years: a late load, a POD request,
    an accessorial/contact question, the occasional missed delivery -- resolved
    without a systemic pattern.
  * No storm flood, no recurring Columbus (HUB-CMH) handling-damage cluster and
    no Jaffle Equipment (CLI-0042) escalation trend: those belong to 2025 and
    are untouched here. New tickets simply continue the ordinary TKT-200xxx mix.

Every new ticket carries exactly one ground-truth label row (category +
sentiment) whose values come from the existing vocabulary and match the body.
"""
import csv, io, os, random, datetime, collections

SEED = 20231002
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

HUB_CITY = {"HUB-CMH": "Columbus", "HUB-CHI": "Chicago", "HUB-IND": "Indianapolis",
            "HUB-DET": "Detroit", "HUB-CIN": "Cincinnati"}
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


def append_rows(name, rows):
    """Append csv rows (CRLF, matching the existing files) after the existing bytes."""
    path = os.path.join(SEEDS, name + ".csv")
    with open(path, "rb") as fh:
        original = fh.read()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerows(rows)
    with open(path, "ab") as fh:
        fh.write(buf.getvalue().encode())
    return len(original)


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


def main():
    rng = random.Random(SEED)

    existing_tk = load("support_tickets")
    shipments = load("shipments")

    max_plain = max(int(r["ticket_id"].split("-")[1])
                    for r in existing_tk if r["ticket_id"].startswith("TKT-2"))
    next_id = max_plain + 1

    # shipments grouped by (year, month) and by status class, with parsed dates.
    # Category is chosen first (mirroring the ordinary 2025 mix), then a shipment
    # whose status fits that category is picked -- so a "currently delayed" body
    # always points at a shipment that really was delayed.
    def sclass(st):
        return "delivered" if st == "delivered" else ("delayed" if st == "delayed" else "failed")

    ships_by_ym = collections.defaultdict(list)
    pool_month = collections.defaultdict(list)
    pool_year = collections.defaultdict(list)
    for s in shipments:
        y = int(s["created_at"][:4])
        if y not in (2023, 2024):
            continue
        created = datetime.datetime.strptime(s["created_at"], "%Y-%m-%dT%H:%M:%S")
        m = int(s["created_at"][5:7])
        cls = sclass(s["status"])
        ships_by_ym[(y, m)].append((created, s))
        pool_month[(y, m, cls)].append((created, s))
        pool_year[(y, cls)].append((created, s))

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

    append_rows("support_tickets", new_tickets)
    append_rows("eval_ticket_triage", new_labels)

    print("added tickets", len(new_tickets), "labels", len(new_labels))
    print("id range: TKT-%d .. TKT-%d" % (max_plain + 1, next_id - 1))
    print("date range:", new_tickets[0][3], "..", max(r[3] for r in new_tickets))
    print("category dist:", dict(collections.Counter(r[1] for r in new_labels)))
    print("sentiment dist:", dict(collections.Counter(r[2] for r in new_labels)))


if __name__ == "__main__":
    main()
