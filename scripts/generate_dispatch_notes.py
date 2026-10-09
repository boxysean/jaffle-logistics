#!/usr/bin/env python3
"""Deterministically extend seeds/dispatch_notes.csv backwards in time, adding the
quiet years 2023 and 2024 to the ops-floor note log.

APPEND ONLY: the existing bytes are read and left byte-identical; new rows are
appended after them. New note_ids continue the existing DN-1NNNNN scheme upward
from the current maximum, and every route_id / driver_id / hub_id points at a row
that already exists. Each note's timestamp falls on its route's service_date, and
the short hub code in the body is derived from the route's hub.

Story the notes tell:
  * 2023 and 2024 are the quiet, healthy years: mundane exceptions only (traffic,
    a late tractor, a dock queue, a customer site closed, a little snow/ice).
  * No storm-scale day (no "Whiteout conditions ..."), no recurring handling-damage
    cluster at HUB-CMH (bay 3). Those are 2025-only signals and are never emitted
    here. The worst weather is snow/ice or freezing rain that clears within a day.
Nothing about 2025 is modified.
"""
import csv, io, os, random, collections, re

SEED = 20230601
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

PER_YEAR = 350                     # notes added per year (2023, 2024)
START_NOTE = 100600                # first free id after the existing DN-1 range

# exception_type vocabulary and its 2025 share (storm-scale weather excluded below).
EXC_TYPES = ["weather", "traffic", "access", "address", "mechanical", "volume", "customer_nsf"]
EXC_WEIGHTS = [148, 96, 80, 73, 73, 70, 59]

# template families per type, weighted to mirror the existing split.
WEATHER = ["snowice", "freezing"]
WEATHER_W = [45, 62]
TRAFFIC = ["accident", "closure"]
TRAFFIC_W = [50, 46]
ACCESS = ["dock", "gate"]
ACCESS_W = [47, 33]
ADDRESS = ["suite", "geocode"]
ADDRESS_W = [44, 27]
NSF = ["closed", "refused"]
NSF_W = [37, 21]
MECH = ["engine", "liftgate"]
MECH_W = [37, 35]
VOLUME = ["manifest", "peak"]
VOLUME_W = [42, 27]

INTERSTATES = [65, 70, 71, 74, 90, 94]


def load(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="") as fh:
        return list(csv.DictReader(fh))


def append_rows(name, rows):
    """Append csv rows (CRLF, matching the existing files) after the existing bytes."""
    path = os.path.join(SEEDS, name + ".csv")
    with open(path, "rb") as fh:
        original = fh.read()
    assert not original or original.endswith(b"\r\n"), "seed does not end with CRLF"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    for r in rows:
        w.writerow(r)
    with open(path, "ab") as fh:
        fh.write(buf.getvalue().encode())
    return len(original)


def wchoice(rng, items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


def make_body(rng, etype, drv, ref):
    """Build the free-text body for one note (with the ''~~NL~~'' line break the
    file uses in place of a real newline)."""
    if etype == "weather":
        if wchoice(rng, WEATHER, WEATHER_W) == "snowice":
            return ("Snow/ice on route. %d stops ATT, %d DEL to next day. "
                    "Salt trucks late. ETA slippage all afternoon."
                    % (rng.randint(19, 65), rng.randint(1, 6)))
        return ("Freezing rain. Driver %s pulled early for safety. %d stops rolled "
                "to tomorrow." % (drv, rng.randint(1, 6)))
    if etype == "traffic":
        if wchoice(rng, TRAFFIC, TRAFFIC_W) == "accident":
            return ("Accident on route, detour added. %d DEL slipped past commit."
                    % rng.randint(1, 6))
        rd = wchoice(rng, INTERSTATES, [1] * 6)
        return ("I-%d closure, major backup. ETA +%dm. %d stops missed cutoff."
                % (rd, rd, rng.randint(1, 6)))
    if etype == "access":
        if wchoice(rng, ACCESS, ACCESS_W) == "dock":
            return ("Dock closed early. %d LTL stops could not unload. Rescheduling AM."
                    % rng.randint(1, 6))
        return "Gate locked at delivery, no answer. ATT x2. the stop left as NSF, reattempt scheduled."
    if etype == "address":
        if wchoice(rng, ADDRESS, ADDRESS_W) == "suite":
            return ("Suite # missing, %d stops undeliverable. Contacting account for update."
                    % rng.randint(1, 6))
        return ("Bad address on %s. Geocode off by ~3mi. Held for dispatch correction." % ref)
    if etype == "customer_nsf":
        if wchoice(rng, NSF, NSF_W) == "closed":
            return "the stop NSF - business closed. ATT 1440. Reattempt next biz day."
        return "Consignee refused delivery the stop. Return to hub initiated."
    if etype == "mechanical":
        if wchoice(rng, MECH, MECH_W) == "engine":
            return ("Check-engine light, reduced power. Swapped to spare, %d stops late."
                    % rng.randint(1, 6))
        return ("Liftgate fault mid-route. %s completed %d stops manual, %d deferred. "
                "VEH flagged for shop." % (drv, rng.randint(18, 65), rng.randint(1, 6)))
    if etype == "volume":
        if wchoice(rng, VOLUME, VOLUME_W) == "manifest":
            return ("Overloaded manifest, %d stops assigned. %d could not be completed "
                    "in service window." % (rng.randint(20, 65), rng.randint(1, 6)))
        return ("Peak volume, truck full. %d pkgs bumped to overflow route."
                % rng.randint(1, 6))
    raise ValueError(etype)


def main():
    rng = random.Random(SEED)

    routes = load("routes")
    shipments = load("shipments")

    # shipments reachable per route (for the "Bad address on SHP-..." template)
    ships_by_route = collections.defaultdict(list)
    for s in shipments:
        if s["route_id"]:
            ships_by_route[s["route_id"]].append(s["shipment_id"])

    eligible = collections.defaultdict(list)
    for r in routes:
        yr = r["service_date"][:4]
        if yr in ("2023", "2024") and 1 <= int(r["exceptions_count"]) <= 6:
            eligible[yr].append(r)

    rows = []
    nid = START_NOTE
    for year in ("2023", "2024"):
        pool = eligible[year]
        chosen = rng.sample(pool, PER_YEAR)
        chosen.sort(key=lambda r: (r["service_date"], r["route_id"]))
        for r in chosen:
            y, m, d = (int(x) for x in r["service_date"].split("-"))
            hh, mm = rng.randint(6, 20), rng.randint(0, 59)
            ts = "%04d-%02d-%02dT%02d:%02d:00" % (y, m, d, hh, mm)
            hub_code = r["hub_id"].split("-")[1]
            etype = wchoice(rng, EXC_TYPES, EXC_WEIGHTS)
            # reference a real shipment on this route sometimes (mirrors the
            # existing "Bad address on SHP-..." rows); otherwise the generic stop.
            ref = "the stop"
            if r["route_id"] in ships_by_route and rng.random() < 0.38:
                ref = rng.choice(ships_by_route[r["route_id"]])
            prefix = "[%02d/%02d %02d:%02d] %s / %s @ %s~~NL~~" % (
                m, d, hh, mm, r["route_id"], r["driver_id"], hub_code)
            text = make_body(rng, etype, r["driver_id"], ref)
            rows.append(["DN-%06d" % nid, r["route_id"], r["driver_id"],
                         r["hub_id"], ts, etype, prefix + text])
            nid += 1

    append_rows("dispatch_notes", rows)
    print("appended", len(rows), "dispatch notes; note_id DN-%06d .. DN-%06d"
          % (START_NOTE, START_NOTE + len(rows) - 1))


if __name__ == "__main__":
    main()
