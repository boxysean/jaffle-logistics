-- Every 2023-2025 accident incident that names a vehicle has exactly one post_incident
-- inspection, and every post_incident inspection names a real accident on the same
-- vehicle in its notes ('Linked incident: INC-YYYY-NNNNN.'). Zero rows expected. Each
-- failing row names the check it broke:
--   count_mismatch      post_incident inspections != 2023-2025 vehicle accidents
--   unknown_incident    linked id missing from notes or not in stg_incidents
--   not_an_accident     linked incident is not of type 'accident'
--   vehicle_mismatch    linked incident names a different vehicle (or none)
with inspections as (
    select
        inspection_id,
        vehicle_id,
        regexp_extract(notes, 'Linked incident: (INC-[0-9-]+)', 1)  as incident_id
    from {{ ref('stg_vehicle_inspections') }}
    where inspection_type = 'post_incident'
),
accidents as (
    select *
    from {{ ref('stg_incidents') }}
    where incident_type = 'accident'
      and vehicle_id is not null
      and occurred_at >= '2023-01-01'
      and occurred_at <  '2026-01-01'
),
checks as (
    select
        null                            as inspection_id,
        null                            as incident_id,
        (select count(*) from inspections)  as post_incident_inspections,
        (select count(*) from accidents)    as vehicle_accidents,
        case
            when (select count(*) from inspections) != (select count(*) from accidents)
                then 'count_mismatch'
        end as failed_check

    union all

    select
        i.inspection_id,
        i.incident_id,
        null,
        null,
        case
            when inc.incident_id is null                    then 'unknown_incident'
            when inc.incident_type != 'accident'            then 'not_an_accident'
            when inc.vehicle_id is null
              or inc.vehicle_id != i.vehicle_id             then 'vehicle_mismatch'
        end
    from inspections i
    left join {{ ref('stg_incidents') }} inc
        on inc.incident_id = nullif(i.incident_id, '')
)
select *
from checks
where failed_check is not null
