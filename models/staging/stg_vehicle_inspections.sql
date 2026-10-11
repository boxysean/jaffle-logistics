-- One row per vehicle inspection, with the odometer at the time of inspection.
select
    inspection_id,
    vehicle_id,
    hub_id,
    cast(inspected_at as date)          as inspected_at,
    inspection_type,
    cast(odometer_reading as integer)   as odometer_reading,
    result,
    defect_area,
    notes
from {{ ref('vehicle_inspections') }}
