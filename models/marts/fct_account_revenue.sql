-- Monthly account-revenue fact (grain: one row per client-month, 2020-01 .. 2025-12).
-- The revenue and cost ledger joined to the client dimension: gross, contract credits
-- and net by account, alongside the trailing-12-month on-time rate the credits are
-- assessed on. This is what puts a dollar figure on the 2025 Jaffle Equipment
-- (CLI-0042) service failure instead of a percentage.

with ledger as (
    select * from {{ ref('stg_revenue_ledger') }}
),
clients as (
    select client_id, client_name, tier, health
    from {{ ref('dim_clients') }}
)
select
    l.revenue_month_key,
    l.client_id,
    c.client_name,
    c.tier,
    c.health,
    l.revenue_month,
    l.contracted_base_revenue,
    l.accessorial_revenue,
    l.contracted_base_revenue + l.accessorial_revenue               as gross_revenue,
    l.credited_amount,
    l.net_revenue,
    round(100.0 * l.credited_amount
          / nullif(l.contracted_base_revenue + l.accessorial_revenue, 0), 2) as credit_rate_pct,
    -- gross per shipment; null before the 2023 shipment record (volume is imputed there)
    round((l.contracted_base_revenue + l.accessorial_revenue)
          / nullif(l.shipment_count, 0), 2)                         as revenue_per_shipment,
    l.shipment_count,
    l.invoice_count,
    l.ontime_pct,
    l.trailing_12m_ontime_pct,
    l.sla_ontime_pct,
    round(l.trailing_12m_ontime_pct - l.sla_ontime_pct, 1)          as ontime_vs_target,
    l.measurement_basis
from ledger l
left join clients c on c.client_id = l.client_id
order by l.client_id, l.revenue_month
