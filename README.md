# True Frame

**True Frame is a proof-of-concept, built in response to the prompt, for an SVG-based visual prompting tool for campaign creative.**

Given a campaign brief (JSON) with 2+ products, target markets, audience, and message, the pipeline:

1. Localizes copy per market (Gemini)
2. Reuses each product's real photo
3. Generates a product-free background matching the layout's camera framing (Gemini)
4. Deterministically composites the product into the background at the layout's exact position/scale
5. Renders localized copy onto the hero
6. Crops every additional aspect ratio staged in that layout

This covers all three required ratios (1:1, 9:16, 16:9) out of the box.

Rather than turning creatives into prompt engineers, it lets them structure a composition visually in Illustrator (where the product sits, where the tagline goes, where the body copy goes), and that geometry is parsed into the camera directions and prompts driving GenAI image generation. A layout is a reusable visual prompt: feed multiple layouts through the same brief to get multiple on-theme compositions, and mark explicitly where an additional aspect ratio should crop from, instead of guessing "roughly centered."

- 🎥 [Explainer video](https://drive.google.com/file/d/11Wl1iuZzg8fjQHkJL9qMHfEUwNySwUEA/view?usp=sharing)
- 📑 [Explainer presentation](https://drive.google.com/file/d/1WBB54twupRb1ZY8pc7eyi8ucNcEsXyGs/view?usp=share_link)
- 🎨 [Illustrator source file](https://drive.google.com/file/d/19woB2Wegv8Nkq1exNZ4L9NLJlAqtuy7G/view?usp=share_link)

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "GEMINI_API_KEY=your-key-here" > .env
python main.py
```

Runs `assets/briefs/example_briefs.json` and writes to `output/<brief_id>/<version>/<product>/<ratio>/...`. Each run gets its own version, nothing overwritten. Edit `campaign_json_path` in `main.py` to run a different brief. A full run makes several Gemini calls per product; expect a few minutes and real API quota use.

## Input Format

See `assets/briefs/example_briefs.json`. A brief declares: **id**/**campaign_message** (tag+body), **products** (id, name, description, category, `asset_dir` — skipped with a warning if it has no real `product.png`, `layouts` for which ratios to generate), **target_markets** (region + IETF language codes), **target_audience**/**tone**, and **brand** (fonts/colors).

`product.png` must already be a transparent cutout of the product (PNG only — JPEG can't carry alpha) — compositing pastes it as-is and does not attempt to remove a background.

## Example Output

```
output/The_Breakfast_Rewind/v1/honey-smacks/
├── 9:16/honey-smacks_hero_center_tall.png, North_America/hero_en-US_center_tall.png, ...
└── 1:1/honey-smacks_hero_center_square.png,
       North_America/hero_en-US_center_square.png, hero_en-US_center_tall.png (center_tall's staged crop), ...
```

Output is organized by each image's *actual* aspect ratio, not by which layout produced it. Filenames carry the source layout's name so images sharing a ratio folder never collide.

## Key Design Decisions

- **The layout SVG is the prompt**: `product`/`header`/`body`/`Crop_Zones` rects drawn once in Illustrator drive camera framing and placement at runtime; no separately-maintained mask asset
- **One hero generation per layout, deterministic crops for the rest**: cheaper than generating every ratio independently, and pixel-consistent with the hero
- **Hybrid GenAI pipeline**: product and background generate independently, then composite deterministically; a single mask-guided call proved unreliable at exact placement
- **Camera framing derives from the layout mask's geometry**, not a separate brief field, so it can't drift out of sync
- **Requires a real product photo per product** — packaging/branding is never GenAI-generated from a text description alone, since exact trademarked design can't be reliably reproduced from text; a product without one is skipped with a console warning rather than generated or failing the whole run
- **Background prompts never reference the product's real contents/category props**, to avoid generating a competing product in-frame
- **Output is versioned** (`vN`), never overwritten

## Assumptions & Limitations

- Layout SVGs are matched by literal element id (`product`, `header`, `body`, `Crop_Zones`, etc.), validated against one Illustrator version/export-settings combination only; see the id spot-check below before trusting a new export
- Drawing a layout's zones is still manual; `TrueFrame.jsx` only exports/validates an existing artboard. A "New Layout" button that scaffolds a blank artboard with the zones pre-built and correctly nested would be the natural next step, catching structural mistakes before they're ever drawn instead of after export
- Storage is local disk only; no cloud/mock storage integration
- Example brief localizes into en-US/es-US/fr-FR; any IETF code Gemini supports should work

## Next Steps

- Add test coverage across the pipeline (layout parsing, compositing, cropping) to catch regressions as the mask/geometry logic evolves
- Get hands-on feedback from the client on the generated creative and workflow to validate the visual-prompting approach before investing further
- Round out the remaining nice-to-haves: brand-compliance checks, legal-content flagging, and analytics/reporting

## Creating a Custom Layout Template in Illustrator

A layout is an SVG with a fixed structure, matched by literal, case-sensitive id, not visual position:

1. **Artboard** at the target ratio (e.g. 1080×1080 for `1:1`, 1080×1920 for `9:16`).
2. **`Product_Zones`** layer: a `product` rect (drives placement + camera framing) and a `spacer` rect spanning the full artboard.
3. **`Copy_Zones`** layer: `header` and `body` rects.
4. **`Crop_Zones`** layer *(optional)*: one child group per additional staged ratio, named exactly as the ratio (e.g. `1:1`), which becomes the output folder name.
5. **Export & validate**: run [`plugins/illustrator/TrueFrame.jsx`](plugins/illustrator/TrueFrame.jsx) *(demo script, not hand-audited like the Python pipeline; see its README)* (File → Scripts → Other Script... in Illustrator): it exports each artboard, fixes Illustrator's id-escaping (`_x5F_`/`_x31_` → plain `_`/`1`), checks the required rects/groups are present, and writes straight to `layout/templates/<ratio>/<name>.svg`.
   - No Illustrator handy? Export manually (File → Export → Export As → SVG) and spot-check with `grep -o 'id="[^"]*"' layout/templates/<ratio>/<name>.svg`; ids should read plainly, not as `_xNN_` escapes.

## Project Structure

```
main.py                        # bootstrap: builds GoogleGenAIService, calls generate_campaign()
campaign/generate.py           # generate_campaign() orchestrator
models.py                      # Brief, Product, Brand, etc. (Pydantic)
generation/                    # ImageGenService/CopyGenService interfaces + Gemini implementation
layout/                        # SVG parsing, mask rendering, compositing, cropping, copy rendering
  templates/<ratio>/<name>.svg # one .svg per staged layout
utils/                         # brief loading, versioning, CLI progress output
assets/                        # sample brief, product photos, brand fonts
output/                        # generated creatives, versioned per run (gitignored)
```
