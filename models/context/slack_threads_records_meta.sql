-- Deliberately NOT chunked (same whole-record pattern as ticket_records_meta): a
-- Slack thread body is already the atomic embedding unit, one operational
-- conversation, so this reshapes it straight to the chunk-shaped output instead of
-- calling chunk(). No packing/window SQL, no split_sentences step; chunk_seq is
-- always 1 by construction, not by an assumption about thread length. Feeds
-- slack_threads_hashed directly.
--
-- Slack threads carry no client_id column, so the account key is resolved from the
-- typed IDs the thread cites (linked_ids first, then body), in precedence order:
--   1. an explicit CLI-#### id;
--   2. else the dominant client of the cited RTE-... route;
--   3. else the dominant client of the cited INC-... incident's route;
--   4. else null, never guessed.
-- Dominant client = most exceptions attributed, then largest stop share, the same
-- convention as tests/assert_columbus_2025_damage_attributed_to_equipment.sql.
-- regex_first returns '' on no match under duckdb, hence the nullif()s.
{{ config(materialized='table') }}

with dominant_client as (
    select
        route_id,
        client_id,
        row_number() over (
            partition by route_id
            order by exception_attributed desc, stop_share desc
        ) as _client_rank
    from {{ ref('stg_route_client_attribution') }}
),

cited as (
    select
        thread_id,
        body,
        started_at,
        nullif({{ regex_first("coalesce(linked_ids, '') || ' ' || body", 'CLI-[0-9]{4}') }}, '')                     as cited_client_id,
        nullif({{ regex_first("coalesce(linked_ids, '') || ' ' || body", 'RTE-[A-Z]{3}-[0-9]{8}-[0-9]{3}') }}, '')   as cited_route_id,
        nullif({{ regex_first("coalesce(linked_ids, '') || ' ' || body", 'INC-[0-9]{4}-[0-9]{5}') }}, '')            as cited_incident_id
    from {{ ref('stg_slack_threads') }}
),

threads as (
    select
        c.thread_id,
        c.body,
        c.started_at,
        coalesce(c.cited_client_id, rd.client_id, id.client_id) as client_id
    from cited c
    left join dominant_client rd
        on  rd.route_id = c.cited_route_id
        and rd._client_rank = 1
    left join {{ ref('stg_incidents') }} i
        on  i.incident_id = c.cited_incident_id
    left join dominant_client id
        on  id.route_id = i.route_id
        and id._client_rank = 1
)

select
    thread_id || '::1'                                     as chunk_id,
    thread_id                                              as partition_key,
    1                                                       as chunk_seq,
    {{ dbt_context_engineering.array_agg('thread_id', 'thread_id') }} as source_rows,
    body                                                    as chunk_text,
    1                                                       as n_source_rows,
    ceil(length(body) / 4.0)                                as token_estimate,
    client_id,
    'slack_thread'                                          as source_type,
    'jaffle_logistics://slack_thread/' || thread_id         as citation_url,
    cast(started_at as {{ dbt.type_timestamp() }})          as artifact_ts
from threads
group by thread_id, body, client_id, started_at
