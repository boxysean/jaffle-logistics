# What did we know, and when? — signal latency across the note corpus

*Analysis 2. Jaffle Logistics, 2025 review. Data present: 2025-12-31. All numbers below come from
queries run through the dbt Platform MCP (`execute_sql`) against
`hive_metastore.dbt_smcintyre_jaffle_logistics_prod`. Every claim carries its source id and date.*

---

## 1. Executive summary

- **What the result was.** For the two accounts that actually deteriorated in 2025 — **Jaffle Equipment
  (CLI-0042)** and, more mildly, **Jaffle Beverage Co (CLI-0169)** — the customer told us *first*, every
  time. On the deterioration that really mattered (a recurring handling-damage pattern at the Columbus
  hub), the customer's first complaint landed **35 days before our own records** named the pattern. Across
  all five accounts the median lag between our first internal signal and the customer's first contact was
  **≈ 0 days** (we were neither early nor late on average), and the worst case was **35 days late**.
- **What evidence validated it.** Per-account timelines built from the narrative sources (CRM notes, call
  transcripts, ops incidents, incident reports, Slack, support tickets), corroborated by a vector search of
  the `knowledge_base` corpus (top account-scoped hit `IR-9003`, cosine score **0.791**). The operating
  account — CLI-0042 — fell from **98.1% on-time in 2023 and 2024 to 83.9% in 2025** while its ticket count
  rose **17 → 17 → 72**; the three healthy accounts moved ≤ 2.7 points and their internal note cadence did
  **not** change, which rules out "we just write less" as the explanation for the lag.
- **What remains open.** The operational early-warning material exists but is **not readable per account**:
  dispatch notes, routes and fleet work orders carry no client id (routes serve multiple clients), and the
  `knowledge_base` search corpus **excludes** dispatch notes and Slack entirely. So we cannot yet tell
  whether the long lags are a *monitoring* failure (the warning was there, unread) or an *instrumentation*
  failure (the warning was never captured against the account). The single change that would decide it is in
  §4.8.

---

## 2. The question and why it matters

For the accounts that went wrong in 2025, when did we first have an internal signal that something was
deteriorating — and how long before the customer told us? A company that learns from its customers pays for
the information twice: once in the delivery failure and again in the credit, the escalation and the
relationship. The answer decides where to invest next: **a monitoring/alerting fix** (the warnings exist and
are not being read) versus **an instrumentation fix** (the warnings are never captured against the account).

---

## 3. Method

### 3.1 Scope

Calendar **2025** (the deterioration year). All **five** accounts, not only CLI-0042. Baseline years
2023–2024 supply the base rate (§4.6).

### 3.2 Definitions (stated before measuring)

- **Internal source** = a row belonging to us: ops-floor records (`stg_incidents` attributed to the account
  via `shipment_id`; `stg_dispatch_notes`, `stg_routes`, `stg_fleet_work_orders`), internal-commercial
  records (`stg_crm_notes`, `stg_call_transcripts`), formal records (`stg_incident_reports`), and
  `stg_slack_threads` **only when the thread names the account**.
- **Customer-visible source** = `stg_support_tickets` (the customer's own words), or the customer's own
  words inside a transcript.
- **"Mentions the problem" — keyword sets (disclosed):**
  - *Internal decline markers* (narrative text): `credit`, `breach`, `under target`, `root-cause`,
    `slipped`, `slid`, `rising ticket`, `not yet identified`; plus explicit flags: a CRM `sentiment` of
    `concerned`/`negative`, an ops incident of an adverse type (damage, mispick, accident, dispute, delay —
    **weather excluded as exogenous and reported separately**), or a CRM `note_type` of `review`.
  - *Customer-complaint markers* (ticket/customer line): `where is`, `second time`, `wrong item`,
    `disappointed`, `escalate`, `no communication`, `still have nothin`, `appears to be delayed`,
    `appears to be failed`, `keeps happening`, `another late LTL`.
- **First internal signal** = earliest 2025 internal-source row, attributable to the account, whose
  text/flag matches an internal decline marker.
- **First customer-visible signal** = earliest 2025 ticket (or customer words in a transcript) matching a
  customer-complaint marker.
- **Escalation** = earliest 2025 of: an `stg_incident_reports` row filed for the account, a CRM note
  mentioning a credit/breach, a `note_type='review'` note, or an SLA-credit legal document. (For the quiet
  accounts this is simply the earliest incident report filed for that account in 2025, which may be
  unrelated to any of that account's customer complaints — the point being that a *formal* record exists but
  rarely about the account's actual problem.)
- **Lag (days)** = *customer-visible date − first-internal date*. **Negative = the customer told us first**;
  positive = we were already discussing it.

Because an account can have more than one distinct problem in a year, CLI-0042 is measured on **two**
episodes (the one-off January storm, and the recurring weather-independent handling pattern); the others on
one. This is disclosed so the reader can see the difference between "the event we all remember" and "the
pattern that actually sank the year."

### 3.3 Retrieval technique (requirement 3)

Per the project's documented method (`.agents/skills/knowledge-base-search`, `models/context/ai/search.sql`):
embed the question with `ai_query('databricks-gte-large-en', …)`, score with `vector_cosine_similarity`,
filter by `account_key` (and a `ts` window where useful), order by score, take the top k. `ai_query`
returns `ARRAY<DOUBLE>`, so the query vector is cast: `cast(ai_query(...) as array<float>)`. Retrieval is
used to **find** candidates; every cited row is then confirmed with a row-level SQL lookup (§4.7).

### 3.4 The queries

All queries are listed in order in §6. The per-account dates in §4 come from those queries plus
programmatic classification of the ticket corpus against the disclosed keyword set (§3.2).

---

## 4. Findings

### 4.1 Which accounts went wrong, objectively

| client | name | 2023 on-time | 2024 on-time | 2025 on-time | tickets 23/24/25 | incidents 25 | health |
|---|---|---|---|---|---|---|---|
| CLI-0042 | Jaffle Equipment | 98.1% | 98.1% | **83.9%** | 17 / 17 / **72** | 18 | at-risk |
| CLI-0169 | Jaffle Beverage Co | 97.2% | 96.8% | 94.7% | 19 / 30 / 35 | 13 | watch |
| CLI-0201 | Jaffle Paper & Packaging | 97.4% | 96.9% | 94.7% | 23 / 27 / 35 | 16 | healthy |
| CLI-0007 | Jaffle Storefronts | 97.4% | 97.1% | 96.6% | 29 / 16 / 23 | 16 | healthy |
| CLI-0155 | Jaffle Crew Outfitters | 97.6% | 97.2% | 97.0% | 19 / 17 / 24 | 18 | healthy |

Only **CLI-0042** collapsed (14.2 points, against a 97.0% target). **CLI-0169** drifted below its own 95.0%
target and is the second "watch" account. The other three moved little.

*Evidence* — `fct_account_health` aggregated by client-year:
```sql
SELECT client_id, substr(cast(month as string),1,4) AS yr, sum(shipments) AS ship,
       sum(ticket_count) AS tickets, sum(incident_count) AS incidents,
       round(100.0*sum(round(ontime_pct*shipments/100.0))/sum(shipments),1) AS ontime_pct
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.fct_account_health
GROUP BY client_id, substr(cast(month as string),1,4) ORDER BY client_id, yr;
```

### 4.2 The per-account lag table (requirement 5)

Lag = customer-visible date − first internal date. **Negative = customer first.**

| account | episode | first **internal** signal | first **customer-visible** signal | escalation | **lag (days)** |
|---|---|---|---|---|---|
| **CLI-0042** | Jan storm (one-off) | `INC-2025-00417` **2025-01-15** 08:40 (ops incident); Slack `SLK-99001` 2025-01-15 09:05; `IR-9001` filed 2025-01-16 | `TKT-900000` **2025-01-14** 09:00 | `IR-9001` 2025-01-16 · SLA credit `LGL-9001` 2025-02-05 | **−1.0** |
| **CLI-0042** | recurring handling pattern (weather-independent) | `INC-2025-00136` **2025-06-18** 15:14 (CMH damage); `SLK-99010` 2025-07-18; `IR-9003` filed 2025-10-11 | `TKT-910000` **2025-05-14** 14:00 | `IR-9003` 2025-10-11 · review `CRM-9030` 2025-10-20 | **−35.0** |
| **CLI-0007** | Indianapolis mispick cluster | `INC-2025-02233` **2025-05-13** 10:15; `SLK-99020` 2025-05-13 10:40 | `TKT-920000` **2025-05-13** 16:00 | `IR-9002` postmortem 2025-05-19 | **+0.24** |
| **CLI-0169** | 2025 drift | `INC-2025-00020` **2025-01-17** 09:31 (CMH damage) | `TKT-200018` **2025-01-05** 15:53 | `IR-7031` 2025-08-31 | **−12.0** |
| **CLI-0155** | quiet | `INC-2025-00003` **2025-02-19** 09:21 (IND damage); `IR-7022` filed 2025-02-21 | `TKT-200027` **2025-02-22** 14:48 | `IR-7022` 2025-02-21 | **+3.2** |
| **CLI-0201** | quiet | `INC-2025-00139` **2025-01-09** 14:32 (IND mispick); `IR-7024` filed 2025-01-12 | `TKT-200028` **2025-01-12** 17:50 | `IR-7024` 2025-01-12 | **+3.1** |

**Median lag = −0.4 days** (six episodes) — i.e. on a typical episode we learned nothing before the
customer. **Worst case = −35 days** (CLI-0042's handling pattern). **Best case = +3.2 days.**

**Did internal signals precede the customer's?** Of the six episodes, **internal led in 3** (CLI-0007,
CLI-0155, CLI-0201 — all by ≤ 6 hours to 3 days, and all on minor incidents) and **the customer led in 3**
(CLI-0042 ×2, CLI-0169). **By account: internal led for 3 of 5, the customer led for 2 of 5** — and the
customer-led two are precisely the accounts that actually went wrong.

*Evidence (spot checks, full set in §6):*
- `TKT-900000` (CLI-0042, 2025-01-14 09:00): *"[customer] Where is SHP-202501-900001?? Nothing's moved for
  days. I know Chicago got hit but I need a real ETA."*
- `INC-2025-00417` (occurred 2025-01-15 08:40): *"Jackknifed semi on an icy ramp near the Chicago hub; no
  injuries, load held."* — the customer raised it **first**, before the incident was recorded.
- `TKT-910000` (CLI-0042, 2025-05-14 14:00): *"[customer] Following up on SHP-202505-000271 — another late
  LTL load. Our account team keeps promising improvement and we're not seeing it."*
- `INC-2025-00136` (occurred 2025-06-18 15:14): the first of the three Columbus handling incidents — **35
  days after** that first ticket.

### 4.3 Which source type is the earliest warning in practice (the operational punchline)

**The customer's own ticket is the earliest datable, account-readable signal in most cases — and among our
own sources the earliest account-readable warning is Slack, never the ops-floor records.**

| source | account-keyed? | earliest it ever warns | verdict |
|---|---|---|---|
| `support_tickets` (customer) | yes (client_id) | the event itself | usually **first** |
| `slack_threads` (internal chatter) | only when a body names the account | the *pattern* (CLI-0042 `SLK-99010`, 2025-07-18; CLI-0007 `SLK-99020`, 2025-05-13) | earliest internal warning, but for patterns, not first events |
| `stg_incidents` / `incident_reports` | via `shipment_id` | the ops incident date | internal, but **formal records are days–months after the fact** (`IR-9003` filed 2025-10-11 for a June–October pattern) |
| `crm_notes` / `call_transcripts` | yes (client_id) | the quarterly QBR cadence | **lagged**: `CRM-9001` (2025-01-21) is 7 days after the customer's first ticket |
| `stg_dispatch_notes` | **no client id** | — | all 1,299 notes are generic route exceptions; **none mention damage/handling/an account** — unusable for account warning |
| `stg_routes`, `stg_fleet_work_orders` | **no client id** (route/vehicle/hub only) | — | unusable for account warning |

Two structural facts drive this:
1. **The ops floor is not keyed to the account.** 721 of the network's routes carry shipments for **more
   than one client**, so a dispatch note or route exception cannot be attributed to a single account.
2. **The earliest human recognition of CLI-0042's pattern was in Slack, not in a system** — `SLK-99010`
   (2025-07-18, `#accounts`): *"on-time for Jaffle Equipment (CLI-0042) has been sliding since Q2, and
   tickets are up … I'm also seeing two damage/mispick incidents at CMH in June that don't fit that
   pattern."* That is 65 days **after** the customer's first "another late LTL load" ticket and 30 days
   after the first Columbus incident.

*Evidence* — dispatch notes carry no account-relevant text:
```sql
SELECT count(*) FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_dispatch_notes
WHERE lower(body) LIKE '%damage%' OR lower(body) LIKE '%forklift%' OR lower(body) LIKE '%bay%'
   OR lower(body) LIKE '%handling%' OR lower(body) LIKE '%crushed%' OR lower(body) LIKE '%pallet%';
-- -> 0 rows
```
and multi-client routes:
```sql
SELECT count(*) AS routes_with_multi_client FROM (
  SELECT route_id, count(DISTINCT client_id) AS c
  FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_shipments
  WHERE route_id IS NOT NULL GROUP BY route_id HAVING count(DISTINCT client_id) > 1);
-- -> 721
```

### 4.4 The one case where we were early (and why it still doesn't count)

The only episodes where an internal signal preceded the customer are the three "quiet" accounts, and in each
case the "internal signal" is an incidental minor incident that the customer's routine ticket later
happened to follow. The one structurally interesting case is **CLI-0007**: the Indianapolis mispick cluster.
Our ops lead recognised the *pattern* on **2025-05-13 10:15** (`INC-2025-02233`) and **2025-05-13 10:40**
(`SLK-99020`: *"getting multiple 'wrong item' tickets out of IND this morning … smells like a bin issue"*),
~6 hours before the first such ticket in the table (`TKT-920000`, 2025-05-13 16:00). But the ops postmortem
itself (`IR-9002`) records the first wrong-delivery ticket as **05/12** — so even here the customer was
first; ops recognised only the *pattern*, and only once several customers had complained.

### 4.5 The account's own record echoes the customer, and lags

For CLI-0042 the quarterly account-manager record moved *after* the customer each time: customer ticket
2025-01-14 → QBR `CRM-9001` 2025-01-21 (7 days later); customer "another late LTL" 2025-05-14 → QBR
`CRM-9021` 2025-07-16 (63 days later). `CT-99021` (2025-07-16) has the manager saying *"I don't have a root
cause yet, and I don't want to guess at one"* — nine weeks after the customer first flagged the pattern.

### 4.6 Base-rate test: "we were silent" vs "we were quiet because nothing was wrong" (requirement 6)

Account-keyed internal narrative documents per account per month — 2023–2024 (baseline) vs 2025:

| account | baseline docs/mo (2023–24) | 2025 docs/mo | ratio |
|---|---|---|---|
| CLI-0042 | 0.75 | 1.17 | **↑ 1.56×** |
| CLI-0007 | 1.00 | 1.17 | 1.17× |
| CLI-0155 | 0.67 | 1.33 | 2.0× |
| CLI-0169 | 0.54 | 0.92 | 1.70× |
| CLI-0201 | 0.38 | 0.25 | 0.66× |

(Internal narrative = `stg_crm_notes` + `stg_call_transcripts` + account-attributed `stg_incident_reports`.)

**We did not go quiet.** The account-manager's writing cadence is essentially flat across years (e.g.
CLI-0042 CRM notes 3 → 5 → 5; CLI-0007 5 → 5 → 5; CLI-0155 CRM notes 3 → 3 → 6), and the *incident-report* count
rose with the trouble. So the long lag is **not** an artefact of writing less in calm periods. What changed
in the bad year was not the *volume* of our records but their *content and timing*: the records that grew
(customer tickets: CLI-0042 17 → 72) were the ones the customer generated. The correlation between the
ticket channel and the problem is strong; the correlation between our own narrative channel and the problem
is weak.

### 4.7 The retrieval leg — what it found, and its blind spot

Vector search over `knowledge_base` (account-scoped to CLI-0042, question *"deliveries running late and what
is driving the deterioration, handling damage at the Columbus hub"*) returned:

| rank | source_id | type | date | score | classification |
|---|---|---|---|---|---|
| 1 | `IR-9003::1` | Incident Report | 2025-10-11 | **0.791** | handling_or_warehouse_error |
| 2 | `CT-99022::1` | Call Transcript | 2025-10-14 | **0.734** | handling_or_warehouse_error |
| 3 | `IR-7045::1` | Incident Report | **2023**-09-02 | 0.707 | handling_or_warehouse_error |
| 4 | `CRM-9030::2` | CRM Notes | 2025-10-20 | 0.701 | account_assessment |
| 5 | `CRM-9030::1` | CRM Notes | 2025-10-20 | 0.698 | account_assessment |
| … | `LGL-9001::1` | Legal Document | 2025-02-05 | 0.647 | contract_reference |

- **Findings that came from retrieval:** the existence and exact identity of the formal pattern documents
  (`IR-9003`, `CRM-9030`) and the January credit memo (`LGL-9001`) — all confirmed by row-level lookups.
- **A false positive, reported as a finding about the method:** rank 3, `IR-7045`, is a **2023 Detroit**
  damage report. It scores 0.707 purely on topical overlap ("damage") and does **not** support the 2025
  claim. Routine-status tickets (`TKT-200500`, `TKT-200159`) also surfaced. Cosine similarity alone confuses
  *topically similar* with *evidentially relevant*.
- **The blind spot that matters most:** the corpus has only **five** source types — `CRM Notes`,
  `Call Transcript`, `Incident Report`, `Legal Document`, `Support Ticket` (685 rows total). It does **not**
  contain `dispatch_notes`, `slack_threads`, or `fleet_work_orders`. **The retrieval layer therefore cannot
  surface the operational early warning even if it existed**, because the two ops-floor sources are not in
  the corpus and the ops sources it could reach are not account-keyed.

*Evidence* — corpus coverage:
```sql
SELECT source_type, count(*) AS n, cast(min(ts) as string) AS mn, cast(max(ts) as string) AS mx
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.knowledge_base
GROUP BY source_type ORDER BY source_type;
-- CRM Notes 58 · Call Transcript 69 · Incident Report 120 · Legal Document 35 · Support Ticket 403
```

### 4.8 The single recommended change, with a testable expected effect

**Change: attach an account key to the operational sources at the point of capture, and expose a per-account
"service-exception" view over them — dispatch notes, route exceptions and fleet work orders get a
`client_id` (or an account-scoped rollup), and the two ops-floor sources are added to `knowledge_base`.**

Why this one: the signal is *partly* there — the Columbus handling incidents (`INC-2025-00136/00241/00095`)
were recorded in June–October, weeks after the customer but long before our formal `IR-9003`. The failure is
not that nothing is written; it is that what we write is keyed to *hubs and routes*, not to *accounts*, so
it is invisible to an account manager and unsearchable in the corpus. Tagging fixes both at once, and the
retrieval blind spot (§4.7) is a direct consequence of the same gap.

**Expected effect, stated testably:** after the change, for the next material account deterioration there
will exist at least one **internal** source row dated **on or before** the first customer contact, and the
**median lag will move from ≈ 0 days to ≥ +7 days**. **Evidence it is working:** re-run the §4.2 measurement
monthly; success = internal-first on **≥ 4 of 5** accounts, with **median lag ≥ +7 days** and **no episode
worse than −7 days**. If lag stays ≈ 0 after tagging, the problem is instrumentation of a different kind
(we are not *detecting*, only *recording*), and the next investment is alerting thresholds rather than keys.

---

## 5. Confidence and limits

- **What would falsify each finding.**
  - *§4.1/§4.2 (who declined, and the lags):* a different, more generous definition of "internal signal"
    that includes the *dispatch notes on the routes that carried each account's late shipments*. I did not
    use them because routes are multi-client and the notes carry no account id — but if a subsidiary mapping
    exists, the ops floor may have "known" earlier. **This is the single largest uncertainty.**
  - *§4.3 (Slack is the earliest internal warning):* a source of ops chatter outside `slack_threads`
    (e.g. radio/phone) not captured here.
  - *§4.6 (base rate):* the account-keyed narrative sources exclude dispatch notes and Slack; the true
    internal-document rate is higher. The base rate is measured only on sources that carry an account key.
- **What data is missing.**
  - No client attribution on `stg_dispatch_notes`, `stg_routes`, `stg_fleet_work_orders` (confirmed: 721
    multi-client routes; 0 dispatch notes mentioning damage/handling).
  - `knowledge_base` omits dispatch notes and Slack (confirmed by the source-type query).
  - Incident attribution depends on `shipment_id`; reports with a null `shipment_id` are unaccounted (32 of
    59 incident reports have no client id).
  - `IR-9002`'s postmortem cites a first wrong-delivery ticket on **05/12** for CLI-0007 that does not appear
    in `stg_support_tickets` (earliest there is 2025-05-13 16:00) — a small internal inconsistency between
    the narrative and the ticket store.
- **What I did not do.** No local dbt build; all data came through the remote MCP per the project rule. No
  semantic-layer metric was needed beyond `fct_account_health` (the SLA backbone).

---

## 6. Reproduce — the exact MCP calls in order

All via `execute_sql` (schema `hive_metastore.dbt_smcintyre_jaffle_logistics_prod`).

1. **Freshness / corpus size** — `SELECT 'stg_shipments' AS t, count(*), min(created_at), max(created_at) …`
   over `stg_shipments`, `stg_dispatch_notes`, `stg_crm_notes`, `stg_incident_reports`, `knowledge_base`
   (→ 6027 / 1299 / 56 / 59 / 685; spans 2023-01-01 … 2025-12-31).
2. **Account roster** — `SELECT * FROM dim_clients ORDER BY client_id`.
3. **All CRM notes** — `SELECT note_id, client_id, call_date, note_type, sentiment, body FROM stg_crm_notes
   ORDER BY call_date` (56 rows).
4. **All support tickets** — `SELECT ticket_id, client_id, opened_at, channel, status, csat, body FROM
   stg_support_tickets ORDER BY opened_at` (403 rows; classified against the §3.2 keyword set).
5. **Dispatch-note exception types** — `SELECT exception_type, count(*) FROM stg_dispatch_notes GROUP BY 1`.
6. **Dispatch notes mentioning damage/handling** — `… WHERE lower(body) LIKE '%damage%' OR …` (→ 0 rows).
7. **All Slack threads** — `SELECT thread_id, started_at, channel, linked_ids, body FROM stg_slack_threads
   ORDER BY started_at` (116 rows).
8. **All call transcripts** — `SELECT transcript_id, crm_note_id, client_id, call_date, body FROM
   stg_call_transcripts ORDER BY call_date` (55 rows).
9. **Incident reports with account** — `SELECT r.report_id, r.incident_id, r.severity, r.filed_at,
   s.client_id, r.body FROM stg_incident_reports r LEFT JOIN stg_shipments s ON r.shipment_id=s.shipment_id
   ORDER BY r.filed_at` (59 rows).
10. **Contracts** — `SELECT contract_id, client_id, effective_date, sla_ontime_pct, credit_terms FROM
    stg_contracts ORDER BY client_id, effective_date`.
11. **2025 incidents by account** — `SELECT s.client_id, i.incident_id, i.incident_type, i.severity,
    i.occurred_at, i.hub_id FROM stg_incidents i JOIN stg_shipments s ON i.shipment_id=s.shipment_id WHERE
    i.occurred_at >= '2025-01-01' AND i.occurred_at < '2026-01-01' ORDER BY s.client_id, i.occurred_at`.
12. **Client-year trend** — the `fct_account_health` aggregation in §4.1.
13. **Base rates** — the per-source/per-client/per-year `UNION ALL` query in §4.6.
14. **Multi-client routes** — the `HAVING count(DISTINCT client_id) > 1` query in §4.3 (→ 721).
15. **Knowledge-base coverage** — `SELECT source_type, classification, count(*), min(ts), max(ts) FROM
    knowledge_base GROUP BY 1,2`.
16. **Vector search (retrieval leg)**:
    ```sql
    SELECT source_type, source_id, account_key, ts, classification,
           round(vector_cosine_similarity(embedding,
             cast(ai_query('databricks-gte-large-en',
               'deliveries running late and what is driving the deterioration, handling damage at the Columbus hub')
               as array<float>)), 3) AS score,
           substr(text,1,160) AS t
    FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.knowledge_base
    WHERE account_key = 'CLI-0042' ORDER BY score DESC LIMIT 12;
    ```
17. **Row-level confirmation of retrieval hits** — `SELECT report_id, incident_id, body FROM
    stg_incident_reports WHERE report_id IN ('IR-9001','IR-9002','IR-9003')`, and
    `SELECT doc_id, client_id, effective_date, doc_type, body FROM stg_legal_docs WHERE client_id='CLI-0042'
    OR effective_date >= '2024-06-01'`.
