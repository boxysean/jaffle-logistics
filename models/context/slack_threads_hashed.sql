-- content_hash needs a real column upstream of the embedding model (not a
-- same-SELECT alias, BigQuery won't resolve that, and the guard/log can't
-- meter it otherwise). Hash the EXACT string handed to embed() (chunk_text,
-- the whole Slack thread body: a thread is already the atomic embedding
-- unit, so slack_threads_records_meta deliberately never calls chunk()).
-- Zero AI-function cost (still ordinary cloud compute cost on
-- Snowflake/BigQuery/Databricks, free only on local DuckDB).
{{ config(materialized='view', docs={'node_color': '#7FAFAF'}) }}

select
    chunk_id,
    partition_key,
    client_id,
    chunk_text,
    source_type,
    citation_url,
    artifact_ts,
    {{ dbt_context_engineering.content_hash('chunk_text') }} as content_hash
from {{ ref('slack_threads_records_meta') }}
where chunk_text is not null
  and length(trim(chunk_text)) > 0
