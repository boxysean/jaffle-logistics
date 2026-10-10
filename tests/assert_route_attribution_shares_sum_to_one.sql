-- Each route's client shares must sum to one, for stops and for revenue. Zero rows
-- expected. The generator rounds to 4 dp and lets the largest share absorb the
-- remainder, so the seed sums exactly; the 0.001 slack only absorbs float storage
-- error.
select
    route_id,
    sum(stop_share)     as stop_share_total,
    sum(revenue_share)  as revenue_share_total
from {{ ref('stg_route_client_attribution') }}
group by route_id
having abs(sum(stop_share) - 1.0) > 0.001
    or abs(sum(revenue_share) - 1.0) > 0.001
