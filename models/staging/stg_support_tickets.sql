-- One row per support ticket (a threaded conversation lives in body).
select
    ticket_id,
    client_id,
    nullif(shipment_id, '')         as shipment_id,
    cast(opened_at as timestamp)    as opened_at,
    channel,
    status,
    {{ dbt.safe_cast("nullif(cast(csat as " ~ dbt.type_string() ~ "), '')", dbt.type_int()) }} as csat,
    -- body is stored with embedded newlines escaped to '~~NL~~' (portable seed-
    -- loading workaround: some engines reject a quoted CSV field containing a
    -- real newline unless configured otherwise); restore them here.
    replace(body, '~~NL~~', chr(10)) as body,
    -- response clock. resolved_at / resolution_hours are blank for open and
    -- pending tickets; the seed loader may already have typed them (timestamp /
    -- number), so go via a string before nullif, as csat does.
    cast(first_response_at as timestamp)    as first_response_at,
    cast(nullif(cast(resolved_at as {{ dbt.type_string() }}), '') as timestamp) as resolved_at,
    cast(first_response_hours as double)    as first_response_hours,
    cast(nullif(cast(resolution_hours as {{ dbt.type_string() }}), '') as double) as resolution_hours
from {{ ref('support_tickets') }}
