-- The promised-delivery clock must agree with the status flag. Zero rows expected.
-- A delivered shipment is never late against its promise (hours_late null, bucket
-- on_time, promise at or after delivery); a delayed one always is (positive
-- hours_late, a late bucket, promise before delivery); failed and returned never
-- arrived, so they carry neither hours_late nor a bucket.
select
    shipment_id,
    status,
    promised_delivery_at,
    delivered_at,
    hours_late,
    late_bucket
from {{ ref('stg_shipments') }}
where (status = 'delivered'
       and (not (hours_late is null and coalesce(late_bucket = 'on_time', false))
            or promised_delivery_at < delivered_at))
   or (status = 'delayed'
       and (not (hours_late is not null and hours_late > 0
                 and late_bucket is not null and late_bucket <> 'on_time')
            or promised_delivery_at >= delivered_at))
   or (status in ('failed', 'returned')
       and (hours_late is not null or late_bucket is not null))
