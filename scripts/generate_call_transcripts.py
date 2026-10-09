#!/usr/bin/env python3
"""Deterministically extend the Jaffle Logistics call-transcript history
backwards in time, adding the quiet years 2023 and 2024 to
seeds/call_transcripts.csv.

APPEND ONLY: the existing CSV bytes are read untouched; new rows are appended
after them. Ids continue the existing CT-10xxx scheme above the current max.

Every transcript is the recording of a CRM note. This script transcribes the
notes the CRM-notes card added (CRM-5034..CRM-5067, all dated 2023-2024): for
each, it writes a transcript whose crm_note_id, client_id and call_date match
the note exactly, and whose spoken content is consistent with the note's stated
topic and sentiment.

Story the transcripts tell (same arc as the notes they transcribe):
  * 2023-2024 are the quiet, healthy years: positive-to-neutral account
    conversations, on-time at or above target, an occasional late load discussed
    and closed out. Jaffle Equipment (CLI-0042) is a good account.
  * No storm escalation, no Columbus bay-3 handling-damage pattern, no
    deterioration narrative: those belong to 2025 and are already written.
Nothing about 2025 is modified.
"""
import csv
import datetime
import io
import os
import random
import sys

SEED = 20240207
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

# client_id -> the account-voice facts the transcripts must stay consistent with
CLIENTS = {
    "CLI-0007": {
        "name": "Jaffle Storefronts",
        "contact": "Doug Ferreira", "contact_org": "Jaffle Storefronts",
    },
    "CLI-0042": {
        "name": "Jaffle Equipment",
        "contact": "Janet Feld", "contact_org": "VP supply chain, Jaffle Equipment",
    },
    "CLI-0155": {
        "name": "Jaffle Crew Outfitters",
        "contact": "Renee Ortiz", "contact_org": "Jaffle Crew Outfitters",
    },
    "CLI-0169": {
        "name": "Jaffle Beverage Co",
        "contact": "Paul Ashby", "contact_org": "Jaffle Beverage Co",
    },
    "CLI-0201": {
        "name": "Jaffle Paper & Packaging",
        "contact": "Gina Marsh", "contact_org": "Jaffle Paper & Packaging",
    },
}

JLOG = "Jaffle Logistics"

# ---- QBR turn pools (positive) -------------------------------------------
QBR_POS_OPEN = [
    "Thanks for making time for the quarterly review. Want to walk through service and then open it up.",
    "Appreciate you joining the QBR. I'll cover performance against the SLA, then hear your side.",
    "Good to have you on. I'll keep it tight — service first, then anything you want to raise.",
]
QBR_POS_CUST = [
    "Honestly, no complaints. Deliveries have been landing on time and your team's been responsive.",
    "We're happy. The last quarter was smooth on our end.",
    "No issues at all. If anything the scheduling has gotten tighter, which we appreciate.",
    "Can't fault it. Everything we routed through you landed when you said it would.",
]
QBR_POS_MID_OWNER = [
    "Good to hear. On our numbers, on-time is running above target for the quarter.",
    "Thanks for the candor. Let me make sure the account plan reflects that.",
    "That tracks with what we're seeing. Steady quarter on our side too.",
]
QBR_POS_MID_CUST = [
    "A few of the expedited ones. I'll forward the tracking numbers.",
    "Only thing is the odd peak-week pickup — nothing that held us up.",
    "Nothing worth chasing. Just a good stretch overall.",
]
QBR_POS_CLOSE = [
    "Great to hear. We'll keep it steady and look at those expanded lanes.",
    "Appreciate that. We'll hold the line and keep you posted on the lane plans.",
    "Good. Same crew on your lanes next quarter; we'll revisit capacity before peak.",
]

# ---- QBR turn pools (neutral) --------------------------------------------
QBR_NEU_OPEN = [
    "Thanks for making time for the quarterly review. Want to walk through service and then open it up.",
    "Appreciate you joining the QBR. I'll cover performance against the SLA, then hear your side.",
    "Good to have you on. I'll keep it brief — service first, then anything you want to raise.",
]
QBR_NEU_CUST = [
    "Mostly fine. A couple of late ones but nothing we lost sleep over.",
    "It's been okay. We'd like a bit more visibility on exceptions, but no fires.",
    "Steady, give or take. One load ran late but it got there.",
]
QBR_NEU_MID_OWNER = [
    "Noted. Anything specific driving that — a hub, a lane, a service level?",
    "Got it. On our numbers, on-time is tracking around target for the quarter.",
    "Understood. Is it a lane thing or just general volume?",
]
QBR_NEU_MID_CUST = [
    "Mostly the exceptions around peak. We'll send examples.",
    "Nothing we can pin down yet, just the overall trend.",
    "One lane in particular, but honestly it's minor.",
]
QBR_NEU_CLOSE = [
    "Understood. I'll get you a cleaner exception report and we'll tighten it up.",
    "Fair enough. I'll have ops watch that lane and follow up.",
    "Got it — I'll pull the exceptions and send them across this week.",
]

# ---- call turn pools ------------------------------------------------------
CALL_POS_OPEN = [
    "Thanks for hopping on. Quick one — just wanted to check in on how things are running.",
    "Hey, thanks for taking the call. Nothing formal, just a touch-base.",
    "Appreciate the time. Short call — checking in before the quarter closes.",
]
CALL_POS_CUST = [
    "Honestly, no complaints. Deliveries have been landing on time and your team's been responsive.",
    "All good here. Nothing's come up since we last spoke.",
    "No issues. Pickups have been on schedule, we've been happy.",
]
CALL_POS_CLOSE = [
    "Great to hear. We'll keep it steady and look at those expanded lanes.",
    "Perfect. I'll leave you to it — shout if anything surfaces.",
    "Good. I'll note that and keep the schedule as it is.",
]
CALL_NEU_CUST = [
    "Mostly fine. A couple of late ones but nothing we lost sleep over.",
    "It's been okay — nothing serious, just watching it.",
    "Steady. Nothing that needs a sit-down.",
]
CALL_NEU_MID_OWNER = [
    "Noted. Anything specific driving that — a hub, a lane, a service level?",
    "Got it. Anything you want me to pull for you?",
]
CALL_NEU_MID_CUST = [
    "Mostly the exceptions around peak. We'll send examples.",
    "Nothing we can pin down yet, just the overall trend.",
]
CALL_NEU_CLOSE = [
    "Understood. I'll get you a cleaner exception report and we'll tighten it up.",
    "Fair enough. I'll have ops keep an eye on it and follow up.",
]

# A call note that links a shipment: a specific late load discussed and closed.
LATE_OPEN = [
    "Thanks for hopping on. I saw the flag on that load from last week and wanted to call you directly.",
    "Appreciate the time. I wanted to talk through the load that ran behind — that one's on us.",
]
LATE_CUST = [
    "Yeah, it showed up a day late. It wasn't catastrophic, but it cost us a shift on the floor.",
    "It landed late, and we had people waiting on it. Not the end of the world, but it stung.",
]
LATE_OWNER_MID = [
    "Understood, and I'm sorry. I've had ops pull the trail — it was a missed pickup window on our side, not anything on the freight.",
    "Thanks for being straight with me. Looking at it, we missed the cut-off at the dock, so it left a day behind.",
]
LATE_CUST_MID = [
    "Appreciated. As long as it doesn't become a habit, we're fine.",
    "Okay. That's fair — I just wanted to know what happened.",
]
LATE_CLOSE = [
    "Noted, and it won't. I'll keep an eye on that lane and follow up next month.",
    "Good. That's closed out from our side — I'll make sure the window's locked.",
]

# ---- plan (joint planning) -----------------------------------------------
PLAN_OPEN = [
    "Thanks for making time. Want to walk through next year's volume and the lane plan together.",
    "Appreciate you joining. I'd like to lock the volume and lane map for the year ahead.",
]
PLAN_CUST = [
    "Sure. Volumes should be broadly flat, maybe up a little on the LTL side.",
    "Happy to. We're not planning any big swings this year.",
]
PLAN_OWNER_MID = [
    "That matches our forecast. We'll reserve capacity and confirm the lane map before the season.",
    "Good — we'll hold the lanes you're on and only adjust if your volumes move.",
]
PLAN_CUST_MID = [
    "Sounds right. Send it over and we'll sign off.",
    "Fine by us. Nothing else outstanding on our side.",
]
PLAN_CLOSE = [
    "Will do. I'll circulate the final plan and we'll revisit at the next QBR.",
    "Perfect. I'll get that over this week.",
]

# Realism touches — applied sparingly so the files still read like the existing
# rows do, but a handful of transcripts carry the small human texture a real
# recording has (a hesitation, an interruption, someone typing, hold music).
REALISM = [
    "{owner} — {jlog}]: Sorry, give me one second — (typing) — okay, got the file open.",
    "{cust} — {corg}]: (hold music) ... okay, I'm back, sorry about that.",
    "{cust} — {corg}]: Let me pull the numbers up — one sec — right, here we go.",
    "{owner} — {jlog}]: Ah — before you finish — sorry, go on, you were saying?",
    "{cust} — {corg}]: Sorry, someone's at the door — (typing) — go ahead, I'm listening.",
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


def turn(speaker, org, text):
    return "[%s \u2014 %s]: %s" % (speaker, org, text)


def build_body(header, turns):
    return header + "~~NL~~" + "~~NL~~".join(turns)


def main():
    rng = random.Random(SEED)

    # ---- id continuation: start above the existing max CT-10xxx ----
    existing = load("call_transcripts")
    band = [int(r["transcript_id"].split("-")[1]) for r in existing
            if 10000 <= int(r["transcript_id"].split("-")[1]) < 11000]
    max_id = max(band)
    if any(n >= 10034 for n in band):
        sys.exit("call_transcripts.csv already extended (found id >= CT-10034); "
                 "refusing to double-append.")

    # ---- the notes to transcribe: the CRM card's new 2023-2024 notes ----
    notes = [n for n in load("crm_notes")
             if n["call_date"][:4] in ("2023", "2024")]
    if not notes:
        sys.exit("no 2023-2024 crm_notes found; run the CRM-notes card first.")
    notes.sort(key=lambda r: (r["call_date"], r["client_id"]))

    rows = []
    next_id = max_id + 1
    added_dates = []

    for note in notes:
        cid = note["client_id"]
        meta = CLIENTS[cid]
        owner = note["account_owner"]
        date = note["call_date"]
        ntype = note["note_type"]
        sentiment = note["sentiment"]
        has_shipment = bool(note["shipment_id"].strip())

        if ntype == "QBR":
            header = "[CALL TRANSCRIPT \u2014 {n} ({c}) | QBR {d} | ref {r}]".format(
                n=meta["name"], c=cid, d=date, r=note["note_id"])
            if sentiment == "positive":
                turns = [
                    turn(owner, JLOG, rng.choice(QBR_POS_OPEN)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(QBR_POS_CUST)),
                    turn(owner, JLOG, rng.choice(QBR_POS_MID_OWNER)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(QBR_POS_MID_CUST)),
                    turn(owner, JLOG, rng.choice(QBR_POS_CLOSE)),
                ]
            else:  # neutral
                turns = [
                    turn(owner, JLOG, rng.choice(QBR_NEU_OPEN)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(QBR_NEU_CUST)),
                    turn(owner, JLOG, rng.choice(QBR_NEU_MID_OWNER)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(QBR_NEU_MID_CUST)),
                    turn(owner, JLOG, rng.choice(QBR_NEU_CLOSE)),
                ]

        elif ntype == "plan":
            header = "[CALL TRANSCRIPT \u2014 {n} ({c}) | planning call {d} | ref {r}]".format(
                n=meta["name"], c=cid, d=date, r=note["note_id"])
            turns = [
                turn(owner, JLOG, rng.choice(PLAN_OPEN)),
                turn(meta["contact"], meta["contact_org"], rng.choice(PLAN_CUST)),
                turn(owner, JLOG, rng.choice(PLAN_OWNER_MID)),
                turn(meta["contact"], meta["contact_org"], rng.choice(PLAN_CUST_MID)),
                turn(owner, JLOG, rng.choice(PLAN_CLOSE)),
            ]

        else:  # call
            header = "[CALL TRANSCRIPT \u2014 {n} ({c}) | call {d} | ref {r}]".format(
                n=meta["name"], c=cid, d=date, r=note["note_id"])
            if has_shipment:
                turns = [
                    turn(owner, JLOG, rng.choice(LATE_OPEN)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(LATE_CUST)),
                    turn(owner, JLOG, rng.choice(LATE_OWNER_MID)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(LATE_CUST_MID)),
                    turn(owner, JLOG, rng.choice(LATE_CLOSE)),
                ]
            elif sentiment == "positive":
                turns = [
                    turn(owner, JLOG, rng.choice(CALL_POS_OPEN)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(CALL_POS_CUST)),
                    turn(owner, JLOG, rng.choice(QBR_POS_MID_OWNER)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(QBR_POS_MID_CUST)),
                    turn(owner, JLOG, rng.choice(CALL_POS_CLOSE)),
                ]
            else:  # neutral
                turns = [
                    turn(owner, JLOG, rng.choice(CALL_POS_OPEN)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(CALL_NEU_CUST)),
                    turn(owner, JLOG, rng.choice(CALL_NEU_MID_OWNER)),
                    turn(meta["contact"], meta["contact_org"], rng.choice(CALL_NEU_MID_CUST)),
                    turn(owner, JLOG, rng.choice(CALL_NEU_CLOSE)),
                ]

        # Occasionally weave in one realism beat (a hesitation, hold music,
        # someone typing) as a valid extra turn after the opening.
        if rng.random() < 0.35:
            beat = rng.choice(REALISM).format(
                owner=owner, jlog=JLOG, cust=meta["contact"], corg=meta["contact_org"])
            turns.insert(1, "[" + beat)

        body = build_body(header, turns)
        participants = "%s (Jaffle Logistics, account owner); %s (%s)" % (
            owner, meta["contact"], meta["contact_org"])

        rows.append(["CT-%d" % next_id, note["note_id"], cid, date,
                     participants, body])
        added_dates.append(date)
        next_id += 1

    earlier = len(existing)
    append_rows("call_transcripts", rows)

    print("appended %d transcripts (call_transcripts %d -> %d)"
          % (len(rows), earlier, earlier + len(rows)))
    print("new id range: %s .. %s" % (rows[0][0], rows[-1][0]))
    print("date range added: %s .. %s" % (min(added_dates), max(added_dates)))


if __name__ == "__main__":
    main()
