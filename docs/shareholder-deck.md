# Shareholder pack

A briefing on the business, assembled from the company's own operating data and skinned as a
16-bit management game: the business and its year, the storm week and the second cause behind
it, how the report itself was made (the stack, how every number traces back, the context layered
on top, how a question becomes an answer), and what that shift means for the data team, from
analytics engineer to context engineer. The dense working sits in an appendix for questions.

[**Open the deck &rarr;**](shareholder-deck/presentation.html){ .md-button .md-button--primary }
[**Open it in the Fivetran + dbt Labs theme &rarr;**](shareholder-deck/presentation-corporate.html){ .md-button }

Use the arrow keys to move, `f` for full screen, `s` for speaker notes, and print to PDF for a
handout. The slide order is `slides/deck-light/manifest.txt`, and `python3 slides/build_deck.py`
builds the deck (`--theme corporate` for the Fivetran + dbt Labs version).

## The network map and the executive group, in three styles

| Network map | Executive group |
|---|---|
| [![Network map, retro](shareholder-deck/png/map-retro.png)](shareholder-deck/png/map-retro.png) | [![Executive group, retro](shareholder-deck/png/exec-retro.png)](shareholder-deck/png/exec-retro.png) |
| [![Network map, dark](shareholder-deck/png/map-dark.png)](shareholder-deck/png/map-dark.png) | [![Executive group, dark](shareholder-deck/png/exec-dark.png)](shareholder-deck/png/exec-dark.png) |
| [![Network map, light](shareholder-deck/png/map-light.png)](shareholder-deck/png/map-light.png) | [![Executive group, light](shareholder-deck/png/exec-light.png)](shareholder-deck/png/exec-light.png) |

## The reports behind every slide

Each slide carries one seat's verified numbers, and names the report it came from. Those reports
live in the repository:

| Seat | Report |
|---|---|
| Chief Financial Officer | [persona-cfo.md](https://github.com/boxysean/jaffle-logistics-europe/blob/main/reports/persona-cfo.md) |
| Chief Operating Officer | [persona-coo.md](https://github.com/boxysean/jaffle-logistics-europe/blob/main/reports/persona-coo.md) |
| Chief Revenue Officer | [persona-cro.md](https://github.com/boxysean/jaffle-logistics-europe/blob/main/reports/persona-cro.md) |
| Head of Customer Experience | [persona-customer-experience.md](https://github.com/boxysean/jaffle-logistics-europe/blob/main/reports/persona-customer-experience.md) |
| Head of Fleet & Maintenance | [persona-fleet.md](https://github.com/boxysean/jaffle-logistics-europe/blob/main/reports/persona-fleet.md) |
| Head of People | [persona-people.md](https://github.com/boxysean/jaffle-logistics-europe/blob/main/reports/persona-people.md) |
| Head of Data | [persona-data.md](https://github.com/boxysean/jaffle-logistics-europe/blob/main/reports/persona-data.md) |

!!! warning "The dataset is synthetic"
    Jaffle Logistics is a worked example, not a real carrier. Nothing here is a real company's
    numbers, and no market or competitor data was available to the analysis — so the deck makes
    no claim about rivals or market share.
