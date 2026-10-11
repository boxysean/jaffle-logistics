# Where the year was lost — 2025 on-time performance, decomposed by volume

## 1. Executive summary

- **What the result was.** 2025 missed 135 of 2,009 shipments (93.28% on time) against 46 of 1,848 in
  2023 (97.51%) and 54 of 1,949 in 2024 (97.23%). One account, **Jaffle Werke (`CLI-0042`), caused 59
  of the 81 extra misses — 73% of the deterioration** — and its rate fell from 97.77% / 97.96% in the
  two quiet years to 83.89%. The two next-largest movers are the **Paris hub (48 of the year's 135
  misses)** and the **Q4 peak quarter (44 misses at the year's highest volume)**. Return the account to
  its own 97.0% contract and 55 of the 135 misses disappear; the three worst client-hub cells alone are
  worth 40.
- **What evidence validated it.** The dbt Semantic Layer (`on_time_rate`, queried by quarter and by
  client) and `execute_sql` queries against `hive_metastore.dbt_smcintyre_jaffle_logistics_prod`; every
  decomposition reconciles to the same 135 misses on all four axes; the narrative records (CRM-9030,
  IR-9001, IR-9003) independently name the same two factors the numbers point at.
- **What remains open.** Shipment volume grew modestly year over year (1,848 → 1,949 → 2,009), and at
  2024's miss rate the extra 60 shipments of 2025 account for under two of the 81 extra misses — the
  deterioration is reliability, not volume. The `service_level` axis is nearly degenerate in 2025
  (every Jaffle Werke shipment is `freight`, and every one of the 67 freight misses is Jaffle Werke's),
  so "freight" is a relabelling of the account, not an independent driver. Root cause for the
  non-January decline is documented in narrative records, not measurable from the shipment table.

---

## 2. The question and why it matters

A rate says something is wrong; it does not say where the money is. A 14-point miss on a 416-shipment
account moves more freight than a 3-point miss on a 387-shipment account. This analysis therefore
decomposes the 2025 shortfall into **missed shipments**, ranks every dimension value by that count
rather than by its rate, and states plainly which axis carries the loss and which two or three cells
are worth fixing first.

---

## 3. Method

**Data.** `hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments` (grain: one shipment),
joined to `dim_clients` for contract targets. The corpus present ends **2025-12-31**; nothing in this
report assumes data after it. `on_time` = `status = 'delivered'`; `delayed`, `failed` and `returned`
are misses.

**Semantic layer first.** The project defines five metrics on the shipment semantic model —
`on_time_rate` (RATIO), `on_time_shipments`, `shipments`, `late_hours`, and
`on_time_rate_change_vs_prior_quarter_pts` — with dimensions `metric_time`, `shipment__client_name`,
`shipment__client_tier`, `shipment__origin_city`, `shipment__service_level`, `shipment__status`,
`shipment__late_bucket`, `shipment__promised_delivery_at`, and entities `client`, `shipment`. The
whole-book quarterly series and the client-by-quarter slice were taken from `query_metrics` (see §4.1
and §4.3, both reproduced in §6).

**Why the rest is `execute_sql`.** Three things the card asks for are not expressible in the semantic
layer as exposed:

1. **Missed counts.** Every on-time metric is delivered-side (`on_time_rate`, `on_time_shipments`,
   `shipments`). A miss count is `shipments − on_time_shipments`, which the layer will not compute in
   one query, and a rate is exactly what this analysis is told not to rank by.
2. **The hub dimension.** The layer exposes `shipment__origin_city`, not the hub id. The card names
   hubs (`HUB-AMS`, `HUB-ZRH`, `HUB-BER`, `HUB-VIE`, and the fifth), so the breakdown runs against
   `fct_shipments.origin_hub_id`.
3. **Counterfactuals and the status mix.** "How many shipments would a cell have recovered at target"
   and the delayed/failed/returned split are arithmetic on the fact table, not metric queries.

**Technique.** One primary attribution per axis (client, origin hub, service level, month), each
reconciled to the 135 total; the client × hub cross-tab reported separately so the interaction is
visible but not double-counted; and a before/after baseline (2023 and 2024) for every dimension value.

---

## 4. Findings

### 4.1 The baseline: 2025 is the only bad year, and it is bad across the whole book

```sql
SELECT year(created_at) AS yr, count(*) AS shipments,
       sum(case when status='delivered' then 1 else 0 end) AS delivered,
       count(*)-sum(case when status='delivered' then 1 else 0 end) AS missed,
       round(100.0*sum(case when status='delivered' then 1 else 0 end)/count(*),2) AS on_time_rate
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
GROUP BY 1 ORDER BY 1;
```

| Year | Shipments | Delivered | Missed | On-time % |
|---|---|---|---|---|
| 2023 | 1,848 | 1,802 | 46 | 97.51 |
| 2024 | 1,949 | 1,895 | 54 | 97.23 |
| 2025 | 2,009 | 1,874 | **135** | **93.28** |

The 2023–2024 baseline is 97.51% / 97.23% — the card's ≈97.5% / ≈97.2% — and 2025 is 93.28%, ≈93%.
The year added **81 missed shipments** over 2024 (135 − 54).

### 4.2 Quarter by quarter, whole book — the loss is not one event

```sql
SELECT year(created_at) AS yr, quarter(created_at) AS q, count(*) AS shipments,
       count(*)-sum(case when status='delivered' then 1 else 0 end) AS missed,
       round(100.0*sum(case when status='delivered' then 1 else 0 end)/count(*),2) AS on_time_rate
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
GROUP BY 1,2 ORDER BY 1,2;
```

| Quarter | 2023 missed (rate) | 2024 missed (rate) | 2025 missed (rate) | 2025 vs 2024 |
|---|---|---|---|---|
| Q1 | 14 (96.87%) | 14 (97.03%) | 47 (90.33%) | **+33** |
| Q2 | 9 (97.75%) | 11 (97.39%) | 20 (95.40%) | +9 |
| Q3 | 10 (97.79%) | 12 (97.48%) | 24 (95.12%) | +12 |
| Q4 | 13 (97.63%) | 17 (97.06%) | 44 (92.62%) | **+27** |
| **Year** | 46 | 54 | **135** | +81 |

Two bad quarters, not one: Q1 (the January event) and Q4 (the year's peak volume, 596 shipments).
Q2 and Q3 cost +9 and +12 respectively and sit only 2–2.5 points below the quiet-year norm.

**Separating reliability from volume — and finding almost nothing on the volume side.** Shipment
volume rose a little each year: 2025 ran 486 / 435 / 492 / 596 by quarter against 472 / 422 / 477 /
578 in 2024 — 60 more shipments over the year, about 3%. Holding 2024's miss rate (54 of 1,949) and
applying it to 2025's volume gives **1.7 extra misses from volume and 79.3 from reliability**; no
quarter's volume effect exceeds half a shipment. Volume still *amplifies* the damage — Q4 is the
largest quarter in every year and one of the two worst in 2025 — but it is not a cause of it. Q1, the
other bad quarter, is not a volume story at all: at 486 shipments it is smaller than Q3 (492). This is
the single most important caveat on any "we ran more freight" reading of 2025 (see §5).

### 4.3 Client by quarter, 2023 → 2025 — the one account that never recovers

Semantic-layer query (`query_metrics`, `on_time_rate` + `shipments` by `shipment__client_name` ×
quarter) and the `execute_sql` equivalent agree; the miss counts below come from the SQL:

```sql
SELECT client_id, client_name, year(created_at) AS yr, quarter(created_at) AS q, count(*) AS shipments,
       count(*)-sum(case when status='delivered' then 1 else 0 end) AS missed,
       round(100.0*sum(case when status='delivered' then 1 else 0 end)/count(*),2) AS on_time_rate
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
GROUP BY 1,2,3,4 ORDER BY 1,3,4;
```

Missed shipments per quarter (on-time % in brackets):

| Client | 2023 Q1–Q4 | 2024 Q1–Q4 | 2025 Q1–Q4 | 2025 year |
|---|---|---|---|---|
| `CLI-0007` Warenhuis | 0, 4, 2, 2 | 4, 1, 3, 3 | 9, 1, 1, 2 | 13 (96.64%) |
| `CLI-0042` Werke | 3, 1, 1, 3 | 1, 2, 2, 3 | **14, 10, 17, 26** | **67 (83.89%)** |
| `CLI-0155` Maison | 3, 2, 2, 2 | 3, 2, 2, 4 | 7, 2, 1, 2 | 12 (96.98%) |
| `CLI-0169` Getränke | 2, 2, 2, 3 | 1, 4, 4, 4 | 13, 1, 2, 5 | 21 (94.67%) |
| `CLI-0201` Papier | 6, 0, 3, 3 | 5, 2, 1, 3 | 4, 6, 3, 9 | 22 (94.69%) |

Year totals and baselines:

| Client | 2023 | 2024 | 2025 | Contract target |
|---|---|---|---|---|
| Warenhuis | 8 (97.74%) | 11 (97.04%) | 13 (96.64%) | 97.0% |
| **Werke** | 8 (97.77%) | 8 (97.96%) | **67 (83.89%)** | 97.0% |
| Maison | 9 (97.64%) | 11 (97.09%) | 12 (96.98%) | 95.0% |
| Getränke | 9 (97.26%) | 13 (96.73%) | 21 (94.67%) | 95.0% |
| Papier | 12 (97.17%) | 11 (97.32%) | 22 (94.69%) | 92.0% |

Every other account's January spike **recovers** — Warenhuis 9 → 1 → 1 → 2, Getränke 13 → 1 → 2 → 5,
Maison 7 → 2 → 1 → 2. Werke does not: after an easing in Q2 (14 → 10) it worsens to 17 and then 26,
the only account whose second half is far worse than its storm quarter. Papier, which had no January
spike, also ends the year high (9 in Q4) — a smaller, separate drift worth watching. That is the shape
of a drift, not a weather event.

### 4.4 Ranked contribution to the shortfall — by missed shipments

```sql
SELECT client_id, origin_hub_id, count(*) AS shipments,
       count(*)-sum(case when status='delivered' then 1 else 0 end) AS missed,
       round(100.0*sum(case when status='delivered' then 1 else 0 end)/count(*),2) AS rate
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
WHERE year(created_at)=2025 GROUP BY 1,2 ORDER BY client_id, origin_hub_id;   -- cross-tab
```

**a) Client** (the three-column contribution table the card asks for):

| Client | 2025 rate | Missed | 2024 missed | Change | Share of the 81-miss increase |
|---|---|---|---|---|---|
| **`CLI-0042` Werke** | 83.89% | **67** | 8 | **+59** | **72.8%** |
| `CLI-0201` Papier | 94.69% | 22 | 11 | +11 | 13.6% |
| `CLI-0169` Getränke | 94.67% | 21 | 13 | +8 | 9.9% |
| `CLI-0007` Warenhuis | 96.64% | 13 | 11 | +2 | 2.5% |
| `CLI-0155` Maison | 96.98% | 12 | 11 | +1 | 1.2% |
| **Total** | 93.28% | **135** | 54 | +81 | 100% |

**b) Origin hub:**

| Hub | 2025 rate | Missed | 2024 missed | Change | Share |
|---|---|---|---|---|---|
| **HUB-PAR** Paris | 88.35% | **48** | 13 | **+35** | 43.2% |
| HUB-BER Berlin | 93.41% | 28 | 5 | +23 | 28.4% |
| HUB-VIE Vienna | 93.68% | 27 | 7 | +20 | 24.7% |
| HUB-ZRH Zürich | 95.98% | 16 | 13 | +3 | 3.7% |
| HUB-AMS Amsterdam | 95.39% | 16 | 16 | 0 | 0.0% |
| **Total** | 93.28% | **135** | 54 | +81 | 100% |

**c) Service level:**

| Service level | 2025 rate | Missed | 2024 missed | Change |
|---|---|---|---|---|
| `freight` | 86.01% | 67 | 15 | +52 |
| `standard` | 95.37% | 52 | 27 | +25 |
| `expedited` | 96.07% | 16 | 12 | +4 |
| **Total** | 93.28% | **135** | 54 | +81 |

**d) Month (2025):** Jan 32 · Feb 10 · Mar 5 · Apr 4 · May 11 · Jun 5 · Jul 6 · Aug 10 · Sep 8 ·
Oct 8 · Nov 16 · Dec 20 — **sums to 135.**

**Reconciliation.** Every axis sums to 135: clients 13 + 67 + 12 + 21 + 22 = 135; hubs
48 + 28 + 27 + 16 + 16 = 135; service levels 67 + 52 + 16 = 135; months 32 + 10 + 5 + 4 + 11 + 5 + 6 +
10 + 8 + 8 + 16 + 20 = 135. The primary attribution is **client** (one miss belongs to one account);
everything else is an overlapping cross-tab of the same 135 shipments, reported so the interaction is
visible and never added on top.

### 4.5 Which single dimension explains the most — and the runner-up

**The client axis explains the most, and it explains most of it through one account.** Of the 81 extra
misses in 2025, Jaffle Werke alone accounts for **59 (72.8%)**; no hub, month or service level comes
close on its own (Paris 43.2%, Berlin 28.4%, Vienna 24.7%, January 30.9% of the increase).

**The runner-up is the origin hub — but only when read with the client.** Paris carries 43.2% of the
increase and is the single worst hub cell in the business (`CLI-0042` × `HUB-PAR`: 22 misses, 73.17%).
Independent corroboration of the ranking: `dim_clients.health` already flags `CLI-0042` as **`at-risk`**
(the only account so flagged) and `CLI-0169` as **`watch`**; the 2025 ranking puts those same two
accounts first and third on the affected list.

### 4.6 The top three drivers, with the arithmetic

**Driver 1 — Jaffle Werke (`CLI-0042`), all year. 67 of 135 misses (49.6% of the level, 72.8% of
the increase).** 416 shipments; on-time rate 83.89% against its own 97.0% contract (`CON-0042-02`,
effective 2025-05-12; the contract it replaced, `CON-0042-01`, carried the same 97.0% target). At
97.0% it needed 404 delivered and had 349, so **55 of its 67 misses are beyond the contractual
target** — 40.7% of the entire year's 135-miss shortfall. Its quarterly path 86.14% → 89.58% → 82.47%
→ 78.69% is monotonically deteriorating after Q2.

**Driver 2 — Paris (`HUB-PAR`). 48 of 135 misses (35.6%), 88.35% vs 96.48% / 96.90% in the quiet
years.** The January contribution is 23 of those 48; the other 25 land in months with no weather
story (Feb 5, Aug 3, Oct 4, Nov 5, Dec 5, plus singles in Mar/Apr/Jun). Paris is not merely a
one-month event even though it contains one.

**Driver 3 — the Q4 peak. 44 of 135 misses in the year's heaviest quarter (596 shipments, 92.62%
against 97.06% in 2024 Q4).** November (16) and December (20) alone are 36 misses at 92.12% / 91.07%,
and Q4 carries the largest single-volume exposure of the year.

**Worst cells (client × hub), 2025 — the honest priority list:**

| Cell | Shipments | Missed | Rate | Recovered at 97% |
|---|---|---|---|---|
| `CLI-0042` × `HUB-PAR` | 82 | 22 | 73.17% | 20 |
| `CLI-0042` × `HUB-VIE` | 83 | 14 | 83.13% | 12 |
| `CLI-0042` × `HUB-BER` | 88 | 11 | 87.50% | 8 |
| `CLI-0042` × `HUB-AMS` | 74 | 10 | 86.49% | 8 |
| `CLI-0042` × `HUB-ZRH` | 89 | 10 | 88.76% | 7 |
| `CLI-0169` × `HUB-PAR` | 77 | 8 | 89.61% | 6 |
| `CLI-0007` × `HUB-PAR` | 92 | 8 | 91.30% | 5 |
| `CLI-0201` × `HUB-PAR` | 74 | 7 | 90.54% | 5 |

The three worst cells recover **20 + 12 + 8 = 40** shipments at 97% — **29.6% of the 135-miss
shortfall** from three client-hub pairs.

### 4.7 The counterfactual, plainly

```sql
SELECT s.client_id, c.client_name, c.sla_ontime_pct, count(*) AS shipments,
       sum(case when s.status='delivered' then 1 else 0 end) AS delivered,
       cast(round(c.sla_ontime_pct/100.0*count(*)) as int) AS target_delivered,
       cast(greatest(0, round(c.sla_ontime_pct/100.0*count(*))
                        - sum(case when s.status='delivered' then 1 else 0 end)) as int) AS recover_at_contract,
       cast(greatest(0, round(0.97*count(*))
                        - sum(case when s.status='delivered' then 1 else 0 end)) as int) AS recover_at_97
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments s
JOIN hive_metastore.dbt_smcintyre_jaffle_logistics_prod.dim_clients c ON c.client_id = s.client_id
WHERE year(s.created_at)=2025 GROUP BY 1,2,3 ORDER BY 3 DESC;
```

| Client | Target | Delivered | Recovered at own contract | Recovered at 97% |
|---|---|---|---|---|
| Werke | 97.0% | 349 | **55** | **55** |
| Papier | 92.0% | 392 | **0** | 10 |
| Getränke | 95.0% | 373 | 1 | 9 |
| Warenhuis | 97.0% | 374 | 1 | 1 |
| Maison | 95.0% | 386 | 0 | 0 |
| **Whole book** | — | 1,874 | — | **75 of 135 (55.6%)** |

Read the two columns separately. Against **each client's own contracted target**, only Werke is
materially in breach — it alone is worth **55 recovered shipments, 40.7% of the year's shortfall**.
Against a flat 97% benchmark the total recoverable is **75 of 135 (55.6%)**, of which Werke is 73%.
The three worst client-hub cells are worth 40 at the same 97% benchmark.

### 4.8 January versus the rest of the year

```sql
SELECT case when month(created_at)=1 then 'January' else 'Feb-Dec' end AS segment,
       count(*) AS shipments, count(*)-sum(case when status='delivered' then 1 else 0 end) AS missed,
       round(100.0*sum(case when status='delivered' then 1 else 0 end)/count(*),2) AS on_time_rate
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
WHERE year(created_at)=2025 GROUP BY 1 ORDER BY 1;
```

| Segment | Shipments | Missed | Rate |
|---|---|---|---|
| January | 183 | 32 | 82.51% |
| February–December | 1,826 | 103 | 94.36% |

**The January event is real and short: 32 misses, 23.7% of the year's shortfall, in 9% of the
volume.** Of January's 32 misses, **23 are Paris** (HUB-PAR was 53 shipments, 23 missed, 56.60%),
against 3 in January 2023 and 2 in January 2024 — a genuine, dated spike. It also explains most of the
Q1 figure: January alone is +25 of Q1's +33 over 2024.

**But January is not the story of the year.** Excluding January, 2025 still ran at **94.36% with 103
misses**, against 47 in the same Feb–Dec window of 2024 — **+56 misses the storm does not explain**.
Split that remainder by hub:

| Hub | Feb–Dec 2024 missed | Feb–Dec 2025 missed | Change |
|---|---|---|---|
| Paris | 11 | 25 | +14 |
| **Berlin** | 4 | 22 | **+18** |
| **Vienna** | 7 | 25 | **+18** |
| Zürich | 11 | 15 | +4 |
| Amsterdam | 14 | 16 | +2 |
| **Total** | 47 | 103 | +56 |

Outside January, **Berlin and Vienna each added more misses than Paris did.** The storm is the loud
quarter; the drift across Berlin and Vienna is the one that persists all year.

### 4.9 Named counterexamples — where the data does **not** support the obvious story

- **"Raw rate, so it must be the priority."** `CLI-0201` Papier has the second-worst 2025 rate of the
  five (94.69%, 22 misses) — and is **not in breach**: its contract target is 92.0% (`CON-0201-01`), it
  delivered 392 against a target of 381, and the counterfactual recovers **0** shipments at its own
  contract (10 at a flat 97%). Ranking by rate would put a compliant account on the work list. This is
  the precise trap the card's volume-weighting instruction is aimed at.
- **"The bad hub with the bad rate is the bad hub."** Vienna had 2025's second-worst hub rate among
  the five, but it was also the **worst hub in 2023 (95.48%)** and the second-best in 2024 (98.09%,
  behind Berlin's 98.66%) — the ranking is not stable, and 14 of its 27 misses sit on one account
  (`CLI-0042`).
- **"Amsterdam is fine because its misses didn't rise."** `HUB-AMS` added **0** misses year over year
  and is the wrong answer to "where did the year go" — yet `CLI-0042`'s Amsterdam cell is at
  **86.49%**, and the narrative records a third handling-damage incident there in October
  (`INC-2025-00095`, `IR-9003`). A hub-level denominator hides a client-level cell.
- **"Freight is the failing service level."** True arithmetic (67 of 135, 86.01%) and still
  misleading: in 2025 **every** Werke shipment is freight (416 of 416), and **all 67** freight misses
  are Werke's — the other 63 freight shipments (Warenhuis 31, Getränke 32) missed none. In 2023–2024
  all five accounts shipped freight (70 to 99 shipments each per year); in 2025 Maison and Papier
  shipped none. In miss terms the dimension is collinear with the account, so it identifies Werke and
  nothing else. Any claim that "freight service" broke down is unsupported by this axis.
- **"Misses rose, so we shipped more."** Volume rose by 60 shipments (about 3%) between 2024 and 2025;
  at 2024's miss rate that is worth 1.7 of the 81 extra misses (§4.2). There is almost no volume story
  in the year-over-year change.

### 4.10 What the narrative records say (context, not measurement)

The shipment table establishes *where*. The project's own written records name *why*, and they name the
same two factors, independently of the numbers above:

- **January storm.** `INC-2025-00417` (2025-01-15, HUB-PAR, severity 3): "Jackknifed semi on an icy
  ramp near the Paris hub; no injuries, load held." Report `IR-9001`: "During the Jan 14-16 winter
  storm, a semi jackknifed on an icy on-ramp departing the Paris hub." `SLK-99001` (#ops-par,
  2025-01-15): "~24 PAR routes with heavy exceptions this morning." Ticket `TKT-900000` (2025-01-14,
  `CLI-0042`, `SHP-202501-900001`) raises it from the customer side, and call transcript `CT-99001`
  records the January QBR (`CRM-9001`) where the client raised the jackknife incident directly.
- **The non-January pattern.** `CRM-9021` (2025-07-16): on-time "slipped again despite no major
  weather … cause not yet identified. Opening a root-cause review." `CRM-9022` (2025-10-14): "The
  January Paris storm (INC-2025-00417) explains part of it, but a second, weather-independent pattern
  has emerged: repeated handling damage at the Amsterdam hub (INC-2025-00136, INC-2025-00241,
  INC-2025-00095)." `CRM-9030` (2025-10-20, Q4 root-cause review) states the two factors explicitly;
  `IR-9003` records `INC-2025-00095` as "the third handling-related incident at HUB-AMS in 2025".
  `SLK-99010` (#accounts, 2025-07-18): "on-time for Jaffle Werke (CLI-0042) has been sliding since
  Q2, and tickets are up."

The distinction is deliberate: the shipment data shows the *shape* of the Werke decline but cannot by
itself prove a handling-damage cause; the cause is a claim made in `CRM-9030` and `IR-9003`.

---

## 5. Confidence and limits

- **Contract targets.** `dim_clients.sla_ontime_pct` is joined per client, so the "own contract"
  counterfactual uses 97.0 / 95.0 / 92.0 as contracted. The card's flat "97% contractual target" is
  also given, because two accounts contract below it. Werke's contract changed mid-year
  (`CON-0042-01` → `CON-0042-02` on 2025-05-12) at an unchanged 97.0% target; the 2025 CRM notes
  still cite `CON-0042-01`, which matters for any credit calculation but not for the counts here.
- **What this analysis does not use.** The fact table now carries `promised_delivery_at`, `hours_late`
  and `late_bucket` (populated for the 109 delayed shipments of 2025), so *how late* is measurable; this
  report counts misses and does not size lateness. There is no cost or revenue column in the shipment
  fact, so "would fixing this have recovered" is expressed in **shipments**, never euros; the credit
  formula in `seeds/contracts.csv` (1% of monthly spend per point below target, capped at 10%) is a
  contract term, not a measured amount.
- **A finding's falsifier.** Finding 4.5 (client explains most of the loss) is falsified by any
  re-cut in which Werke's quarterly misses track the rest of the book's — they do not: it is the only
  account whose misses climb to 17 and 26 in Q3 and Q4 while the January-hit accounts fall back to
  single digits.
- **The service-level axis is not independent in 2025** (every Werke shipment is freight, and every
  freight miss is Werke's). Treat all service-level numbers as a restatement of the client cut (§4.9).
- **Year-over-year volumes.** The warehouse holds 1,848 / 1,949 / 2,009 shipments for 2023 / 2024 /
  2025. The 2023–2024 history differs from earlier cuts of this corpus, which held 2,009 shipments in
  every year; the 2025 numbers are unchanged. Any comparison against an older copy of this report
  should be re-run rather than read across.
- **The incident table under-records the January storm.** Only 18 incidents appear in January 2025 and
  only one is explicitly storm-related (`INC-2025-00417`); the storm's shipment impact (Paris 56.60% in
  January) is far larger than the incident record implies. The storm's scale is documented in the
  narrative (`IR-9001`, `SLK-99001`), not in the incident table.
- **Small cells.** `CLI-0042` × `HUB-PAR` January is 13 shipments. The cell-level January rate swings
  on single shipments; the year-level figures in §4.4 are the stable ones.
- **What the European network raises that this data cannot answer.** The shipment fact has no
  border-crossing, customs-hold or driver-hours field, so this analysis cannot say whether any of the
  misses came from Swiss customs clearance on Zürich lanes, from EU driving- and rest-time limits
  (Regulation (EC) No 561/2006) constraining storm-recovery scheduling, or from cabotage restrictions
  on cross-border legs. Those are open questions, not findings.

---

## 6. Reproduce

Run in this order. Tools are the `dbt-platform` MCP server over the remote endpoint; relations resolve
against production metadata (`hive_metastore.dbt_smcintyre_jaffle_logistics_prod`).

1. `list_metrics` — confirms `on_time_rate`, `on_time_shipments`, `shipments`, `late_hours`,
   `on_time_rate_change_vs_prior_quarter_pts` and their dimensions.
2. `query_metrics` — `metrics: ["on_time_rate"]`, `group_by: [{name: "metric_time", type:
   "time_dimension", grain: "QUARTER"}]`, ordered ascending. Returns the 12-quarter series (§4.2).
3. `query_metrics` — `metrics: ["on_time_rate", "shipments"]`, grouped by `{name:
   "shipment__client_name", type: "dimension"}` and quarter, `where: "{{ TimeDimension('metric_time',
   'QUARTER') }} >= '2025-01-01'"`. Returns the client series (§4.3).
4. `execute_sql` — the yearly baseline (§4.1).
5. `execute_sql` — whole book by quarter, plus the volume/reliability split against 2024's miss rate
   (§4.2): whole book 1.7 volume, 79.3 reliability.
6. `execute_sql` — client by quarter, 2023→2025 (§4.3).
7. `execute_sql` — client by year (baseline columns for §4.4a).
8. `execute_sql` — hub by year (§4.4b).
9. `execute_sql` — service level by year (§4.4c), and freight by client by year (§4.9).
10. `execute_sql` — month, 2025 only (§4.4d).
11. `execute_sql` — status mix, 2025 only (`group by status`): 1,874 delivered / 109 delayed / 21
    failed / 5 returned.
12. `execute_sql` — client × status, 2025 only (§4.4 reconciliation by miss type).
13. `execute_sql` — client × hub cross-tab, 2025 only (§4.6 cell table).
14. `execute_sql` — January vs Feb–Dec, 2025 only (§4.8).
15. `execute_sql` — Jan/Feb–Dec × year × hub, 2024 vs 2025 (§4.8 hub table).
16. `execute_sql` — the counterfactual: `fct_shipments` joined to `dim_clients` on `client_id`, 2025
    only, computing `round(sla_ontime_pct/100*n) − delivered` and `round(0.97*n) − delivered` per client
    (§4.7). Whole-book control: 2,009 shipments, 1,874 delivered, 135 missed, 75 recoverable at 97%.
17. `execute_sql` — the cited incidents (`incident_id in ('INC-2025-00417','INC-2025-00136',
    'INC-2025-00241','INC-2025-00095')`) and the January 2025 incident list (§4.10).

Narrative citations are read from the repository seeds rather than the warehouse where they are the
source of record: `seeds/crm_notes.csv` (`CRM-9001`, `CRM-9020`, `CRM-9021`, `CRM-9022`, `CRM-9030`),
`seeds/incident_reports.csv` (`IR-9001`, `IR-9003`), `seeds/shipments.csv`,
`seeds/slack_threads.csv` (`SLK-99001`, `SLK-99010`), `seeds/contracts.csv`, `seeds/clients.csv`.
