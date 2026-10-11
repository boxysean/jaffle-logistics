-- A termination is the end of a driver's record: every driver the roster no longer calls
-- 'active' has one, and nothing is logged for a driver after it. Zero rows expected.
-- Each failing row names the check it broke:
--   event_after_termination  an event for the driver is dated after their termination
--                            (or shares its day without being the termination itself)
--   missing_termination      stg_drivers.status is not 'active' but no termination event
with terminations as (
    select
        driver_id,
        min(event_date) as terminated_on
    from {{ ref('stg_driver_events') }}
    where event_type = 'termination'
    group by driver_id
),
checks as (
    select
        e.driver_id,
        e.event_id,
        e.event_date,
        t.terminated_on,
        'event_after_termination'       as failed_check
    from {{ ref('stg_driver_events') }} e
    inner join terminations t
        on t.driver_id = e.driver_id
    where e.event_date > t.terminated_on
       or (e.event_date = t.terminated_on and e.event_type <> 'termination')

    union all

    select
        d.driver_id,
        null,
        null,
        null,
        'missing_termination'
    from {{ ref('stg_drivers') }} d
    left join terminations t
        on t.driver_id = d.driver_id
    where d.status <> 'active'
      and t.driver_id is null
)
select *
from checks
