-- The 2025 handling-damage incidents must land on Jaffle Equipment (CLI-0042) through
-- the attribution bridge: incident -> route -> the route's dominant client (most
-- exceptions attributed, then largest stop share). Covers every 2025 damage incident
-- with a route, the HUB-CMH bay-3 cluster included. Zero rows expected; each row is an
-- incident whose route is led by another account.
with damage as (
    select incident_id, route_id, hub_id, occurred_at
    from {{ ref('stg_incidents') }}
    where incident_type = 'damage'
      and route_id is not null
      and extract(year from occurred_at) = 2025
),
ranked as (
    select
        route_id,
        client_id,
        exception_attributed,
        stop_share,
        row_number() over (
            partition by route_id
            order by exception_attributed desc, stop_share desc
        ) as _client_rank
    from {{ ref('stg_route_client_attribution') }}
)
select
    d.incident_id,
    d.route_id,
    d.hub_id,
    d.occurred_at,
    a.client_id as dominant_client_id
from damage d
join {{ ref('stg_routes') }} r on r.route_id = d.route_id
left join ranked a
    on  a.route_id = r.route_id
    and a._client_rank = 1
where a.client_id is null
   or a.client_id != 'CLI-0042'
