#!/usr/bin/env python3
"""Deterministically extend the Jaffle Logistics operational backbone backwards in
time, adding the quiet years 2023 and 2024 to seeds/shipments.csv, routes.csv and
incidents.csv (plus a handful of drivers/vehicles so the prior years are staffed).

APPEND ONLY: the existing CSV bytes are read and re-written untouched; new rows are
appended after them. Every id continues the existing scheme and every foreign key
points at a row that exists (clients, hubs, drivers, vehicles, routes, shipments).

Story the numbers tell:
  * 2023: whole-book on-time ~97.5%, Jaffle Equipment (CLI-0042) ~98%
  * 2024: whole-book on-time ~97.2%, Jaffle Equipment (CLI-0042) ~98%
  * incidents are ordinary weather/mechanical only, milder than 2025, with no
    storm-scale event and no Columbus handling-damage cluster.
Nothing about 2025 is modified.
"""
import csv, io, os, random, datetime, collections

SEED = 20231001
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")

HUBS = ["HUB-CMH", "HUB-CHI", "HUB-IND", "HUB-DET", "HUB-CIN"]
HUB_CITY = {"HUB-CMH": "Columbus", "HUB-CHI": "Chicago", "HUB-IND": "Indianapolis",
            "HUB-DET": "Detroit", "HUB-CIN": "Cincinnati"}
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


def load(name):
    with open(os.path.join(SEEDS, name + ".csv"), newline="") as fh:
        return list(csv.DictReader(fh))


def append_rows(name, header, rows):
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


def main():
    rng = random.Random(SEED)

    existing_routes = load("routes")
    existing_ship = load("shipments")
    existing_inc = load("incidents")
    drivers = load("drivers")
    vehicles = load("vehicles")

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
    max_drv = max(int(d["driver_id"].split("-")[1]) for d in drivers)
    drv_plan = [("HUB-CMH", "contractor", "2022-09-14", "4.10"),
                ("HUB-CHI", "contractor", "2023-03-19", "4.35"),
                ("HUB-IND", "employee",   "2023-08-07", "4.02"),
                ("HUB-CIN", "contractor", "2024-01-22", "4.28"),
                ("HUB-DET", "contractor", "2024-04-11", "4.16"),
                ("HUB-CMH", "employee",   "2024-07-30", "3.88")]
    for i, (hub, emp, hire, perf) in enumerate(drv_plan, start=1):
        new_drivers.append({"driver_id": "DRV-%05d" % (max_drv + i), "hub_id": hub,
                            "employment_type": emp, "hire_date": hire,
                            "status": "active", "perf_score": perf})
    new_vehicles = []
    max_veh = max(int(v["vehicle_id"].split("-")[1]) for v in vehicles)
    veh_plan = [("HUB-CMH", "van", "58920"), ("HUB-CHI", "box_truck", "41250"),
                ("HUB-IND", "box_truck", "77310"), ("HUB-DET", "van", "33180")]
    for i, (hub, typ, odo) in enumerate(veh_plan, start=1):
        new_vehicles.append({"vehicle_id": "VEH-%04d" % (max_veh + i), "hub_id": hub,
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
    cmh_damage_days = []          # persisted across years: keep the 2025 bay-3 pattern unique

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
            # The 2025 story has a recurring handling-damage cluster at HUB-CMH (bay 3).
            # Never let 2023/2024 pre-empt it: no two Columbus damage incidents within
            # 90 days of each other in the prior years.
            if itype == "damage" and hub == "HUB-CMH":
                if any(abs((day - d).days) < 90 for d in cmh_damage_days):
                    itype = weighted_choice(rng, ["delay", "mispick", "accident"], [0.5, 0.3, 0.2])
            if itype == "damage" and hub == "HUB-CMH":
                cmh_damage_days.append(day)
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

    # -------------------------------------------------------------------- write
    append_rows("drivers", None, [[d["driver_id"], d["hub_id"], d["employment_type"],
                                   d["hire_date"], d["status"], d["perf_score"]]
                                  for d in new_drivers])
    append_rows("vehicles", None, [[v["vehicle_id"], v["hub_id"], v["type"],
                                    v["status"], v["odometer"]] for v in new_vehicles])
    append_rows("shipments", None, all_new["shipments"])
    append_rows("routes", None, all_new["routes"])
    append_rows("incidents", None, all_new["incidents"])

    print("added shipments", len(all_new["shipments"]),
          "routes", len(all_new["routes"]),
          "incidents", len(all_new["incidents"]),
          "drivers", len(new_drivers), "vehicles", len(new_vehicles))


if __name__ == "__main__":
    main()
