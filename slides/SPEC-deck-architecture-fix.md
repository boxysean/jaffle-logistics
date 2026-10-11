Two fixes to the architecture slide you just added (`<section class="arc">` in slides/presentation.html). The first render at 1280x720 shows the diagram panel's content sitting too high, leaving a large empty band under the dashed marker, and the marker's third line is crossed by the dashed bottom border. Change only the SVG geometry inside `.arc .flow` (and keep the CSS comment's fit budget accurate); do not touch anything else on the slide, and do not touch other slides.

New SVG geometry (viewBox stays `0 0 1196 270`; keep `width="1196" height="280"` on the `<svg>` so it scales cleanly - the panel has 282px of room inside its padding):

- layer titles: `y=14`
- boxes: `y=28`, `height=140` (bottom edge 168), x positions unchanged (`0, 247, 494, 741, 988`), width 207
- the arrows between boxes: shaft at `y=94`, i.e. `y="94" height="5"`, with the triangle head centred on `y=96.5` -> shaft `y="94"`, head points `x1,88.5 x2,y96.5 x1,104.5`
- inside each box, the four centred lines move to `y=70, 96, 118, 140`
- the agent marker: rectangle `x=741 y=190 width=455 height=64`
- the short arrow from the marker up into CONTEXT + AI's bottom border (now 168): shaft `x="857.5" y="180" width="5" height="10"` and head points `851.5,180 860,168 868.5,180`
- the marker's three lines: `y=214` (pixel `AGENT PLUGS IN HERE`), `y=232` (`MCP tool surface · 43 tools · lookup + vector cosine`), `y=248` (`scoped per account and time`)

Then update the CSS comment above `.arc` so its fit budget matches what is actually on the slide. Report what you changed and nothing else.
