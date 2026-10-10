-- One row per driver-month of driver labour cost, from the driver's hire month to
-- 2025-12. hours_worked is not modelled for 2023-2025: it is that driver-month's
-- route count x 9 hours (stg_routes), so hours tie to routes exactly; before 2023,
-- when no routes are recorded, it is a modelled steady state. The driver-month
-- route count is joined back here for the cost-per-route derivation:
-- cost_per_route = total_cost / routes_run, null when the driver ran nothing that
-- month (routes_run is 0 before 2023 and in the months a driver has no routes).
with payroll as (
    select
        cast(payroll_month as date)                         as payroll_month,
        driver_id,
        hub_id,
        employment_type,
        cast(hours_worked as {{ dbt.type_numeric() }})      as hours_worked,
        cast(hourly_rate as {{ dbt.type_numeric() }})       as hourly_rate,
        cast(gross_pay as {{ dbt.type_numeric() }})         as gross_pay,
        cast(overtime_hours as {{ dbt.type_numeric() }})    as overtime_hours,
        cast(total_cost as {{ dbt.type_numeric() }})        as total_cost
    from {{ ref('payroll_monthly') }}
),

route_volume as (
    select
        driver_id,
        {{ month_key('service_date') }} as month_key,
        count(*)                        as routes_run
    from {{ ref('stg_routes') }}
    group by 1, 2
)

select
    p.payroll_month,
    p.driver_id,
    p.hub_id,
    p.employment_type,
    p.hours_worked,
    p.hourly_rate,
    p.gross_pay,
    p.overtime_hours,
    p.total_cost,
    coalesce(r.routes_run, 0)                             as routes_run,
    p.total_cost / nullif(r.routes_run, 0)                as cost_per_route
from payroll p
left join route_volume r
    on  p.driver_id = r.driver_id
    and {{ month_key('p.payroll_month') }} = r.month_key
