# Support cases by topic, 2023–2025

*For the Head of Customer Experience. Generated 2026-10-12 from the dbt Platform warehouse over the
dbt Platform remote MCP. Corpus ends 2025-12-29.*

## 1. The two-minute read

- **403 support cases over three years** (first 2023-01-11, last 2025-12-29). Every one of them
  carries a graded topic and sentiment — 403 labels for 403 tickets, no gaps.
- **Volume was flat, then jumped**: 107 cases in 2023, 107 in 2024, **189 in 2025** (+77%).
- **The mood moved further than the volume.** Cases graded negative went 18 → 25 → **66**
  (17% → 23% → **35%** of the year's cases).
- **Delivery delay is the swing.** 31 → 26 → **61** cases, and average CSAT on those cases fell
  3.70 → 3.50 → **2.06**. Delay complaints in 2023 were not graded negative at all; in 2025,
  44 of 61 were.
- **One account carries most of 2025.** CLI-0042 (Werke) raised 72 cases — 38% of the year — 45 of
  them graded negative, at an average CSAT of 2.88.
- **Where the topics come from is not obvious, and §4 is explicit about it.** They are graded
  labels over the ticket text, not the output of the AI layer's classifier.

## 2. The three years, by topic

| topic | 2023 | 2024 | 2025 | total | share of 3-year corpus |
|---|---|---|---|---|---|
| `general_inquiry` | 55 | 51 | 100 | **206** | 51.1% |
| `delivery_delay` | 31 | 26 | 61 | **118** | 29.3% |
| `delivery_failed` | 18 | 19 | 24 | **61** | 15.1% |
| `wrong_item` | 3 | 11 | 4 | **18** | 4.5% |
| **total cases** | **107** | **107** | **189** | **403** | 100% |

**Graded negative, same grid**

| topic | 2023 | 2024 | 2025 |
|---|---|---|---|
| `general_inquiry` | 0 | 0 | 0 |
| `delivery_delay` | 0 | 1 | **44** |
| `delivery_failed` | 15 | 13 | 18 |
| `wrong_item` | 3 | 11 | 4 |
| **total negative** | **18** | **25** | **66** |

**Average CSAT (1–5)**

| topic | 2023 | 2024 | 2025 |
|---|---|---|---|
| `general_inquiry` | 4.47 | 4.49 | 4.75 |
| `delivery_delay` | 3.70 | 3.50 | **2.06** |
| `delivery_failed` | 1.88 | 2.61 | 2.00 |
| `wrong_item` | 2.00 | **1.22** | 2.00 |

## 3. What the pattern says

- **Inquiries are the quiet majority.** 206 of 403 cases (51%) are `general_inquiry`, and in three
  years not one of them was graded negative. They are inbound questions, not failures, and they
  hold a CSAT of ~4.5 throughout. Reading the raw case count as "customer unhappiness" would be
  wrong: half the volume is people asking things.
- **The deterioration is concentrated in delay.** Delays went from 29% of cases in 2023 to 32% in
  2025 — a small mix shift — but their *character* changed completely: no negative grades in 2023,
  1 in 2024, **44 in 2025**, with CSAT falling from 3.70 to 2.06. The same topic, three years later,
  is a different conversation.
- **`wrong_item` is small and vicious.** Only 18 cases in three years, but 11 of 11 graded negative
  in 2024 at a CSAT of 1.22 — the lowest single cell in the table. It is rare, and when it happens
  the customer is not asking a question.
- **2025 is one account plus a general rise.** Werke (CLI-0042) raised 72 cases; the next four
  accounts raised 35, 35, 24 and 23. Werke alone is 38% of the year and 68% of its negative grades.
- **Resolution and channel**, for completeness: 327 of 403 cases are resolved (81%), 33 open, 43
  pending. By channel: email 131, phone 122, chat 89, portal 61. Portal is the tidiest channel —
  58 of 61 resolved and no pending backlog.

## 4. How this information is produced from the free text

This is the part that matters for trusting the table, so it is written out in full — including the
part where the answer is "the pipeline does *not* produce these topics".

### 4.1 What the topic labels are — and are not

- The four topics and the three sentiment values come from **`eval_ticket_triage`**: one row per
  ticket carrying `true_category` and `true_sentiment`. Coverage is complete — 403 graded rows for
  403 tickets in `stg_support_tickets`.
- The repo treats those columns as **ground truth for evaluating classification**, and the naming
  says so (`true_*`). The repo does not record whether they were authored by a person or produced
  during dataset generation, and **they are not the output of a model in this project**.
- **The AI layer does not classify tickets into these four topics.** The project's only classify
  taxonomy is `jaffle_content_type` v1 — `account_assessment`, `contract_reference`,
  `weather_disruption`, `vehicle_or_driver_incident`, `handling_or_warehouse_error`,
  `routine_status`. That is a *content type* taxonomy, deliberately shared across all seven
  free-text sources as a worked example. It is not `delivery_delay` / `delivery_failed` /
  `general_inquiry` / `wrong_item`, and no model in the warehouse emits those.
- So: this report counts **graded labels over the ticket free text**. The AI layer's real
  contribution to tickets is normalisation, embedding and content-type classification for
  *retrieval* (§4.2) — it is not what produces this table.

### 4.2 What the free-text pipeline actually does

Each free-text source runs its own independent end-to-end path — chunk, embed, enrich — and the
paths converge only at the end, in the knowledge base. For support tickets:

1. **One ticket becomes one unit — with no chunking.** `models/context/ticket_records_meta.sql`
   reshapes a ticket body straight into the chunk-shaped record the rest of the pipeline expects:
   `chunk_id = ticket_id::1`, `chunk_seq = 1`, `chunk_text = body`, `token_estimate =
   ceil(length(body)/4)`, `citation_url = jaffle_logistics://support_ticket/<ticket_id>` and
   `artifact_ts = opened_at`. It **never calls `chunk()`**, because a ticket body is already the
   atomic embedding unit. The chunking path — `chunk_crm_notes`, `chunk_incident_reports`,
   `chunk_legal_docs`, `chunk_transcripts` with their `*_chunks_meta` companions — serves the other
   four free-text sources, where one document legitimately contains several topics.
2. **Normalise and hash** (`support_tickets_hashed`), so identical text is identifiable and costs
   are attributable.
3. **Embed** (`support_tickets_embed`) through the package's `embed()`, which carries cache metadata,
   so text that has not changed is not paid for twice. Embedding is the cheap, repeatable half.
4. **Classify** (`support_tickets_classify`) through `ai_classify` with the shared prompt and output
   schema, wrapped in `guard_batch()` and cost-logged with `log_ai_run` / `complete_ai_run`. This
   model is deliberately **not incremental**: `classify()` has no cache metadata equivalent, so
   every build reclassifies the whole corpus — a disclosed cost tradeoff at this demo's scale. On
   duckdb there is no `classify()` implementation, so the model substitutes a constant label to keep
   the project parsing; it proves nothing about real output.
5. **Converge** — each source's `*_embedded_classified` model feeds the package's `knowledge_base()`
   combine, so every source keeps its own lineage into one retrievable surface, and every record
   keeps a citation URL back to the artifact it came from.
6. **Retrieve** — `search` goes by meaning first and then filters by category. The docs disclose the
   known gap: filtering by category excludes other categories, but does not guarantee the best
   chunk *within* a surviving category outranks every other chunk sharing it.
7. **Governance and cost** — AI functions cost real money here: oversized batches are blocked by
   `guard_batch`, every call is logged, and the entire AI layer only exists when a build ran with
   `ai_functions_enabled` set. If it was not, the embeddings and knowledge base are simply absent.

### 4.3 What it would take for the pipeline to generate these topics itself

- The mechanism already exists: a named, versioned prompt plus an output schema, exactly as
  `jaffle_content_type` v1 is declared. What is missing is a **ticket-topic taxonomy** and a second
  classify model that emits it.
- That would give topics computed at build time rather than read from a fixed eval label — and it
  would carry real AI spend on every build until `classify()` gains cache metadata.

## 5. Caveats

- **403 cases is a small corpus.** A single account moves the percentages; treat year-on-year change
  as directional, not precise.
- **The topics are graded labels, not the customer's own categorisation**, and CSAT is a 1–5 score
  held in the seed. "Negative" means *graded* negative.
- **The corpus ends 2025-12-29.** 2026 is out of scope, and 2025's final days may still have open
  cases.
- **Nothing in this table comes from the embeddings.** The vector layer's role is retrieval. This
  report counts labelled rows over the same free text.
- **2025's rise is not uniform.** Werke dominates it; the other four major accounts also rose, but
  from a much lower base.

## 6. Appendix: the queries

All run through `execute_sql` on the dbt Platform remote MCP, relations written in full.

**A1. Corpus coverage — tickets against graded labels**

```sql
SELECT (SELECT count(*) FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_support_tickets) AS tickets,
       (SELECT count(*) FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.eval_ticket_triage) AS graded,
       (SELECT count(*) FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_support_tickets t
          JOIN hive_metastore.dbt_smcintyre_jaffle_logistics_prod.eval_ticket_triage e
            ON e.ticket_id = t.ticket_id) AS joined,
       (SELECT cast(min(opened_at) AS string) FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_support_tickets) AS first_at,
       (SELECT cast(max(opened_at) AS string) FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_support_tickets) AS last_at
```

**A2. Cases by year and topic, with sentiment and CSAT (§2)**

```sql
SELECT cast(substr(cast(t.opened_at AS string),1,4) AS int) AS yr,
       e.true_category AS topic,
       count(*) AS cases,
       sum(case when e.true_sentiment = 'negative' then 1 else 0 end) AS negative,
       round(avg(t.csat), 2) AS avg_csat
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_support_tickets t
JOIN hive_metastore.dbt_smcintyre_jaffle_logistics_prod.eval_ticket_triage e ON e.ticket_id = t.ticket_id
GROUP BY 1, 2 ORDER BY 1, 2
```

**A3. The account side, 2025 (§3)**

```sql
SELECT t.client_id AS client, count(*) AS cases,
       sum(case when e.true_category = 'delivery_delay' then 1 else 0 end) AS delay,
       sum(case when e.true_category = 'delivery_failed' then 1 else 0 end) AS failed,
       sum(case when e.true_category = 'general_inquiry' then 1 else 0 end) AS inquiry,
       sum(case when e.true_sentiment = 'negative' then 1 else 0 end) AS negative,
       round(avg(t.csat), 2) AS avg_csat
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_support_tickets t
JOIN hive_metastore.dbt_smcintyre_jaffle_logistics_prod.eval_ticket_triage e ON e.ticket_id = t.ticket_id
WHERE cast(substr(cast(t.opened_at AS string),1,4) AS int) = 2025
GROUP BY 1 ORDER BY cases DESC
```

**A4. Channel and resolution state (§3)**

```sql
SELECT t.channel, t.status, count(*) AS cases
FROM hive_metastore.dbt_smcintyre_jaffle_logistics_prod.stg_support_tickets t
GROUP BY 1, 2 ORDER BY 1, 2
```
