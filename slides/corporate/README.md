# The Fivetran + dbt Labs theme

    python3 slides/build_deck.py --theme corporate     # writes slides/presentation.html

The same deck, same slides, numbers, fragment steps and speaker notes, in the corporate Fivetran +
dbt Labs slide template's look: navy title and section slides with the template's colour blocks,
white content slides with a navy Inter headline, hairline cards, IBM Plex Mono labels, and the logo
badge with the brand gradient along the foot of every slide. The docs workflow publishes it beside
the deck, at `docs/shareholder-deck/presentation-corporate.html`.

The theme is applied to the built page, so a slide is still written once, in the retro deck's
parts, and themes without any change:

- `theme.py` swaps the fonts, maps the colours written into the slides' SVGs, appends `theme.css`
  with the images inlined, and sets the all-caps headlines in sentence case at load time.
- `theme.css` holds the palette (the deck's colour variables, redefined) and the chrome. A new
  slide family that brings its own dark colours or a white logo may need a line here.
- `assets/` holds the logo lock-up, the logo badge, and the title and section backgrounds, taken
  from the corporate slide template.
