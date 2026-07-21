# TrueFrame.jsx

> Written and iterated against a real Illustrator export for this POC's demo,
> unlike the hand-written Python pipeline elsewhere in this repo — included
> to show the idea is buildable, not as production-audited code.

An Illustrator ExtendScript that replaces the manual "export SVG, then `grep`
its ids by hand" workflow described in the main README. It exports each
selected artboard as a layout SVG, fixes Illustrator's id-escaping, checks
the required structure, and writes the result straight into this repo's
`layout/templates/<ratio>/<name>.svg` — nothing else. It doesn't touch the
campaign brief or generate any creative.

## Running it

Illustrator → **File → Scripts → Other Script...** → select `TrueFrame.jsx`.

(To get it listed directly under File → Scripts instead, copy it into
Illustrator's Scripts folder — e.g. `.../Adobe Illustrator <version>/Presets/<locale>/Scripts/`
on macOS/Windows — and restart Illustrator.)

## What it does per artboard

1. Exports just that artboard to SVG.
2. Decodes any `_x5F_`/`_x31_`-style hex-escaped ids back to plain text
   (`Crop_Zones`, `_1:1`, etc.) — some Illustrator export settings mangle ids
   this way, which silently breaks the Python-side parser.
3. Rewrites Illustrator's document-wide duplicate-name suffixes (`product 2`,
   `product-2`, `header copy`, or a stamped numeric id like
   `product_00000045608712381742929620000008998566533944603012_`) back to
   the bare canonical id. Illustrator enforces unique ids across the *whole
   document*, not per artboard, so if every artboard has its own `product`
   rect, exporting one artboard still picks up whatever suffix Illustrator
   stamped on that instance.
4. Checks a `product` rect exists (hard requirement — export fails without
   it) and that `header`/`body` rects exist (soft warning if missing).
5. If any group's id looks like a ratio (`1:1`, `9:16`, ...), checks it's
   actually nested inside a `Crop_Zones` layer, not just sitting at the top
   level — a group outside `Crop_Zones` is silently ignored by
   `layout/crop.py`.
6. Writes the sanitized SVG to `layout/templates/<ratio-with-dashes>/<name>.svg`.

You pick the target ratio and output name per artboard in the dialog (ratio
defaults to whichever supported ratio the artboard's own dimensions are
closest to); untick an artboard's checkbox to skip it.

## Limitations

This is a lightweight pre-flight check, not a full XML validator — it
regex-tokenizes `<g>` nesting rather than parsing real XML, so pathological
SVG structures could confuse it. The actual source of truth for what's
required is still `layout/mask.py` / `layout/crop.py` / `layout/engine.py`;
if that parsing logic changes, this script's validation needs a matching
manual update (ExtendScript can't import the Python code).
