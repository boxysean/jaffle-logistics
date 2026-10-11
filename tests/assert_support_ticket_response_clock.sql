-- The response clock must run forward and stop at the dataset's present
-- (2025-12-31). Zero rows expected. Every ticket has a non-negative first
-- response no earlier than opened_at; a resolution always takes longer than the
-- first reply; nothing is answered or closed after 2025-12-31T23:59:59.
select
    ticket_id,
    opened_at,
    first_response_at,
    resolved_at,
    first_response_hours,
    resolution_hours
from {{ ref('stg_support_tickets') }}
where first_response_hours is null
   or first_response_hours < 0
   or first_response_at is null
   or first_response_at < opened_at
   or (resolution_hours is not null and resolution_hours <= first_response_hours)
   or first_response_at > cast('2025-12-31 23:59:59' as timestamp)
   or resolved_at > cast('2025-12-31 23:59:59' as timestamp)
