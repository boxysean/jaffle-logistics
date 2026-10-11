# Add a second Head of Data slide: what dbt's quality layer found when we audited ourselves

Add **one more slide** to `slides/presentation.html`, placed **immediately after the
`EVERY NUMBER TRACES BACK` slide** (which is currently the last slide). The deck becomes
**seventeen** slides; renumber every status bar to `SLIDE NN / 17`. Match the existing retro
style exactly - same fonts, colours, panel borders, status bar, heading and footnote conventions.
No new libraries; if you draw anything it is inline SVG in the deck's own register.

The voice is the Head of Data being straight with a board: we pointed the quality layer at our own
project, published what it found, fixed what we could, and named what we have not fixed yet. The
honesty is the point of the slide - do not soften or trim the "not fixed" panel. Every figure is
verified against the project and its audit report; invent nothing.

## Heading

`WE AUDITED OURSELVES`

**Subheading:** `What dbt's quality layer found when we pointed it at our own project`

## Panel 1 - `WHAT RUNS ON EVERY CHANGE`

- `340 checks` / `pass, with no warnings and no errors` - the whole project built and tested from
  an empty warehouse by one command.
- `+4 tests added, 2 removed` / `the two we removed could never fail`
- `A failing test stops the release.` / `the build fails, the release does not ship`

## Panel 2 - `WHAT WE FIXED`

Two bullets, each one or two lines:

- **The governed on-time metric had no null guard.** `stg_shipments.status` was checked for valid
  values - but **that test ignores nulls**. A null status would have counted toward shipments and
  toward neither delivered nor late, and the build would have stayed green. `not_null` now guards
  all four columns that decide a time bucket.
- **Two tests could never fail.** A test that cannot fail only buys false confidence. Both were
  deleted rather than left in the count.

## Panel 3 - `WHAT WE HAVE NOT FIXED` (say it plainly, do not hide it)

Three bullets, each one or two lines:

- **No unit tests.** The logic most likely to break silently is engine-specific: the shipment-ID
  regex and the transcript parser each branch per engine, and the local check only exercises the
  DuckDB branch - so the production branch is never checked against known inputs before it runs.
- **No contracts, access levels or exposures.** Two agent skills read `knowledge_base` and
  `fct_shipments` by name. A column rename would break them with no build-time signal.
- **The on-time rule is written out in three places.** Three copies drift.

## Footnote (small, at the foot of the content)

`Full audit: reports/dbt-best-practices-audit.md`

Status bar right label: `the dbt audit`

## Rules

- Insert this slide only, at the end; leave the other sixteen slides exactly as they are apart from
  the `/ 17` renumbering.
- All three panels must fit with the status bar visible and nothing clipped or overlapping - check
  the panel heights before you finish, as this has needed a fix before.
- Verify the file loads and reveal.js still initialises, and report the renumbering.
