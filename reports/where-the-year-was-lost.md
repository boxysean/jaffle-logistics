# Where the year was lost — 2025 on-time performance, decomposed by volume

## 1. Executive summary

- **What the result was.** 2025 missed 135 of 2,009 shipments (93.28% on time) against 50 in 2023
  (97.51%) and 56 in 2024 (97.21%). One account, **Jaffle Equipment (`CLI-0042`), caused 59 of the 79
  extra misses — 75% of the deterioration — and its rate fell from 98.07% in both quiet years to
  83.89%. The two next-largest movers are the **Chicago hub (48 of the year's 135 misses)** and the
  **Q4 peak quarter (44 misses at the year's highest volume)**. Return the account to its own 97.0%
  contract and 55 of the 135 misses disappear; the three worst client-hub cells alone are worth 40.
- **What evidence validated it.** The dbt Semantic Layer (`on_time_rate`, queried by quarter and by
  client) and 14 `execute_sql` queries against
  `hive_metastore.dbt_smcintyre_jaffle_logistics_prod`; every decomposition reconciles to the same 135
  misses on all four axes; the narrative records (CRM-9030, IR-9001, IR-9003) independently name the
  same two factors the numbers point at.
- **What remains open.** The warehouse holds **identical shipment volumes in 2023, 2024 and 2025**, so
  this analysis cannot separate a volume effect from a reliability effect on the year-over-year change —
  there is none to separate on this corpus. The `service_level` axis is degenerate in 2025 (every
  `freight` shipment is Jaffle Equipment, and only Jaffle Equipment ships freight), so "freight" is a
  relabelling of the account, not an independent driver. Root cause for the non-January decline is
  documented in narrative records, not measurable from the shipment table.

---

## 2. The question and why it matters

A rate says something is wrong; it does not say where the money is. A 14-point miss on a 416-shipment
account moves more freight than a 3-point miss on a 379-shipment account. This analysis therefore
decomposes the 2025 shortfall into **missed shipments**, ranks every dimension value by that count
rather than by its rate, and states plainly which axis carries the loss and which two or three cells
are worth fixing first.

---

## 3. Method

**Data.** `hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments` (grain: one shipment),
joined to `dim_clients` for contract targets. The corpus present ends **2025-12-31**; nothing in this
report assumes data after it. `on_time` = `status = 'delivered'`; `delayed`, `failed` and `returned`
are misses.

**Semantic layer first.** `list_metrics` returns four metrics — `on_time_rate` (RATIO),
`on_time_shipments`, `shipments`, and `on_time_rate_change_vs_prior_quarter_pts` — with dimensions
`metric_time`, `shipment__client_name`, `shipment__client_tier`, `shipment__origin_city`,
`shipment__service_level`, `shipment__status`, and entities `client`, `shipment`. The whole-book
quarterly series and the client-by-quarter slice were taken from `query_metrics` (see §4.1 and §4.3,
both reproduced in §6).

**Why the rest is `execute_sql`.** Three things the card asks for are not expressible in the semantic
layer as exposed:

1. **Missed counts.** Every metric is delivered-side (`on_time_rate`, `on_time_shipments`,
   `shipments`). A miss count is `shipments − on_time_shipments`, which the layer will not compute in
   one query, and a rate is exactly what this analysis is told not to rank by.
2. **The hub dimension.** The layer exposes `shipment__origin_city`, not the hub id. The card names
   hubs (`HUB-CMH`, `HUB-CIN`, `HUB-IND`, `HUB-DET`, and the fifth), so the breakdown runs against
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
| 2023 | 2,009 | 1,959 | 50 | 97.51 |
| 2024 | 2,009 | 1,953 | 56 | 97.21 |
| 2025 | 2,009 | 1,874 | **135** | **93.28** |

The 2023–2024 baseline is 97.51% / 97.21% — the card's ≈97.5% / ≈97.2% — and 2025 is 93.28%, ≈93%.
The year added **79 missed shipments** over 2024 (135 − 56).

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
| Q1 | 14 (97.12%) | 15 (96.91%) | 47 (90.33%) | **+32** |
| Q2 | 12 (97.24%) | 11 (97.47%) | 20 (95.40%) | +9 |
| Q3 | 10 (97.97%) | 12 (97.56%) | 24 (95.12%) | +12 |
| Q4 | 14 (97.65%) | 18 (96.98%) | 44 (92.62%) | **+26** |
| **Year** | 50 | 56 | **135** | +79 |

Two bad quarters, not one: Q1 (the January event) and Q4 (the year's peak volume, 596 shipments).
Q2 and Q3 cost +9 and +12 respectively and sit only 2–2.5 points below the quiet-year norm.

**Separating reliability from volume — and finding there is nothing to separate.** Shipment volume is
*identical* in every year at every quarter: Q1 = 486, Q2 = 435, Q3 = 492, Q4 = 596, in 2023, 2024 and
2025 alike. The whole-book shortfall therefore contains **zero volume effect**: all 79 extra misses are
reliability. Volume still *amplifies* the damage — Q1 and Q4 are the two largest quarters (486 and 596
shipments) and also the two worst — but it is not a cause of it. This is a property of this corpus and
is the single most important caveat on any "we ran more freight" reading of 2025 (see §5).

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
| `CLI-0007` Storefronts | 0, 5, 2, 3 | 4, 1, 3, 3 | 9, 1, 1, 2 | 13 (96.64%) |
| `CLI-0042` Equipment | 3, 1, 1, 3 | 1, 2, 2, 3 | **14, 10, 17, 26** | **67 (83.89%)** |
| `CLI-0155` Crew Outfitters | 3, 3, 2, 2 | 3, 2, 2, 4 | 7, 2, 1, 2 | 12 (96.98%) |
| `CLI-0169` Beverage Co | 2, 3, 2, 3 | 1, 4, 4, 4 | 13, 1, 2, 5 | 21 (94.67%) |
| `CLI-0201` Paper & Packaging | 6, 0, 3, 3 | 6, 2, 1, 4 | 4, 6, 3, 9 | 22 (94.69%) |

Year totals and baselines:

| Client | 2023 | 2024 | 2025 | Contract target |
|---|---|---|---|---|
| Storefronts | 10 (97.36%) | 11 (97.11%) | 13 (96.64%) | 97.0% |
| **Equipment** | 8 (98.07%) | 8 (98.07%) | **67 (83.89%)** | 97.0% |
| Crew Outfitters | 10 (97.56%) | 11 (97.16%) | 12 (96.98%) | 95.0% |
| Beverage Co | 10 (97.16%) | 13 (96.81%) | 21 (94.67%) | 95.0% |
| Paper & Packaging | 12 (97.36%) | 13 (96.90%) | 22 (94.69%) | 92.0% |

Every other account's January spike **recovers** — Storefronts 9 → 1 → 1 → 2, Beverage 13 → 1 → 2 → 5,
Crew 7 → 2 → 1 → 2. Equipment does not: 14, 10, 17, 26, worsening every single quarter while everyone
else recovers. That is the shape of a drift, not a weather event.

### 4.4 Ranked contribution to the shortfall — by missed shipments

```sql
SELECT client_id, origin_hub_id, count(*) AS shipments,
       count(*)-sum(case when status='delivered' then 1 else 0 end) AS missed,
       round(100.0*sum(case when status='delivered' then 1 else 0 end)/count(*),2) AS rate
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_shipments
WHERE year(created_at)=2025 GROUP BY 1,2 ORDER BY client_id, origin_hub_id;   -- cross-tab
```

**a) Client** (the three-column contribution table the card asks for):

| Client | 2025 rate | Missed | 2024 missed | Change | Share of the 79-miss increase |
|---|---|---|---|---|---|
| **`CLI-0042` Equipment** | 83.89% | **67** | 8 | **+59** | **74.7%** |
| `CLI-0201` Paper & Packaging | 94.69% | 22 | 13 | +9 | 11.4% |
| `CLI-0169` Beverage Co | 94.67% | 21 | 13 | +8 | 10.1% |
| `CLI-0007` Storefronts | 96.64% | 13 | 11 | +2 | 2.5% |
| `CLI-0155` Crew Outfitters | 96.98% | 12 | 11 | +1 | 1.3% |
| **Total** | 93.28% | **135** | 56 | +79 | 100% |

**b) Origin hub:**

| Hub | 2025 rate | Missed | 2024 missed | Change | Share |
|---|---|---|---|---|---|
| **HUB-CHI** Chicago | 88.35% | **48** | 15 | **+33** | 41.8% |
| HUB-IND Indianapolis | 93.41% | 28 | 5 | +23 | 29.1% |
| HUB-DET Detroit | 93.68% | 27 | 7 | +20 | 25.3% |
| HUB-CIN Cincinnati | 95.98% | 16 | 13 | +3 | 3.8% |
| HUB-CMH Columbus | 95.39% | 16 | 16 | 0 | 0.0% |
| **Total** | 93.28% | **135** | 56 | +79 | 100% |

**c) Service level:**

| Service level | 2025 rate | Missed | 2024 missed | Change |
|---|---|---|---|---|
| `freight` | 83.89% | 67 | 16 | +51 |
| `standard` | 95.37% | 52 | 28 | +24 |
| `expedited` | 96.60% | 16 | 12 | +4 |
| **Total** | 93.28% | **135** | 56 | +79 |

**d) Month (2025):** Jan 32 · Feb 10 · Mar 5 · Apr 4 · May 11 · Jun 5 · Jul 6 · Aug 10 · Sep 8 ·
Oct 8 · Nov 16 · Dec 20 — **sums to 135.**

**Reconciliation.** Every axis sums to 135: clients 13 + 67 + 12 + 21 + 22 = 135; hubs
48 + 28 + 27 + 16 + 16 = 135; service levels 67 + 52 + 16 = 135; months 32 + 10 + 5 + 4 + 11 + 5 + 6 +
10 + 8 + 8 + 16 + 20 = 135. The primary attribution is **client** (one miss belongs to one account);
everything else is an overlapping cross-tab of the same 135 shipments, reported so the interaction is
visible and never added on top.

### 4.5 Which single dimension explains the most — and the runner-up

**The client axis explains the most, and it explains most of it through one account.** Of the 79 extra
misses in 2025, Jaffle Equipment alone accounts for **59 (74.7%)**; no hub, month or service level comes
close on its own (Chicago 41.8%, Indianapolis 29.1%, Detroit 25.3%, January 31.6% of the increase).

**The runner-up is the origin hub — but only when read with the client.** Chicago carries 41.8% of the
increase and is the single worst hub cell in the business (`CLI-0042` × `HUB-CHI`: 22 misses, 73.17%).
Independent corroboration of the ranking: `dim_clients.health` already flags `CLI-0042` as **`at-risk`**
(the only account so flagged) and `CLI-0169` as **`watch`**; the 2025 ranking puts those same two
accounts first and third on the affected list.

### 4.6 The top three drivers, with the arithmetic

**Driver 1 — Jaffle Equipment (`CLI-0042`), all year. 67 of 135 misses (49.6% of the level, 74.7% of
the increase).** 416 shipments; on-time rate 83.89% against its own 97.0% contract (CON-0042-01).
At 97.0% it needed 404 delivered and had 349, so **55 of its 67 misses are beyond the contractual
target** — 40.7% of the entire year's 135-miss shortfall. Its quarterly path 86.14% → 89.58% → 82.47%
→ 78.69% is monotonically deteriorating after Q2.

**Driver 2 — Chicago (`HUB-CHI`). 48 of 135 misses (35.6%), 88.35% vs 96.75% / 96.54% in the quiet
years.** The January contribution is 23 of those 48; the other 25 land in months with no weather
story (Feb 5, Aug 3, Oct 4, Nov 5, Dec 5, plus singles in Mar/Apr/Jun). Chicago is not merely a
one-month event even though it contains one.

**Driver 3 — the Q4 peak. 44 of 135 misses in the year's heaviest quarter (596 shipments, 92.62%
against 96.98% in 2024 Q4).** November (16) and December (20) alone are 36 misses at 92.12% / 91.07%,
and Q4 carries the largest single-volume exposure of the year.

**Worst cells (client × hub), 2025 — the honest priority list:**

| Cell | Shipments | Missed | Rate | Recovered at 97% |
|---|---|---|---|---|
| `CLI-0042` × `HUB-CHI` | 82 | 22 | 73.17% | 20 |
| `CLI-0042` × `HUB-DET` | 83 | 14 | 83.13% | 12 |
| `CLI-0042` × `HUB-IND` | 88 | 11 | 87.50% | 8 |
| `CLI-0042` × `HUB-CMH` | 74 | 10 | 86.49% | 8 |
| `CLI-0042` × `HUB-CIN` | 89 | 10 | 88.76% | 7 |
| `CLI-0169` × `HUB-CHI` | 77 | 8 | 89.61% | 6 |
| `CLI-0007` × `HUB-CHI` | 92 | 8 | 91.30% | 5 |
| `CLI-0201` × `HUB-CHI` | 74 | 7 | 90.54% | 5 |

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
| Equipment | 97.0% | 349 | **55** | **55** |
| Paper & Packaging | 92.0% | 392 | **0** | 10 |
| Beverage Co | 95.0% | 373 | 1 | 9 |
| Storefronts | 97.0% | 374 | 1 | 1 |
| Crew Outfitters | 95.0% | 386 | 0 | 0 |
| **Whole book** | — | 1,874 | — | **75 of 135 (55.6%)** |

Read the two columns separately. Against **each client's own contracted target**, only Equipment is
materially in breach — it alone is worth **55 recovered shipments, 40.7% of the year's shortfall**.
Against a flat 97% benchmark the total recoverable is **75 of 135 (55.6%)**, of which Equipment is 73%.
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

**The January event is real and short: 32 misses, 23.7% of the year's shortfall, in 8% of the
volume.** Of January's 32 misses, **23 are Chicago** (HUB-CHI was 53 shipments, 23 missed, 56.60%),
against 3 in January 2023 and 2 in January 2024 — a genuine, dated spike. It also explains the Q1
figure: Q1's +32 over 2024 is almost entirely this month.

**But January is not the story of the year.** Excluding January, 2025 still ran at **94.36% with 103
misses**, against 49 in the same Feb–Dec window of 2024 — **+54 misses the storm does not explain**.
Split that remainder by hub:

| Hub | Feb–Dec 2024 missed | Feb–Dec 2025 missed | Change |
|---|---|---|---|
| Chicago | 13 | 25 | +12 |
| **Indianapolis** | 4 | 22 | **+18** |
| **Detroit** | 7 | 25 | **+18** |
| Cincinnati | 11 | 15 | +4 |
| Columbus | 14 | 16 | +2 |
| **Total** | 49 | 103 | +54 |

Outside January, **Indianapolis and Detroit each added more misses than Chicago did.** The storm is the
loud quarter; the drift across Indianapolis and Detroit is the one that persists all year.

### 4.9 Named counterexamples — where the data does **not** support the obvious story

- **"Raw rate, so it must be the priority."** `CLI-0201` Paper & Packaging has the second-worst 2025
  rate of the five (94.69%, 22 misses) — and is **not in breach**: its contract target is 92.0%
  (`CON-0201-01`), it delivered 392 against a target of 381, and the counterfactual recovers **0**
  shipments at its own contract (10 at a flat 97%). Ranking by rate would put a compliant account on
  the work list. This is the precise trap the card's volume-weighting instruction is aimed at.
- **"The bad hub with the bad rate is the bad hub."** Detroit had 2025's second-worst hub rate among
  the five, but it was also the **worst hub in 2023 (95.72%)** and the best in 2024 (98.16%) — the
  ranking is not stable, and 14 of its 27 misses sit on one account (`CLI-0042`).
- **"Columbus is fine because its misses didn't rise."** `HUB-CMH` added **0** misses year over year and
  is the wrong answer to "where did the year go" — yet `CLI-0042`'s Columbus cell is at **86.49%**, and
  the narrative records a third handling-damage incident there in October (`INC-2025-00095`, `IR-9003`).
  A hub-level denominator hides a client-level cell.
- **"Freight is the failing service level."** True arithmetic (67 of 135, 83.89%) and still misleading:
  in 2025 **every** freight shipment is `CLI-0042` and **only** `CLI-0042` ships freight (416 containers
  == 416 shipments, exactly). In 2023–2024 the other four accounts shipped freight (75/101/80/92 and
  75/85/101/74 shipments) and did not in 2025. The dimension is collinear with the account in 2025, so
  it identifies Equipment and nothing else. Any claim that "freight service" broke down is unsupported
  by this axis.
- **"Missing counts rose, so we shipped more."** Volumes are identical year over year (2,009 each year;
  486/435/492/596 each quarter in all three years). There is no volume story in the year-over-year
  change at all.

### 4.10 What the narrative records say (context, not measurement)

The shipment table establishes *where*. The project's own written records name *why*, and they name the
same two factors, independently of the numbers above:

- **January storm.** `INC-2025-00417` (2025-01-15, HUB-CHI, severity 3): "Jackknifed semi on an icy
  ramp near the Chicago hub; no injuries, load held." Report `IR-9001`: "During the Jan 14-16 winter
  storm, a semi jackknifed on an icy on-ramp departing the Chicago hub." `SLK-99001` (#ops-chi,
  2025-01-15): "~24 CHI routes with heavy exceptions this morning." Ticket `TKT-900000` (2025-01-14,
  `CLI-0042`, `SHP-202501-900001`) raises it from the customer side, and call transcript `CT-99001`
  records the January QBR (`CRM-9001`) where the client "raised the jackknife incident directly."
- **The non-January pattern.** `CRM-9021` (2025-07-16): on-time "slipped again despite no major
  weather … cause not yet identified. Opening a root-cause review." `CRM-9022` (2025-10-14): "the
  January Chicago storm (INC-2025-00417) explains part of it, but a second, weather-independent pattern
  has emerged: repeated handling damage at the Columbus hub (`INC-2025-00136`, `INC-2025-00241`,
  `INC-2025-00095`)." `CRM-9030` (2025-10-20, Q4 root-cause review) states the two factors explicitly;
  `IR-9003` records `INC-2025-00095` as "the third handling-related incident at HUB-CMH in 2025".
  `SLK-99010` (#accounts, 2025-07-18): "on-time for Jaffle Equipment (CLI-0042) has been sliding since
  Q2, and tickets are up."

The distinction is deliberate: the shipment data shows the *shape* of the Equipment decline but
cannot by itself prove a handling-damage cause; the cause is a claim made in `CRM-9030` and `IR-9003`.

---

## 5. Confidence and limits

- **Contract targets.** `dim_clients.sla_ontime_pct` is joined per client, so the "own contract"
  counterfactual uses 97.0 / 95.0 / 92.0 as contracted. The card's flat "97% contractual target" is
  also given, because two accounts contract below it.
- **What data is missing.** The fact table has no promised-delivery date, so lateness is a status flag
  (`delayed`/`failed`/`returned`), not a lateness duration — the analysis can count misses but not
  measure *how late* or the size of any service credit. There is no cost or revenue column, so "would
  fixing this have recovered" is expressed in **shipments**, never dollars; the credit formula in
  `seeds/contracts.csv` (1% of monthly spend per point below target, capped at 10%) is a contract term,
  not a measured amount.
- **A finding's falsifier.** Finding 4.5 (client explains most of the loss) is falsified by any
  re-cut in which Equipment's quarterly misses track the fleet's — they do not: it is the only account
  that worsens in every quarter of 2025 while the other four recover after January.
- **The service-level axis is not independent in 2025** (freight ≡ `CLI-0042`, exactly). Treat all
  service-level numbers as a restatement of the client cut (§4.9).
- **Identical volumes across years.** The warehouse holds the same 2,009 shipments per year and the
  same quarterly split in 2023, 2024 and 2025. This makes the reliability/volume separation clean —
  there is no volume effect — but it also means the corpus cannot be used to ask whether *more* freight
  caused *more* misses. If the reloaded 2023–2024 backbone was generated on the 2025 volume skeleton,
  that is a data-generation property, not an operational one, and should be confirmed with the team
  that built `seeds/shipments.csv` before any volume-based claim is made.
- **The incident table under-records the January storm.** Only 18 incidents appear in January 2025 and
  only one is explicitly storm-related (`INC-2025-00417`); the storm's shipment impact (Chicago
  56.60% in January) is far larger than the incident record implies. The storm's scale is documented in
  the narrative (`IR-9001`, `SLK-99001`), not in the incident table.
- **Small cells.** `CLI-0042` × `HUB-CHI` January is 13 shipments. The cell-level January rate swings
  on single shipments; the year-level figures in §4.4 are the stable ones.

---

## 6. Reproduce

Run in this order. Tools are the `dbt-platform` MCP server over the remote endpoint; relations resolve
against production metadata (`hive_metastore.dbt_smcintyre_jaffle_logistics_prod`).

1. `list_metrics` — confirms `on_time_rate`, `on_time_shipments`, `shipments`,
   `on_time_rate_change_vs_prior_quarter_pts` and their dimensions.
2. `query_metrics` — `metrics: ["on_time_rate"]`, `group_by: [{name: "metric_time", type:
   "time_dimension", grain: "QUARTER"}]`, ordered ascending. Returns the 12-quarter series (§4.2).
3. `query_metrics` — `metrics: ["on_time_rate", "shipments"]`, grouped by `{name:
   "shipment__client_name", type: "dimension"}` and quarter, `where: "{{ TimeDimension('metric_time',
   'QUARTER') }} >= '2025-01-01'"`. Returns the client series (§4.3).
4. `execute_sql` — the yearly baseline (§4.1).
5. `execute_sql` — whole book by quarter (§4.2).
6. `execute_sql` — client by quarter, 2023→2025 (§4.3).
7. `execute_sql` — client by year (baseline columns for §4.4a).
8. `execute_sql` — hub by year (§4.4b).
9. `execute_sql` — service level by year (§4.4c).
10. `execute_sql` — month, 2025 only (§4.4d).
11. `execute_sql` — status mix, 2025 only (`group by status`): 1,874 delivered / 109 delayed / 21
    failed / 5 returned.
12. `execute_sql` — client × status, 2025 only (§4.4 reconciliation by miss type).
13. `execute_sql` — client × hub cross-tab, 2025 only (§4.6 cell table).
14. `execute_sql` — January vs Feb–Dec, 2025 only (§4.8).
15. `execute_sql` — Jan/Feb–Dec × year × hub × client, 2024 vs 2025 (§4.8 hub table).
16. `execute_sql` — the counterfactual: `fct_shipments` joined to `dim_clients` on `client_id`, 2025
    only, computing `round(sla_ontime_pct/100*n) − delivered` and `round(0.97*n) − delivered` per client
    (§4.7). Whole-book control: 2,009 shipments, 1,874 delivered, 135 missed, 75 recoverable at 97%.
17. `execute_sql` — the cited incidents (`incident_id in ('INC-2025-00417','INC-2025-00136',
    'INC-2025-00241','INC-2025-00095')`) and the January 2025 incident list (§4.10).

Narrative citations are read from the repository seeds rather than the warehouse where they are the
source of record: `seeds/crm_notes.csv` (`CRM-9001`, `CRM-9020`, `CRM-9021`, `CRM-9022`, `CRM-9030`),
`seeds/incident_reports.csv` (`IR-9001`, `IR-9003`), `seeds/shipments.csv`,
`seeds/slack_threads.csv` (`SLK-99001`, `SLK-99010`), `seeds/contracts.csv`, `seeds/clients.csv`.
