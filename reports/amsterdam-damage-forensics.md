# Amsterdam damage forensics — is the 2025 handling-damage cluster a fleet problem or a process problem?

## 1. Executive summary

- **What the result was.** The 2025 handling-damage cluster at the Amsterdam hub (`HUB-AMS`) — **15
  incidents against 2 in each of 2023 and 2024** — is **not explained by the fleet**. It does not follow
  particular vehicles or particular drivers in any way the data can support: five of the hub's nine
  vehicles and eight of its fifteen drivers appear at all, and the apparent "worst" vehicle and driver
  are within ordinary random variation. The vehicles that do appear carry an **ordinary** maintenance
  history, and the hub's two most-repaired vehicles recorded **no** damage at all. What the record does
  show is a **place**: **11 of the 15 damage events were found at bay 3**, a bay that recorded none in
  2023 or 2024, handles an ordinary share of the hub's freight, and whose average staging dwell rose from
  about 46 to 70 minutes in 2025. Fourteen of the fifteen incident reports name dock staging, and most
  name bay 3.
- **What evidence validated it.** `execute_sql` queries against
  `hive_metastore.dbt_smcintyre_jaffle_logistics_prod`: exposure-normalised rates (incidents per 100
  routes) for every Amsterdam vehicle and driver against the hub average; a join to `fleet_work_orders`;
  the incidence by hour and weekday; the freight mix; the bay-level dock record (`dock_bay_events`); and a
  full-text search of the narrative records. Of the fifteen damage incidents, ten are attributable to a
  route, and that route recovers the vehicle and driver the incident itself leaves blank. Three
  independent facts agree: the fleet explanation has no footprint in the maintenance record, the bay
  record puts the damage at one bay, and the incident reports name the same dock.
- **What remains open.** The bay record says *where*, not *why* — it shows longer staging at bay 3 but
  carries no equipment-inspection result. The incident-report record is **not internally clean**: five
  reports cite `IR-9003` although four of them were filed months before it, and `IR-9003` itself says the
  earlier incidents had no common-cause review while the earlier reports already describe one. And
  **damage rose at four of the five hubs in 2025, not only Amsterdam** — so part of the move is
  network-wide and no Amsterdam bay fix would touch it.

---

## 2. The question and why it matters

Two remediations are on the table and they spend the money in opposite places. If the damage travels with
a set of vehicles or drivers, the fix is maintenance, equipment and personnel. If it travels with a
place or a window — a staging area, a shift, a bay — the fix is process, layout and supervision. The
numbers below are normalised so that a busy vehicle is not called bad merely for being busy, and the
narrative record is quoted where it exists and flagged where it does not hold together.

---

## 3. Method

**Population.** Incidents with `incident_type = 'damage'` at `hub_id = 'HUB-AMS'`, attributed by the
calendar year of `occurred_at`. **"Handling damage" is the single `damage` incident type, all severities
(1–4).** The primary window is **2025**; the same definition is shown for **2023 and 2024**. The corpus
present is **2025-12-31** and nothing here assumes data after it. Dates are outward-facing, so the
year filter is on `occurred_at`, read from `stg_incidents` (typed) or `fct_incidents` (enriched).

**Exposure normalisation — the heart of the report.** A route (`stg_routes`) is one driver-day in one
vehicle at one hub. Every rate below is **incidents per 100 routes**; the reference line is the **hub
average** = attributable damage incidents ÷ Amsterdam routes = 10 ÷ 709 = **1.41 per 100 routes**. Raw
counts are shown beside every rate. For the bay test the exposure is the bay's own handling events
(staging, unloading and loading) in `dock_bay_events`.

**Recovering attribution.** The incident's own `vehicle_id` / `driver_id` are mostly blank (see Finding
3). Where they are blank, the vehicle and driver are recovered from the incident's `route_id` joined to
`stg_routes`. Both fields agree wherever both are populated (the route never contradicts the incident),
so the join is used to enlarge the attributable set, not to override it.

**Maintenance.** `stg_fleet_work_orders` is joined to the implicated vehicles. A work order that hangs
off an incident (`linked_incident_id is not null`) is a **consequence**, not a cause, and is counted
separately and excluded from the cause comparison.

**Place.** `dock_bay_events` records every staging, unloading, loading, inspection and delay event per
bay; a `damage_found` event carries the `incident_id` it belongs to.

**Narrative.** Case-insensitive `LIKE` search for `BAY`, `STAGING`, `DOCK`, `FORKLIFT`, `PALLET`,
`SECUR` over `stg_incident_reports.body` and `stg_dispatch_notes.body`.

---

## 4. Findings

### 4.1 The population: 2025 is the only bad year, and Amsterdam is the largest single cluster

```sql
SELECT year(occurred_at) AS yr, incident_type, severity, count(*) AS n
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents
WHERE hub_id = 'HUB-AMS' GROUP BY 1,2,3 ORDER BY 1,2,3;
```

| Year | Amsterdam damage | severities | Amsterdam routes | damage per 100 routes | all Amsterdam incidents |
|---|---|---|---|---|---|
| 2023 | **2** | 2,2 | 666 | 0.30 | 24 |
| 2024 | **2** | 2,2 | 666 | 0.30 | 30 |
| 2025 | **15** | 4×sev1, 4×sev2, 3×sev3, 4×sev4 | 709 | **2.12** | 47 |

Damage went from 0.30 per 100 routes to **2.12 — a 7× rise** on route volume up about 6%
(666 / 666 / 709). Damage also grew as a *share* of the hub's incidents (8.3% → 6.7% → **31.9%**). The
2023 and 2024 damage incidents are cited for the baseline: `INC-2023-00014`, `INC-2023-00061`,
`INC-2024-00021`, `INC-2024-00035` — all severity 2, all at Amsterdam.

### 4.2 The anomaly is not Amsterdam-only — damage rose at four of five hubs

```sql
SELECT hub_id, year(occurred_at) AS yr, count(*) AS n
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents
WHERE incident_type='damage' GROUP BY 1,2 ORDER BY 1,2;
```

| Hub | 2023 | 2024 | 2025 | 2025 routes | 2025 damage / 100 routes |
|---|---|---|---|---|---|
| AMS (Amsterdam) | 2 | 2 | **15** | 709 | **2.12** |
| VIE (Vienna) | 2 | 1 | 9 | 741 | 1.21 |
| ZRH (Zürich) | 2 | 1 | 8 | 712 | 1.12 |
| BER (Berlin) | 1 | 1 | 5 | 719 | 0.70 |
| PAR (Paris) | 0 | 3 | 3 | 748 | 0.40 |

Amsterdam has the highest *rate*, but **four of the five hubs' damage counts rose sharply in 2025**
(network total 7 → 8 → 40); only Paris held flat at 3. A rise present at four hubs cannot be explained
by a single hub's bay. Amsterdam is the worst cell, not the origin of the network-wide move — the two
need different fixes. *(This is the first place a naive reading goes wrong, and the card asks for it
early: the 2025-only number is not by itself an Amsterdam finding.)*

### 4.3 Attribution is sparse — and that shapes everything downstream

```sql
SELECT count(*) AS n,
       count(route_id)    AS with_route,
       count(shipment_id) AS with_shipment,
       count(driver_id)   AS with_driver,
       count(vehicle_id)  AS with_vehicle
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_incidents
WHERE incident_type='damage' AND hub_id='HUB-AMS' AND year(occurred_at)=2025;
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
WHERE r.hub_id='HUB-AMS' AND year(r.service_date)=2025
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
is not evidence of a bad vehicle:** at the hub rate you expect ~1.2, and getting 3 or more by chance
happens about 1 time in 9 per vehicle — with nine vehicles measured, seeing one at 3 is unremarkable. The
distribution is also the *opposite* of "a set of vehicles": the incidents scatter across five of nine
vehicles, and the four zero-damage vehicles are the modal outcome. Raw counts alone would have named
VEH-0038 — the normalised table shows it is indistinguishable from noise. **Verdict: undetermined,
leaning refuted.**

### 4.5 H2 — "it follows the drivers": **undetermined (one weak outlier)**

```sql
SELECT r.driver_id, count(*) AS routes
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_routes r
WHERE r.hub_id='HUB-AMS' AND year(r.service_date)=2025
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
(`RTE-AMS-20251217-003`, incidents `INC-2025-00143` and `INC-2025-00254`), so it is really **two events**;
and it is the maximum of fifteen drivers, so the multiple-comparison-adjusted chance of seeing at least
one driver this high is large. The rate is worth watching, not acting on. **Verdict: undetermined.**

### 4.6 H3 — "it follows time / process / staging": **supported — by place, not by time**

**Structured time data shows no window.**

```sql
SELECT case when incident_type='damage' then 'damage' else 'other' end AS grp,
       hour(occurred_at) AS hr, count(*) AS n
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents
WHERE hub_id='HUB-AMS' AND year(occurred_at)=2025 GROUP BY 1,2 ORDER BY 1,2;
```

Damage by hour: 07×2, 08×2, 09×2, 11×1, 15×3, 16×2, 18×2, 20×1 — spread across the whole day, no shift
edge. *(Routes carry a date but no clock time, so hour-of-day has no exposure denominator — a genuine
missing measurement, see §5.)* Damage by weekday: Mon 3, Tue 1, Wed 5, Thu 2, Fri 2, Sat 1, Sun 1, against
the hub's route-weekday mix (Fri 149, Wed 127, Thu 126, Mon 125, Tue 112, Sun 36, Sat 34). Wednesday is
mildly over-represented (5 observed vs ~2.7 expected) and the weekend sits at about its expected share
(2 observed vs ~1.5); on 15 events none of it is significant. **No time window survives.**

**The bay record shows a place.**

```sql
SELECT bay_id,
       count(*) FILTER (WHERE event_type IN ('staging','unloading','loading')) AS handling,
       round(avg(minutes_at_bay) FILTER (WHERE event_type='staging'),1)      AS avg_staging_min,
       count(*) FILTER (WHERE event_type='damage_found')                     AS damage
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.dock_bay_events
WHERE hub_id='HUB-AMS' AND year(event_at)=2025
GROUP BY 1 ORDER BY 1;
```

| Bay | handling events 2025 | avg staging dwell (min) | damage found | damage per 1,000 handling events |
|---|---|---|---|---|
| BAY-1 | 826 | 47.7 | 1 | 1.21 |
| BAY-2 | 720 | 46.4 | 1 | 1.39 |
| **BAY-3** | 801 | **69.9** | **11** | **13.73** |
| BAY-4 | 762 | 47.9 | 1 | 1.31 |
| BAY-5 | 865 | 47.5 | 1 | 1.16 |
| BAY-6 | 818 | 46.4 | 0 | 0 |

Every one of the 15 damage incidents has a `damage_found` bay event on the same day. **Eleven are at
bay 3**, which handles an ordinary share of the hub's freight (801 of 4,792 handling events) and so has
no volume excuse: its damage rate is roughly ten times any other bay's. Bay 3 is also new as a problem —
it recorded **no** damage in 2023 or 2024, when its staging dwell was 46.5 and 46.1 minutes, in line with
the other bays; in 2025 it rose to 69.9 while the other five stayed at 47.2. The four non-bay-3 events in
2025 (one each at bays 1, 2, 4 and 5) are close to the hub's 2023–2024 level of two a year.

**The narrative names the same dock — repeatedly.**

```sql
SELECT report_id, incident_id, filed_at, body
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incident_reports
WHERE report_id = 'IR-9003';
```

> **IR-9003** (incident `INC-2025-00095`, filed 2025-10-11, J. Alvarez (Ops)) — *"Freight damage
> discovered during unloading at the Amsterdam hub. This is the third handling-related incident at
> HUB-AMS in 2025… The pattern points to a dock-staging issue rather than three isolated events: **all
> three incidents trace to bay 3 forklift staging.** … **Bay 3 staging cordoned** pending equipment
> inspection. Hub supervisor to audit loading procedures against SOP."*

Every one of the fifteen 2025 damage incidents now has an incident report, and **fourteen of them name
dock staging** — a `LIKE` search for `BAY` returns exactly those fourteen reports and no others across
all 357 in the warehouse; the same search across `stg_dispatch_notes` returns **nothing** (dispatch notes
never mention a bay; their "dock" mentions are access notes, unrelated). The odd one out is **IR-7031**
(`INC-2025-00196`, 28 Aug), which attributes that event to **load securing — "secured for the manifest
weight but not for the actual pallet mix, so it shifted en route"** — a different mechanism, and still
not a vehicle defect.

The reports do not hold together as a timeline, and that matters for how much weight they carry on
their own. Four reports filed **before** `IR-9003` (`IR-7266` 20 Mar, `IR-7268` 28 Mar, `IR-7278` 17 May,
`IR-7289` 20 Jun) describe their incident as "the same bay 3 staging pattern as IR-9003", a report that
did not yet exist; and `IR-7251` (filed 23 Jan) already records "staging capacity at bay 3 capped",
while `IR-9003` in October says the earlier incidents "were closed without a common-cause review". The
narrative therefore looks partly written after the fact. The bay record (`dock_bay_events`) does not
depend on it and points the same way.

**Verdict: supported.** An Amsterdam-specific dock-staging problem at bay 3 is the only cause anywhere in
the record, the bay-level data locates 11 of 15 events there against an ordinary handling volume, and
it is consistent with damage clustering at one hub while vehicles and drivers do not repeat. It does
not explain the rise at the other hubs (§4.2).

### 4.7 H4 — "it follows the freight": **refuted**

```sql
SELECT client_name, count(*) AS n, round(100.0*count(*)/sum(count(*)) over (),1) AS pct
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
WHERE origin_hub_id='HUB-AMS' AND year(created_at)=2025 GROUP BY 1 ORDER BY 2 DESC;
```

Twelve of the 15 incidents carry a shipment; the client and service-level mix of those shipments matches
the hub baseline, so there is no freight signal:

| Dimension | Damage incidents (n=12) | Amsterdam 2025 baseline (n=347) |
|---|---|---|
| Jaffle Papier | 4 (33%) | 21.9% |
| Jaffle Getränke | 3 (25%) | 18.4% |
| Jaffle Werke | 2 (17%) | 21.3% |
| Jaffle Warenhuis | 2 (17%) | 20.2% |
| Jaffle Maison | 1 (8%) | 18.2% |
| service level: standard / expedited / freight | 7 / 3 / 2 | 55.9% / 20.2% / 23.9% |

The client mix drifts slightly toward Papier and the service mix toward expedited, but on twelve rows
that is noise. More importantly the **shipment links are not trustworthy**: the incident→shipment pairing
is not time-consistent — `INC-2025-00014` (occurred 11 May 2025) points at `SHP-202512-000405`, a
shipment created 16 December 2025, and `INC-2025-00020` (17 Jan) points at a September shipment. The
2023 and 2024 Amsterdam damage incidents carry **no** shipment link at all, so the 2025 linkage looks
like a capture artifact. **Verdict: refuted — no freight signal that the data can support.**

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
| VEH-0003 | 3 | **1** | €2,374 | 2025-03-07 |
| VEH-0038 | 3 | 3 | €4,382 | 2024-07-07 |
| VEH-0021 | 2 | 7 | €17,952 | 2025-04-10 |
| VEH-0028 | 1 | 4 | €14,758 | 2025-09-11 |
| VEH-0001 | 1 | 4 | €13,682 | 2025-03-25 |
| VEH-0007 | 0 | **9** | €34,166 | 2025-12-17 |
| VEH-0033 | 0 | **9** | €19,833 | 2024-11-20 |
| VEH-0012 | 0 | 2 | €8,738 | 2025-02-05 |
| VEH-0031 | 0 | 3 | €18,082 | 2025-08-21 |

*(Costs are in the reporting currency, EUR. All nine vehicles ran only Amsterdam routes in 2025, so no
CHF-invoiced Zürich cost is involved.)*

- **Implicated vehicles average 3.8 work orders each — the fleet average is 3.7** (163 work orders /
  44 vehicles, `stg_fleet_work_orders`; 3.9 if only the 42 vehicles with any work order are counted). The
  vehicles in damage incidents are **ordinary**, not heavy.
- The **two most-repaired vehicles at the hub, VEH-0007 and VEH-0033 (9 work orders each), recorded zero
  damage.** If heavy maintenance were the cause, they would be the worst offenders; they are the cleanest.
- The vehicle with the most damage, VEH-0003, has the **least** maintenance history of any Amsterdam
  vehicle (one work order).

**Cause vs consequence.** Only four work orders at Amsterdam in 2025 hang off an incident, and **all four
are accidents, none is a damage event**:

```sql
SELECT w.wo_id, w.vehicle_id, w.linked_incident_id, i.incident_type, w.cost
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_fleet_work_orders w
JOIN hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_incidents i
  ON i.incident_id = w.linked_incident_id
WHERE i.hub_id='HUB-AMS' AND year(i.occurred_at)=2025;
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
| H1 | Follows **vehicles** | **Undetermined (leaning refuted)** | Leading vehicles 3.6/100 routes vs hub 1.41, but only 3 events and 5 of 9 vehicles appear; five incidents have no vehicle at all (§4.3–4.4) |
| H2 | Follows **drivers** | **Undetermined** | DRV-01028 6.12/100 vs 1.41, but it is the max of 15 drivers and two of its three events are one route/day (§4.5) |
| H3 | Follows **time/process** | **Supported (by place)** | No hour/weekday window; but 11 of 15 events found at bay 3 at ~10× any other bay's rate, bay 3's staging dwell up from ~46 to 70 min, and 14 of 15 reports name dock staging (§4.6) |
| H4 | Follows the **freight** | **Refuted** | Client and service-level mix match the hub baseline; shipment links are not time-consistent and absent in 2023–2024 (§4.7) |

### 4.11 Leading explanation

**The leading explanation is an Amsterdam dock-staging process fault at bay 3 in 2025, not a fleet or
driver defect — at moderate confidence.** The fleet hypothesis is genuinely *refuted*: the implicated
vehicles are ordinary in the maintenance record, the cluster has no work-order footprint, and the shape
of the incidents — spread across vehicles, drivers and routes, with no repeated vehicle/driver pair but
concentrated at one bay — is what a place-and-process cause looks like, not what a bad asset or bad
actor looks like. Confidence stops at moderate because the bay record shows *where* and *how long*
freight sat, not *why*, and because the incident reports that name the cause are chronologically
inconsistent (§4.6). The remaining competitor is that Amsterdam is simply the loudest instance of a
**network-wide 2025 rise in damage** that no Amsterdam process change would fix; the two are not
mutually exclusive, and Amsterdam's bay 3 accounts for 11 of Amsterdam's 15 events but cannot account
for any of the other hubs' 25.

### 4.12 What would settle it (the missing measurement)

1. **Equipment-inspection results for bay 3** (forklift and staging-lane condition) — the one thing
   IR-9003 asks for and the warehouse does not hold. The bay record locates the damage; an inspection
   result would say whether it was the equipment, the layout or the volume of overflow staging.
2. **A vehicle-inspection log** independent of incidents — to test whether VEH-0003/VEH-0038 are
   mechanically worse, rather than lucky with three events.
3. **Shift rosters with route start times** — so hour-of-day can be normalised against the operations
   that actually ran, and a shift/process window tested (routes today carry a date but no clock time).
4. **Damage photos / chain-of-custody** per incident, **complete incident FKs** — 13 of 15 damage
   records name no vehicle and 8 name no driver — and **filing-date provenance for the incident
   reports**, so it is clear which root-cause statements were written at the time.

---

## 5. Confidence and limits

- **What would falsify each finding.** H1/H2 would turn *supported* if the five unattributable incidents
  (or shift rosters) resolved to a repeated vehicle or driver — currently they cannot be attached to
  either. H3 would be *weakened* if an inspection showed bay 3 working normally and the dwell increase
  turned out to be a recording change rather than freight sitting longer. H4 is only weakly falsified
  because the shipment links themselves are unreliable.
- **The strongest honest limits.** (a) The incident reports are **not a clean contemporaneous record**:
  four cite `IR-9003` before it was filed and `IR-9003` contradicts the earlier remediation notes. (b)
  **Damage rose at four of five hubs in 2025**, so Amsterdam is the worst cell of a network-wide move,
  not a demonstrably unique event. (c) **Attribution is incomplete** (13/15 lack a vehicle, 8/15 lack a
  driver), so the vehicle/driver tests are under-powered by construction. (d) Hours have **no exposure
  denominator**, so "no time window" is weaker than "no weekday window".
- **Not measured at all:** equipment-inspection outcomes, loading-crew rosters, damage cost in euros.
- **What the European network raises that this data cannot answer.** Whether damaged freight crossed a
  border before or after the event (for example on Zürich lanes, where Swiss customs inspection could add
  handling), whether any Amsterdam-loaded damage became a cross-border claim, and whether driving- and
  rest-time limits under Regulation (EC) No 561/2006 pushed loading into compressed windows at bay 3. The
  warehouse holds no customs, tachograph or claim-jurisdiction record, so these are open.

---

## 6. Reproduce

All queries run through the **`dbt-platform` MCP `execute_sql` tool** against
`hive_metastore.dbt_smcintyre_jaffle_logistics_prod`, in this order:

1. `SHOW TABLES IN hive_metastore.dbt_smcintyre_jaffle_logistics_prod` — confirm relations.
2. Population/definition: `stg_incidents` grouped by `year(occurred_at), hub_id, incident_type, severity`.
3. Amsterdam by type/severity: same, filtered `hub_id='HUB-AMS'`.
4. Shipment years (`stg_shipments`) — confirm the reloaded 2023–2025 corpus.
5. The 15 damage rows with FKs and report/work-order counts (`fct_incidents`).
6. Recover driver/vehicle via `fct_incidents.route_id = stg_routes.route_id` (Finding 3).
7. Freight join: `fct_incidents`: `shipment_id = fct_shipments.shipment_id` (Finding 7).
8. Time: hour-of-day and weekday of Amsterdam 2025 damage vs other incidents (`stg_incidents`).
9. Exposure — routes per vehicle and per driver at `HUB-AMS` 2025 (`stg_routes`).
10. Hub-level context — damage by hub by year; routes per hub per year; routes per year.
11. Maintenance — all work orders for the nine Amsterdam vehicles; fleet totals; incident-linked work
    orders for Amsterdam 2025.
12. Freight baseline — AMS 2025 shipments by client and by service level (`fct_shipments`).
13. Place — `dock_bay_events` at `HUB-AMS` by bay and year: handling events, staging dwell, `damage_found`
    events and their `incident_id`s.
14. Narrative — `LIKE '%BAY%'`, `'%STAGING%'`, `'%DOCK%'` over `stg_incident_reports` and
    `stg_dispatch_notes`; full bodies of the fifteen 2025 Amsterdam damage reports, including `IR-9003`
    and `IR-7031`; reports citing `IR-9003` with their `filed_at`.

**Reconciliation.** Population = 15 Amsterdam 2025 damage incidents. Of these, 10 are route-attributable
(to VEH-0038, VEH-0003, VEH-0021, VEH-0001, VEH-0028 — summing to 10) and 5 carry no route. The vehicle
table (§4.4) sums to 10; the driver table (§4.5) sums to 10. The five unattributable incidents are named
in §4.3 and appear in no vehicle or driver count. The bay table (§4.6) sums to 15: every incident has a
same-day `damage_found` event.
