-- Daily time spine for the Semantic Layer. MetricFlow joins to it for metric
-- offsets such as the prior-quarter comparison on on_time_rate. The range
-- covers the shipment data in seeds/shipments.csv with room on both sides.
{{ config(materialized='table') }}

with days as (
    {{ dbt.date_spine(
        'day',
        "cast('2024-01-01' as date)",
        "cast('2027-01-01' as date)"
    ) }}
)

select cast(date_day as date) as date_day
from days
