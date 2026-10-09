-- Client dimension, enriched with the client's contract SLA target.
-- A client can carry several contracts over time (an original -00 agreement, the
-- standing -01, later amendments). dim_clients holds one row per client, so take
-- the STANDING contract — the latest by effective_date (tie-broken by contract_id).
with clients as (
    select * from {{ ref('stg_clients') }}
),
contracts as (
    select
        client_id,
        contract_id,
        sla_ontime_pct,
        effective_date,
        row_number() over (
            partition by client_id
            order by effective_date desc, contract_id desc
        ) as _contract_rank
    from {{ ref('stg_contracts') }}
),
standing_contract as (
    select client_id, contract_id, sla_ontime_pct, effective_date
    from contracts
    where _contract_rank = 1
)
select
    c.client_id,
    c.client_name,
    c.tier,
    c.line_of_business,
    c.region,
    c.health,
    con.contract_id,
    con.sla_ontime_pct,
    con.effective_date  as contract_effective_date
from clients c
left join standing_contract con on con.client_id = c.client_id
