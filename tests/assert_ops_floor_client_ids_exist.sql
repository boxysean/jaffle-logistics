-- Relationships guard for the two ops-floor sources' derived account key: every
-- non-null client_id on dispatch_notes_records_meta and slack_threads_records_meta
-- must be a real stg_clients row. null is allowed (client_id is nullable by design,
-- never guessed); a dangling id is not. A thread citing a CLI- id that doesn't exist
-- would fail here. Zero rows expected.
with attributed as (
    select chunk_id, client_id, 'dispatch_notes_records_meta' as model_name
    from {{ ref('dispatch_notes_records_meta') }}
    where client_id is not null
    union all
    select chunk_id, client_id, 'slack_threads_records_meta' as model_name
    from {{ ref('slack_threads_records_meta') }}
    where client_id is not null
)
select a.*
from attributed a
left join {{ ref('stg_clients') }} c on c.client_id = a.client_id
where c.client_id is null
