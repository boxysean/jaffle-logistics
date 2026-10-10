-- One row per dock event (one event at one bay). Nullable FK columns: blank strings -> null.
select
    event_id,
    hub_id,
    bay_id,
    nullif(route_id, '')                as route_id,
    nullif(vehicle_id, '')              as vehicle_id,
    nullif(driver_id, '')               as driver_id,
    cast(event_at as timestamp)         as event_at,
    event_type,
    cast(minutes_at_bay as integer)     as minutes_at_bay,
    nullif(incident_id, '')             as incident_id,
    detail
from {{ ref('dock_bay_events') }}
