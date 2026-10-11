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
    cluster at HUB-AMS (bay 3). Those are 2025-only signals and are never emitted
    here. The worst weather is snow/ice or freezing rain that clears within a day.
Nothing about 2025 is modified.

Frozen inputs: the notes were drawn before scripts/generate_volume_variation.py thinned
2023-2024 routes and shipments. That revision only dropped rows no other seed references,
so no note's route went away, but the dropped rows sat in this script's sampling pool and
in its per-route shipment lists, and the seeded draws depend on both. To keep the draws
byte-identical, REVISED_AWAY_POOL_ROUTES restores the dropped routes to their pool slots
(as placeholders that can never be emitted) and REVISED_AWAY_SHIPMENT_LINKS restores the
dropped shipments to their routes' lists.

Texture is the European network's: road closures name the A-motorway the route runs on,
distances are in km, bad addresses name the hub's postcode, refusals are noted on the CMR
consignment note, an overloaded manifest runs out of EC 561/2006 driving time, and a
Zürich dock closure is a trailer held for Swiss customs at the border.
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

# Motorway draw. The draw is the legacy road number (it also sets the ETA slip in
# minutes); the note names the European motorway it maps to.
ROAD_NUMBERS = [65, 70, 71, 74, 90, 94]
MOTORWAY = {65: "A1", 70: "A7", 71: "A4", 74: "A2", 90: "A9", 94: "A10"}

# Postcode a mis-geocoded stop's street fails to match, by hub.
POSTCODE = {"HUB-AMS": "1234 AB", "HUB-PAR": "75001", "HUB-BER": "10115",
            "HUB-VIE": "1010", "HUB-ZRH": "8001"}


# Current hub code -> the code it carried before the hubs were relabelled.
LEGACY_HUB_CODE = {"AMS": "CMH", "PAR": "CHI", "BER": "IND", "VIE": "DET", "ZRH": "CIN"}


def legacy_route_id(route_id):
    prefix, code, rest = route_id.split("-", 2)
    return "-".join((prefix, LEGACY_HUB_CODE[code], rest))


# Rows the 2023-2024 volume revision dropped after these notes were drawn (see docstring).
# Pool routes: (index in that year's sampling pool, route_id).
REVISED_AWAY_POOL_ROUTES = {
    "2023": (
        (12, "RTE-PAR-20230105-003"),
        (92, "RTE-AMS-20230219-001"),
        (125, "RTE-AMS-20230310-001"),
        (151, "RTE-AMS-20230324-001"),
        (184, "RTE-VIE-20230412-002"),
        (208, "RTE-ZRH-20230425-003"),
        (294, "RTE-PAR-20230619-003"),
        (345, "RTE-PAR-20230713-004"),
        (351, "RTE-VIE-20230717-001"),
        (370, "RTE-BER-20230726-004"),
        (419, "RTE-AMS-20230825-001"),
        (449, "RTE-VIE-20230909-001"),
        (453, "RTE-BER-20230912-002"),
        (465, "RTE-AMS-20230920-001"),
        (480, "RTE-PAR-20230926-004"),
        (499, "RTE-PAR-20231004-001"),
        (589, "RTE-AMS-20231121-004"),
        (596, "RTE-PAR-20231124-001"),
        (601, "RTE-BER-20231127-003"),
        (607, "RTE-AMS-20231130-001"),
        (649, "RTE-ZRH-20231223-001"),
        (661, "RTE-BER-20231229-002"),
    ),
    "2024": (
        (85, "RTE-BER-20240216-002"),
        (142, "RTE-PAR-20240325-003"),
        (376, "RTE-ZRH-20240722-001"),
        (456, "RTE-VIE-20240906-002"),
    ),
}

# Shipment links: (shipment_id, route_id).
REVISED_AWAY_SHIPMENT_LINKS = (
    ("SHP-202301-000024", "RTE-BER-20230119-001"),
    ("SHP-202301-000126", "RTE-VIE-20230104-001"),
    ("SHP-202301-000145", "RTE-AMS-20230129-001"),
    ("SHP-202304-000141", "RTE-ZRH-20230411-002"),
    ("SHP-202305-000004", "RTE-AMS-20230514-002"),
    ("SHP-202306-000002", "RTE-VIE-20230627-001"),
    ("SHP-202306-000138", "RTE-PAR-20230622-001"),
    ("SHP-202307-000060", "RTE-VIE-20230710-001"),
    ("SHP-202307-000127", "RTE-BER-20230707-003"),
    ("SHP-202308-000025", "RTE-VIE-20230808-001"),
    ("SHP-202308-000118", "RTE-VIE-20230820-001"),
    ("SHP-202308-000123", "RTE-AMS-20230829-003"),
    ("SHP-202309-000101", "RTE-BER-20230928-001"),
    ("SHP-202309-000121", "RTE-AMS-20230915-001"),
    ("SHP-202310-000118", "RTE-VIE-20231017-001"),
    ("SHP-202310-000125", "RTE-VIE-20231012-001"),
    ("SHP-202310-000147", "RTE-AMS-20231011-002"),
    ("SHP-202311-000008", "RTE-AMS-20231116-001"),
    ("SHP-202311-000035", "RTE-PAR-20231114-002"),
    ("SHP-202312-000156", "RTE-BER-20231224-002"),
    ("SHP-202312-000192", "RTE-ZRH-20231223-001"),
    ("SHP-202401-000056", "RTE-VIE-20240108-003"),
    ("SHP-202402-000026", "RTE-VIE-20240202-001"),
    ("SHP-202403-000160", "RTE-PAR-20240326-001"),
    ("SHP-202404-000083", "RTE-PAR-20240404-002"),
    ("SHP-202405-000080", "RTE-BER-20240502-002"),
    ("SHP-202406-000057", "RTE-PAR-20240607-001"),
    ("SHP-202409-000104", "RTE-PAR-20240928-001"),
    ("SHP-202412-000035", "RTE-ZRH-20241230-001"),
    ("SHP-202412-000068", "RTE-PAR-20241213-003"),
    ("SHP-202412-000090", "RTE-BER-20241209-001"),
)


def load(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="") as fh:
        return list(csv.DictReader(fh))


def append_rows(name, rows, existing_ids):
    """Append csv rows (CRLF, matching the existing files) after the existing bytes.

    If any new id is already on file, the block must already be the file's tail, byte
    for byte (a re-run: report it, write nothing, return False); otherwise it is an error.
    """
    path = os.path.join(SEEDS, name + ".csv")
    with open(path, "rb") as fh:
        original = fh.read()
    assert not original or original.endswith(b"\r\n"), "seed does not end with CRLF"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    for r in rows:
        w.writerow(r)
    block = buf.getvalue().encode()
    if any(r[0] in existing_ids for r in rows):
        if original.endswith(block):
            print("already present: the block is %s.csv's tail, byte for byte; nothing written" % name)
            return False
        raise RuntimeError("%s.csv already holds %s.. but not this block; refusing to append"
                           % (name, rows[0][0]))
    with open(path, "ab") as fh:
        fh.write(block)
    return True


def wchoice(rng, items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


def make_body(rng, etype, drv, ref, hub):
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
        rd = wchoice(rng, ROAD_NUMBERS, [1] * 6)
        return ("%s closure, major backup. ETA +%dm. %d stops missed cutoff."
                % (MOTORWAY[rd], rd, rng.randint(1, 6)))
    if etype == "access":
        if wchoice(rng, ACCESS, ACCESS_W) == "dock":
            held = ("; trailer held at the Zürich border crossing for Swiss customs clearance"
                    if hub == "HUB-ZRH" else "")
            return ("Dock closed early%s. %d LTL stops could not unload. Rescheduling AM."
                    % (held, rng.randint(1, 6)))
        return "Gate locked at delivery, no answer. ATT x2. the stop left as NSF, reattempt scheduled."
    if etype == "address":
        if wchoice(rng, ADDRESS, ADDRESS_W) == "suite":
            return ("postcode missing, %d stops undeliverable. Contacting account for update."
                    % rng.randint(1, 6))
        return ("Bad address on %s; street does not match postcode %s. Geocode off by ~5km. "
                "Held for dispatch correction." % (ref, POSTCODE[hub]))
    if etype == "customer_nsf":
        if wchoice(rng, NSF, NSF_W) == "closed":
            return "the stop NSF - business closed. ATT 1440. Reattempt next biz day."
        return ("Consignee refused delivery the stop; refusal noted on the CMR consignment note. "
                "Return to hub initiated.")
    if etype == "mechanical":
        if wchoice(rng, MECH, MECH_W) == "engine":
            return ("Check-engine light, reduced power. Swapped to spare, %d stops late."
                    % rng.randint(1, 6))
        return ("Liftgate fault mid-route. %s completed %d stops manual, %d deferred. "
                "VEH flagged for shop." % (drv, rng.randint(18, 65), rng.randint(1, 6)))
    if etype == "volume":
        if wchoice(rng, VOLUME, VOLUME_W) == "manifest":
            return ("Overloaded manifest, %d stops assigned. %d could not be completed "
                    "within the EC 561/2006 driving-time limit (tachograph)." % (rng.randint(20, 65), rng.randint(1, 6)))
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
    for shipment_id, route_id in REVISED_AWAY_SHIPMENT_LINKS:
        ships_by_route[route_id].append(shipment_id)
        ships_by_route[route_id].sort()

    eligible = collections.defaultdict(list)
    for r in routes:
        yr = r["service_date"][:4]
        if yr in ("2023", "2024") and 1 <= int(r["exceptions_count"]) <= 6:
            eligible[yr].append(r)
    for yr, dropped in REVISED_AWAY_POOL_ROUTES.items():
        for idx, route_id in dropped:
            eligible[yr].insert(idx, {"route_id": route_id, "revised_away": True})

    rows = []
    nid = START_NOTE
    for year in ("2023", "2024"):
        pool = eligible[year]
        chosen = rng.sample(pool, PER_YEAR)
        assert not any(r.get("revised_away") for r in chosen), "drew a revised-away route"
        # Same-day notes run in legacy route_id order (the hub code before the relabel).
        chosen.sort(key=lambda r: (r["service_date"], legacy_route_id(r["route_id"])))
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
            text = make_body(rng, etype, r["driver_id"], ref, r["hub_id"])
            rows.append(["DN-%06d" % nid, r["route_id"], r["driver_id"],
                         r["hub_id"], ts, etype, prefix + text])
            nid += 1

    existing_ids = {r["note_id"] for r in load("dispatch_notes")}
    if not append_rows("dispatch_notes", rows, existing_ids):
        return
    print("appended", len(rows), "dispatch notes; note_id DN-%06d .. DN-%06d"
          % (START_NOTE, START_NOTE + len(rows) - 1))


if __name__ == "__main__":
    main()
