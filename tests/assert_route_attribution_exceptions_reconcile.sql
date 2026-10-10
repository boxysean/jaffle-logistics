-- The attribution must cover every route and reconcile to it. Zero rows expected.
-- Each failing row names the check it broke:
--   missing_route        a route in stg_routes with no attribution rows
--   client_count         fewer than 1 or more than 4 clients on the route
--   exception_mismatch   exception_attributed does not sum to exceptions_count
with attributed as (
    select
        route_id,
        count(*)                    as client_count,
        sum(exception_attributed)   as exceptions_attributed
    from {{ ref('stg_route_client_attribution') }}
    group by route_id
),
checks as (
    select
        r.route_id,
        r.exceptions_count,
        a.client_count,
        a.exceptions_attributed,
        case
            when a.route_id is null
                then 'missing_route'
            when a.client_count < 1 or a.client_count > 4
                then 'client_count'
            when a.exceptions_attributed != r.exceptions_count
                then 'exception_mismatch'
        end as failed_check
    from {{ ref('stg_routes') }} r
    left join attributed a on a.route_id = r.route_id
)
select *
from checks
where failed_check is not null
