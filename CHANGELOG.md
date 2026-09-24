# Changelog

Morale is pre-1.0. Stitch output has not been validated by physical sew-outs;
test on scrap fabric before sewing a finished piece.

## Unreleased

### Artwork and image digitizing
- **Split suitable branching shapes** now cuts at branch crotches along short
  interior chords, so Y, X, star and K forms at any angle become satin columns
  and stems separate cleanly from broad fills.
- **Branch join overlap** (default 0.3 mm) extends one piece across each branch
  cut, inside the artwork, so satin columns overlap instead of just touching.
  Saved in presets; older presets keep exact joins.
- Tiny junction wedges left by branch cuts merge into a neighbouring satin.
- **Branch-join sew-out pack** (`examples/branch-sewout/`, or
  `python -m morale.sewout_pack --output DIR`): nine test cells comparing exact,
  0.3 mm and 0.6 mm joins, with PES, EXP, DST and a placement PDF.
- **Coverage layers** view in the density review: a fixed-scale map of how many
  objects sew over each point, with overlapping object pairs and their shared area
  in conversion checks and the review PDF.
- **Fabric for guidance** (medium woven, lightweight, knit, heavy, pile) flags
  stacked layers, dense cells, narrow satins and small fills against
  starting-point thresholds, without regenerating.
- **Keep different artwork colors on different threads**: thread matching plans
  the whole palette so clearly different colors never merge onto one thread.
- **Group regions by thread to reduce color changes**: reorders regions that do
  not overlap anything in between, keeping layer order.
- Faster area measurement across conversion (full test suite about 27% faster).

## 0.2.0 — 2026-09-24

Image-to-embroidery becomes the headline feature, with broader library, thread
and export tooling around it.

### Artwork and image digitizing
- **File → Digitize artwork** traces PNG/JPEG/BMP/WebP images with smooth
  shared-boundary curves, or takes SVG directly, and exports the fitted SVG.
- Automatic running/satin/fill selection by physical width, with per-region
  overrides and explanations; open-ribbon and closed-band satin fitting,
  optional branch splitting and band seam control.
- Perceptual (Oklab) palette reduction, border-connected white background
  removal that keeps enclosed white details, and thread-chart matching.
- Covered-fill removal with seam allowance, small-hole filling, physical detail
  filtering, fill-angle search and disconnected fill-run routing.
- Conversion workspace with aligned source/vector/stitch panels, artwork overlay,
  density and overlap reviews, light-thread contrast, stitch and underlay
  settings, portable presets and a shareable review PDF.
- SVG dashed-stroke expansion, `pathLength` calibration and `paint-order`.

### Editing
- Object edge and center snapping while dragging.
- Multi-stitch selection, box selection, movement and deletion on the canvas.
- **Split long stitches** in the stitch editor.
- Lettering placed along a drawn path.

### Threads, library and export
- INF/EDR palette import and export; perceptual matching by default with a
  match preview tab.
- Recursive library search, visible-result thumbnails and printable PDF
  catalogs with a file index.
- Long sewn-span diagnostics and overlay, export preparation counts (including
  multi-hoop bundles) and sewn-start handling.
- Automatic satin appliqué covers with tatami fallback.

### Quality and packaging
- Repeatable internal image benchmark (`python -m morale.image_benchmark`) with
  a strict sampled sewn-path export gate.
- Packaged-bundle self-test (`scripts/check_bundle.py`).
- 1,800 automated tests passing on Linux (offscreen Qt).

### Known issues
- VP3 export fails the sampled sewn-path gate in 7 of 11 benchmark cases: the
  installed pyembroidery writer loses internal jump positions. See
  [VP3_INVESTIGATION.md](docs/VP3_INVESTIGATION.md). Prefer PES, DST or EXP.
- Windows and macOS builds are untested, and no machine-specific profiles
  have been validated yet.
- New dependency: `vtracer`.

## 0.1.0

Native Qt foundation: vector shapes and paths, running/tatami/satin stitches,
thread sequence, numeric transforms, undo/redo, hoop checks, playback, editable
`.morale` projects, machine-file import and export, and automated tests.
