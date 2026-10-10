# dbt best-practices audit: jaffle-logistics

**Date:** 2026-10-10 · **Branch:** `wt/t_76dd34ad` · **dbt:** dbt-core 1.12.5 + dbt-duckdb 1.11.0

> **Provenance (orchestrator note, added after this audit was written).** The audit and fixes below
> were produced against the branch base `5033269`. Between then and merge, `main` advanced 46
> commits (new staging/mart models — revenue, cost attribution, payroll, dock-bay events — plus a
> promised-delivery clock on `fct_shipments`). The branch was rebased onto `0f6b95c` to merge, and
> the fixes were re-verified there. Section line references and the PASS counts below are as
> measured on the original base; the re-measured gate on the rebased tree is
> **PASS=340 WARN=0 ERROR=0 SKIP=0** (baseline on `0f6b95c` was PASS=338; this PR still nets +4
> tests added and −2 tautological tests removed). The new models `main` added are outside the
> audited scope of this report.

**Gate after changes:** `dbt build --target duckdb --vars '{ai_functions_enabled: false}'` gave
**PASS=241 WARN=0 ERROR=0 SKIP=0** on the original base. The baseline was PASS=239. This PR adds 4 tests and removes 2
tautological ones.

---

## Executive summary: top three findings

1. **High: there are no unit tests, and the logic most likely to break silently is engine-specific.**
   No `unit_tests:` block exists anywhere in `models/`. The shipment-ID regex goes through
   adapter-branching macros (`macros/portable.sql:7-22`): `regexp_extract` on DuckDB and
   `regexp_substr` everywhere else. The transcript parser has four per-engine branches plus
   string-offset maths and a window function (`models/context/int_transcript_turns.sql:21-53,62-64,74`).
   The local gate runs only the DuckDB branch, so the Databricks (prod) branch is never checked
   against known inputs before it materialises. *Skill:* `adding-dbt-unit-test`, "When to use":
   regex, window functions, complex logic. **Listed, not attempted** (see H1 for why).
2. **High: the inputs to the governed on-time metric had no null guard.** *Fixed in this PR.*
   `stg_shipments.status` had only `accepted_values`, and that test ignores nulls. A null status
   would count toward `shipments` but toward neither `delivered` nor `not_ontime`, and the build
   would stay green. `created_at` (the `agg_time_dimension`) and the month-bucketing timestamps
   `stg_support_tickets.opened_at` and `stg_incidents.occurred_at` had no test at all.
   *Skill:* `using-dbt-for-analytics-engineering` → `writing-data-tests.md`, Tier 2.
3. **Medium: real consumer-facing APIs have no governance.** `knowledge_base` is read by name over
   MCP `execute_sql` by `.agents/skills/knowledge-base-search`, and it declares its own
   `meta.mcp_search` contract (`models/context/ai/_context_ai.yml:89-109`). The `fct_shipments`
   metrics are consumed by `.agents/skills/explain-metric-movement`. Neither model has a contract,
   an access level, a group, or an `exposure`. A column rename would break those agents without any
   build-time signal. *Skill:* `working-with-dbt-mesh`, "Should this model have a contract?".
   **Listed, not attempted.**

---

## 1. The skills and how they were obtained

The skills are dbt Labs' curated **dbt Agent Skills** (`metadata.author: dbt-labs` in each
`SKILL.md`). The orchestrator had already cloned them to
`/home/hermes/.hermes/cache/scratch/dbt-skills-audit/skills/dbt/skills/`. I read the `SKILL.md`
files directly from that path. I did not re-clone or vendor them, and nothing from the clone is
in this repo. I did not record the clone's commit SHA: reading git metadata outside the worktree
was not permitted in this session.

| Skill | Files read |
|---|---|
| `using-dbt-for-analytics-engineering` | `SKILL.md`, `references/writing-data-tests.md`, `references/writing-documentation.md` |
| `adding-dbt-unit-test` | `SKILL.md` |
| `maintaining-dbt-documentation` | `SKILL.md`; ran `audit_coverage.py` |
| `working-with-dbt-mesh` | `SKILL.md` |
| `running-dbt-commands` | `SKILL.md` |
| `building-dbt-semantic-layer` | `SKILL.md`, `references/time-spine.md`, `references/best-practices.md` |

## 2. Scope

**Audited (static):** every YAML and SQL file under `models/`, `macros/`, `tests/`;
`dbt_project.yml`, `vars.yml`, `packages.yml`/`package-lock.yml`; the parsed
`target/manifest.json` (via `dbt parse` and `audit_coverage.py`); and `docs/multi-platform.md`,
whose claims I checked against the SQL.

**Local data checks:** these ran only against the **local DuckDB file** built by the gate
(`jaffle_logistics.duckdb`), opened read-only. Every staging model reads a seed via `ref()`
(the project has no `sources:`), so this is the same CSV content the warehouse loads. It is not
the warehouse, though, and I drew no conclusions about production tables.

**Not audited:** anything in the dbt Platform / Databricks warehouse (see §5), and the
`models/context/ai/` layer at runtime, which is disabled in the gate.

---

## 3. Findings, ranked

Each finding gives: the skill and rule → evidence → why it matters → what a fix needs. Fix status
is one of **Fixed**, **Partly fixed**, or **Listed, not attempted**.

### Critical

None found. Nothing I could check statically is broken, and the gate passes.

### High

#### H1. No unit tests; complex engine-branching logic is untested. *Listed, not attempted*

- **Skill/rule:** `adding-dbt-unit-test`, "When to use": *regex, date math, window functions,
  `case when` with many `when`s, complex joins*; also *"Models with high criticality"*.
- **Evidence:** `grep unit_tests models/` returns nothing. Candidates, ranked by what a unit test
  would catch:
  1. **`int_shipment_touchpoints`**: regex extraction via `regex_first`/`has_match`
     (`int_shipment_touchpoints.sql:81,87`; `macros/portable.sql:7-22`), a six-way union, and a
     dedupe (`:101-108`). It feeds `fct_shipments.touchpoint_count`. Only 2 of 599 dispatch notes
     match locally, so real data barely exercises the regex. A fixture with zero, one and repeated
     IDs would pin the behaviour per engine.
  2. **`int_transcript_turns`**: four per-engine array-explode branches (`:21-53`), speaker and
     text parsing by offsets (`substr(... , 2)`, `position(']: ') + 3`, `:62-64`), a `LIKE` header
     filter (`:67`), and `row_number()` (`:74`). If parsing breaks, a transcript silently drops out
     of the knowledge base. Locally every transcript yields at least one turn, but nothing asserts
     that.
  3. **`int_client_monthly_sla`**: multi-branch `case` + `date_trunc` + rounded ratio (`:11-17`).
     This is the SQL twin of the governed `on_time_rate` metric. A unit test would lock the two
     definitions together (see M3).
  4. **`fct_account_health`**: a three-way join on `(client_id, month)` with zero-fill `coalesce`
     (`:44-49`). It would catch month-alignment and fan-out regressions.
  5. `fct_incidents` and `ticket_records_meta`: low value. These are simple aggregates and
     reshapes; the skill says not to unit-test built-in functions.
- **Why it matters:** the gate only runs the DuckDB branches. The Databricks `regexp_substr` and
  `posexplode` paths reach prod untested.
- **Why not attempted:** under `dbt build`, a failing unit test blocks materialisation of its model.
  A fixture that passes on DuckDB but mistypes on Databricks would block `int_shipment_touchpoints`,
  and with it `fct_shipments`, in the Nightly. That can't be verified while the warehouse is
  mid-rebuild. **To fix:** add `dict`-format unit tests for items 1–3 and run them in CI against
  Databricks. Per the skill, exclude them from production jobs with
  `--exclude-resource-type unit_test`.

#### H2. Core metric inputs had no `not_null` guard. *Fixed*

- **Skill/rule:** `writing-data-tests.md`, Tier 2: *"Non-PK column used in logic, … confirmed 0%
  nulls → `not_null`"*. Also note that `accepted_values` passes on nulls.
- **Evidence (before):** `stg_shipments.status` had only `accepted_values`. `created_at`,
  `stg_support_tickets.opened_at` and `stg_incidents.occurred_at` had no tests. All four have 0
  nulls in the local build (2009/189/174 rows).
- **Why it matters:** each of these columns decides whether a row lands in a time bucket or the
  on-time numerator. A null removes the row from `int_client_monthly_sla`, `fct_account_health`
  counts, or Semantic Layer time series, and the build stays green.
- **Fix:** added `not_null` (severity error) to all four in `models/staging/_staging.yml`, each
  with a description saying why.

### Medium

#### M1. Consumer-facing models have no contract, access level, group, or exposure. *Listed, not attempted*

- **Skill/rule:** `working-with-dbt-mesh`. *"Use a contract when … external consumers … query
  the table directly and would break from column renames"*; *"Default new models to `private` and
  widen access only when needed"*; adoption order is Groups & Access → Contracts → Versions.
- **Evidence:** no `contract:`, `access:`, `group:`, `versions:` or `exposures:` anywhere in the
  repo, and no `dependencies.yml` (single project, so Mesh cross-project refs don't apply).
  Consumers do exist, though:
  - `knowledge_base` is read by `.agents/skills/knowledge-base-search` through MCP `execute_sql`.
    Its `meta.mcp_search` block (`models/context/ai/_context_ai.yml:105-109`) is a schema promise
    with nothing enforcing it.
  - `fct_shipments` (`_marts.yml:46+`) hosts the semantic model and metrics consumed by
    `.agents/skills/explain-metric-movement`.
- **Placement rule:** if governance is added, `access`/`group`/`contract` must go under `config:`,
  not top level (the skill says top-level placement breaks Fusion). There are no current
  violations because none exist.
- **To fix:** (1) declare `exposures` for the two agent skills so lineage shows them; (2) add
  `config: {contract: {enforced: true}}` with declared `data_type`s on `knowledge_base`, after
  confirming the shape on Databricks; (3) optionally add groups and `access: private` on the
  `context/` internals. This is judgement-heavy, so it was not done here.

#### M2. `dbt.type_float()` narrows to 32-bit; the `dbt_project.yml` comment says it's harmless. *Listed, not attempted*

- **Skill/rule:** `running-dbt-commands`/project hygiene (`dbt_project.yml` correctness), and the
  task's multi-engine check against `docs/multi-platform.md`.
- **Evidence:** `dbt_project.yml:106-108` forces seed `contracts.sla_ontime_pct` to `'float'` on
  every non-BigQuery target and calls this *"harmless on Snowflake/DuckDB/Databricks, which infer it
  correctly"*. `stg_contracts.sql:6` and `stg_drivers.sql:8` also cast to `dbt.type_float()`.
  In the local build those columns are DuckDB `FLOAT` (4-byte), while the unforced `drivers` seed
  inferred `DOUBLE`. `stg_drivers.perf_score` 4.85 reads back as `4.849999904632568`. In Spark
  SQL, `FLOAT` is also 4-byte. I could not confirm dbt-databricks' `type_float` rendering here
  (that adapter isn't installed locally).
- **Why it matters:** today's SLA targets (97.0/95.0/92.0) are exact in float32, so no wrong number
  ships yet. But `fct_account_health.ontime_vs_target` subtracts a float32 from a double, and any
  fractional SLA such as 97.3 would drift. The comment is wrong for DuckDB.
- **Why not attempted:** changing these to `double` retypes columns on `dim_clients`, `dim_drivers`
  and `fct_account_health`. `using-dbt-for-analytics-engineering` treats retyping as a **breaking
  change**. On Databricks the seed type change would also need `dbt seed --full-refresh`.

#### M3. The on-time rule is defined in three places (DRY). *Listed, not attempted*

- **Skill/rule:** `using-dbt-for-analytics-engineering`: *"Focus heavily on DRY principles"*.
- **Evidence:** `int_client_monthly_sla.sql:13-17` (`status = 'delivered'`, plus a hardcoded
  complement list `('delayed','failed','returned')`); `fct_shipments.sql:26` (`is_ontime`); and the
  metric `on_time_shipments` (`_marts.yml:124`), whose `on_time_rate` description says it is "the
  same definition int_client_monthly_sla uses".
- **Why it matters:** a change to what "on time" means has to be made three times. `not_ontime`
  silently stops equalling `shipments - delivered` if a fifth status appears. The `accepted_values`
  on `stg_shipments.status` is what currently catches that, and I documented this on the column.
- **To fix:** compute `is_ontime` once (in `stg_shipments` or a small int model) and aggregate it
  in `int_client_monthly_sla`. That is a logic refactor, so it is out of scope here.

#### M4. Degenerate and redundant tests. *Partly fixed*

- **Skill/rule:** `writing-data-tests.md`: *"Don't check that the SQL ran correctly"*,
  *"Don't duplicate tests for pass-through columns"*, *"To check business logic, write a unit
  test instead."*
- **Fixed (tautological, so they can never fail):**
  - `int_shipment_touchpoints.source` `accepted_values`. Each union branch assigns `source` as a
    string literal (`int_shipment_touchpoints.sql:18,29,42,54,67,82`). I replaced the test with a
    description and a YAML comment pointing to the unit test in H1.
  - `int_transcript_turns.transcript_id` → `stg_call_transcripts` `relationships`. Every row is
    exploded from that model (`int_transcript_turns.sql:21-53`), so the child set is a subset of
    the parent by construction. I kept `not_null`. The real hazard runs the other way (a transcript
    with zero turns); that is listed under H1, not added as a test. Placing a test on the staging
    model that refs a downstream model risks build-ordering surprises in `dbt build`.
- **Listed (redundant, not wrong):** these mart tests re-check pass-through columns already tested
  identically upstream: `fct_shipments.status` (`_marts.yml:76` duplicates `stg_shipments.status`),
  `dim_clients.health`, `fct_incidents.incident_type`, `dim_drivers.home_hub_id → dim_hubs`
  (`:43`), and `fct_incidents.hub_id → dim_hubs` (`:162`). `dim_hubs` is a straight select of
  `stg_hubs`, and the `stg_*` FKs are already tested against `stg_hubs`. They cost a few queries
  and catch nothing new. I left them in place because removal is a style call for the owners.
- **Nullable-FK `relationships` checked:** none are trivially satisfied on the local data. The
  weakest is `stg_legal_docs.driver_id` (1 of 9 non-null) and `stg_crm_notes.shipment_id` (1 of 22
  non-null). Both are real tests, just thinly exercised.

#### M5. `int_shipment_touchpoints` model description contradicted its SQL. *Fixed*

- **Skill/rule:** `maintaining-dbt-documentation`: *"Leave existing descriptions alone unless the
  SQL has changed and they are now wrong"*. *This is an edit to an existing description, flagged
  separately as the skill requires.*
- **Evidence:** the old description said shipment IDs come "from free text via regex (dispatch
  notes, Slack, CRM notes, incident reports)". The SQL header (`:2-9`) and CTEs show regex is used
  only for dispatch notes; CRM notes and incident reports use typed columns; call transcripts
  inherit through CRM notes; and Slack is explicitly **not** a source.

#### M6. Column documentation coverage is low. *Partly fixed*

- **Skill/rule:** `maintaining-dbt-documentation` (audit + backfill, trace through `ref()`, don't
  guess); `writing-documentation.md` (*"Never … simply restate the entity's name. Describe why"*).
- **Evidence:** output of `audit_coverage.py`:

  | Folder | Models (before → after) | Declared columns documented (before → after) |
  |---|---|---|
  | marts | 6/6 | **0/18 → 32/32** |
  | intermediate | 2/2 | 1/4 → 10/10 |
  | utilities | 1/1 | 0/1 → 1/1 |
  | staging | 17/17 | 2/67 → 6/70 |
  | context | 16/21 | 1/21 → 2/21 |

  The script counts only columns *declared* in YAML. Most model columns aren't declared at all, so
  real coverage is lower than the table shows.
- **Still open:**
  - Five undocumented models: `call_transcripts_hashed`, `crm_notes_hashed`,
    `incident_reports_hashed`, `legal_docs_hashed`, `support_tickets_hashed`.
  - Ten `models/context/ai/` models (5 `*_classify`, 5 `*_embedded_classified`) have no YAML entry.
    Because they are disabled in the gate they are not in the manifest, so the auditor can't see
    them.
  - Staging columns are mostly undeclared.
  - Model descriptions like `"Hub dimension."` and `"One row per hub."` are the minimum allowed.
- **Needs a human answer:** what `stg_incidents.severity` 1–4 means (is 1 most or least severe?).
  Neither the seed nor the SQL says, so I did not document it.

### Low

- **L1. The time spine has a hardcoded range** (`time_spine_daily.sql:9-10`, 2024-01-01 to
  2026-12-31). `building-dbt-semantic-layer` → `time-spine.md` builds spines relative to
  `current_date`. The seed data is all 2025, so it is fine today. The spine is otherwise correct:
  `time_spine:` + `standard_granularity_column` + `granularity: day` (`_utilities.yml:6-10`).
- **L2. Semantic layer design.** Checked against `building-dbt-semantic-layer`:
  - Passes: latest spec used consistently (no top-level `semantic_models:`), a time dimension is
    present (`agg_time_dimension: created_at`), every metric has name/label/description/type, the
    ratio and the `offset_window: 1 quarter` derived metric are well-formed (`_marts.yml:132-149`),
    and the time spine is configured.
  - Gaps: the `client` foreign entity has no semantic model with `client` as its primary entity,
    so it joins to nothing. Client attributes are denormalised into `fct_shipments` instead.
    `best-practices.md` says *"Prefer normalization … Pure dimensional tables only need a primary
    entity"*. `on_time_shipments` also uses a `case` expression rather than a `filter` on the
    `status` dimension.
  - Known MetricFlow behaviour, already documented in `CHANGES_FROM_PUBLIC.md`: a finer-grain time
    filter makes the change metric return wrong values silently.
- **L3. Partial parse produced a false duplicate-metric error.** After my YAML edit to
  `_marts.yml`, `dbt parse` failed with *"duplicate … metric.jaffle_logistics.on_time_rate"*.
  `dbt parse --no-partial-parse` was clean, and the gate passed. I saw this once and could not
  re-run a reproduction. If you see it, use `--no-partial-parse` after editing model-nested
  metrics.
- **L4. Hygiene** (`running-dbt-commands` / `writing-data-tests.md`):
  - YAML uses the older `tests:` key, while the skill examples use `data_tests:`.
  - The `_staging.yml:3-5` header promises "accepted_values on every enum", but
    `stg_dispatch_notes.exception_type` (7 values locally), `stg_slack_threads.channel` and
    `stg_clients.region` have none.
  - `require-dbt-version: [">=1.12.0"]` (`dbt_project.yml:7`) has no upper bound.
- **L5. Layering and naming** (`using-dbt-for-analytics-engineering`, *"Conform to the existing
  style"*):
  - `models/context/` mixes `int_*` models with unprefixed intermediate-grain models (`split_*`,
    `chunk_*`, `*_meta`, `*_hashed`).
  - The `replace(body, '~~NL~~', chr(10))` newline restore is copy-pasted into nine staging
    models. `docs/multi-platform.md:57-62` calls this deliberate; a macro would be the DRY form.
  - Otherwise the staging layer does what dbt expects: one seed per model, rename/cast only, no
    joins, views. Marts are tables.
- **L6. `fct_account_health`** (`fct_account_health.sql:46-50`):
  - Shipments drive the model, so tickets and incidents in a client-month with no shipments are
    dropped. There are 0 such rows locally; this is now documented on the column.
  - `order by` in a table materialisation costs a sort and is not preserved on Delta.
- **L7. Doc drift on where vars live.** `README.md:49`, `docs/multi-platform.md:85`,
  `models/context/_context.yml:12` and `models/context/ai/_context_ai.yml:7` point to
  `dbt_project.yml`. The values are set in `vars.yml`; `dbt_project.yml` only holds the
  `var(..., false)` fallback.

### `docs/multi-platform.md` claims vs the SQL

| Claim | Verdict |
|---|---|
| All truncation via `dbt.date_trunc` | ✅ No raw `date_trunc` in `models/`/`macros/` |
| `double`/`try_cast`/`varchar` replaced | ✅ `double` only inside `target.type == 'duckdb'` branches |
| `split_part`/`position` normalised | ✅ `int_transcript_turns.sql:62,64` use `dbt.split_part`/`dbt.position` |
| Newline restore in all 9 text staging models | ✅ Present in all 9 |
| `column_types` override "harmless" elsewhere | ❌ Narrows to 32-bit on DuckDB (M2) |
| Required vars set "in `dbt_project.yml`" | ❌ They are in `vars.yml` (L7) |
| Regex portable | ⚠️ Through target-branching macros; non-DuckDB branch untested locally (H1) |

---

## 4. What this PR changes

| File | Change | Finding |
|---|---|---|
| `models/staging/_staging.yml` | `not_null` + description on `stg_shipments.status`, `stg_shipments.created_at`, `stg_support_tickets.opened_at`, `stg_incidents.occurred_at` | H2 |
| `models/intermediate/_intermediate.yml` | Corrected `int_shipment_touchpoints` description; removed tautological `accepted_values` on `source`; documented `touchpoint_key`, `source`, `artifact_id` and all `int_client_monthly_sla` columns | M4, M5, M6 |
| `models/context/_context.yml` | Removed tautological `relationships` on `int_transcript_turns.transcript_id` (kept `not_null`); documented the column | M4 |
| `models/marts/_marts.yml` | Column descriptions for all declared mart columns, plus derived columns (`is_ontime`, `touchpoint_count`, `delivered_at`, `sla_ontime_pct`, `ontime_pct`, `sla_target`, `ontime_vs_target`, `ticket_count`, `incident_count`, `report_count`, `work_order_count`, `has_report`). No test or semantic config changed. | M6 |
| `models/utilities/_utilities.yml` | Documented `time_spine_daily.date_day`, including its fixed range | M6, L1 |

No model SQL, materialisation, contract, access, group or version was changed. Every description
was traced through the SQL and `ref()` chain or checked in the local build (for example, `delayed`
shipments all have `delivered_at` set, and the 26 null `delivered_at` rows are exactly the 21
failed + 5 returned).

**Not attempted, listed above:** unit tests (H1), contracts/exposures/access/groups (M1), float
retyping (M2), the on-time DRY refactor (M3), removing redundant mart tests (M4), remaining doc
backfill for `staging/` and `context/` (M6), and everything under Low.

---

## 5. Deferred: data-dependent checks

The dbt Platform Nightly is mid-rebuild and the run before it failed, so none of these were run
against production. All are **deferred**.

- Confirm the 4 new `not_null` tests pass on the Databricks tables. The inputs are the same seed
  CSVs, but Databricks seed type inference and blank handling were not verified.
- Confirm the actual Databricks column types of `sla_ontime_pct`/`perf_score` (FLOAT vs DOUBLE)
  for M2.
- Semantic Layer validation (`dbt sl validate`) and test queries of `on_time_rate` /
  `on_time_rate_change_vs_prior_quarter_pts`.
- AI-layer tests in prod (`knowledge_base.source_id`, the `*_embed` orphan `relationships`), and
  whether `source_id` is unique across the five sources. It is locally across the `*_hashed`
  inputs, but `knowledge_base` itself was not built.
- Whether `fct_account_health` drops any ticket or incident months on prod (L6).

## 6. What I could not check

- The `models/context/ai/` layer: disabled in the gate (`ai_functions_enabled: false`), so it is
  absent from the manifest and its tests never ran.
- Non-DuckDB SQL branches (Databricks, BigQuery, Snowflake) in `macros/portable.sql` and
  `int_transcript_turns.sql`. Only DuckDB is available locally.
- Fusion parsing, `mf validate-configs` and `dbt sl validate`. No MetricFlow or Fusion CLI was
  provided, and I installed nothing.
- `profiles.yml` and the Nightly job definition, including whether it uses `--select` or excludes
  unit tests. These are outside the worktree.
- A reproduction of the partial-parse error (L3).
