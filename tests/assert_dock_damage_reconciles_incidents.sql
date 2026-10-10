-- Every damage incident has exactly one damage_found dock event, and vice versa:
-- same count per (hub_id, year) on both sides, and HUB-CMH 2025 = 15 (the Columbus
-- cluster in reports/columbus-damage-forensics.md). Zero rows expected. Each failing
-- row names the check it broke:
--   count_mismatch   dock damage_found count != damage incident count for a hub-year
--   cmh_2025_not_15  HUB-CMH 2025 damage_found count is not 15
with dock as (
    select
        hub_id,
        extract(year from event_at)     as yr,
        count(*)                        as n
    from {{ ref('stg_dock_bay_events') }}
    where event_type = 'damage_found'
    group by 1, 2
),
incidents as (
    select
        hub_id,
        extract(year from occurred_at)  as yr,
        count(*)                        as n
    from {{ ref('stg_incidents') }}
    where incident_type = 'damage'
    group by 1, 2
),
checks as (
    select
        coalesce(d.hub_id, i.hub_id)    as hub_id,
        coalesce(d.yr, i.yr)            as yr,
        coalesce(d.n, 0)                as dock_damage_found,
        coalesce(i.n, 0)                as damage_incidents,
        case
            when coalesce(d.n, 0) != coalesce(i.n, 0)
                then 'count_mismatch'
        end as failed_check
    from dock d
    full outer join incidents i
        on  i.hub_id = d.hub_id
        and i.yr = d.yr

    union all

    -- Separate from the join so it fires even if HUB-CMH 2025 is missing on both sides.
    select
        'HUB-CMH'                       as hub_id,
        2025                            as yr,
        coalesce((select n from dock where hub_id = 'HUB-CMH' and yr = 2025), 0),
        coalesce((select n from incidents where hub_id = 'HUB-CMH' and yr = 2025), 0),
        case
            when coalesce((select n from dock where hub_id = 'HUB-CMH' and yr = 2025), 0) != 15
                then 'cmh_2025_not_15'
        end
)
select *
from checks
where failed_check is not null
