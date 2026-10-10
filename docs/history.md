# The history behind the data

The warehouse holds a fictional operator, **Jaffle Logistics**, with five
hubs (Columbus, Chicago, Indianapolis, Detroit, Cincinnati) and five
customers. The seed data was originally a single operating year, **2025**,
which made every "how are we doing?" question impossible to answer: with
one year there is nothing to compare against. The dataset has since been
**extended backwards in time**, adding **2023 and 2024** to the
operational records so that 2025 reads as the third year of a business
with a visible past.

## Three years, two stories

| Year | On-time delivery | Jaffle Equipment (`CLI-0042`) | What it is |
|---|---|---|---|
| 2023 | ≈ 97.5% | ≈ 98% | Quiet, healthy year |
| 2024 | ≈ 97.2% | ≈ 98% | Quiet, healthy year |
| 2025 | behind the 97% SLA target | down to ≈ 79% | The year under analysis |

**2023 and 2024 are the baseline.** Ordinary operations, ordinary
weather, an occasional incident resolved inside the week. Whole-book
on-time delivery sits at or just above the 97% contractual target in both
years, and Jaffle Equipment is a *good* account in that period, close to
98% on time.

**2025 is the year the story is about.** The January Chicago storm, a
recurring handling-damage pattern at the Columbus hub (`HUB-CMH`, bay 3
staging), and Jaffle Equipment's decline to roughly 79% on time all live
in 2025 and nowhere earlier. Every analysis written about 2025 still
holds; what changed is that it now has two calm years to be measured
against.

## What was added

The extension was **append-only**. No existing row, id or value was
rewritten (a later, separate change *did* revise rows — see
[Revision: year-over-year volume and the service-level mix](#revision-year-over-year-volume-and-the-service-level-mix)),
and no date was pushed past the dataset's present
(2025-12-31; a late-December shipment may still deliver a few days into
January, exactly as the original data already does).

- `shipments`, `routes` and `incidents` each gained **two full prior
  years**, roughly doubling every table.
- `drivers` and `vehicles` grew slightly, with hire dates in 2022–2024,
  so the earlier years are credibly staffed.
- New ids continue the existing schemes: `SHP-YYYYMM-NNNNNN`,
  `RTE-<HUB3>-YYYYMMDD-NNN`, and `INC-YYYY-NNNNN` (the year is embedded
  in an incident id).
- Every new row points at something that already exists — the same five
  clients, the same five hubs, and real drivers, vehicles, routes and
  shipments — so referential integrity holds across the whole timeline.
- `dock_bay_events` (new, `DBE-NNNNNN`) is the bay-level dock record: every
  bay at every hub, every day of 2023–2025, with one `damage_found` row per
  damage incident. `incident_reports` gained a report for every severity 1–2
  incident and every Columbus damage incident that lacked one (`IR-7067` on).

The quiet years were generated deliberately, not uniformly at random:
their on-time rates, incident mix and severity were chosen to match the
story above, so the 2025 decline shows up as a change from a known
baseline rather than as the only year on record.

## Route-to-client attribution

Cost is recorded per route and per hub. Revenue is recorded per account.
To put cost on accounts you need a bridge that says which accounts each
route carried. `route_client_attribution` is that bridge: one row per
route × client, for **every route from 2023-01-01 to 2025-12-31**, with
one to four clients per route.

| Column | Meaning |
|---|---|
| `stop_share` | the client's share of the route's stops |
| `revenue_share` | the client's share of the route's revenue (may differ from `stop_share`: LTL freight earns more per stop) |
| `exception_attributed` | how many of the route's `exceptions_count` belong to the client |

**It reconciles to the route record.** Per route, `stop_share` and
`revenue_share` each sum to exactly 1.0. Shares are rounded to 4 dp and the
largest share absorbs the remainder. `exception_attributed` sums to the
route's `exceptions_count`, using a largest-remainder split. Every route
appears. Two singular tests enforce this:
`assert_route_attribution_shares_sum_to_one` and
`assert_route_attribution_exceptions_reconcile`.

The mix starts from the evidence: every client with a shipment on the route.
Shipments are only a sample of a route's stops, so the mix is topped up from
each account's shipment volume at that hub that month. On every route
carrying a 2025 damage incident, Jaffle Equipment (`CLI-0042`) holds the
largest share of exceptions, so incidents traced through the bridge land the
Columbus handling-damage cluster on that account
(`assert_columbus_2025_damage_attributed_to_equipment`). The 2023–2024
damage routes are led by other accounts.

`fct_client_cost_attribution` uses the bridge to give cost per client by
month: attributed exceptions, plus each hub-month's fleet maintenance spread
by the client's share of attributed stops. **That allocation is by share and
is therefore an approximation.** The bridge records the mix on a route, not
which account caused a given cost.
Generated by `scripts/generate_route_client_attribution.py`.

## Promised-delivery clock

On-time was originally only a status flag: `delivered` means on time and
`delayed` means late. There was no promised date, so nobody could say *how*
late a shipment was. `shipments` now carries three more columns. The
existing columns are byte-identical.

| Column | Meaning |
|---|---|
| `promised_delivery_at` | when the shipment was promised |
| `hours_late` | whole hours past the promise; delayed shipments only |
| `late_bucket` | `on_time`, `<4h`, `4-12h`, `1-2d` or `>2d`; null for failed and returned |

The promise is `created_at` plus the account's committed transit. That is a
service-level base (expedited 36h, standard 60h, freight 84h), plus hours
for a looser contract SLA (6h per point below 97%), plus a lane offset
from the origin hub's state to the client's region (0h same state, 12h
neighbouring state, 24h farther), plus a small seeded jitter.

**The clock agrees with the flag.** A delivered shipment's promise lands at
or after its delivery. A delayed shipment's promise is reconstructed as
`delivered_at - hours_late`. Failed and returned shipments still carry the
promise that was made, with no lateness. The singular test
`assert_shipment_lateness_matches_status` enforces this.

**It tells the 2025 story in hours.** Late shipments in 2023 and 2024 were
barely late, 2–10 hours. In 2025 they run a day or more: multi-day during
the January Chicago storm and on Jaffle Equipment's (`CLI-0042`) freight,
and one to two days elsewhere. The `late_hours` metric on the `shipments`
semantic model sums it.

One caveat: a delayed promise is never placed before its service-level base
transit. So a quiet-year late shipment's window comes out close to its
actual (long) transit. That is deliberate: in the healthy years the
promise was a generous window, missed by only hours.

Generated by `scripts/generate_promised_delivery.py`.

## Revision: year-over-year volume and the service-level mix

**This was a revision of existing rows, not an append.** Unlike the
extension above, it rewrote `seeds/shipments.csv` and `seeds/routes.csv` in
place. Two things were wrong with the extended data:

- **Every year had the same volume**: 2,009 shipments and 3,629 routes in
  each of 2023, 2024 and 2025. With identical volumes no analysis can tell
  a volume effect apart from a reliability effect.
- **`service_level` was degenerate in 2025**: every 2025 `freight`
  shipment belonged to Jaffle Equipment (`CLI-0042`), so "freight" was just
  another name for that account.

What changed:

| Year | Shipments | Routes | On-time | `CLI-0042` share | Freight carried by |
|---|---|---|---|---|---|
| 2023 | 2,009 → **1,848** (−8%) | 3,629 → **3,338** | 97.51% (unchanged) | 20.7% → **19.4%** | all five accounts |
| 2024 | 2,009 → **1,949** (−3%) | 3,629 → **3,521** | 97.21% → 97.23% | 20.6% → **20.1%** | all five accounts |
| 2025 | 2,009 (unchanged) | 3,629 (unchanged) | 93.28% (unchanged) | 20.7% | `CLI-0042` (416), `CLI-0169` (32), `CLI-0007` (31) |

- **2023 and 2024 lost rows; nothing was added, renumbered or re-drawn.**
  Every surviving row keeps all of its values. A row was dropped only if no
  other seed refers to it: no incident, support ticket, CRM note, incident
  report, dispatch note or Slack thread. Drops were chosen so that each
  month shrinks by the year's factor (the January trough and the Q4 peak
  are kept), each year's on-time rate holds, and `CLI-0042`'s share rises
  2023 → 2024 → 2025 while the other four accounts stay roughly flat.
- **Routes shrank by the same annual factor**, month by month. Only routes
  that no surviving shipment, incident or note refers to were dropped. No
  2023–2024 driver-month or vehicle-month is now busier than the busiest
  one in 2025.
- **2025 is unchanged apart from its service-level mix.** Every 2025
  shipment keeps its id, client, hub, dates, status and route. The only
  change: 63 of them (8% of `CLI-0007`'s and of `CLI-0169`'s 2025 book)
  were relabelled from `expedited` to `freight`. That makes three freight
  accounts in every year, and `CLI-0042` still has the largest 2025
  freight book. The 2025 routes are byte-identical.
- No status, incident or date was changed. Nothing is dated after
  2025-12-31, and no 2025 signal shows up in 2023–2024.
- **The promised-delivery clock was carried through, not recomputed.**
  Every surviving shipment keeps its `promised_delivery_at`, `hours_late`
  and `late_bucket` exactly. That includes the 63 relabelled 2025 shipments,
  whose promise was set on the expedited base (36h), not the freight base
  (84h). The clock still agrees with the status flag. Do not re-run
  `scripts/generate_promised_delivery.py`. It draws one seeded stream across
  all rows, so running it on the shorter file would redraw every
  shipment's promise, including 2025's. Its `--check` now reports a
  difference for the same reason.

**The derived seeds were regenerated as a result**: `revenue_ledger`,
`payroll_monthly`, `route_client_attribution` and `cost_ledger` are rebuilt
from the revised shipments and routes, so their reconciliation tests still
tie out. Their 2023–2024 figures, and any 2025 figure computed over a
trailing window or from the service-level mix (revenue, credits), differ
from the values before the revision. Generated by
`scripts/generate_volume_variation.py`. The script refuses to run a second
time on data that has already been revised.
