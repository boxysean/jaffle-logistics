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

The extension is **append-only**. No existing row, id or value was
rewritten, and no date was pushed past the dataset's present
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

The quiet years were generated deliberately, not uniformly at random:
their on-time rates, incident mix and severity were chosen to match the
story above, so the 2025 decline shows up as a change from a known
baseline rather than as the only year on record.
