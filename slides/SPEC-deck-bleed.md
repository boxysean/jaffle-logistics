# Fix request: make the two image slides full-bleed

Edit the existing `slides/presentation.html`. Two slides in this deck are a single big image:
the **network map** slide (the one showing `map-retro.png`) and the **executive group** slide
(showing `exec-retro.png`). The owner wants those two slides to show the image as large as the
slide can hold, with the surrounding text gone.

On **those two slides only**:

1. **Delete the subtext.** Remove the caption paragraph under the image and the `SOURCE ...`
   line entirely. Those slides should be the picture and nothing else.
2. **Blow the image up to the full canvas.** The slide is 1280x720 in reveal units and both
   images are 1920x1080 - the same 16:9 shape - so the image can fill the slide exactly, edge to
   edge, with no letterboxing, no border, no frame, and no visible background around it. Remove
   whatever padding/margin/border those two slides currently use, and make the image occupy the
   whole 1280x720 area. It must not be stretched out of shape: `object-fit` on a 16:9 box holding
   a 16:9 image, or an explicit 1280x720 box.
3. **Hide the deck's bottom status bar on those two slides.** Each of these images already carries
   its own caption bar along its bottom edge, so the deck's status bar would sit on top of it. On
   every other slide the status bar stays exactly as it is.

Leave the other nine slides **byte-identical** - same content, same layout, same status bar - and
do not change the pixel headings, the colours, or the fonts anywhere. Body text on the other
slides stays 24px or larger.

Verify the file still loads and reveal.js still initialises, and report which lines you changed.
