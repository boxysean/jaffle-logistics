-- The revenue ledger must reconcile, to itself and to the ops record. Zero rows
-- expected. Each failing row names the check it broke:
--   net_mismatch      net_revenue != base + accessorials - credits (beyond a cent)
--   negative_credit   credited_amount < 0 (credits are positive, subtracted)
--   unassessed_credit a credit outside a full trailing-12-month window
--   shipment_mismatch ledger shipment_count / ontime_pct disagree with stg_shipments
with ledger as (
    select * from {{ ref('stg_revenue_ledger') }}
),
shipped as (
    select
        client_id,
        {{ dbt.date_trunc('month', 'created_at') }}                 as revenue_month,
        count(*)                                                    as shipments,
        round(100.0 * sum(case when status = 'delivered' then 1 else 0 end)
              / count(*), 1)                                        as ontime_pct
    from {{ ref('stg_shipments') }}
    group by 1, 2
),
checks as (
    select
        l.revenue_month_key,
        case
            when abs(l.net_revenue - (l.contracted_base_revenue + l.accessorial_revenue
                                      - l.credited_amount)) >= 0.01
                then 'net_mismatch'
            when l.credited_amount < 0
                then 'negative_credit'
            when l.credited_amount > 0 and l.measurement_basis != 'trailing_12m'
                then 'unassessed_credit'
            when l.shipment_count is not null
                 and (s.shipments is null
                      or l.shipment_count != s.shipments
                      -- both sides are 1dp; the slack only absorbs float storage error
                      or abs(l.ontime_pct - s.ontime_pct) > 0.01)
                then 'shipment_mismatch'
        end as failed_check
    from ledger l
    left join shipped s
        on s.client_id = l.client_id
       and cast(s.revenue_month as date) = l.revenue_month
)
select *
from checks
where failed_check is not null
