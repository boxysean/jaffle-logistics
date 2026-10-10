-- raw cosine similarity, account-scoped
select source_id, score, text
from {{ ref('search') }}
where demo = 'jaffle_werke_performance_issues'
order by score desc