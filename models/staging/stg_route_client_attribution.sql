-- One row per route x client the route serves (1-4 clients per route, 2023-2025).
-- The bridge that allocates route-level cost to accounts: stop_share and
-- revenue_share each sum to one per route, exception_attributed sums to the
-- route's exceptions_count. route_client_key carries the grain for a unique test.
select
    route_id || ':' || client_id                                as route_client_key,
    route_id,
    client_id,
    cast(stop_share as {{ dbt.type_float() }})                  as stop_share,
    cast(revenue_share as {{ dbt.type_float() }})               as revenue_share,
    cast(exception_attributed as {{ dbt.type_int() }})          as exception_attributed
from {{ ref('route_client_attribution') }}
