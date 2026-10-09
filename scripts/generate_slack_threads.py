#!/usr/bin/env python3
"""Deterministically extend seeds/slack_threads.csv backwards in time, adding the
quiet years 2023 and 2024 to the internal chatter.

APPEND ONLY: the existing bytes are read and re-written untouched; the new rows are
appended after them. Each new thread continues the SLK-9xxx scheme upward and is
anchored to a real incident from the operational backbone whose occurred_at falls in
the same period (the incident's own route is cited too, and always exists).

Story these threads tell:
  * 2023 and 2024 are ordinary, healthy operating years. The chatter is routine --
    a stuck trailer, a driver who cannot find a dock, a mispick, a customer chasing a
    driver, a Friday-afternoon escalation -- all resolved inside the week.
  * No 2025 signal starts early: no storm, no recurring Columbus handling-damage
    cluster, no bay-3 pattern. Only severity 1-2 incidents are referenced.
  * Jaffle Equipment (CLI-0042) is referenced only neutrally-positive (a good quarter,
    a renewal) -- the deliberate contrast with 2025.
Nothing about 2025 is modified.
"""
import csv, io, os, random, datetime, collections

SEED = 20241010
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

FIRST_SLK = 9050          # continue SLK-9xxx upward from SLK-9049

HUB_CITY = {"HUB-CMH": "Columbus", "HUB-CHI": "Chicago", "HUB-IND": "Indianapolis",
            "HUB-DET": "Detroit", "HUB-CIN": "Cincinnati"}

# Handle vocabulary, read off the existing rows (same people, same style). Two new
# people are added sparingly -- the prior years' roster is otherwise the same crew.
HANDLES = ["@tina", "@ray", "@mcardenas", "@gordon", "@curtis", "@marla", "@yolanda",
           "@devon", "@elaine", "@tokafor", "@marcus", "@hank", "@dana", "@sam",
           "@rhalvorsen", "@priya.n", "@sandra", "@frank", "@alicia", "@dcabrera",
           "@nhaas"]

# Response pool (responders), weighted to mirror the existing mix.
MIDS = ["on it. how many stops affected?",
        "ugh again? pulling the route now",
        "looping in ops lead",
        "let's get a report filed",
        "who's the driver on this one",
        "is this the same thing from this morning?",
        "k, I'll cover the reattempts",
        "customer already asking"]
MID_W = [16, 15, 11, 10, 10, 9, 8, 7]

ROUTE_STATUS = ["driver's holding for instructions", "exceptions piling up",
                "we may need to reassign"]
ROUTE_W = [12, 10, 8]

CLOSERS = ["ok tracking", "filed. see the incident record", "thx. will update the thread"]
CLOSE_W = [17, 17, 16]


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


def wchoice(rng, items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


def build_thread(rng, thread_id, incident, route_id, hub):
    """Assemble one routine incident thread, exactly in the existing format."""
    iid = incident["incident_id"]
    city = HUB_CITY[hub]
    n_parts = rng.choices([2, 3, 4], weights=[14, 24, 17], k=1)[0]
    people = rng.sample(HANDLES, n_parts)
    opener = people[0]
    responders = people[1:]

    # Route line present whenever the incident carries a route (the runner posts it).
    show_route = bool(route_id) and rng.random() < 0.92

    lines = ["%s: heads up, seeing an issue tied to %s at %s" % (opener, iid, city)]
    mid1 = wchoice(rng, MIDS, MID_W)
    lines.append("%s: %s" % (responders[0], mid1))
    alt_mids = [m for m in MIDS if m != mid1]
    alt_w = [w for m, w in zip(MIDS, MID_W) if m != mid1]
    if show_route:
        lines.append("%s: route %s, %s" % (opener, route_id, wchoice(rng, ROUTE_STATUS, ROUTE_W)))
        if len(responders) >= 2:
            lines.append("%s: %s" % (responders[rng.randrange(1, len(responders))],
                                     wchoice(rng, alt_mids, alt_w)))
    elif len(responders) >= 2:
        lines.append("%s: %s" % (responders[rng.randrange(1, len(responders))],
                                 wchoice(rng, alt_mids, alt_w)))
    lines.append("%s: %s" % (opener, wchoice(rng, CLOSERS, CLOSE_W)))

    body = "~~NL~~".join(lines)
    participants = ", ".join(people)

    # Channel: the hub's ops room most of the time, network rooms the rest.
    if rng.random() < 0.60:
        channel = "#ops-%s" % hub.split("-")[1].lower()
    else:
        channel = wchoice(rng, ["#dispatch", "#fleet", "#incident-response"], [5, 5, 3])

    occurred = datetime.datetime.strptime(incident["occurred_at"], "%Y-%m-%dT%H:%M:%S")
    delta = datetime.timedelta(minutes=rng.randint(12, 235))
    started = occurred + delta
    if started.day != occurred.day:            # never spill across midnight
        started = occurred + datetime.timedelta(minutes=rng.randint(5, 60))

    linked = iid + (" " + route_id if route_id else "")
    return [thread_id, channel, participants, started.strftime("%Y-%m-%dT%H:%M:00"),
            linked, body]


def build_account_note(rng, thread_id, when, year, people, lines):
    """A neutral-positive Jaffle Equipment (CLI-0042) note -- the deliberate contrast."""
    participants = ", ".join(people)
    body = "~~NL~~".join("%s: %s" % (p, t) for p, t in zip(people, lines))
    return [thread_id, "#accounts", participants, when, "CLI-0042", body]


def main():
    rng = random.Random(SEED)

    incidents = load("incidents")
    routes = {r["route_id"] for r in load("routes")}

    # Candidate anchors: 2023/2024 only, routine severity, and (when they carry a
    # route) a route that actually exists.
    cands = []
    for r in incidents:
        if r["occurred_at"][:4] not in ("2023", "2024"):
            continue
        if int(r["severity"]) > 2:             # no storm-scale / severe events before 2025
            continue
        if r["route_id"] and r["route_id"] not in routes:
            continue
        cands.append(r)

    rng.shuffle(cands)
    n_routine = 58
    chosen = cands[:n_routine]

    rows = []
    tid = FIRST_SLK
    for inc in chosen:
        rows.append(build_thread(rng, "SLK-%d" % tid, inc, inc["route_id"], inc["hub_id"]))
        tid += 1

    # Two neutral-positive CLI-0042 notes, one per prior year.
    rows.append(build_account_note(
        rng, "SLK-%d" % tid, "2023-08-11T15:20:00", 2023,
        ["@marcus", "@rhalvorsen", "@dana"],
        ["Jaffle Equipment (CLI-0042) closed the quarter at 98.7% on-time, best on the book",
         "they've been a clean account all year -- renewals should be straightforward",
         "agreed, worth a mention in the Q3 business review"]))
    tid += 1
    rows.append(build_account_note(
        rng, "SLK-%d" % tid, "2024-11-08T14:05:00", 2024,
        ["@dana", "@marcus", "@tokafor"],
        ["CLI-0042 renewal is signed for 2025, two-year term",
         "on-time held at 98%+ again this year, no escalations worth flagging",
         "nice one. keeping them off the watchlist"]))
    tid += 1

    before = append_rows("slack_threads", rows)
    print("appended", len(rows), "threads (SLK-%d..SLK-%d); file was %d bytes"
          % (FIRST_SLK, tid - 1, before))


if __name__ == "__main__":
    main()
