-- maintenance_cost in the cost ledger must equal the sum of fleet work orders for
-- the same hub-month, for every row. This one tie is what makes the ledger
-- defensible; returns any row where the ledger and the work orders disagree.
with ledger as (
    select
        hub_id,
        {{ month_key('cost_month') }} as month_key,
        maintenance_cost
    from {{ ref('stg_cost_ledger') }}
),

work_orders as (
    select
        hub_id,
        {{ month_key('opened_at') }} as month_key,
        sum(cost)                    as work_order_cost
    from {{ ref('stg_fleet_work_orders') }}
    group by 1, 2
)

select
    l.hub_id,
    l.month_key,
    l.maintenance_cost,
    coalesce(w.work_order_cost, 0) as work_order_cost
from ledger l
left join work_orders w
    on  l.hub_id = w.hub_id
    and l.month_key = w.month_key
where l.maintenance_cost <> coalesce(w.work_order_cost, 0)
