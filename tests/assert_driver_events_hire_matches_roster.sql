-- The hire events rebuild the roster: every driver in stg_drivers has exactly one hire
-- event, dated on their hire_date. Zero rows expected. Each failing row names the check
-- it broke:
--   hire_count_not_one      the driver has no hire event, or more than one
--   hire_date_mismatch      the driver's single hire event is not on stg_drivers.hire_date
with hires as (
    select
        driver_id,
        count(*)        as hire_events,
        min(event_date) as hired_on
    from {{ ref('stg_driver_events') }}
    where event_type = 'hire'
    group by driver_id
),
checks as (
    select
        d.driver_id,
        coalesce(h.hire_events, 0)      as hire_events,
        d.hire_date                     as roster_hire_date,
        h.hired_on                      as event_hire_date,
        'hire_count_not_one'            as failed_check
    from {{ ref('stg_drivers') }} d
    left join hires h
        on h.driver_id = d.driver_id
    where coalesce(h.hire_events, 0) <> 1

    union all

    select
        d.driver_id,
        h.hire_events,
        d.hire_date,
        h.hired_on,
        'hire_date_mismatch'
    from {{ ref('stg_drivers') }} d
    inner join hires h
        on h.driver_id = d.driver_id
    where h.hire_events = 1
      and h.hired_on <> d.hire_date
)
select *
from checks
