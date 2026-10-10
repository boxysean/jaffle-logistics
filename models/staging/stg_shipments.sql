-- One row per shipment. Light typing; blank strings -> null. No joins.
select
    shipment_id,
    client_id,
    origin_hub_id,
    service_level,
    cast(created_at as timestamp)                    as created_at,
    -- cast to string first so this works whether dbt seeds delivered_at as a
    -- timestamp (empties -> null) or as a raw string; dbt.safe_cast (portable
    -- try-cast) so a genuinely malformed value becomes null instead of failing the build
    {{ dbt.safe_cast("nullif(cast(delivered_at as " ~ dbt.type_string() ~ "), '')", dbt.type_timestamp()) }} as delivered_at,
    status,
    nullif(route_id, '')                             as route_id,
    -- promised-delivery clock (scripts/generate_promised_delivery.py): hours_late is
    -- null unless the shipment is delayed; late_bucket is null for failed/returned
    cast(promised_delivery_at as timestamp)          as promised_delivery_at,
    cast(hours_late as {{ dbt.type_int() }})         as hours_late,
    nullif(late_bucket, '')                          as late_bucket
from {{ ref('shipments') }}
