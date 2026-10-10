-- gross_pay must be exactly hours_worked x hourly_rate, and total_cost must add
-- exactly the 50% overtime premium (overtime_hours x hourly_rate x 0.5), both to
-- the cent, for every driver-month. Returns any row where either does not tie.
select
    payroll_month,
    driver_id,
    hours_worked,
    hourly_rate,
    gross_pay,
    overtime_hours,
    total_cost
from {{ ref('stg_payroll_monthly') }}
where gross_pay <> round(hours_worked * hourly_rate, 2)
   or total_cost <> round(gross_pay + overtime_hours * hourly_rate * 0.5, 2)
