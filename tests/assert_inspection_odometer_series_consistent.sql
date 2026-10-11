-- The inspection odometer is a series, not a snapshot: along each vehicle's inspections
-- in date order it never goes down, and it never passes the vehicle's current odometer
-- (stg_vehicles.odometer, the 2025-12-31 snapshot). Zero rows expected. Each failing
-- row names the check it broke:
--   odometer_decreased     a reading is lower than the vehicle's previous one
--   exceeds_current        the vehicle's highest reading is above stg_vehicles.odometer
with ordered as (
    select
        vehicle_id,
        inspection_id,
        inspected_at,
        odometer_reading,
        lag(odometer_reading) over (
            partition by vehicle_id
            order by inspected_at, inspection_id
        ) as previous_odometer_reading
    from {{ ref('stg_vehicle_inspections') }}
),
checks as (
    select
        vehicle_id,
        inspection_id,
        odometer_reading,
        previous_odometer_reading       as compared_to,
        'odometer_decreased'            as failed_check
    from ordered
    where odometer_reading < previous_odometer_reading

    union all

    select
        o.vehicle_id,
        null,
        max(o.odometer_reading),
        v.odometer,
        'exceeds_current'
    from ordered o
    inner join {{ ref('stg_vehicles') }} v
        on v.vehicle_id = o.vehicle_id
    group by o.vehicle_id, v.odometer
    having max(o.odometer_reading) > v.odometer
)
select *
from checks
