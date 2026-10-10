-- Deliberately NOT chunked (same whole-record pattern as ticket_records_meta): a
-- dispatch note body is already the atomic embedding unit, one operational record
-- off the ops floor, so this reshapes it straight to the chunk-shaped output
-- instead of calling chunk(). No packing/window SQL, no split_sentences step;
-- chunk_seq is always 1 by construction, not by an assumption about note length.
-- Feeds dispatch_notes_hashed directly.
--
-- Dispatch notes carry no client_id of their own, only a route_id, so the account
-- key is the route's dominant client through the attribution bridge (most
-- exceptions attributed, then largest stop share), the same convention as
-- tests/assert_columbus_2025_damage_attributed_to_equipment.sql. left join:
-- client_id stays null when a route has no attribution rows, never guessed.
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

notes as (
    select
        n.note_id,
        n.body,
        n.noted_at,
        d.client_id
    from {{ ref('stg_dispatch_notes') }} n
    left join dominant_client d
        on  d.route_id = n.route_id
        and d._client_rank = 1
)

select
    note_id || '::1'                                       as chunk_id,
    note_id                                                as partition_key,
    1                                                       as chunk_seq,
    {{ dbt_context_engineering.array_agg('note_id', 'note_id') }} as source_rows,
    body                                                    as chunk_text,
    1                                                       as n_source_rows,
    ceil(length(body) / 4.0)                                as token_estimate,
    client_id,
    'dispatch_note'                                         as source_type,
    'jaffle_logistics://dispatch_note/' || note_id          as citation_url,
    cast(noted_at as {{ dbt.type_timestamp() }})            as artifact_ts
from notes
group by note_id, body, client_id, noted_at
