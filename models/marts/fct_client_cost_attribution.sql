-- Monthly client cost-attribution fact (grain: one row per client-month, 2023-01 ..
-- 2025-12). Allocates route-level cost to accounts through the route-to-client
-- attribution bridge:
--   * exceptions: each route's exceptions_count split by exception_attributed;
--   * maintenance: each hub-month's fleet work-order cost (= stg_cost_ledger
--     maintenance_cost, reconciled by tests/assert_cost_ledger_maintenance_reconciles.sql)
--     split by the client's share of that hub-month's attributed stops
--     (stop_count x stop_share).
-- Volume (routes, attributed stops, shipments) and revenue ride along for context.
-- The allocation is BY SHARE and therefore an approximation: the bridge says which
-- accounts a route carried and in what proportion, not which account caused a given
-- breakdown or exception.

with attribution as (
    select * from {{ ref('stg_route_client_attribution') }}
),
routes as (
    select
        route_id,
        hub_id,
        cast({{ dbt.date_trunc('month', 'service_date') }} as date) as month,
        stop_count
    from {{ ref('stg_routes') }}
),
-- route x client, with the client's attributed stops on that route
route_clients as (
    select
        a.client_id,
        r.hub_id,
        r.month,
        a.route_id,
        r.stop_count * a.stop_share     as attributed_stops,
        a.exception_attributed
    from attribution a
    join routes r on r.route_id = a.route_id
),
hub_client_month as (
    select
        hub_id,
        month,
        client_id,
        sum(attributed_stops)           as attributed_stops
    from route_clients
    group by 1, 2, 3
),
hub_month as (
    select
        hub_id,
        month,
        sum(attributed_stops)           as attributed_stops
    from hub_client_month
    group by 1, 2
),
maintenance as (
    select
        hub_id,
        cost_month                      as month,
        maintenance_cost
    from {{ ref('stg_cost_ledger') }}
),
-- each hub-month's maintenance spread over its clients by attributed-stop share
allocated_maintenance as (
    select
        hc.client_id,
        hc.month,
        sum(m.maintenance_cost * hc.attributed_stops
            / nullif(hm.attributed_stops, 0))   as allocated_maintenance_cost
    from hub_client_month hc
    join hub_month hm
        on  hm.hub_id = hc.hub_id
        and hm.month = hc.month
    join maintenance m
        on  m.hub_id = hc.hub_id
        and m.month = hc.month
    group by 1, 2
),
route_volume as (
    select
        client_id,
        month,
        count(distinct route_id)        as route_count,
        sum(attributed_stops)           as attributed_stops,
        sum(exception_attributed)       as attributed_exceptions
    from route_clients
    group by 1, 2
),
shipments as (
    select
        client_id,
        cast({{ dbt.date_trunc('month', 'created_at') }} as date) as month,
        count(*)                        as shipment_count
    from {{ ref('stg_shipments') }}
    group by 1, 2
),
revenue as (
    select
        client_id,
        revenue_month                   as month,
        contracted_base_revenue + accessorial_revenue   as gross_revenue,
        net_revenue
    from {{ ref('stg_revenue_ledger') }}
),
clients as (
    select client_id, client_name, tier, health
    from {{ ref('dim_clients') }}
),
-- client x month spine over the route record (2023-01 .. 2025-12)
spine as (
    select c.client_id, m.month
    from clients c
    cross join (select distinct month from routes) m
)
select
    s.client_id || ':' || {{ month_key('s.month') }}               as client_month_key,
    s.client_id,
    c.client_name,
    c.tier,
    c.health,
    s.month,
    coalesce(v.route_count, 0)                                      as route_count,
    round(coalesce(v.attributed_stops, 0), 2)                       as attributed_stops,
    coalesce(sh.shipment_count, 0)                                  as shipment_count,
    coalesce(v.attributed_exceptions, 0)                            as attributed_exceptions,
    round(coalesce(am.allocated_maintenance_cost, 0), 2)            as allocated_maintenance_cost,
    -- maintenance per attributed stop: compares accounts of different sizes
    round(am.allocated_maintenance_cost / nullif(v.attributed_stops, 0), 2)
                                                                    as maintenance_cost_per_stop,
    rv.gross_revenue,
    rv.net_revenue,
    round(100.0 * am.allocated_maintenance_cost / nullif(rv.gross_revenue, 0), 2)
                                                                    as maintenance_pct_of_gross
from spine s
left join clients c                 on c.client_id = s.client_id
left join route_volume v            on v.client_id = s.client_id and v.month = s.month
left join shipments sh              on sh.client_id = s.client_id and sh.month = s.month
left join allocated_maintenance am  on am.client_id = s.client_id and am.month = s.month
left join revenue rv                on rv.client_id = s.client_id and rv.month = s.month
order by s.client_id, s.month
