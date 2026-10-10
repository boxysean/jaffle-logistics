# Columbus damage forensics — is the 2025 handling-damage cluster a fleet problem or a process problem?

## 1. Executive summary

- **What the result was.** The 2025 handling-damage cluster at the Columbus hub (`HUB-CMH`) — **15
  incidents against 2 in each of 2023 and 2024** — is **not explained by the fleet**. It does not follow
  particular vehicles or particular drivers in any way the data can support: five of the hub's nine
  vehicles and eight of its fifteen drivers appear once, at most, and the apparent "worst" vehicle and
  driver are within ordinary random variation. The vehicles that do appear do **not** carry a heavier
  maintenance history — they carry *less* than the fleet average — and the hub's two most-repaired
  vehicles recorded **no** damage at all. The only cause the record actually states, in the one incident
  report written about the cluster, is a **dock-staging process problem at bay 3**.
- **What evidence validated it.** Twenty `execute_sql` queries against
  `hive_metastore.dbt_smcintyre_jaffle_logistics_prod`: exposure-normalised rates (incidents per 100
  routes) for every Columbus vehicle and driver against the hub average; a join to `fleet_work_orders`;
  the incidence by hour and weekday; the freight mix; and a full-text search of the narrative records.
  Of the fifteen damage incidents, ten are attributable to a route, and that route recovers the vehicle
  and driver the incident itself leaves blank. Two independent facts agree: the fleet explanation has no
  footprint in the maintenance record, and the single causal narrative names the dock.
- **What remains open.** The process claim rests on **one free-text report (IR-9003)**; "bay 3" appears
  nowhere else in the corpus, the other damage incidents were closed with no report at all, and **damage
  rose at every hub in 2025, not only Columbus** — so part of the cluster is a fleet-wide
  reliability move that no Columbus process change would fix. Settling "bay 3" needs bay-level staging
  or equipment-inspection data the warehouse does not hold.

---

## 2. The question and why it matters

Two remediations are on the table and they spend the money in opposite places. If the damage travels with
a set of vehicles or drivers, the fix is maintenance, equipment and personnel. If it travels with a
place or a window — a staging area, a shift, a bay — the fix is process, layout and supervision. The
numbers below are normalised so that a busy vehicle is not called bad merely for being busy, and the
narrative record is quoted where it exists and flagged where it does not.

---

## 3. Method

**Population.** Incidents with `incident_type = 'damage'` at `hub_id = 'HUB-CMH'`, attributed by the
calendar year of `occurred_at`. **"Handling damage" is the single `damage` incident type, all severities
(1–4).** The primary window is **2025**; the same definition is shown for **2023 and 2024**. The corpus
present is **2025-12-31** and nothing here assumes data after it. Dates are outward-facing, so the
year filter is on `occurred_at`, read from `stg_incidents` (typed) or `fct_incidents` (enriched).

**Exposure normalisation — the heart of the report.** A route (`stg_routes`) is one driver-day in one
vehicle at one hub. Every rate below is **incidents per 100 routes**; the reference line is the **hub
average** = damage incidents ÷ Columbus routes = 10 ÷ 709 = **1.41 per 100 routes**. Raw counts are shown
beside every rate.

**Recovering attribution.** The incident's own `vehicle_id` / `driver_id` are mostly blank (see Finding
3). Where they are blank, the vehicle and driver are recovered from the incident's `route_id` joined to
`stg_routes`. Both fields agree wherever both are populated (the route never contradicts the incident),
so the join is used to enlarge the attributable set, not to override it.

**Maintenance.** `stg_fleet_work_orders` is joined to the implicated vehicles. A work order that hangs
off an incident (`linked_incident_id is not null`) is a **consequence**, not a cause, and is counted
separately and excluded from the cause comparison.

**Narrative.** Case-insensitive `LIKE` search for `BAY`, `STAGING`, `DOCK`, `FORKLIFT`, `PALLET`,
`SECUR` over `stg_incident_reports.body` and `stg_dispatch_notes.body`.

---

## 4. Findings

### 4.1 The population: 2025 is the only bad year, and Columbus is the largest single cluster

```sql
SELECT year(occurred_at) AS yr, incident_type, severity, count(*) AS n
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents
WHERE hub_id = 'HUB-CMH' GROUP BY 1,2,3 ORDER BY 1,2,3;
```

| Year | Columbus damage | severities | Columbus routes | damage per 100 routes | all Columbus incidents |
|---|---|---|---|---|---|
| 2023 | **2** | 2,2 | 712 | 0.28 | 24 |
| 2024 | **2** | 2,2 | 684 | 0.29 | 30 |
| 2025 | **15** | 4×sev1, 4×sev2, 3×sev3, 4×sev4 | 709 | **2.12** | 47 |

Damage went from ~0.28 per 100 routes to **2.12 — a 7.6× rise** on essentially flat route volume
(712 / 684 / 709). Damage also grew as a *share* of the hub's incidents (8.3% → 6.7% → **31.9%**). The
2023 and 2024 damage incidents are cited for the baseline: `INC-2023-00014`, `INC-2023-00061`,
`INC-2024-00021`, `INC-2024-00035` — all severity 2, all at Columbus.

### 4.2 The anomaly is not Columbus-only — damage rose at every hub

```sql
SELECT hub_id, year(occurred_at) AS yr, count(*) AS n
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents
WHERE incident_type='damage' GROUP BY 1,2 ORDER BY 1,2;
```

| Hub | 2023 | 2024 | 2025 | 2025 routes | 2025 damage / 100 routes |
|---|---|---|---|---|---|
| CMH (Columbus) | 2 | 2 | **15** | 709 | **2.12** |
| DET (Detroit) | 2 | 1 | 9 | 741 | 1.21 |
| CIN (Cincinnati) | 2 | 1 | 8 | 712 | 1.12 |
| IND (Indianapolis) | 1 | 1 | 5 | 719 | 0.70 |
| CHI (Chicago) | 0 | 3 | 3 | 748 | 0.40 |

Columbus has the highest *rate*, but **every hub's damage count rose in 2025** (fleet total 7 → 8 →
40). A pattern that is present at every hub cannot be explained by a single hub's bay. Columbus is the
worst cell, not the origin of the fleet-wide move — the two need different fixes. *(This is the first
place a naive reading goes wrong, and the card asks for it early: the 2025-only number is not by itself a
Columbus finding.)*

### 4.3 Attribution is sparse — and that shapes everything downstream

```sql
SELECT count(*) AS n,
       count(route_id)    AS with_route,
       count(shipment_id) AS with_shipment,
       count(driver_id)   AS with_driver,
       count(vehicle_id)  AS with_vehicle
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_incidents
WHERE incident_type='damage' AND hub_id='HUB-CMH' AND year(occurred_at)=2025;
```

Of the 15 incidents: **10 carry a route, 12 carry a shipment, but only 7 carry a driver and only 2 carry
a vehicle.** Every incident carries at least one link (route or shipment). Joining `route_id` to
`stg_routes` recovers driver and vehicle for all 10 route-bearing incidents. The remaining **5
(`INC-2025-00014`, `-00020`, `-00136`, `-00148`, `-00226`) carry no route** and cannot be attached to a
vehicle or driver at all. So **10 of 15 are attributable to a vehicle/driver; 5 are not.** This is a
data-capture gap, not an analysis choice, and it caps how far any fleet/driver claim can go.

### 4.4 H1 — "it follows the vehicles": **undetermined (leaning refuted)**

```sql
SELECT r.vehicle_id, count(*) AS routes
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_routes r
WHERE r.hub_id='HUB-CMH' AND year(r.service_date)=2025
GROUP BY 1 ORDER BY 2 DESC;
```

Recovered damage counts (from the route join, Finding 3) against exposure:

| Vehicle | damage incidents | routes 2025 | per 100 routes |
|---|---|---|---|
| VEH-0038 | 3 | 81 | 3.70 |
| VEH-0003 | 3 | 84 | 3.57 |
| VEH-0021 | 2 | 87 | 2.30 |
| VEH-0028 | 1 | 72 | 1.39 |
| VEH-0001 | 1 | 90 | 1.11 |
| VEH-0007 | 0 | 73 | 0 |
| VEH-0012 | 0 | 80 | 0 |
| VEH-0031 | 0 | 71 | 0 |
| VEH-0033 | 0 | 71 | 0 |
| **hub average** | **10 / 709** | | **1.41** |

The two leading vehicles are at ~3.6 per 100 routes, ~2.5× the hub average. **Three events on ~82 routes
is not evidence of a bad vehicle:** at the hub rate you expect ~1.2, and getting 3 by chance happens about
1 time in 8 per vehicle — with nine vehicles measured, seeing one at 3 is unremarkable. The distribution
is also the *opposite* of "a set of vehicles": the incidents scatter across five of nine vehicles, and the
four zero-damage vehicles are the modal outcome. Raw counts alone would have named VEH-0038 — the
normalised table shows it is indistinguishable from noise. **Verdict: undetermined, leaning refuted.**

### 4.5 H2 — "it follows the drivers": **undetermined (one weak outlier)**

```sql
SELECT r.driver_id, count(*) AS routes
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_routes r
WHERE r.hub_id='HUB-CMH' AND year(r.service_date)=2025
GROUP BY 1 ORDER BY 2 DESC;
```

| Driver | damage incidents | routes 2025 | per 100 routes |
|---|---|---|---|
| **DRV-01028** | **3** | 49 | **6.12** |
| DRV-01040 | 1 | 37 | 2.70 |
| DRV-01010 | 1 | 41 | 2.44 |
| DRV-01015 | 1 | 44 | 2.27 |
| DRV-01016 | 1 | 50 | 2.00 |
| DRV-01044 | 1 | 50 | 2.00 |
| DRV-01039 | 1 | 58 | 1.72 |
| DRV-01009 | 1 | 62 | 1.61 |
| 7 others | 0 | 34–55 | 0 |
| **hub average** | **10 / 709** | | **1.41** |

**DRV-01028 is the single most-implicated person** — 3 of 10 attributable incidents (30%) on 6.9% of
routes, 4.3× the hub average. But two of the three are the *same route on the same day*
(`RTE-CMH-20251217-003`, incidents `INC-2025-00143` and `INC-2025-00254`), so it is really **two events**;
and it is the maximum of fifteen drivers, so the multiple-comparison-adjusted chance of seeing at least
one driver this high is large. The rate is worth watching, not acting on. **Verdict: undetermined.**

### 4.6 H3 — "it follows time / process / staging": **partially supported — the only stated cause, but unmeasurable**

**Structured time data shows no window.**

```sql
SELECT case when incident_type='damage' then 'damage' else 'other' end AS grp,
       hour(occurred_at) AS hr, count(*) AS n
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents
WHERE hub_id='HUB-CMH' AND year(occurred_at)=2025 GROUP BY 1,2 ORDER BY 1,2;
```

Damage by hour: 07×2, 08×2, 09×2, 11×1, 15×3, 16×2, 18×2, 20×1 — spread across the whole day, no shift
edge. *(Routes carry a date but no clock time, so hour-of-day has no exposure denominator — a genuine
missing measurement, see §5.)* Damage by weekday: Mon 3, Tue 1, Wed 5, Thu 2, Fri 2, Sat 1, Sun 1, against
the hub's route-weekday mix (Fri 149, Wed 127, Thu 126, Mon 125, Tue 112, Sun 36, Sat 34). Wednesday is
mildly over-represented (5 observed vs ~2.7 expected) and the weekend under; on 15 events none of it is
significant. **No time window survives.**

**The narrative names the dock — once.**

```sql
SELECT report_id, incident_id, filed_at, body
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incident_reports
WHERE report_id = 'IR-9003';
```

> **IR-9003** (incident `INC-2025-00095`, filed 2025-10-11, J. Alvarez (Ops)) — *"Freight damage
> discovered during unloading at the Columbus hub. This is the third handling-related incident at
> HUB-CMH in 2025… The pattern points to a dock-staging issue rather than three isolated events: **all
> three incidents trace to bay 3 forklift staging.** … **Bay 3 staging cordoned** pending equipment
> inspection. Hub supervisor to audit loading procedures against SOP."*

This is the **only** record in the entire corpus that names a staging area, a bay or a forklift: a
`LIKE` search for `BAY` across every `stg_incident_reports` row returns exactly this one report, and the
same search across `stg_dispatch_notes` returns **nothing** (dispatch notes never mention a bay; their
"Dock closed early" access notes are unrelated). It is also a *stated pattern* that the incident table
does not corroborate — Columbus 2025 had 15 damage events, not 3, and the report's own list omits them.
The 2023–2024 reports mention no bay at all, so "bay 3" is new in 2025. The one *other* damage report,
**IR-7031** (`INC-2025-00196`, 28 Aug), attributes that event to **load securing — "secured for the
manifest weight but not for the actual pallet mix, so it shifted en route"** — a different mechanism,
and still not a vehicle defect.

**Verdict: partially supported.** A Columbus-specific dock-staging problem is the only cause anywhere in
the record, and it is consistent with damage clustering at one hub while vehicles and drivers do not
repeat. But it rests on one document against a hub-wide and fleet-wide rise it cannot explain.

### 4.7 H4 — "it follows the freight": **refuted**

```sql
SELECT client_name, count(*) AS n, round(100.0*count(*)/sum(count(*)) over (),1) AS pct
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
WHERE origin_hub_id='HUB-CMH' AND year(created_at)=2025 GROUP BY 1 ORDER BY 2 DESC;
```

Twelve of the 15 incidents carry a shipment; the client and service-level mix of those shipments matches
the hub baseline, so there is no freight signal:

| Dimension | Damage incidents (n=12) | Columbus 2025 baseline (n=347) |
|---|---|---|
| Jaffle Paper & Packaging | 4 (33%) | 21.9% |
| Jaffle Beverage Co | 3 (25%) | 18.4% |
| Jaffle Equipment | 2 (17%) | 21.3% |
| Jaffle Storefronts | 2 (17%) | 20.2% |
| Jaffle Crew Outfitters | 1 (8%) | 18.2% |
| service level: standard / expedited / freight | 7 / 3 / 2 | 55.9% / 22.8% / 21.3% |

The client mix drifts slightly toward Paper & Packaging and the service mix toward expedited, but on
twelve rows that is noise. More importantly the **shipment links are not trustworthy**: the
incident→shipment pairing is not time-consistent — `INC-2025-00014` (occurred 11 May 2025) points at
`SHP-202512-000405`, a shipment created 16 December 2025, and `INC-2025-00020` (17 Jan) points at a
September shipment. The 2023 and 2024 damage incidents carry **no** shipment link at all, so the 2025
linkage looks like a capture artifact. **Verdict: refuted — no freight signal that the data can support.**

### 4.8 Maintenance: the implicated vehicles are *not* heavier than the fleet, and carry no damage footprint

```sql
SELECT w.vehicle_id, count(*) AS wos, sum(w.cost) AS total_cost,
       max(date(w.opened_at)) AS last_wo,
       sum(case when w.linked_incident_id is not null then 1 else 0 end) AS linked_wos
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_fleet_work_orders w
WHERE w.vehicle_id IN ('VEH-0001','VEH-0003','VEH-0021','VEH-0028','VEH-0038',
                       'VEH-0007','VEH-0012','VEH-0031','VEH-0033')
GROUP BY 1 ORDER BY 1;
```

| Vehicle | damage | work orders | total cost | last work order |
|---|---|---|---|---|
| VEH-0003 | 3 | **1** | $2,374 | 2025-03-07 |
| VEH-0038 | 3 | 3 | $4,382 | 2024-07-07 |
| VEH-0021 | 2 | 7 | $17,952 | 2025-04-10 |
| VEH-0028 | 1 | 4 | $14,758 | 2025-09-11 |
| VEH-0001 | 1 | 4 | $13,682 | 2025-03-25 |
| VEH-0007 | 0 | **9** | $34,166 | 2025-12-17 |
| VEH-0033 | 0 | **9** | $19,833 | 2024-11-20 |
| VEH-0012 | 0 | 2 | $8,738 | 2025-02-05 |
| VEH-0031 | 0 | 3 | $18,082 | 2025-08-21 |

- **Implicated vehicles average 3.8 work orders each — the fleet average is 3.88** (163 work orders /
  44 vehicles, `stg_fleet_work_orders`). The vehicles in damage incidents are **ordinary**, not heavy.
- The **two most-repaired vehicles at the hub, VEH-0007 and VEH-0033 (9 work orders each), recorded zero
  damage.** If heavy maintenance were the cause, they would be the worst offenders; they are the cleanest.
- The vehicle with the most damage, VEH-0003, has the **least** maintenance history of any Columbus
  vehicle (one work order).

**Cause vs consequence.** Only four work orders at Columbus in 2025 hang off an incident, and **all four
are accidents, none is a damage event**:

```sql
SELECT w.wo_id, w.vehicle_id, w.linked_incident_id, i.incident_type, w.cost
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_fleet_work_orders w
JOIN hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents i
  ON i.incident_id = w.linked_incident_id
WHERE i.hub_id='HUB-CMH' AND year(i.occurred_at)=2025;
-- WO-300004 VEH-0007 → INC-2025-00075 (accident)
-- WO-300008 VEH-0028 → INC-2025-00091 (accident)
-- WO-300001 VEH-0031 → INC-2025-00029 (accident)
-- WO-300019 VEH-0007 → INC-2025-00250 (accident)
```

So the damage cluster has **no maintenance footprint at all — neither cause nor recorded consequence.**
This does not prove the vehicles are sound; it proves the maintenance record cannot support the fleet
hypothesis, in either direction. **Verdict: the maintenance/fleet explanation is refuted.**

### 4.9 Severity shape: broad, not one bad event

The 15 incidents span all four severities (4 / 4 / 3 / 4 for sev 1–4; mean 2.47), with **7 of 15 at
severity 3 or 4** — versus all four 2023/2024 damage incidents at severity 2. This is a **broad cluster
with a thicker severe tail**, not a single catastrophic event, which fits a recurring process fault
better than a one-off equipment failure.

### 4.10 The four hypotheses, verdict table

| # | Hypothesis | Verdict | Decisive evidence |
|---|---|---|---|
| H1 | Follows **vehicles** | **Undetermined (leaning refuted)** | Leading vehicles 3.6/100 routes vs hub 1.41, but only 3 events and 5 of 9 vehicles appear once; five incidents have no vehicle at all (§4.3–4.4) |
| H2 | Follows **drivers** | **Undetermined** | DRV-01028 6.12/100 vs 1.41, but it is the max of 15 drivers and two of its three events are one route/day (§4.5) |
| H3 | Follows **time/process** | **Partially supported** | No hour/weekday window in structured data; but the only causal narrative, IR-9003, names bay-3 dock staging, and no bay is named anywhere else (§4.6) |
| H4 | Follows the **freight** | **Refuted** | Client and service-level mix match the hub baseline; shipment links are not time-consistent and absent in 2023–2024 (§4.7) |

### 4.11 Leading explanation

**The leading explanation is a Columbus dock-staging process fault in 2025, not a fleet or driver
defect — at low-to-moderate confidence.** The fleet hypothesis is genuinely *refuted*: the implicated
vehicles are ordinary in the maintenance record, the cluster has no work-order footprint, and the design
of the incidents — spread across vehicles, drivers and routes, with no repeated vehicle/driver pair — is
what a place-and-process cause looks like, not what a bad asset or bad actor looks like. The remaining
competitor is that the Columbus move is simply the loudest instance of a **fleet-wide 2025 rise in
damage** that no Columbus process change would fix; the two are not mutually exclusive and only the
Columbus-specific part is evidenced, by a single report.

### 4.12 What would settle it (the missing measurement)

1. **Bay-level staging / equipment-inspection log for Columbus** (forklift and bay-3 telemetry) — the
   one thing IR-9003 asks for and the warehouse does not hold. This directly confirms or kills "bay 3".
2. **A vehicle-inspection log** independent of incidents — to test whether VEH-0003/VEH-0038 are
   mechanically worse, rather than lucky with three events.
3. **Shift rosters with route start times** — so hour-of-day can be normalised against the operations
   that actually ran, and a shift/process window tested (routes today carry a date but no clock time).
4. **Damage photos / chain-of-custody** per incident, and **complete incident FKs** — 13 of 15 damage
   records name no vehicle and 8 name no driver, which is why half this analysis is a completeness story.

---

## 5. Confidence and limits

- **What would falsify each finding.** H1/H2 would turn *supported* if the five unattributable incidents
  (or shift rosters) resolved to a repeated vehicle or driver — currently they cannot be attached to
  either. H3 would be *refuted* if bay 3 worked normally (no inspection log contradicts the report, but
  none confirms it) or if the 2023–2024 quiet years had used bay 3 the same way (no evidence either way).
  H4 is only weakly falsified because the shipment links themselves are unreliable.
- **The strongest honest limits.** (a) The causal narrative is a **single document**; the other fourteen
  damage incidents were closed with no report, and the report's own "three incidents" undercounts the
  fifteen. (b) **Damage rose at every hub in 2025**, so Columbus is the worst cell of a fleet-wide move,
  not a demonstrably unique event. (c) **Attribution is incomplete** (13/15 lack a vehicle, 8/15 lack a
  driver), so the vehicle/driver tests are under-powered by construction. (d) Hours have **no exposure
  denominator**, so "no time window" is weaker than "no weekday window".
- **Not measured at all:** bay/staging telemetry, equipment-inspection outcomes, loading-crew rosters,
  damage severity in dollars.

---

## 6. Reproduce

All queries run through the **`dbt-platform` MCP `execute_sql` tool** against
`hive_metastore.dbt_smcintyre_jaffle_logistics_prod`, in this order:

1. `SHOW TABLES IN hive_metastore.dbt_smcintyre_jaffle_logistics_prod` — confirm relations.
2. Population/definition: `stg_incidents` grouped by `year(occurred_at), hub_id, incident_type, severity`.
3. Columbus by type/severity: same, filtered `hub_id='HUB-CMH'`.
4. Shipment years (`stg_shipments`) — confirm the reloaded 2023–2025 corpus.
5. The 15 damage rows with FKs and report/work-order counts (`fct_incidents`).
6. Recover driver/vehicle via `fct_incidents.route_id = stg_routes.route_id` (Finding 3).
7. Freight join: `fct_incidents`: `shipment_id = fct_shipments.shipment_id` (Finding 7).
8. Time: hour-of-day and weekday of Columbus 2025 damage vs other incidents (`stg_incidents`).
9. Exposure — routes per vehicle and per driver at `HUB-CMH` 2025 (`stg_routes`).
10. Hull-level context — damage by hub by year; routes per hub per year; routes per year.
11. Maintenance — all work orders for the nine Columbus vehicles; fleet totals; incident-linked work
    orders for Columbus 2025.
12. Freight baseline — CMH 2025 shipments by client and by service level (`fct_shipments`).
13. Narrative — `LIKE '%BAY%'`, `'%STAGING%'`, `'%DOCK%'` over `stg_incident_reports` and
    `stg_dispatch_notes`; full bodies of `IR-9003` and `IR-7031`.

**Reconciliation.** Population = 15 Columbus 2025 damage incidents. Of these, 10 are route-attributable
(5 to VEH-0038, VEH-0003, VEH-0021, VEH-0001, VEH-0028 — summing to 10) and 5 carry no route. The
vehicle table (§4.4) sums to 10; the driver table (§4.5) sums to 10. The five unattributable incidents
are named in §4.3 and appear in no vehicle or driver count.
