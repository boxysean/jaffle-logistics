-- For 2023-2025, when the routes record exists, a driver is paid hours in a month if
-- and only if they ran at least one route that month. Returns any driver-month paid
-- with no routes, or with routes but no pay. There are no exceptions to carve out:
-- the corpus holds no leave or absence records (hr_docs.doc_type is only onboarding,
-- review, certification, training, disciplinary or exit), so paid time off cannot be
-- told apart from unrecorded work and none is modelled.
select
    payroll_month,
    driver_id,
    hours_worked,
    routes_run
from {{ ref('stg_payroll_monthly') }}
where payroll_month >= cast('2023-01-01' as date)
  and (
        (hours_worked > 0 and routes_run = 0)
     or (hours_worked = 0 and routes_run > 0)
  )
