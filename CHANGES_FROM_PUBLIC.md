# Changes from the public jaffle-logistics project

This branch (`search_exploration`) adds a Semantic Layer metric, a query-time
search over the knowledge base, and an orchestration skill to the public
reference project. Together they support one demo. A bare question such as "How
is our on-time delivery performance?" returns governed metric movement from the
Semantic Layer, then explains why it moved from documents in the knowledge base.

Everything not listed below matches the public project.

## Summary

| Change | Location | Type |
|---|---|---|
| Daily time spine | `models/utilities/` | New models |
| Shipment semantic model and four metrics | `models/marts/_marts.yml` | Modified |
| Search contract on `knowledge_base` | `models/context/ai/_context_ai.yml` | Modified |
| Query-time search skill | `.agents/skills/knowledge-base-search/` | New |
| Metric-to-context orchestration skill | `.agents/skills/explain-metric-movement/` | New |
| Skill discovery symlinks | `.claude/skills/` | New, local only |
| Ignore rules | `.gitignore` | Modified |
| Regenerated lockfile | `package-lock.yml` | Modified, no functional change |

## 1. Daily time spine

**What.** `time_spine_daily.sql` builds one row per day from 2024-01-01 up to
2027-01-01. `_utilities.yml` registers it as the Semantic Layer time spine on
`date_day`, with `unique` and `not_null` tests.

**Why.** The public project has no Semantic Layer. The change metric compares a
quarter with the one before it, and MetricFlow needs a time spine to compute that
offset.

**How it is used.** MetricFlow reads it when a query includes
`on_time_rate_change_vs_prior_quarter_pts`. The model has to be built in the
production environment. A compile does not create the table, and the offset
metric failed with a missing-table error until it was built. The spine runs past
the end of the data, so queries return an empty trailing quarter, Q1 2026.

## 2. Shipment semantic model and metrics

**What.** `fct_shipments` in `models/marts/_marts.yml` becomes a semantic model
named `shipments`, with `created_at` as the time dimension at day grain. It
declares a `shipment` primary entity and a `client` foreign entity. The
dimensions are `status`, `client_name`, `client_tier`, `origin_city`, and
`service_level`. Four metrics sit on it.

| Metric | Type | Definition |
|---|---|---|
| `shipments` | simple | count of shipments |
| `on_time_shipments` | simple | shipments with status `delivered` |
| `on_time_rate` | ratio | on-time shipments over shipments |
| `on_time_rate_change_vs_prior_quarter_pts` | derived | change in on-time rate versus one quarter earlier, in points |

The existing tests on `fct_shipments` are unchanged.

**Why.** The public project calculates on-time delivery only in SQL, in
`int_client_monthly_sla` and the `is_ontime` flag. A governed metric gives the
demo a number whose movement can be queried by quarter and by client.

**How it is used.** Agents call `list_metrics` and `query_metrics` through the
dbt MCP server. "On time" means status `delivered`. Late arrivals carry status
`delayed`, and failed or returned shipments never arrive. The data has no
promised-delivery date, so lateness comes from that status flag. Quarterly values
for Jaffle Equipment were checked against a plain SQL calculation and matched.

## 3. Search contract on `knowledge_base`

**What.** A `meta.mcp_search` block on `knowledge_base` in
`models/context/ai/_context_ai.yml`, with `version: 1`, `shape: knowledge_base`,
`content_source: user_generated`, and `embedding_model` taken from the project's
`embedding_model` var.

**Why.** It follows the contract in the Warehouse Search for dbt-mcp proposal.
Tooling can then read the embedding model and the trust level from model
metadata and does not hardcode them. The query vector must come from the same
model as the stored vectors.

**How it is used.** The search skill reads `meta.mcp_search.embedding_model` and
`content_source` through `get_node_details`. `content_source` is a single value
per index, but this corpus mixes staff-written and customer text, so the most
restrictive value is used.

## 4. Query-time search skill

**What.** `.agents/skills/knowledge-base-search/` holds `SKILL.md` and
`references/query-templates.md`. It is a stand-in for the proposal's
`search_documents` tool. The templates cover Snowflake, Databricks, and
BigQuery, and only Snowflake has been run. Each template embeds the question once
in a CTE, tags the query with a leading comment, breaks score ties on
`source_key`, and returns a 600-character snippet. The skill documents the
literal-escaping rules and a response envelope that follows the proposal.

**Why.** The public project shows retrieval at build time, through
`models/context/ai/search.sql` and `analyses/the_pattern/`. This adds retrieval
for an arbitrary question at query time, without building a model, and it
prototypes the proposed tool contract.

**How it is used.** The orchestration skill calls it, or a user can ask for a
search directly. It resolves the relation and embedding model with
`get_node_details`, finds the warehouse type in the latest run's manifest, then
runs one SQL statement with `execute_sql`. That statement is the only SQL the
skill runs. Filter values come from the model details. Each search makes one
paid embedding call. The skill describes retrieved content and never claims
something is absent from the corpus.

## 5. Metric-to-context orchestration skill

**What.** `.agents/skills/explain-metric-movement/SKILL.md` ties the two channels
together in seven steps. It measures the movement, locates the segment by entity,
chooses what to explain, resolves the mover to the knowledge base key, retrieves
context, reconciles claims against a finer grain, and writes a short answer.

**Why.** The public project shows the metric and the context separately. This
skill is the demo's point: the number alone is not the story. It uses only the
Semantic Layer and the knowledge base search and runs no other SQL. Causes come
only from retrieved text, so a segment split or a volume change is reported as
where something moved and not as a reason.

**How it is used.** It triggers on a question about how a metric is performing.
The answer has a fixed shape of about 230 words. It has a headline, one table,
up to three document findings, a list of places where notes and numbers
disagree, a footer, and the generated search SQL. For a metrics-only comparison,
prefix the question with "Using only the Semantic Layer," which worked in one
test. Launching Claude Code with the skills hidden and `execute_sql` removed is a
stronger switch, built from documented flags and not yet tried.

## 6. Skill discovery symlinks

**What.** Two symlinks in `.claude/skills/` point to the skills in
`.agents/skills/`.

**Why.** Claude Code scans `.claude/skills/` and does not scan `.agents/`.

**How it is used.** `.claude` is gitignored, so the symlinks exist only on this
machine. A fresh clone needs them recreated.

```
mkdir -p .claude/skills
ln -s ../../.agents/skills/knowledge-base-search .claude/skills/knowledge-base-search
ln -s ../../.agents/skills/explain-metric-movement .claude/skills/explain-metric-movement
```

## 7. Ignore rules

`.gitignore` gains `.mcp*`, `scratch/`, and `.claude`. They keep the local MCP
configuration, scratch notes, and the skill symlinks out of commits. The
`.claude` rule is also why the symlinks are not shared.

## 8. Lockfile

`package-lock.yml` lists the same packages and versions, `dbt_context_engineering`
0.1.2 and `dbt_utils` 1.4.1. Only the formatting and the hash differ, because a
different dbt engine regenerated it. It is not a functional change and can be
reverted to the public file to reduce noise in the diff.

## Local setup that is not in the repo

The demo needs a dbt MCP server entry in a local `.mcp.json`. The entry needs
`"type": "http"`, because without it Claude Code skips the server. Its headers
come from the environment variables `DBT_TOKEN`, `DBT_PROD_ENV_ID`,
`DBT_DEV_ENV_ID`, and `DBT_USER_ID`. The file is gitignored.

## Operating notes

- **Builds.** The time spine and `knowledge_base` must be built in the production
  environment. `knowledge_base` needs `ai_functions_enabled` true to exist. It is
  a union of five tables and makes no AI calls itself.
- **Discovery state.** `get_node_details` reflects the most recent build-type
  run. A build without the AI layer removes `knowledge_base` from it, and the
  search skill then stops. Compile runs did not restore it. A build that selects
  only `knowledge_base` with the AI vars on did.
- **Filter grain.** A time filter at a finer grain than the query makes the change
  metric return wrong values with no error. A day-grain `metric_time` filter on a
  quarter query turns the prior-period value into 100%, because the prior-period
  rate is computed per day and the best day is taken. Use no time filter, or a
  filter at the query's grain. Filters on a dimension or entity are safe.

## Known limits

- Only the Snowflake search template has been run.
- Movers that map to most accounts, such as an origin hub, cannot be narrowed by
  account, and the knowledge base has no hub column. This is a data modeling gap.
- Retrieval quality limits described in the public `docs/comparison.md` still
  apply, such as boilerplate chunks and near-duplicate tickets.
- Agent output varies between runs. In seven test runs the client pick and the
  main citations were stable. Claims of uniqueness or share, such as "the only
  client," recurred and were sometimes wrong.
