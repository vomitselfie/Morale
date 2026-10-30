# Changelog

Morale is pre-1.0. Stitch output has not been validated by physical sew-outs;
test on scrap fabric before sewing a finished piece.

## Unreleased

### Machines and threads
- **Bernina colour files:** exporting EXP also saves a matching `.inf` thread
  colour file, as Bernina's own software does. Copy both to the machine.
- **Brother Embroidery threads** chart with the catalog numbers printed on
  Brother spools, for matching colours and converting artwork.

### Stitches
- **New stitch types:** *Blanket (E-stitch)* for appliqué edges, *Meander* (a
  soft quilting line) and *Cross-stitch*. Satin columns can be sewn as
  *S-stitch* or *Open zigzag* (Satin style). Test them with the new
  `decorative-stitches` sew-out coupon.

### Artwork
- **Stitch settings in SVG layer names:** name a layer or object in Illustrator,
  Inkscape or Affinity (`petals fill a=30`, `border stroke.satin w=2`, `skip`) and
  File → Import SVG artwork… stitches it that way. Unusable names are listed.

## 0.4.0 — 2026-10-30

Cleaner satin columns, sharp corners, test swatches for your own fabric, richer
SVG import and fabric starting points. Stitch output is still not validated by
physical sew-outs. Several ideas come from ZigZag (Apache-2.0), credited in
THIRD_PARTY_NOTICES.md.

### Satin
- **Sharp corners are sewn instead of refused.** When a satin column turns a
  corner tighter than it is wide, the inside of the corner becomes a fan around
  one point. This also applies when pull compensation makes rails cross. Swapped
  rails and columns that really overlap themselves are still reported.
- **Short stitches on tight curves:** where stitches crowd together on the inside
  of a curve or corner, every other one stops a little short, so thread does not
  pile up.
- **No more jump back to the start of a column.** Underlay now runs out and back
  along the column, so the top stitches start where the underlay finishes. The
  top stitches keep the direction you drew. Satin lettering benefits too.
- **Long satin stitches are split at staggered points**, so the splits do not line
  up into a groove down a wide column.
- **Satin corners sew-out coupon** (`python -m morale.coupons --coupon
  satin-corners`, or File → Load sewout coupon…): corners from 120° to 30° in 2 and
  4 mm columns.

### Fabric
- **Edit → Fabric settings…** applies experimental starting points (density,
  pull compensation and underlay) for stable woven, stretch knit and textured
  fabrics to selected fill and satin parts. Adjust and save your own settings as
  presets. Image digitizing can use them too, keeping your region corrections.
- **Fabric comparison sampler** (File → Load fabric comparison sampler) sews all
  three side by side.

### Artwork and image digitizing
- SVG import handles far more real-world files: clipping paths, cropped
  viewports, reusable symbols, embedded stylesheets and CSS variables, modern
  colour notations, opacity, masks, and linear and radial gradients, which are
  traced into thread colours.
- Candidate satin columns are checked with the stitch settings you chose; when a
  column cannot use them, the preview explains why it kept a fill.

### Lettering
- Embroidery fonts can follow a curve or a line you have drawn, and make
  monograms. Extra-large font sizes are available.

### Designing
- **Design → Test swatches…**: copies of the selected parts with one setting
  (row spacing, pull compensation, stitch length or fill angle) stepped across
  2–9 values, each labelled, as a new design to sew on your own fabric.
- **Edit → Copy / Paste stitch settings** and **Select same stitch type**.
- **Choose where a fill starts and ends** in Edit → Sewing start and direction…
  (renamed from Path start and direction), so the thread comes in and leaves near
  the neighbouring parts.
- **Fills can travel inside the shape** between sections instead of jumping
  across it, when *Connect safe fill rows* and *Route disconnected fill runs* are
  both on.
- **Circular ripple fill** with an adjustable centre.
- **View → Layout guides…**: straight guide lines that objects snap to.
- **Design → Design notes…**: notes saved with the project, printed on sew-out
  worksheets and searchable in the design library (`notes:`).
- Drawing shapes, paths and satin rails entirely from the keyboard.
- **Help → Getting started** for first steps inside the app.

### Exports
- Trims you add between parts are kept in PES, EXP, JEF, U01, XXX, DST, VP3 and
  TBF files, and the export check now compares trims and stops with the design.

### Fixes
- On a Mac, pressing Return on a design library search result now opens it.

### Project files
- Projects are saved in a new layout (version 3) that groups each part's
  settings by purpose. Older projects open as before, but **projects saved by
  0.4 cannot be opened in Morale 0.3 or earlier.**

### Behind the scenes
- Stitches are generated as structured passes before becoming machine commands,
  the groundwork for better travel between parts.
- Release bundles now collect third-party licenses and check notices and a
  source manifest; continuous integration builds and self-tests the bundle on
  Linux, Windows and macOS for every push.

## 0.3.0 — 2026-09-27

Embroidery fonts, safer exports and the start of real-world validation. Morale is
now free software under the GNU GPL.

### License
- Morale is now licensed under the **GNU GPL, version 3 or later**. Anyone may use,
  share and change it, and shared versions must stay free and open. Version 0.2.0
  and earlier remain available under the MIT license they were released with.

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

### Lettering
- **120 embroidery fonts**, digitized by hand for sewing, converted from the
  Ink/Stitch font library (Open Font License, CC BY-SA and public domain fonts;
  credits in THIRD_PARTY_NOTICES.md). Each font lists the sizes it sews best at.
- **Satin-column lettering** from any installed font, now the default for new
  text: strokes become satin columns over a center run, bowls and counters are
  opened and split at their joins, and wide strokes or dots keep a tatami fill.

### Fixes (continued)
- **VP3 export no longer misplaces stitches.** Jumps were dropped, so the machine
  sewed a line where the design travelled. Jumps are now written as long-form moves
  to their real landing, following Embroidermodder's VP3 implementation, and
  VP3 exports verify like the other formats. Confirm on a Husqvarna or Pfaff
  machine before relying on it.

### Checking and validation
- **Design → Check design…** reviews a design without changing it: outside the
  hoop, narrow satins, small fills, long stitches, untrimmed jumps between
  objects, stacked layers and command count. Clicking an issue shows it.
  Thresholds are labelled provisional until sew-outs confirm them.
- **Sew-out coupons** (`python -m morale.coupons`): twelve single-variable test
  designs with a scale square, metadata and evaluation forms, and a documented
  process in docs/SEWOUT_VALIDATION.md.
- **Export verification:** every machine-file export is reopened with the real
  reader and compared with the design (stitch and thread-change counts, edges,
  sampled path). The confirmation says "Export verified" or lists differences.
  It revealed the VP3 problem fixed above.
- Saving validates the project with the same rules as opening it, so Morale never
  writes a `.morale` file it cannot reopen.

### Responsiveness
- Editing no longer re-serializes the whole project several times per change:
  unsaved-changes and stale-preview checks use revision numbers, and each state
  is serialized at most once.
- Opening and importing designs decode in a background process with a
  cancellable progress dialog, so large machine files no longer freeze the
  window.

### Accessibility
- Text follows the system font size instead of fixed pixels; muted text, labels
  and input borders meet WCAG contrast; focused controls show a clear border.
- Every menu entry has a keyboard accelerator, and arrow keys nudge the selected
  objects (Shift for 1 mm, or one grid step when snapping).
- An automated audit checks the main window and 13 dialogs for screen-reader
  names and keyboard focus.

### Fixes
- **File → Split for multiple hoopings** opened the wrong dialog and failed: two
  different `HoopDialog` classes shared one name in the main window module.

### Packaging and CI
- Proper platform packages from `packaging/build.py`: Linux AppImage and tar.gz,
  Windows installer and portable zip, macOS `.dmg`, each self-tested, with app
  icons, version information and `.morale` file associations.
- Double-clicking a `.morale` file (or passing it on the command line) opens it.
- CI tests Ubuntu (Python 3.11–3.13), Windows and macOS on every push, installs
  the Qt system libraries Ubuntu lacked, reports failures as annotations and
  names a hung test. Releases verify the tag version and add a wheel and sdist.

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
