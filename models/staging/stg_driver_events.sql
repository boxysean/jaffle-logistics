-- One row per driver employment event: hire, leave, termination, certification.
select
    event_id,
    driver_id,
    hub_id,
    cast(event_date as date)            as event_date,
    event_type,
    reason,
    cast(voluntary as boolean)          as voluntary
from {{ ref('driver_events') }}
