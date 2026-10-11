# Fix request: three defects in slides/presentation.html

Read the existing `slides/presentation.html` and fix exactly these problems, changing nothing
else about the design or the content:

1. **The slide background is light.** The area around the content panels is near-white with a
   faint stripe texture. It must be the same deep navy/near-black as the retro graphics in
   `png/map-retro.png` and `png/exec-retro.png` — the panels should sit on a dark ground, and
   any scanline texture should be a subtle dark overlay on navy, not light stripes on white.
   Reveal's own background (`.reveal`, `body`, `html`) and the slide container all need it, so
   no white shows at the edges, behind the status bar, or in the corners.

2. **The SOURCE line is illegible.** On every slide a line like
   `SOURCE reports/persona-cfo.md` is rendered just below the content panel, in pale grey on
   the pale background, half outside the panel. Put it **inside** the panel's frame (bottom-left
   area, inside the border) and set it in a legible colour against the navy — clearly a caption,
   still subordinate to the content, but readable on a projector. Same on all 11 slides.

3. **Two chrome elements sit outside the dark ground.** Reveal's slide-number badge (top-right)
   and its progress bar (bottom edge) currently render against white / as a stray bar. Give them
   their existing retro look but on the navy ground, and make sure nothing peeks out below the
   bottom status bar — the status bar should be the last thing at the bottom edge.

Constraints: keep the 16:9 layout, the pixel headings, the amber accent, the bottom status bar
and all slide content exactly as they are. Do not rename or move any slide. Body text stays
24px or larger. Verify the file still loads and reveal.js still initialises.
