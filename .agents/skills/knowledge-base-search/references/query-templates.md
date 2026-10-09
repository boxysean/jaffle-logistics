# Query templates by warehouse

Placeholders:

- `<relation>`: fully qualified `knowledge_base` relation from Step 1.
- `<model>`: embedding model from Step 2.
- `<question_literal>`: the question as a complete SQL string literal, quotes
  included, built with the escaping rules below.
- `<filters>`: `and`-joined predicates from Step 4, with columns prefixed by the
  `k.` alias or `base.` on BigQuery. Drop the `where` clause when there are none.
- `<top_k>`: result count.

Each template embeds the question once in a CTE, tags the query with a leading
comment for warehouse-side cost attribution, cuts `snippet` to 600 characters,
and breaks score ties on `source_key` so the `top_k` cutoff is stable. These
follow the compiled query in the Warehouse Search for dbt-mcp proposal and the
`embed` and `vector_search` macros in `dbt_context_engineering`. If either
changes, update these templates to match.

## Escaping the question

These rules mirror the package's `str_literal` macro. Apply them in this order.

1. Double every backslash. This applies to Snowflake, Databricks, and BigQuery,
   where backslash is an escape character inside string literals.
2. Split the text on newline characters. Wrap each part in single quotes and
   join the parts with ` || chr(10) || `. BigQuery rejects a raw newline inside a
   literal, and this form is valid on every engine.
3. Escape single quotes inside each part. Snowflake and Databricks use `''`.
   BigQuery uses `\'`, because it reads `''` as two adjacent literals.

A question with no backslashes, newlines, or quotes becomes `'<question>'`.

## Snowflake

```sql
/* dbt-mcp:search index=knowledge_base mode=vector top_k=<top_k> */
with q as (
    select ai_embed('<model>', <question_literal>) as v
)
select
    vector_cosine_similarity(k.embedding, q.v) as score,
    k.source_key, k.source_id, k.source_type, k.citation_url, k.ts, k.classification,
    left(k.text, 600) as snippet
from <relation> k, q
where <filters>
order by score desc, k.source_key
limit <top_k>
```

## Databricks

`ai_query` returns `array<double>`, and the stored column is `array<float>`, so
the query vector is cast to match.

```sql
/* dbt-mcp:search index=knowledge_base mode=vector top_k=<top_k> */
with q as (
    select cast(ai_query('<model>', <question_literal>) as array<float>) as v
)
select
    vector_cosine_similarity(k.embedding, q.v) as score,
    k.source_key, k.source_id, k.source_type, k.citation_url, k.ts, k.classification,
    left(k.text, 600) as snippet
from <relation> k, q
where <filters>
order by score desc, k.source_key
limit <top_k>
```

## BigQuery

`VECTOR_SEARCH` is a table function. It embeds the query once through its query
subquery, and filters apply to the base subquery. Add
`connection_id => '<connection>'` inside `AI.EMBED` when the project sets the
`bq_connection` var. `VECTOR_SEARCH` resolves ties inside the function, so the
outer `order by` stabilizes the returned order but not which row makes the cutoff.

```sql
/* dbt-mcp:search index=knowledge_base mode=vector top_k=<top_k> */
select
    (1 - distance) as score,
    base.source_key, base.source_id, base.source_type, base.citation_url, base.ts,
    base.classification, left(base.text, 600) as snippet
from vector_search(
    (select * from <relation> as base where <filters>), 'embedding',
    (select (AI.EMBED(content => <question_literal>, endpoint => '<model>')).result as embedding),
    top_k => <top_k>,
    distance_type => 'COSINE',
    options => '{"use_brute_force": true}'
)
order by score desc, base.source_key
```
