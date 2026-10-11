# Fix request: put the source report in the status bar

Edit `slides/presentation.html`. The deck has a bottom status bar on every slide: company name
on the left, `SLIDE 04 / 11` in the middle, and `synthetic dataset` on the right. The owner wants
that right-hand label to show **the source report for that slide** instead.

1. **In the status bar, replace the right-hand `synthetic dataset` label with that slide's source
   report path** - the same value the slide's existing `SOURCE ...` line uses. So the CFO slide's
   status bar reads `reports/persona-cfo.md`, the customer-experience slide reads
   `reports/persona-customer-experience.md`, the network-map and executive-group slides read
   `reports/company-profile.md`, and so on. Every slide gets its own value.
2. **Remove the duplicate `SOURCE ...` line that sits under the content panel** on those slides,
   since the status bar now carries the same information. The source should appear exactly once
   per slide, in the status bar.
3. **The two image slides** (the network map and the executive group) already have the status bar
   hidden and must stay that way - those two are the picture edge to edge, nothing else.
4. **The title slide has no source report**, so leave its status bar reading `synthetic dataset`.
   It is the one slide that carries the honesty marker, and it must keep saying that.
5. Leave everything else alone: same layout, same fonts, same colours, the other nine slides
   otherwise unchanged, body text still 24px or larger.

Verify the file loads and reveal.js still initialises, and report which lines you changed.
