-- The ops-floor half of the Columbus story: every Slack thread that cites a 2025
-- handling-damage incident with a route must land on Jaffle Equipment (CLI-0042) in
-- the corpus, through the same attribution bridge as
-- assert_columbus_2025_damage_attributed_to_equipment (thread -> cited route or
-- incident -> the route's dominant client). Checks slack_threads_records_meta itself,
-- so it proves the account key the knowledge base will carry, not a re-derivation.
-- Covers the HUB-CMH bay-3 cluster's threads included.
--
-- Threads, not dispatch notes: no 2025 dispatch note sits on a damage incident's
-- route, so the notes don't carry this story; 2025 HUB-CMH notes spread across that
-- hub's accounts by route, which is the bridge working, not a gap. Incidents with no
-- route are left out: their threads correctly stay null unless they cite a CLI- id.
-- Zero rows expected; each row is a thread attributed to another account, or none.
with damage as (
    select incident_id
    from {{ ref('stg_incidents') }}
    where incident_type = 'damage'
      and route_id is not null
      and extract(year from occurred_at) = 2025
),
citing as (
    select distinct
        d.incident_id,
        t.thread_id
    from damage d
    join {{ ref('stg_slack_threads') }} t
        on (coalesce(t.linked_ids, '') || ' ' || t.body) like '%' || d.incident_id || '%'
)
select
    c.incident_id,
    c.thread_id,
    m.client_id
from citing c
left join {{ ref('slack_threads_records_meta') }} m
    on m.partition_key = c.thread_id
where m.client_id is null
   or m.client_id != 'CLI-0042'
