-- The closure clock must agree with the status flag. Zero rows expected.
-- A resolved ticket always carries resolved_at and resolution_hours, closed no
-- earlier than its first reply; open and pending are both unresolved, so they
-- carry neither.
select
    ticket_id,
    status,
    first_response_at,
    resolved_at,
    resolution_hours
from {{ ref('stg_support_tickets') }}
where (status = 'resolved'
       and (resolved_at is null
            or resolution_hours is null
            or resolved_at < first_response_at))
   or (status in ('open', 'pending')
       and (resolved_at is not null or resolution_hours is not null))
