-- Service intervals per vehicle: each periodic inspection against the one before it,
-- in km and in days, measured from the odometer at the time of inspection. The
-- schedule is 20,000 km or 365 days, whichever comes first; km_over_interval and
-- days_over_interval are how far past each target the vehicle ran before it was
-- serviced. This is the "was servicing on time" measure the fleet report was missing.
-- Grain: one row per periodic inspection. A vehicle's first periodic has no previous
-- one, so its lags (and the measures built on them) are null and it reads 'ok'.

with periodic as (
    select * from {{ ref('stg_vehicle_inspections') }}
    where inspection_type = 'periodic'
),

lagged as (
    select
        vehicle_id,
        hub_id,
        inspection_id,
        inspected_at,
        odometer_reading,
        lag(inspected_at) over (
            partition by vehicle_id order by inspected_at, inspection_id
        )                                                           as previous_inspected_at,
        lag(odometer_reading) over (
            partition by vehicle_id order by inspected_at, inspection_id
        )                                                           as previous_odometer_reading
    from periodic
),

measured as (
    select
        *,
        {{ dbt.datediff('previous_inspected_at', 'inspected_at', 'day') }}
                                                                    as days_since_previous,
        odometer_reading - previous_odometer_reading                as km_since_previous,
        20000                                                       as service_interval_km,
        365                                                         as service_interval_days
    from lagged
)

select
    vehicle_id,
    hub_id,
    inspection_id,
    inspected_at,
    odometer_reading,
    previous_inspected_at,
    previous_odometer_reading,
    days_since_previous,
    km_since_previous,
    service_interval_km,
    greatest(0, km_since_previous - service_interval_km)           as km_over_interval,
    service_interval_days,
    greatest(0, days_since_previous - service_interval_days)       as days_over_interval,
    case
        when km_since_previous > service_interval_km
         and days_since_previous > service_interval_days then 'over_both'
        when km_since_previous > service_interval_km      then 'over_km'
        when days_since_previous > service_interval_days  then 'over_days'
        else 'ok'
    end                                                             as interval_status
from measured
