# Morale

A native, open-source embroidery studio for the joy of making. Built with
Python and Qt Widgets for Windows, Linux, and macOS. No browser, server, account,
or network connection is used by the application.

This is an early working release (**0.2.0**), **not yet a Hatch replacement**. The ambition
is a capable, approachable digitizer that hobbyists can use without a subscription.

Release notes are in [CHANGELOG.md](CHANGELOG.md). Progress toward v1 is tracked in
[the parity ledger](docs/V1_PARITY.md) and [the roadmap](docs/ROADMAP.md).

## Run

```sh
conda activate morale
python -m morale
```

From a fresh Python 3.11+ environment:

```sh
python -m pip install -e ".[dev]"
python -m morale
```

The app opens an editable wildflower example. Use **File → New design** for a
blank hoop. Projects and exports are saved wherever you choose. Local recovery
copies protect interrupted sessions without overwriting your saved project.

Main-window stitch previews calculate in a separate process. Keep editing while
counts and stitches update; obsolete calculations are cancelled. **Cancel
calculation** stops a job and **Recalculate** retries it. Playback, machine export,
thread charts and stitch editing wait for a current preview. Projects can still
be saved while calculating. Preview workers have a 60-second limit. Some editing
commands still validate candidates synchronously, and ordinary file decoding and
some export/dialog operations can still pause the interface.

## Highlights

- **Image and SVG to embroidery:** smooth color tracing, automatic running/satin/fill
  selection, perceptual thread matching, covered-fill removal and review reports.
- **Manual digitizing:** shapes, Bezier paths, satin rails, compound outlines,
  Boolean operations, snapping, grouping and numeric transforms.
- **Stitch types:** tatami (with spacing gradients), contour, motif fills and
  repeats, running/triple, satin, configurable underlay and pull compensation.
- **Lettering and appliqué:** system-font text (straight, arced, along a path,
  monograms) and three-stage appliqué with automatic satin covers.
- **Stitch-level editing** in a command table or directly on the canvas.
- **Machine files:** 40 readers, 9 writers, batch conversion, file comparison and
  multi-hoop splitting.
- **Library:** folder browser, recursive search, thumbnails and PDF catalogs.

## Artwork and image digitizing

- **File → Digitize artwork** accepts SVG vectors directly and traces PNG/JPEG/BMP/WebP color regions into
  editable fill objects using smooth shared-boundary curves. Set physical width,
  color count, detail filtering and curve simplification; compare source, vector
  and stitch previews in a cancellable worker, then add the result with Undo.
  Save the fitted curves as SVG. Holes, transparency and source padding are
  preserved. Smooth tracing samples up to 1024 pixels; the original pixel tracer
  remains available for comparison. Automatic selection produces running stitches
  for thin columns, satin for eligible narrow regions, and fill elsewhere, with
  per-region explanations and overrides. Optional travel ordering keeps overlap
  order and reports the distance saved within each thread-color run. Match traced
  colors to a built-in palette or your CSV thread chart before applying them.
  **Split suitable branching shapes** cuts Y, X, star and letter-like forks at
  their crotches into satin columns, leaving broad areas as fill. Join treatment
  and photographic digitizing remain pending. See [image digitizing](docs/IMAGE_DIGITIZING.md).
- Embedded PNG/JPEG/BMP/WebP reference images for manual tracing, with numeric
  positioning, sizing, rotation, opacity, visibility, removal and undo.

Use **File → Import reference image** to place a tracing guide beneath the grid
and stitches. **View → Reference image settings** adjusts it; **Remove reference
image** removes it with undo. The image is embedded as PNG in the project and is
never exported to the embroidery machine. Import is limited to 20 MB/16 megapixels
and reduces the preview's longest side to 2048 pixels. The source file is untouched.
This does not automatically digitize the image; trace it using the drawing tools.

- **File → Import SVG artwork** converts solid fills into editable compound
  objects and strokes into editable Bezier running outlines. Physical units,
  viewBox sizing, group transforms, local use references, fill rules and holes
  are supported. Artwork is centered at its physical size; it is not auto-shrunk
  to the hoop. SVG stroke widths become centerlines, and transparency becomes
  opaque thread color, with import notes. Text, stylesheets, gradients, clipping,
  masks and filters must first be converted to plain paths in a vector editor;
  dashed strokes can be expanded through **Digitize artwork** (below). Imports are limited to 2 MB and 500 resulting objects.

SVG stroke expansion also supports dashed borders with numeric or absolute-length
patterns, signed offsets, odd pattern repetition, and round/square dotted caps.
Enable **Expand SVG strokes into satin or fill regions** in artwork conversion.
Each dash becomes part of editable filled geometry, with travel across gaps.
Positive, finite `pathLength` values calibrate dash spacing and offsets before
transforms, preserving cap size. Percentage/font-relative dash lengths and
zero-valued `pathLength` still require conversion to plain paths in the source editor. Expansion is bounded to 2,000
candidate dash pieces and the existing project contour limits.

SVG `paint-order` is preserved in both direct import and assisted conversion.
For example, `paint-order="stroke"` sews the border before the fill, matching a
border painted underneath its interior. Group/inline styles and omitted-order
shorthand are supported. Preview layers and optional covered-fill removal use
that same ordering. SVG marker artwork itself remains unsupported.

Artwork conversion offers **Fill holes smaller than** (mm²), disabled by default.
It closes tiny voids while preserving larger nested holes, saves the choice in
conversion presets, and reports the added material for review. Original artwork
remains available for comparison, and insertion can be undone.

After generating artwork, **Save conversion review PDF…** creates a shareable
report of the artwork, stitches, both density maps and conversion measurements.
It uses the completed preview and is invalidated when settings change. The report
is an overview, not an actual-size placement template.

## Drawing and object editing

- Native menus, file dialogs, color picker, and scalable drawing canvas.
- Ellipse, rectangle, leaf, polygon, and open running-path digitizing tools.
- Drag to move; numerical position, dimensions, and rotation in millimeters.
- Mirror objects left/right or top/bottom and align their actual geometry to
  sewing-field edges or centers through **Edit → Arrange object**.
- Native copy/cut/paste of selected editable objects, including transfer
  between Morale windows, with validation and fresh identities on paste.
- Multi-selection, persistent flat groups, selection-wide moves/mirrors, palette
  changes, duplication/deletion, sequence movement, alignment and center distribution.
- Thread colors, object visibility, sequence ordering, duplication, deletion,
  and undo/redo (up to 100 snapshots and a 32 MiB budget per direction; at least
  the latest snapshot is retained even if larger).
- Numeric point editing for polygons, running paths, satin rails, and compound
  contours, with undo. Compound editing includes a contour selector, live outline
  preview, selected-point marker, and adding/removing contours and vertices.
- Direct canvas node dragging for polygons, running paths, satin rails, and compound
  shapes. Select one object, choose **Nodes**, and drag a handle. Grid snapping
  applies; Escape cancels, and releasing validates and regenerates stitches in one
  Undo step. Numeric editors provide point insertion/deletion.
- **Edit → Path start and direction** chooses an existing start anchor and
  direction for closed running/triple outlines, reverses open paths or satin
  station order, and changes compound contour sewing order. The preview includes
  actual stitches, travel, underlay and finishing, with entry/exit markers and
  coordinates. Changes support Undo. Primitives become polygons when rerouted;
  lettering becomes editable contours. Fill routing, arbitrary points within
  curve segments and reversal of imported manual commands are not included.
- Editable cubic Bezier paths and closed polygons. Draw a path/polygon, choose
  **Edit → Enable Bezier handles**, then drag the small handles in **Nodes** mode.
  Anchors move their incoming/outgoing handles together. Numeric rows repeat
  incoming handle, anchor, outgoing handle. Curves persist in projects and
  regenerate running/fill stitches after resizing. **Edit → Bezier handle dragging**
  selects independent, smooth or symmetric canvas editing. Smooth keeps the
  opposite handle's length while aligning it; symmetric also matches its length.
  Moving an anchor translates both handles. A collapsed smooth handle retains the
  opposite handle because its direction is undefined. Each drag supports Undo.
  The mode applies to subsequent drags in the current window; numeric edits remain
  independent and persistent per-node constraints are not implemented yet.
- Union, subtraction, and intersection of selected closed outlines. Cut holes or
  combine components through **Edit → Combine closed outlines**. The first selected
  object in sewing order supplies thread and stitch settings; subtraction cuts all
  later selected shapes out of it. The result replaces the sources with an editable
  compound shape, and Undo restores them. Modified lettering becomes plain contours.

Draw shapes by dragging. For polygons and paths, click each point and press Enter
or double-click to finish; Escape cancels. Scroll to zoom, middle-drag to pan,
and use View → Fit hoop to recenter. Select an object to edit its properties.
Playback counts include travel commands; the design summary counts sewn stitches.
Reset playback before editing on the canvas.

Mirroring operates in canvas coordinates about the object's center, or the bounds
center of a multiple selection, including rotation and fill direction. Imported stitch commands remain in
sequence. Sewing-field alignment uses geometry bounds and does not resize the
object; a design larger than the field still needs resizing before export.
Shift/Ctrl/Command-click shapes to toggle selection, or use extended selection in
the sequence list. Dragging a selected shape moves the entire selection. Edit →
Select all objects selects the design; text fields keep native Select All behavior.
The palette recolors the selection. Individual properties require one object.

**Edit → Arrange object** provides Group/Ungroup, collective field alignment,
alignment between selected objects and even spacing of their centers (three or
more objects). A normal click selects the whole group; Alt-click selects one member
for editing. Groups persist in projects. Duplicate and Paste assign new group IDs
so copies do not remain linked to originals. **Scale / rotate selection** scales
in canvas axes, then rotates about the selection bounds center or sewing-field
center. Set percentages or a physical width/height; uncheck **Keep proportions**
to stretch the two axes independently. Dimensions describe source geometry before
rotation, excluding compensation and motif extensions. Unequal scaling converts
primitives and lettering to editable outlines; Bezier controls, satin rails and
holes remain editable. Lettering's text settings are removed by this conversion,
and Undo restores them. Fill angles follow the stretch, while stitch spacing,
underlay, compensation and physical motif sizes retain their settings.
Editable shapes regenerate stitches; manual stitch objects retain their command
sequence and change density. The full transform is validated before one Undo step
is committed. Groups are flat; nested groups remain open.

Drag from blank canvas space with Select to enclose objects in a rectangle; only
fully enclosed visible objects are selected, with their group members. Shift adds
the enclosed objects to the selection. Escape cancels the rectangle. **View → Snap
to grid** snaps drawing points and the dragged object's center, moving a multiple
selection by a shared delta. Measurement remains unsnapped. **View → Grid spacing**
sets a physical step from 0.1 to 100 mm. Fine display lines are thinned when zoomed
out, but snap spacing stays exact; zoom in to see all subdivisions.

**Edit → Copy / Cut / Paste** uses the desktop clipboard. Object pastes preserve
their positions and appear after the selected object in the sewing sequence;
Duplicate remains the operation that offsets a copy. Native text fields keep
their normal clipboard behavior. The clipboard payload retains geometry, lettering,
manual commands and thread metadata, but excludes reference images. Invalid or
oversized payloads and project-limit violations do not change the target design.

Use **View → Snap to object edges and centers** to align objects while dragging.
Dashed blue guides mark nearby edges or centers; a selection moves together.
Object alignment takes priority over grid snapping on an aligned axis.

## Stitch types and sew-out controls

- Basic tatami fill and running stitches, adjustable row spacing, stitch length,
  fill angle, and optional edge-run underlay. Resizing regenerates stitches.
- **Gradient row spacing** gradually changes tatami spacing from **Row spacing**
  to **End row spacing** across the shape, perpendicular to the fill angle.
  Larger spacing produces sparser coverage. **Reverse spacing gradient** swaps
  the dense and sparse sides. Holes, safe row connectors, compensation and
  finishing remain available; underlay retains its own spacing. Equal endpoint
  spacing gives the original uniform fill. This is a spacing gradient in one
  thread color; automatic color blending and radial fills remain pending.
  [Gradient sampler](examples/density-gradient.morale).
- Contour fill follows successive inward offsets, including holes and separate
  components. Choose **Contour fill** in object properties. The first contour is
  half a row spacing inside the outline; each closed run is separated by a jump.
  Underlay, finishing and cleanup remain available. Tatami pull compensation and
  row connectors do not apply. Very small features can disappear between offsets.
- Repeating diamond, box and cross motifs along open or closed outlines. Choose
  **Repeating motifs** and set physical motif width, height and spacing. Motifs
  rotate to the local guide direction; they remain rigid and can extend beyond
  the guide. Open guides use balanced end margins, while closed guides distribute
  repeats evenly. Jumps separate motifs (and cross strokes). Resizing the guide
  regenerates the arrangement while retaining motif size in millimeters.
- **Motif fill** repeats built-in or custom motifs across a closed shape.
  Set motif width/height, horizontal **Motif spacing**, **Motif row spacing** and
  fill angle. The centered grid clips stitched segments at boundaries and holes;
  disconnected fragments use jumps. Motif sizes remain physical dimensions when
  resizing the shape. Select Motif fill before applying a captured/loaded custom
  motif to retain area filling. Underlay, tatami compensation and spacing
  gradients do not apply; finishing and short-stitch cleanup remain available.
  This uses straight motif segments in one thread color. Clipping complexity and
  candidate tiles are bounded; dense overlaps need sew-out evaluation.
  [Motif fill sampler](examples/motif-fill.morale).
- **Edit → Custom motifs** captures an editable outline and applies it to selected
  guides. Custom geometry repeats in each guide's thread color and is embedded in
  the project. Save/load standalone `.mmotif` files to reuse or share it, including
  motifs recovered from a selected guide. Templates support 64 paths and 2,000
  points. [Example custom motif](examples/corner.mmotif).
- Single/triple running stitches, paired-rail satin with a split-length limit and
  center-run underlay, optional ties and object-end trims, and interior-only fill
  row connections. File → Load satin and running sampler demonstrates these.
- Adjustable pull compensation (0–2 mm per side) for fill row ends and satin
  rails. Original outlines and underlay retain their size. Compensation can shrink
  or close small holes; overlapping expanded fill spans are merged. Compensated
  endpoints outside the original shape use jumps between rows. Satin split limits
  and hoop checks still apply. Choose settings through physical sew-out tests.
- Configurable underlay: edge run, sparse perpendicular fill, or both for filled
  shapes; center run, zigzag, or both for satin. Set an inset (0–3 mm) and support
  row spacing. Insets preserve holes and may remove narrow support regions;
  fully collapsed satin supports use a center run. Default settings retain the
  original edge/center-run behavior. These are geometric controls, not calibrated
  fabric presets.
- Optional short-stitch cleanup (0–1 mm threshold) removes redundant interior
  points in generated stitches within a 0.01 mm path tolerance. Endpoints, sharp
  corners, reversals, controls and finishing ties are retained, so necessary short
  stitches can remain. Zero disables cleanup. Imported manual stitches are unchanged.

Fill objects also offer **Route disconnected fill runs** to reduce internal jump
travel while retaining entry/exit and the original sewn segments. Artwork
conversion exposes the same optional setting. It compares up to 2,000 runs;
review changed sewing order and exported travel before a test sew-out.

Satin rails are clicked in alternating left/right pairs, then finished with Enter.
The engine interpolates between pairs and rejects crossed or concave local cells.
It does not yet optimize acute corners or detect all distant self-overlaps. Long
spans split at the selected limit; center-run underlay is available. Edit → Edit
path / satin points changes coordinates, adds points, or removes them. Pair counts
and geometry are checked before edits replace the object.

## Lettering

- Editable system-font lettering with text, font, height, and character spacing.
  Compound contours preserve letter holes and separate components in fills.

**Edit → Add lettering** (Ctrl+L) creates a single line of text from an installed
font. **Edit → Edit lettering** changes text, font, letter height, spacing, and layout.
Choose straight text, curved outlines, or a three-letter monogram. Curves accept
−180° to 180° and reject configurations that fold the letters across the arc
center. Monograms use the entered left-to-right order, with the center initial
1.4 times the outer-letter size. Their spacing control changes the gaps.
Use the regular stitch controls for fill, single running, or triple running text.
Generated contours are saved in the project, so a missing font on another computer
does not change the saved design. Editing text there requires a replacement font;
the dialog identifies unavailable saved fonts. Unsupported characters are rejected.

This is system-font outline digitizing, not a library of purpose-digitized satin
fonts. Small lettering needs physical tests. Curved layout bends the outlines
along an arc. **Edit → Add lettering along path** places shaped glyph groups
without bending them on a selected path or polygon, including drawn Bezier paths.
The baseline is copied into the lettering and stays fixed when editing text;
the original guide is hidden by default, with an option to keep it stitchable.
Adding text and hiding the guide undo together. Text must fit the baseline.
Inspect tight bends for overlaps or gaps between connected-script glyphs.
Font-specific satin routing remains open.
Text is limited to 80 characters, 1–100 mm letter height, 256 contours and 20,000
outline points. Compound fill uses even-odd nesting: holes stay empty and nested
islands are filled. Connections are checked against all contours.

## Appliqué

- Three-stage appliqué from a closed outline: placement, tack-down, and automatic satin
  cover borders with tatami fallback, with operator pauses and saved fabric-handling instructions.

Select a closed shape and choose **Edit → Create appliqué stages**. The command
replaces it with three editable stages in sewing order: a placement run and stop
to place fabric, a tack-down run and stop to trim excess fabric, then cover borders.
Automatic mode uses validated satin rails where possible, with named tatami
fallbacks and a reason in the stage instructions. Separate outer/cutout borders
become separate cover objects. Tatami mode retains a single compound cover band.
Border width is 0.5–6 mm. Instructions appear with the selected stage and in the
CSV chart. Undo restores the original object. Verify operator stops in the target
machine and test fabric/stabilizer settings on scrap material.

**Operator stop after object** is also available for other generated objects.
Formats that encode stops as thread changes require reusing the current thread
at those pauses; the export dialog describes this distinction.

## Individual stitch editing

- Individual stitch editing with a virtual coordinate/command table, insertion,
  multi-row deletion, and a nearby-stitch preview with dashed travel lines.

Choose **Edit → Edit individual stitches** for the selected object. Coordinates
use millimeters; change a command through its dropdown or insert/delete rows.
Trim and stop commands do not move the needle, so their coordinates follow the
preceding motion command. Each object must retain an initial jump. The detail
preview highlights the selected command and up to 50 neighbors.

Applying stitch edits converts that object to manual stitch data. Its color,
identity, and sequence position remain; resizing then changes density instead of
regenerating stitches. Cancel leaves the object untouched, and Undo after applying
restores the original editable geometry. The dialog has its own Undo/Redo buttons
and standard keyboard shortcuts for committed coordinate/command changes,
insertions and multi-row deletions. Trim/stop position adjustments belong to the
same action. New edits clear Redo; invalid and unchanged edits do not. History
retains up to 100 actions and 500,000 changed-row entries, always keeping the most
recent action. Opening a coordinate editor without changing its displayed value
preserves the original precision.

Choose **Stitch points** on the toolbar to move one or more needle positions on
one selected object directly in the main canvas. Click or drag a point; repeated
clicks cycle coincident positions. **[** and **]** select adjacent motion commands,
skipping trim/stop controls. Arrow keys move 0.1 mm, Shift+arrows move 1 mm, or one
grid step when snapping is enabled. Escape cancels a drag; releasing makes one
Undo action. Moving generated stitches converts that object to manual stitches,
with its actual commands retained and following trims/stops repositioned.
Undo restores the source geometry. At dense overview zoom, displayed point dots
are sampled to 20,000; hit testing and keyboard navigation include every command.

In **Stitch points** mode, Ctrl-click toggles needle positions and Shift-click
selects a command range (excluding trim/stop controls). Shift+[ / ] extends a
selection with the keyboard. Drag a selected point or use arrows to move the
whole set; snapping uses the active point and preserves relative offsets. Drag
from empty canvas space to box-select points; Ctrl/Shift adds to the selection,
and Alt-drag removes points (including when starting over a point). Each
move is one Undo step. Moving generated stitches converts that object to manual
stitches; Undo restores its editable geometry. With the stitch canvas focused,
Ctrl+A selects all needle positions and Delete removes selected positions.
Retained trim/stop controls stay in order. At least one motion point must remain;
use Delete object to remove the whole object. Removing the initial jump adds an
entry jump at the first remaining position. Deleting points reconnects the
remaining path, so inspect the preview.

In **Edit individual stitches**, **Split long stitches** adds intermediate needle
positions along sewn spans. Choose a maximum length and either the whole object
or selected commands. Travel, trim and stop commands are retained. Review the
extra penetrations before applying; local Undo and the main window's Undo are
available.

## Threads and colors

- Thread brand/catalog/name editing, imported thread metadata retention, and sewn
  path/travel measurements. CSV charts include metadata and per-object lengths.
- **Edit → Thread catalog / match colors** offers searchable PEC/JEF format
  palettes and personal CSV catalogs. Assign a highlighted thread to the selection,
  or match each selected color to the nearest shown row (perceptual Oklab by
  default, RGB optional).
  Catalog metadata is saved in the project and changes support Undo. The last
  catalog is remembered within the current window; reload its CSV in a new session.
  [Example CSV](examples/thread-catalog.csv) uses fictional collection labels.
  Screen-color matching is approximate; bundled format palettes are not verified current
  manufacturer spool inventories.

Thread brand, catalog number, and name are editable in object properties. New
shapes inherit the selected thread; changing RGB manually clears its catalog
identity so a recolored object is not mislabeled. Undo restores both. Distinct
catalog identities cause a thread change even when their RGB colors match.
PES v6 retains supported thread metadata; other formats may drop or map fields.
Keep the `.morale` project and CSV chart for the complete information.

The design summary reports **sewn path length**, not calibrated spool consumption.
Travel is measured separately in CSV, while trims/stops add no sewn distance.
Actual consumption depends on fabric thickness, tension, underlay, and tails;
fabric-specific estimation and manufacturer thread libraries remain to be added.

Thread tools and artwork conversion can import **INF and EDR palettes** alongside
CSV catalogs. INF retains RGB values, descriptions and chart names; EDR contains
RGB colors only. These are explicitly selected color sources for matching, not
stitch files or automatically assigned machine companions. Palette order and
repeated colors are retained. Truncated or inconsistent records are rejected.

The thread-selection table displays chart names alongside descriptions and RGB
distance. Chart names can be searched, including those imported from INF palettes,
and remain attached to the assigned thread.

Manual thread matching now defaults to **Perceptual (Oklab)**, with RGB comparison
available in the thread dialog. Ranking, displayed distance and per-object color
matching use the selected metric. The choice is retained while the main window
is open; assignment remains undoable and preserves catalog metadata. These are
screen-color estimates, not measurements of physical thread.

The thread dialog’s **Match preview** tab shows proposed matches for every distinct
selected object color, including affected-object counts. Changes to the palette,
search filter or metric rebuild the preview. Computation yields between source
colors and stops on close. “Match colors to shown threads” applies the same filtered
candidate set and metric; assigning a single highlighted thread remains on the
Catalog threads tab.

**Export shown palette…** in the Catalog threads tab saves the filtered catalog
in displayed order as INF or EDR. INF exports RGB, descriptions and chart names;
EDR exports RGB only. Other thread metadata is omitted. Palette files contain no
stitches, and their displayed order is not automatically a design’s sewing order.
Exports are written atomically, with byte-correct UTF-8 lengths for INF names.

## Preview, measurement and templates

- Hoop presets, grid, zoom/pan, stitch counts, and stitch playback.
- Preview individual consecutive thread runs through the playback selector.
  **View → Show travel moves** adds dashed jump lines; **Show trims, stops and
  thread changes** adds command markers. Previous/next control actions navigate
  trims, stops and thread boundaries. The counter reports the current command.
  Reset restores the complete design. These controls do not alter sewing order.
- **File → Compare machine file with design** overlays current and decoded sewn
  paths, with independent visibility, optional travel paths, pan and zoom. The
  table compares command counts, thread runs, path lengths and sewn-point bounds.
  Point-by-point distance is calculated only for matching command sequences;
  coordinates are never automatically aligned. Matching metrics do not prove
  equivalent physical sewing.
- Custom rectangular sewing fields, millimeter/inch property display, rulers,
  and a drag-to-measure tool. Unit switching never changes document geometry.
- **File → Export placement template (PDF)** creates actual-size A4 or Letter
  pages with 10 mm overlaps, shared alignment crosses, hoop outlines, and a 50 mm
  scale-check ruler. Choose stitches or source outlines. Light thread colors are
  darkened for visibility. Print at 100% / Actual size and measure the ruler before
  using the template. This does not split the embroidery into multiple sew-outs.

Use **View → Custom sewing field** to enter usable hoop dimensions (20–500 mm).
**View → Measurement units** changes dimension/stitch-setting display between
millimeters and inches; coordinate data and machine exports remain millimeter-based.
The point and individual-stitch dialogs explicitly continue to use millimeters.
Choose **Measure** in the tool strip and drag between two points to read distance
and X/Y differences. Rulers follow zoom/pan; default grids are 10 mm or ¼ inch,
with custom spacing available. These are
design measurements, not a physical screen calibration or printable template.

## Projects, machine files and export

- Editable `.morale` JSON projects, atomic saves, validation, unsaved-change prompts.
- Local recovery snapshots after three idle seconds and every 30 seconds during
  editing. Startup offers abandoned sessions; **File → Recover interrupted session**
  opens them later. Restored designs require Save As. Cancel keeps recovery copies;
  saving, deliberately replacing a design, or closing normally clears its copy.
  Live windows keep separate locked copies in the OS application-data directory.
  Long synchronous operations can delay checkpoints; failed writes appear in the
  status bar. Recovery does not replace explicitly saving your work.
- Machine export through pyembroidery and CSV thread sequence charts.
- Machine-file open/import and merging through 40 registered readers. Imported
  color blocks remain independently transformable stitch objects.
- Nine machine exports: DST, EXP, JEF, PEC, PES (v1/v6), TBF, U01, VP3, and XXX.
  PES v6 is the default; v1 is available in the export format selector.
- Empty-design and hoop-bound checks before machine export.

After export, the confirmation reports the source stitch count and any needle
positions added to preserve long sewn spans within the format's limits. Batch
reports include the same information. These are preparation counts; file writers
may add further stitches or control commands.

Imported designs preserve stitches, travel, trims, stops, and color boundaries.
Some formats encode stops as color changes or decode repeated colors as stops;
the app reports these distinctions. Needle selections are normalized to thread
blocks with a notice. Sequin/specialist commands are rejected rather than discarded.
Imported objects can be recolored, moved, rotated, resized, reordered, and combined
with newly digitized shapes. Resizing imported stitches changes density rather
than regenerating it. Save the result as a `.morale` project; source machine files
are never overwritten by project saving. Schema v2 projects still load v1 data.

## Design library

- **File → Browse design folder** provides a native folder tree, filename filter,
  and a stitch thumbnail with details for the selected project or machine file.
  Preview decoding runs in a cancellable subprocess with a 30-second timeout;
  changed files require a refreshed preview before opening. The browser reads
  originals and cleans its temporary images. It remembers the folder for the
  current window. Opening still uses the normal unsaved-change prompt.

The design library also offers **Search subfolders** for case-insensitive matches
in filenames and relative paths. Results are found without decoding designs;
the selected result gets a detailed preview. Enable **Thumbnails** to load
visible result tiles, one at a time in a separate decoder. Up to 200 thumbnails
are cached in memory; scrolling loads more. Switch thumbnails off to cancel. Search runs separately and can be
cancelled. Hidden entries and symbolic links are skipped. Limits of 200,000
entries, 5,000 matches and 30 seconds keep scans bounded; the result summary
reports truncation and unreadable entries. **Folder view** returns to browsing.

In the design library, **Create PDF catalog…** lets you choose up to 100 designs
and prepare a printable thumbnail sheet. Each preview runs separately with a
30-second timeout; Cancel stops preparation. Save PDF becomes available when
preparation finishes. The catalog lists dimensions, stitch/RGB-color counts and
unreadable files, six entries per A4 page. These are preview snapshots, not
actual-size placement templates. Saving replaces the destination only after the
PDF is complete.

Catalog cards use numbered references and shortened labels to stay readable.
A paginated file index retains the full source paths and failure details, so
similarly named designs and long errors can still be identified in print.

Catalog saving rejects destinations that name a source design or an existing
symbolic/hard-link alias of one. The check runs before rendering and again before
publishing the completed PDF; rejected saves leave the source intact.

After searching the library, **Catalog results…** prepares the current found set
in its displayed order without another file picker. Select up to 100 results from a larger search, or clear the selection to catalog
the whole found set. Oversized selections are never silently truncated. Folder view does not
reuse a hidden, older search result list.

Library search results support native extended selection. The catalog button
shows “Catalog selection (N)” when results are selected and otherwise catalogs
all found results. Selected designs retain their displayed order in the PDF.

## Multiple hoopings

**File → Split for multiple hoopings** plans an oversized design in a cancellable
worker. Choose hoop dimensions, margins and optional machine output. Review the
placement map, then save a new ZIP bundle containing the original project,
individual manual-stitch projects, optional machine files, a PDF/PNG overview,
paired alignment coordinates, per-placement stitch counts and instructions.
`placements.csv` and the PDF distinguish native stitches from positions added
for machine-format preparation. Existing bundles are never
overwritten. Changing settings invalidates the reviewed plan.

Hoop fields overlap by twice the margin; sewn content belongs to nonoverlapping
cores. Crossing stitches gain seam endpoints, with jumps/trims between fragments.
Shared-boundary segments are assigned once. Optional removable alignment crosses
form a separate first stage with a pause. Source operator stops are retained even
when a preceding stage lies in another tile. Needle positioning, seam reinforcement
and physical alignment still require checking on scrap fabric; seam ties are not
added automatically. The map is an overview, not an actual-size template.
Disconnected tiles may need placement from center coordinates and the separate
actual-size source template. Plans are limited to 100 candidate placements and a
60-second worker run. [Multi-hoop sampler](examples/multihoop-sampler.morale).

## Batch conversion

- Native batch conversion queue with per-file results, JSON reports, cancellation,
  60-second worker timeouts, collision detection, and no-overwrite publication.

Choose **File → Batch convert machine files**, add up to 500 files, choose an
output folder and format, then start. Conversions run in separate processes; one
bad file does not stop the queue. Cancel stops the current worker and pending
files. Completed conversions remain available. Closing the dialog during a job
cancels it and waits for worker shutdown.

Existing destinations are skipped. Inputs with colliding output names (including
case-only differences) are all skipped so the result does not depend on file order.
Staging files are published only after successful conversion, using a hard link
or a native exclusive rename. If neither operation is supported by the destination
filesystem, that file fails without a partial output; convert locally and copy the
completed files to the machine. Ordinary open/import operations remain synchronous;
batch worker isolation does not yet cover those workflows.

For terminal use, the same queue emits one JSON result per file:

```sh
python -m morale.batch design.pes another.jef --output ./converted --format dst
```

Create the output folder first. The command exits nonzero if any file fails or is
skipped. Use `--pes-version 1` with `--format pes` for older PES readers; v6 is the
default. File format and physical machine compatibility limits still apply.

## Embroidery limitations

Stitch generation is experimental and has not been validated by physical sew-outs.
Preview on the target machine and test on scrap fabric. The app checks a rectangular
hoop boundary, not the machine's actual sewing field or hardware compatibility.
Choose the format and hoop supported by your particular machine.

Fill rows use explicit jumps by default. Enable **Connect safe fill rows** to sew
short connectors only when their entire line stays inside the polygon; jumps
remain across exterior gaps. Tie-in/tie-off options lock each continuous sewn run,
so disconnected fills can add many locks. Object-end trims are optional.
Pull compensation, inset underlay and bounded fill-run routing are geometric
controls, not fabric-calibrated presets; general travel optimization remains open.
Overlapping shapes sew on top of one another, except where artwork conversion's
optional covered-fill removal cuts lower fills away.
JEF, PEC, and PES v1 map colors to fixed palettes; DST, EXP, and U01 do not embed RGB
thread colors. PES v6 preserves RGB. Export a CSV chart to retain the intended color sequence. Preview
shows the engine's commands; format writers may normalize them during export.

Advanced automatic digitizing and routing remain open. Exports contain machine stitches;
retain the `.morale` file for editable geometry. See [the v1 parity ledger](docs/V1_PARITY.md)
and [the roadmap](docs/ROADMAP.md). V1 parity remains in progress.

## Test and package

```sh
python -m pytest
python -m morale.compatibility --output docs/compatibility-report.json
python -m PyInstaller --noconfirm --clean --windowed --onedir --name Morale --collect-data morale --add-data "LICENSE:." --add-data "THIRD_PARTY_NOTICES.md:." run_morale.py
python scripts/check_bundle.py --output artifacts/bundle-self-test
```

The test suite runs Qt with its offscreen platform plugin. Tests cover the engine,
project validation, all 81 ordered writer conversion pairs, controls/pauses, a
hand-encoded DST fixture, and native UI workflows. The generated report distinguishes
synthetic round trips from unverified reader availability. Real machine sew-outs
and externally produced golden files remain necessary evidence.

Build on each target OS: PyInstaller does not cross-compile. Output is in `dist/`;
distribute the entire `Morale` directory on Linux/Windows, or the `.app` bundle on
macOS. The repository includes a manually triggered GitHub Actions build matrix.
These are development bundles, not signed installers. Windows/macOS execution,
signing, installers, and physical machine compatibility still need validation.

The bundle check launches the built executable with `--self-test` and requires a
new output directory. It exercises an offscreen native window, project save/reopen,
generation and raster/SVG tracing subprocesses, artwork Undo, and nine-format
export/reopen. It leaves a JSON report, generated fixtures, previews and worker
logs. The manually triggered build matrix runs this check and retains the report
with each platform bundle, including failed runs. A successful smoke test confirms
those packaged workflows; it does not establish full parity or physical sewing
fidelity. To run the same workflow from source, use
`python -m morale --self-test artifacts/source-self-test`.

To publish a release, update the version in `pyproject.toml` and
`morale/__init__.py`, add a `## X.Y.Z` section to [CHANGELOG.md](CHANGELOG.md),
commit, then tag and push over SSH:

```sh
git tag -a vX.Y.Z -m "Morale X.Y.Z"
git push origin master vX.Y.Z
```

The tag triggers `.github/workflows/release.yml`, which tests, builds and
self-tests Linux, Windows and macOS bundles, then creates a GitHub Release with
that changelog section, the archives and `SHA256SUMS`.

## Architecture and contributing

- `morale/model.py`: versioned project schema and editable geometry.
- `morale/engine.py`: Qt-independent geometry-to-stitch generation.
- `morale/formats.py`: pyembroidery adapters and guarded exports.
- `morale/canvas.py`: native drawing, hit testing, tools, and playback rendering.
- `morale/app.py`: desktop workspace, editing commands, and file workflows.
- `morale/smooth_trace.py`, `raster_trace.py`: raster color tracing to vector regions.
- `morale/auto_digitize.py`: physical-width running/satin/fill suggestions.
- `morale/trace_dialog.py`: the conversion workspace and its cancellable worker.
- `morale/library.py`, `preview_worker.py`: design browsing and isolated decoding.
- `morale/image_benchmark.py`, `self_test.py`: internal benchmark and bundle smoke test.

Start with a reproducible example and test for engine or format changes. Preserve
millimeter units in the model; convert to tenths of millimeters only at the format
boundary. Large designs are capped at 250,000 preview commands and 500 objects.
The application entry point enables worker-based main-window previews. Internal
test/library windows can use deterministic synchronous previews; asynchronous
window tests exercise real subprocesses, cancellation and result versioning.
Pre-commit generation checks and some dialog/export workflows remain synchronous. Engine, format and
conversion modules have docstrings describing their responsibilities; about 85
modules live in `morale/`.

Morale is MIT-licensed. Dependencies retain their own licenses; see
[third-party notices](THIRD_PARTY_NOTICES.md).
