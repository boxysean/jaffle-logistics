-- One row per hub-month of non-labour operating cost, 2020-01 .. 2025-12.
-- maintenance_cost is not modelled: it is the exact sum of that hub-month's fleet
-- work orders (stg_fleet_work_orders), which is the tie that makes the ledger
-- defensible. Route volume is joined purely for the cost-per-route derivation so
-- hubs of different sizes can be compared; route_count is 0 (and cost_per_route
-- null) before 2023, when no routes are recorded yet.
with ledger as (
    select
        cast(cost_month as date)             as cost_month,
        hub_id,
        cast(fuel_cost as integer)           as fuel_cost,
        cast(maintenance_cost as integer)    as maintenance_cost,
        cast(subcontractor_cost as integer)  as subcontractor_cost,
        cast(facility_cost as integer)       as facility_cost,
        cast(technology_cost as integer)     as technology_cost,
        cast(total_cost as integer)          as total_cost
    from {{ ref('cost_ledger') }}
),

route_volume as (
    select
        hub_id,
        {{ month_key('service_date') }} as month_key,
        count(*)                        as route_count
    from {{ ref('stg_routes') }}
    group by 1, 2
)

select
    l.cost_month,
    l.hub_id,
    l.fuel_cost,
    l.maintenance_cost,
    l.subcontractor_cost,
    l.facility_cost,
    l.technology_cost,
    l.total_cost,
    coalesce(r.route_count, 0)                            as route_count,
    l.total_cost / nullif(r.route_count, 0)               as cost_per_route
from ledger l
left join route_volume r
    on  l.hub_id = r.hub_id
    and {{ month_key('l.cost_month') }} = r.month_key
