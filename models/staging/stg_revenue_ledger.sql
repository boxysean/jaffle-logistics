-- One row per account-month (2020-01 .. 2025-12). Light typing; blank measurement
-- columns -> null. No joins. revenue_month_key carries the grain for a unique test.
select
    client_id || ':' || cast(cast(revenue_month as date) as {{ dbt.type_string() }}) as revenue_month_key,
    client_id,
    cast(revenue_month as date)                                     as revenue_month,
    cast(contracted_base_revenue as {{ dbt.type_numeric() }})       as contracted_base_revenue,
    cast(accessorial_revenue as {{ dbt.type_numeric() }})           as accessorial_revenue,
    cast(credited_amount as {{ dbt.type_numeric() }})               as credited_amount,
    cast(net_revenue as {{ dbt.type_numeric() }})                   as net_revenue,
    cast(invoice_count as {{ dbt.type_int() }})                     as invoice_count,
    -- cast to string first so nullif works whether the seed typed these columns or
    -- delivered them as raw strings (blank before the 2023 shipment record)
    cast(nullif(cast(shipment_count as {{ dbt.type_string() }}), '') as {{ dbt.type_int() }})            as shipment_count,
    cast(nullif(cast(ontime_pct as {{ dbt.type_string() }}), '') as {{ dbt.type_float() }})              as ontime_pct,
    cast(nullif(cast(trailing_12m_ontime_pct as {{ dbt.type_string() }}), '') as {{ dbt.type_float() }}) as trailing_12m_ontime_pct,
    cast(sla_ontime_pct as {{ dbt.type_float() }})                  as sla_ontime_pct,
    measurement_basis
from {{ ref('revenue_ledger') }}
