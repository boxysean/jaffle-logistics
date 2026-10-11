#!/usr/bin/env python3
"""Deterministically extend the Jaffle Logistics operational backbone backwards in
time, adding the quiet years 2023 and 2024 to seeds/shipments.csv, routes.csv and
incidents.csv (plus a handful of drivers/vehicles so the prior years are staffed).

APPEND ONLY: the existing CSV bytes are read and re-written untouched; new rows are
appended after them. Every id continues the existing scheme and every foreign key
points at a row that exists (clients, hubs, drivers, vehicles, routes, shipments).

Story the numbers tell:
  * 2023: whole-book on-time ~97.5%, Jaffle Werke (CLI-0042) ~98%
  * 2024: whole-book on-time ~97.2%, Jaffle Werke (CLI-0042) ~98%
  * incidents are ordinary weather/mechanical only, milder than 2025, with no
    storm-scale event and no Amsterdam handling-damage cluster.
Nothing about 2025 is modified.

Ids are pinned to where the block first started (DRV-01189, VEH-0041), and on a
re-run the block's own rows (the 2023-2024 routes, drivers DRV-01189 upward,
vehicles VEH-0041 upward) are left out of the inputs, so the same rows come out.

Later revisions this script replays so a re-run reproduces the committed rows:
  * scripts/generate_promised_delivery.py added promised_delivery_at, hours_late
    and late_bucket to every shipment. When shipments.csv has them, the new rows
    get them from that script's own build(), run over the existing rows and the
    full pre-revision block.
  * scripts/generate_volume_variation.py then dropped 2023-2024 shipments and
    routes no other seed referenced. Its draws depended on every seed's references
    at the time, so the dropped rows are listed here (DROPPED_SHIPMENTS,
    DROPPED_ROUTES) and left out of what is written; they are still generated, so
    every seeded draw after them is unchanged.
"""
import csv, io, os, sys, random, datetime, collections

SEED = 20231001
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

HUBS = ["HUB-AMS", "HUB-PAR", "HUB-BER", "HUB-VIE", "HUB-ZRH"]
HUB_CITY = {"HUB-AMS": "Amsterdam", "HUB-PAR": "Paris", "HUB-BER": "Berlin",
            "HUB-VIE": "Vienna", "HUB-ZRH": "Zürich"}
CLIENTS = ["CLI-0007", "CLI-0042", "CLI-0155", "CLI-0169", "CLI-0201"]
CLIENT_WEIGHTS = [387, 416, 398, 394, 414]          # mirror 2025 share
SERVICE_LEVELS = ["standard", "expedited", "freight"]
SERVICE_WEIGHTS = [1123, 470, 416]                  # mirror 2025 share
MISS_SPLIT = [("delayed", 0.807), ("failed", 0.156), ("returned", 0.037)]
WEEKDAY_WEIGHT = [1.0, 1.05, 1.03, 1.0, 1.05, 0.28, 0.30]   # Mon..Sun
INC_TYPES = ["weather", "delay", "damage", "accident", "mispick", "dispute"]
INC_TYPE_W = [0.30, 0.28, 0.10, 0.12, 0.12, 0.08]
INC_SEV = [1, 2, 3, 4]
INC_SEV_W = [0.58, 0.30, 0.10, 0.02]
DELIVERED_LAG_W = {1: 826, 2: 325, 3: 335, 4: 386}
DELAYED_LAG_W = {4: 12, 5: 13, 6: 64, 7: 9, 8: 8, 9: 6}

MONTH_SHP = {1: 183, 2: 143, 3: 160, 4: 145, 5: 151, 6: 139,
             7: 171, 8: 162, 9: 159, 10: 169, 11: 203, 12: 224}
MONTH_RTE = {1: 343, 2: 258, 3: 290, 4: 294, 5: 275, 6: 302,
             7: 323, 8: 280, 9: 317, 10: 324, 11: 293, 12: 330}

FIRST_DRIVER = 1189   # pinned: the block's drivers run DRV-01189 upward
FIRST_VEHICLE = 41    # pinned: the block's vehicles run VEH-0041 upward
BLOCK_YEARS = ("2023", "2024")

# Rows scripts/generate_volume_variation.py later dropped (see docstring).
# Shipments: month -> the SHP-<month>-NNNNNN sequence numbers dropped.
DROPPED_SHIPMENTS = {
    "202301": "17 21 24 29 61 70 81 118 126 133 145 155 160 168 182",
    "202302": "18 40 42 44 50 54 64 69 72 97 131",
    "202303": "15 17 32 56 68 91 112 114 122 127 129 141 155",
    "202304": "15 16 19 30 32 60 61 90 100 109 121 141",
    "202305": "4 12 38 60 71 96 112 116 126 128 135 136",
    "202306": "2 21 62 69 77 83 87 118 127 133 138",
    "202307": "5 31 48 60 108 109 110 116 127 139 143 154 158 171",
    "202308": "1 16 24 25 45 58 104 112 118 123 130 154 156",
    "202309": "27 38 40 58 74 83 95 101 113 121 142 146 149",
    "202310": "9 54 62 104 105 118 125 129 133 134 146 147 153",
    "202311": "2 3 8 35 46 73 77 99 112 117 127 138 142 150 153 154",
    "202312": "4 30 70 80 101 104 106 107 125 145 156 163 165 168 173 192 193 204",
    "202401": "48 56 86 87 148",
    "202402": "26 40 99 121",
    "202403": "11 132 138 158 160",
    "202404": "18 33 73 83",
    "202405": "77 80 89 125 131",
    "202406": "40 57 69 88",
    "202407": "26 69 96 144 165",
    "202408": "11 107 113 149 161",
    "202409": "58 64 83 93 104",
    "202410": "61 96 120 144 154",
    "202411": "27 81 88 91 107 154",
    "202412": "31 35 56 68 90 208 221",
}
# Routes: month -> <day><hub code><seq> for each RTE-<code>-<month><day>-<seq> dropped.
DROPPED_ROUTES = {
    "202301": (
        "02VIE4 04BER2 04ZRH1 05AMS4 05PAR3 05BER1 05ZRH4 06PAR2 11VIE1 12BER2 12ZRH1 "
        "13BER4 13ZRH2 16PAR2 17BER1 17VIE2 19VIE6 20VIE4 23AMS2 24VIE2 25BER4 25ZRH4 "
        "26VIE4 27PAR1 29PAR1 30AMS2 31BER3 31ZRH4"
    ),
    "202302": (
        "01AMS1 01PAR7 04AMS1 06AMS3 08AMS5 08PAR4 08ZRH1 10AMS3 11PAR3 14PAR5 15VIE1 "
        "15VIE3 19AMS1 20PAR1 22VIE1 22VIE3 23PAR1 25ZRH1 26AMS1 27VIE2 27ZRH2"
    ),
    "202303": (
        "01BER1 01VIE1 02ZRH2 03ZRH2 06PAR1 06VIE1 07BER1 09BER2 10AMS1 13BER4 22BER3 "
        "22ZRH4 23AMS1 23AMS4 23ZRH2 24AMS1 24PAR4 24VIE2 27BER2 27VIE2 28PAR1 30PAR3 "
        "30ZRH4"
    ),
    "202304": (
        "04AMS3 05ZRH4 07BER3 12AMS1 12VIE2 14PAR1 14PAR4 14VIE2 14VIE3 17PAR3 19PAR2 "
        "19PAR4 20PAR3 21PAR3 24PAR1 24PAR3 24BER2 25ZRH3 26AMS2 28AMS6 28ZRH3 29PAR4 "
        "30PAR1 30BER2"
    ),
    "202305": (
        "05PAR3 06BER2 08AMS3 09AMS3 10PAR1 10PAR3 12PAR1 17AMS2 18VIE1 18ZRH1 19AMS2 "
        "19VIE5 19ZRH1 22PAR2 24PAR2 25BER3 27VIE1 31BER1 31VIE1 31VIE2 31VIE3 31VIE5"
    ),
    "202306": (
        "01PAR2 01VIE4 02VIE3 06VIE4 07BER2 07BER3 08AMS1 14PAR2 15VIE1 16VIE1 18PAR1 "
        "19PAR3 21AMS2 21ZRH3 22PAR4 22BER1 23PAR1 23BER2 28BER5 28ZRH1 29PAR1 29BER2 "
        "29ZRH1 30ZRH4"
    ),
    "202307": (
        "01AMS1 01VIE2 03AMS3 04AMS1 07BER1 08AMS1 08PAR1 12VIE2 12VIE3 13PAR1 13PAR3 "
        "13PAR4 16AMS1 17VIE1 18PAR1 19PAR1 20ZRH1 21PAR2 25AMS3 25ZRH4 26PAR2 26BER4 "
        "26VIE4 26ZRH6 27ZRH2 31ZRH2"
    ),
    "202308": (
        "02AMS2 07AMS1 09ZRH3 10VIE1 11PAR2 11ZRH2 12VIE1 12ZRH1 15PAR3 18PAR3 21ZRH2 "
        "21ZRH3 22PAR1 22VIE1 22ZRH2 25AMS1 25PAR4 25VIE1 25VIE3 26VIE1 28BER2 29VIE2"
    ),
    "202309": (
        "01VIE1 03BER1 04ZRH3 07BER2 09VIE1 12PAR5 12BER2 14AMS3 18ZRH7 19PAR1 19BER1 "
        "19BER4 19ZRH3 20AMS1 21PAR3 22PAR1 22VIE3 24VIE2 25BER2 25ZRH1 26PAR4 27VIE1 "
        "27VIE7 28PAR1 30ZRH3"
    ),
    "202310": (
        "02BER2 04PAR1 04PAR3 04PAR4 04BER2 04VIE2 05VIE2 05ZRH2 08ZRH1 09PAR1 10PAR2 "
        "12AMS2 12PAR2 13ZRH5 16BER2 16BER3 16ZRH1 16ZRH3 17VIE2 18VIE1 20AMS2 23AMS2 "
        "25BER1 26VIE2 27ZRH1 30PAR2"
    ),
    "202311": (
        "01VIE1 02BER2 02BER3 04AMS4 05PAR1 06ZRH2 06ZRH4 10BER1 14VIE1 14ZRH2 16ZRH1 "
        "16ZRH6 17PAR4 17ZRH2 19ZRH1 19ZRH2 20ZRH1 20ZRH2 21AMS4 21PAR1 24PAR1 27BER3 "
        "29ZRH4 30AMS1"
    ),
    "202312": (
        "01AMS2 02BER2 03AMS1 05PAR2 06BER5 06VIE2 08AMS1 08ZRH2 11BER2 11ZRH1 11ZRH3 "
        "14AMS1 18AMS2 18ZRH3 19BER2 20PAR2 20PAR5 22PAR5 22ZRH1 23ZRH1 24PAR1 26ZRH3 "
        "27BER2 29BER2 29ZRH1 29ZRH5"
    ),
    "202401": "01PAR1 02AMS4 05VIE2 08ZRH1 10ZRH2 14ZRH1 25PAR3 28ZRH1 29ZRH3 31ZRH3",
    "202402": "06ZRH1 06ZRH2 14ZRH3 14ZRH4 16BER2 16ZRH3 19PAR2 23ZRH2",
    "202403": "01PAR2 11ZRH2 12PAR1 14PAR2 20BER2 23PAR2 25AMS1 25PAR3 26ZRH1",
    "202404": "02AMS1 06PAR3 11PAR2 14ZRH2 22PAR1 22VIE1 24AMS2 25BER2 27BER1",
    "202405": "08ZRH1 11AMS1 17BER1 23ZRH1 27PAR4 29PAR1 30BER1 31ZRH2",
    "202406": "06VIE1 10VIE2 12VIE4 14PAR4 14VIE3 18VIE5 21VIE1 26VIE2 27ZRH3",
    "202407": "04AMS2 13ZRH1 14PAR2 17VIE2 18AMS3 19AMS3 19VIE3 22ZRH1 23PAR2",
    "202408": "09PAR4 09BER1 10PAR2 21PAR3 21BER4 27PAR3 29BER1 29VIE2",
    "202409": "02AMS1 02AMS2 04PAR1 04BER1 06AMS1 06VIE2 13ZRH1 18ZRH4 27PAR1",
    "202410": "02AMS2 08ZRH3 12BER1 13BER1 14AMS1 14BER2 14ZRH5 20VIE1 21AMS2 31VIE3",
    "202411": "01BER2 04PAR1 04ZRH1 13AMS1 13VIE3 17PAR1 20BER4 22AMS1 28PAR1",
    "202412": "02PAR1 05PAR2 09PAR3 12PAR1 13ZRH5 19AMS3 19AMS4 19VIE3 20ZRH4 25PAR2",
}


def dropped_shipment_ids():
    return {"SHP-%s-%06d" % (month, int(seq))
            for month, seqs in DROPPED_SHIPMENTS.items() for seq in seqs.split()}


def dropped_route_ids():
    return {"RTE-%s-%s%s-%03d" % (code[2:5], month, code[:2], int(code[5:]))
            for month, codes in DROPPED_ROUTES.items() for code in codes.split()}


def load(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="") as fh:
        return list(csv.DictReader(fh))


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
    with open(os.path.join(SEEDS, name + ".csv"), "ab") as fh:
        fh.write(block)


def month_days(year, month):
    d = datetime.date(year, month, 1)
    out = []
    while d.month == month:
        out.append(d)
        d += datetime.timedelta(days=1)
    return out


def weighted_choice(rng, items, weights):
    return rng.choices(items, weights=weights, k=1)[0]


def pick_datetime(rng, day):
    return datetime.datetime(day.year, day.month, day.day,
                             rng.randint(6, 20), rng.randint(0, 59), rng.randint(0, 59))


def with_promise(new_shipments):
    """The new rows plus the promise columns scripts/generate_promised_delivery.py
    gives them, from its own build() over the existing rows and the full block."""
    sys.path.insert(0, HERE)
    import generate_promised_delivery as pd
    with open(os.path.join(SEEDS, "shipments.csv"), newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        keep = [header.index(c) for c in pd.BASE_COLUMNS]
        existing = [[r[i] for i in keep] for r in reader if r[header.index("created_at")][:4]
                    not in BLOCK_YEARS]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows([pd.BASE_COLUMNS] + existing + new_shipments)
    _, rows = pd.build(buf.getvalue())
    promise = {r["shipment_id"]: new for r, new in rows}
    return [s + promise[s[0]] for s in new_shipments]


def main():
    rng = random.Random(SEED)

    # Inputs without this block's own rows (present on a re-run).
    existing_routes = [r for r in load("routes") if r["service_date"][:4] not in BLOCK_YEARS]
    drivers = [d for d in load("drivers")
               if int(d["driver_id"].split("-")[1]) < FIRST_DRIVER]
    vehicles = [v for v in load("vehicles")
                if int(v["vehicle_id"].split("-")[1]) < FIRST_VEHICLE]

    # ---- driver / vehicle pools by hub (hire_date respected later per route day) ----
    drivers_by_hub = collections.defaultdict(list)
    for d in drivers:
        drivers_by_hub[d["hub_id"]].append(d)
    active_veh_by_hub = collections.defaultdict(list)
    for v in vehicles:
        if v["status"] == "active":
            active_veh_by_hub[v["hub_id"]].append(v)

    # ---- a few new drivers / vehicles so the prior years are staffed (ids continue) ----
    new_drivers = []
    drv_plan = [("HUB-AMS", "contractor", "2022-09-14", "4.10"),
                ("HUB-PAR", "contractor", "2023-03-19", "4.35"),
                ("HUB-BER", "employee",   "2023-08-07", "4.02"),
                ("HUB-ZRH", "contractor", "2024-01-22", "4.28"),
                ("HUB-VIE", "contractor", "2024-04-11", "4.16"),
                ("HUB-AMS", "employee",   "2024-07-30", "3.88")]
    for i, (hub, emp, hire, perf) in enumerate(drv_plan):
        new_drivers.append({"driver_id": "DRV-%05d" % (FIRST_DRIVER + i), "hub_id": hub,
                            "employment_type": emp, "hire_date": hire,
                            "status": "active", "perf_score": perf})
    new_vehicles = []
    veh_plan = [("HUB-AMS", "van", "58920"), ("HUB-PAR", "box_truck", "41250"),
                ("HUB-BER", "box_truck", "77310"), ("HUB-VIE", "van", "33180")]
    for i, (hub, typ, odo) in enumerate(veh_plan):
        new_vehicles.append({"vehicle_id": "VEH-%04d" % (FIRST_VEHICLE + i), "hub_id": hub,
                             "type": typ, "status": "active", "odometer": odo})

    for d in new_drivers:
        drivers_by_hub[d["hub_id"]].append(d)
    for v in new_vehicles:
        active_veh_by_hub[v["hub_id"]].append(v)

    # ---- routes index (existing + generated), keyed by (hub, service_date) ----
    routes_by_hub_date = collections.defaultdict(list)

    def idx_route(route_id, hub, date):
        routes_by_hub_date[(hub, date)].append(route_id)

    for r in existing_routes:
        idx_route(r["route_id"], r["hub_id"], r["service_date"])

    all_new = {"shipments": [], "routes": [], "incidents": []}
    ams_damage_days = []          # persisted across years: keep the 2025 bay-3 pattern unique

    for year in (2023, 2024):
        # ---------------------------------------------------------------- routes
        for month in range(1, 13):
            days = month_days(year, month)
            target = MONTH_RTE[month]
            weights = [WEEKDAY_WEIGHT[d.weekday()] for d in days]
            day_counts = collections.Counter(rng.choices(days, weights=weights, k=target))
            for day in days:
                n = day_counts.get(day, 0)
                if n == 0:
                    continue
                date_s = day.isoformat()
                picks = [weighted_choice(rng, HUBS, [1, 1, 1, 1, 1]) for _ in range(n)]
                per_hub = collections.Counter(picks)
                for hub in HUBS:
                    k = per_hub.get(hub, 0)
                    if not k:
                        continue
                    pool = [d for d in drivers_by_hub[hub] if d["hire_date"] <= date_s]
                    vpool = active_veh_by_hub[hub]
                    for seq in range(1, k + 1):
                        drv = rng.choice(pool)
                        veh = rng.choice(vpool)
                        stops = rng.randint(18, 65)
                        exc = 0 if rng.random() < 0.815 else rng.randint(1, 6)
                        status = weighted_choice(rng, ["completed", "partial", "canceled"],
                                                 [3237, 364, 28])
                        route_id = "RTE-%s-%s-%03d" % (hub.split("-")[1],
                                                       day.strftime("%Y%m%d"), seq)
                        all_new["routes"].append(
                            [route_id, hub, drv["driver_id"], veh["vehicle_id"],
                             date_s, str(stops), str(exc), status])
                        idx_route(route_id, hub, date_s)

        # ------------------------------------------------------------ shipments
        ship_by_hub_date = collections.defaultdict(list)
        year_ships = []
        for month in range(1, 13):
            days = month_days(year, month)
            target = MONTH_SHP[month]
            weights = [WEEKDAY_WEIGHT[d.weekday()] for d in days]
            for seq, day in enumerate(rng.choices(days, weights=weights, k=target), start=1):
                created = pick_datetime(rng, day)
                client = weighted_choice(rng, CLIENTS, CLIENT_WEIGHTS)
                hub = weighted_choice(rng, HUBS, [1, 1, 1, 1, 1])
                level = weighted_choice(rng, SERVICE_LEVELS, SERVICE_WEIGHTS)
                # route reference ~79% of the time, service date 0-3 days after creation
                route_id = ""
                if rng.random() < 0.79:
                    delta = weighted_choice(rng, [0, 1, 2, 3], [1278, 232, 72, 6])
                    for d2 in (delta, 0, 1, 2, 3):
                        cand = routes_by_hub_date.get((hub, (day + datetime.timedelta(days=d2)).isoformat()))
                        if cand:
                            route_id = rng.choice(cand)
                            break
                sid = "SHP-%04d%02d-%06d" % (year, month, seq)
                year_ships.append({"shipment_id": sid, "client_id": client,
                                   "origin_hub_id": hub, "service_level": level,
                                   "created_at": created.strftime("%Y-%m-%dT%H:%M:%S"),
                                   "route_id": route_id, "_day": day})
                ship_by_hub_date[(hub, day.isoformat())].append(sid)

        # assign statuses to hit the per-client on-time baseline exactly
        if year == 2023:
            miss_rate = {"CLI-0042": 0.020, "CLI-0007": 0.026, "CLI-0155": 0.025,
                         "CLI-0169": 0.027, "CLI-0201": 0.027}
        else:
            miss_rate = {"CLI-0042": 0.020, "CLI-0007": 0.030, "CLI-0155": 0.028,
                         "CLI-0169": 0.031, "CLI-0201": 0.031}
        by_client = collections.defaultdict(list)
        for s in year_ships:
            by_client[s["client_id"]].append(s)
        for client, rows in by_client.items():
            n_miss = round(len(rows) * miss_rate[client])
            miss_idx = set(rng.sample(range(len(rows)), n_miss))
            for i, s in enumerate(rows):
                if i in miss_idx:
                    s["status"] = weighted_choice(rng, [m[0] for m in MISS_SPLIT],
                                                  [m[1] for m in MISS_SPLIT])
                else:
                    s["status"] = "delivered"
        for s in year_ships:
            created = datetime.datetime.strptime(s["created_at"], "%Y-%m-%dT%H:%M:%S")
            if s["status"] == "delivered":
                lag = weighted_choice(rng, list(DELIVERED_LAG_W), list(DELIVERED_LAG_W.values()))
                delivered = (created + datetime.timedelta(days=lag)).strftime("%Y-%m-%dT%H:%M:%S")
            elif s["status"] == "delayed":
                lag = weighted_choice(rng, list(DELAYED_LAG_W), list(DELAYED_LAG_W.values()))
                delivered = (created + datetime.timedelta(days=lag)).strftime("%Y-%m-%dT%H:%M:%S")
            else:
                delivered = ""
            all_new["shipments"].append([s["shipment_id"], s["client_id"],
                                         s["origin_hub_id"], s["service_level"],
                                         s["created_at"], delivered, s["status"], s["route_id"]])

        # ------------------------------------------------------------ incidents
        inc_target = 100 if year == 2023 else 110
        days = [d for m in range(1, 13) for d in month_days(year, m)]
        weights = [WEEKDAY_WEIGHT[d.weekday()] for d in days]
        seq = 0
        for day in rng.choices(days, weights=weights, k=inc_target):
            seq += 1
            hub = weighted_choice(rng, HUBS, [1, 1, 1, 1, 1])
            itype = weighted_choice(rng, INC_TYPES, INC_TYPE_W)
            # The 2025 story has a recurring handling-damage cluster at HUB-AMS (bay 3).
            # Never let 2023/2024 pre-empt it: no two Amsterdam damage incidents within
            # 90 days of each other in the prior years.
            if itype == "damage" and hub == "HUB-AMS":
                if any(abs((day - d).days) < 90 for d in ams_damage_days):
                    itype = weighted_choice(rng, ["delay", "mispick", "accident"], [0.5, 0.3, 0.2])
            if itype == "damage" and hub == "HUB-AMS":
                ams_damage_days.append(day)
            sev = weighted_choice(rng, INC_SEV, INC_SEV_W)
            if itype == "weather":
                sev = min(sev, 3)
            occurred = pick_datetime(rng, day)
            route_id = driver_id = vehicle_id = shipment_id = ""
            if rng.random() < 0.68:
                for off in (0, 1, -1, 2, -2):
                    cands = routes_by_hub_date.get(
                        (hub, (day + datetime.timedelta(days=off)).isoformat()))
                    if cands:
                        route_id = rng.choice(cands)
                        break
                if route_id:
                    rm = next((r for r in all_new["routes"] if r[0] == route_id), None)
                    if rm:
                        driver_id, vehicle_id = rm[2], rm[3]
            if rng.random() < 0.47:
                for off in (0, 1, -1, 2, -2):
                    cands = ship_by_hub_date.get(
                        (hub, (day + datetime.timedelta(days=off)).isoformat()))
                    if cands:
                        shipment_id = rng.choice(cands)
                        break
            if rng.random() < 0.10:
                summary = ("%s at the %s hub disrupted %s routes; %s resolved within the week."
                           % (itype.capitalize(), HUB_CITY[hub],
                              rng.randint(1, 4), rng.choice(["driver recovered", "vehicle swapped",
                                                             "load re-sequenced"])))
            else:
                summary = "%s event (severity %d) at %s." % (itype.capitalize(), sev, HUB_CITY[hub])
            iid = "INC-%d-%05d" % (year, seq)
            all_new["incidents"].append([iid, itype, str(sev), shipment_id, route_id,
                                         driver_id, vehicle_id, hub, occurred.strftime("%Y-%m-%dT%H:%M:%S"),
 summary])

    # ------------------------------------------- later revisions (see docstring)
    shipments_out = all_new["shipments"]
    with open(os.path.join(SEEDS, "shipments.csv"), newline="") as fh:
        ship_header = next(csv.reader(fh))
    if "promised_delivery_at" in ship_header:
        shipments_out = with_promise(all_new["shipments"])
    gone = dropped_shipment_ids()
    shipments_out = [r for r in shipments_out if r[0] not in gone]
    gone = dropped_route_ids()
    routes_out = [r for r in all_new["routes"] if r[0] not in gone]

    # -------------------------------------------------------------------- write
    out = [
        ("drivers", [[d["driver_id"], d["hub_id"], d["employment_type"],
                      d["hire_date"], d["status"], d["perf_score"]] for d in new_drivers]),
        ("vehicles", [[v["vehicle_id"], v["hub_id"], v["type"],
                       v["status"], v["odometer"]] for v in new_vehicles]),
        ("shipments", shipments_out),
        ("routes", routes_out),
        ("incidents", all_new["incidents"]),
    ]
    # Check every file before writing any, so a re-run is a clean no-op and a partial
    # state is refused rather than topped up.
    blocks = [(name, build_block(rows)) for name, rows in out]
    present = [block_present(name, rows, block) for (name, rows), (_, block) in zip(out, blocks)]
    if all(present):
        print("already present: each block is its file's tail, byte for byte; nothing written")
        return
    if any(present):
        raise RuntimeError("only some blocks are present (%s); refusing to append"
                           % ", ".join(n for (n, _), p in zip(out, present) if p))
    for name, block in blocks:
        append_block(name, block)

    print("added shipments", len(shipments_out),
          "routes", len(routes_out),
          "incidents", len(all_new["incidents"]),
          "drivers", len(new_drivers), "vehicles", len(new_vehicles))


if __name__ == "__main__":
    main()
