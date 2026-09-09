# V1 parity test ledger

## Objective

Reach a v1 test of advanced hobbyist embroidery feature parity, with as much
cross-platform and machine-format compatibility as we can establish before
collecting externally produced files. This ledger keeps the full objective open;
passing today's tests does not mean v1 or Hatch parity is complete.

Reference benchmarks: [Hatch Digitizer](https://hatchembroidery.com/products/hatch-embroidery/digitizer)
and the [published feature comparison](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/New_Release/prodiff_table/Feature_Comparison_Table.htm).
The comparison table is for Hatch 3; a final parity audit must also reconcile the
current Digitizer release. The acceptance scenarios below are Morale's work plan,
not a reproduction of the vendor's specifications or a claim of equivalence.

## Acceptance ledger

| Area | Required v1 test scenario | Current evidence / outstanding work |
| --- | --- | --- |
| Native desktop | Launch and complete create/save/reopen/export on Windows, Linux, macOS | Linux offscreen native tests and development packaging; Windows/macOS runs pending |
| File compatibility | Open, combine, transform, save, reopen, convert machine designs | 40 registered readers; 9 writers and 81 conversion pairs checked synthetically; external files absent |
| Project fidelity | Preserve geometry, settings, stitch commands, thread order, and undo history semantics | Schema v2 retains imported stitches; v1 loading supported; undo/save/reopen tests |
| Batch workflows | Convert many files with per-file results, cancellation, and no source overwrites | Native queue and CLI; process isolation, timeouts, reports, collision/race protection and cancellation tested. Windows/macOS and actual removable-drive execution pending |
| Manual digitizing | Draw/edit open and closed Bezier paths, holes, nodes, entry/exit points | Open/closed Bezier editing, smooth/symmetric handle dragging, compound editing and outline Boolean operations available. Running/triple start-anchor and direction controls, satin station reversal and contour sewing order tested. Persistent per-node constraints, arbitrary curve-segment starts and fill entry/exit routing pending |
| Object editing | Multi-select, clipboard, group, transform, mirror, align/distribute, snap | Multi/marquee selection, flat groups, clipboard, uniform/nonuniform transforms, alignment/distribution and configurable grid snapping tested. Nested groups and object/guide snapping pending |
| Stitch editing | Select individual stitches, move/insert/delete, change travel/trim/stop commands | Virtual command table, numeric movement, insertion/multi-row deletion, command dropdowns and dialog-local Undo/Redo tested. Main-canvas point picking/dragging, coincident-point cycling, keyboard navigation/nudging, snapping and cancellation tested. Multi-stitch canvas selection remains pending |
| Running stitches | Single/triple runs and controlled corners along open/closed paths | Single/triple running and corner preservation tested |
| Satin | Digitize rails, vary width, handle corners, split excessive spans | Paired-rail drawing, numeric editing, interpolation, local crossing rejection, split length, center underlay tested; acute corner optimization/global overlap checks pending |
| Fill generation | Predictable tatami coverage of concave shapes/holes, variable angles/density | Scanline fill supports compound even-odd contours, holes, nested islands, and disjoint components with interior-tested connectors; advanced routing pending |
| Sew-out quality | Tie stitches, trims, minimum-length filtering, compensation, underlay, overlaps | Ties/trims, conservative short-stitch cleanup, inset edge/sparse-fill and center/zigzag underlay, and fill/satin compensation tested. Fabric presets, overlap optimization and physical sew-outs pending |
| Lettering | Editable text, font choice, sizing/spacing, curved layouts, monograms | Straight/arc-bent system-font text and center-enlarged three-letter monograms, editable settings, portable contours and nine-format export tested. Arbitrary-path glyph placement and purpose-digitized embroidery fonts pending |
| Artwork | Reference image, SVG import with units/transforms/holes, editable tracing | Embedded raster references, SVG solid-fill/running-outline import, and raster color-region tracing with editable contours and Undo tested. SVG effects and trace smoothing pending |
| Automatic digitizing | Turn raster/vector artwork into editable objects; expose correction tools | Solid SVG fills generate tatami and SVG strokes generate running outlines. Raster color reduction and connected-region tracing preserve holes with cancellable previews. Stitch-type inference, photographic digitizing and optimized automatic routing pending |
| Appliqué | Placement, tack-down, cover stitches, operator stops, fabric instructions | Editable placement/tack-down/tatami-cover stages, pauses, instructions, Undo and nine-format pause preservation tested. Automatic satin borders and physical fabric validation pending |
| Decorative stitches | Motifs, programmable fills, contour/ripple/stipple and gradient/radial effects | Contour fill, built-in/custom outline repeats and clipped area motif fills, plus linear tatami spacing gradients tested. Ripple/stipple fills, gradient color blending and radial fills remain pending |
| Thread tools | Thread catalogs, color mapping, palette editing, usage estimates | Metadata, sequencing, charts/path lengths, PEC/JEF fixed palettes, searchable CSV catalogs and RGB-distance matching tested. Verified manufacturer libraries, perceptual/physical color matching and calibrated consumption estimates pending |
| Simulation | Scrub/play actual commands, travel/trim/stop overlays, per-color inspection | Indexed playback, command overlays/navigation, isolated thread runs and source-versus-decoded file comparison tested. Physical timing simulation and machine-behavior validation pending |
| Measurements | Custom hoops, units, rulers/guides, measurement tools, calibrated printing | Custom fields, mm/in display, rulers, drag measurement and actual-size tiled placement PDFs tested. Printer/physical scale validation, guides and screen calibration pending. Point/stitch dialogs remain explicitly mm |
| Multi-hooping | Split oversized designs into sewable fields with alignment/placement aids | Native worker planning, nonoverlapping sewn cores in overlapping fields, seam splitting, temporary paired alignment crosses, global pauses, ZIP bundles and placement maps tested. Physical alignment/sew-outs, seam reinforcement and nonrectangular hoop planning remain unverified/pending |
| Machine setup | Profiles with supported formats/versions, hoop fields, needle setup | Generic format/hoop controls; no claimed machine profiles yet |
| Design management | Browse library, thumbnails, search, printable catalogs/templates | Native folder tree, filename filtering, isolated selected-file stitch previews and tiled placement PDFs tested. Indexed library search, thumbnail grids and printable catalogs pending |
| Reliability | Background generation/import, cancellation, autosave/recovery, corrupt input checks | Main-window preview/property-refresh workers with versioned results, cancellation/retry and timeouts; batch, folder, tracing and multi-hoop workers; bounded history and local recovery tested. Pre-commit generation checks, ordinary file decoding and some dialogs/exports remain synchronous and can delay checkpoints |
| Accessibility | Keyboard-complete editing, screen-reader labels, contrast, large-text checks | Native widgets and some labels; full audit pending |
| Distribution | Repeatable platform builds, license bundle, install/uninstall, release checks | Build matrix exists; execution and release packaging pending |

## Current compatibility gate

`tests/test_generation.py` exercises real generation workers and main windows with
background previews enabled: complete command/metadata fidelity, replacement of
obsolete jobs, timeout/cancel/retry, malformed output rejection, preview-dependent
action guards, stale result/failure rejection, error correction, cached Undo,
unfinished text retention, a responsive GUI timer during a stalled worker and
shutdown cleanup. Production startup explicitly enables asynchronous previews;
older deterministic UI fixtures use synchronous preview injection. Serialization,
result decoding, source-outline rendering and pre-commit validations still run on
the GUI thread. Worker inputs/results are limited to 50/64 MB and 250,000 commands.

`tests/test_multihoop.py` proves continuous, exactly-once coverage for seam-crossing
segments and shared-boundary lines; total sewn-length retention for a holed fill;
matching world coordinates for paired marks; tile hoop checks; thread metadata
and global stops across stages; source preservation; worker cancellation/errors;
review invalidation; exclusive ZIP publication; project/PDF artifacts and all
nine writers' hoop bounds and pause encodings. Native source and split commands
are tested; these do not establish physical seam quality or alignment accuracy.
Splitting regenerates travel and adds seam needle penetrations. No automatic seam
ties are added. The PDF is a scaled overview with a coordinate table, not an
actual-size sewing template. Tile generation is capped at 100 candidate fields
and 60 seconds in the native workflow.

`tests/test_pattern_fill.py` checks segment clipping at holes, tangencies and
collinear boundaries; nested islands; built-in/custom patterns at different angles;
all generated sewn segments staying inside material; disconnected-fragment jumps;
asymmetric reflections; rotation; persistence; native custom application/Undo;
legacy loading and complexity limits. Nine-format tests check sewn bounds within
0.15 mm and absence of sewn points in the hole interior; these do not certify
travel-command fidelity. Area motifs use a centered rectangular lattice with
physical motif dimensions, at most 5,000 candidate tiles, and a clipping-work
budget. Multi-color and curved tile programs are not implemented.

`tests/test_density.py` checks uniform-fill equivalence, integrated linear-spacing
profiles in both directions, nearly equal endpoints, hole/connector containment,
unchanged underlay, rotated and mirrored density placement, schema/legacy project
loading, native controls/Undo and nine-format sewn bounds within 0.15 mm. Spacing
varies linearly perpendicular to the fill angle; density is its reciprocal.
Nonuniform profiles place scan rows at unit intervals of integrated density with
balanced edge margins, preserving the profile under reflection. Physical coverage
and fabric behavior still require sew-outs.

`tests/test_canvas_stitches.py` checks direct movement, generated-to-manual
conversion, exact command retention, dependent trim/stop positions, coincident
point cycling, keyboard movement, grid snapping, Escape/tool-switch cancellation,
playback/multi-object exclusion, rejected moves, Undo, project persistence and
nine-format export of a moved sewn point. Precise manual rebasing is tested over
100 deterministic coordinate sets. Point dots are sampled at dense zoom; actual
hit testing and keyboard navigation retain all motion commands.

Stitch-editor history tests cover dependent trim/stop positions, command type
changes, disjoint and whole-table deletion, mixed edit sequences, redo branches,
invalid/unchanged edits, active delegate commits, precision retention, recovery
from invalid Apply and keyboard isolation from the parent window. A 100,001-row
table verifies changed-row storage and retention limits. History retains at most
100 actions and 500,000 before/after row entries, except that the newest action is
always retained; this is a row-count bound rather than a byte-memory guarantee.

`tests/test_routing.py` checks closed running/triple start anchors and direction,
Bezier handle exchange on reversal, open-path endpoints, satin station reversal
and underlay entry, compound contour order, primitive conversion, native preview,
independent contour settings, Cancel, Undo, persistence and nine-format sewn-end
preservation within 0.15 mm. The tool reroutes editable geometry and regenerates
stitches; it does not reverse a raw machine command stream or optimize fill paths.

Bezier drag tests cover independent/smooth/symmetric movement, opposite-handle
lengths, collapsed handles, anchor translation, native menu selection and mouse
drags, save/reopen and Undo. Coupling is a current-window canvas editing mode;
numeric edits do not enforce persistent node constraints.

`tests/test_raster_trace.py` checks physical size, holes, transparency, white
background inclusion, palette limits, small-region omission, geometry limits,
real preview workers, cancellation, settings invalidation, application/Undo and
nine-format export. Tracing samples at most 256 pixels on the longest side;
outlines follow pixel boundaries. Omitted regions become empty space. This is
editable color-region tracing, not optimized automatic stitch-type selection.

Run from the repository in the `morale` environment:

```sh
python -m pytest -q
python -m morale.compatibility --output docs/compatibility-report.json
```

`tests/test_formats.py` checks all 81 ordered writer conversion pairs for retained
sewn bounds within 0.15 mm and four thread groups using the wildflower fixture.
Separate tests cover explicit stops, trims, repeated-color boundaries, PES versions
and RGB fidelity, coordinate transforms, fixed header fields, and hand-encoded
DST records. These scopes are deliberately stated: bounds/block counts alone do
not establish arbitrary stitch-by-stitch fidelity. Format writers can normalize
travel and trims; format-specific tests must grow with each discovered behavior.

The generated [compatibility report](compatibility-report.json) records package
version, measured counts/bounds/colors, conversion results, and unverified readers.
It is evidence for its synthetic fixture only. Its `physical_machine_tested` and
`external_fixture_tested` flags remain false.

`tests/test_digitizing.py` additionally covers variable-width and tapered satin,
split limits, invalid rails, triple retracing, finishing controls without sewn
travel bridges, exact-interval connector checks (including a narrow notch), and a
satin/triple/connected-fill sampler exported and read back in all nine formats.
Native tests exercise mouse-driven rail creation, point-edit validation and undo,
and stitch-setting controls. These are geometric/software tests, not sew-outs.

`tests/test_compensation.py` checks directional fill expansion at multiple angles,
unchanged source outlines and underlay, reduced holes without sewn connectors
crossing their remaining gaps, merging overlapping expanded spans, satin width
and split limits, retained tapered tips, compensated hoop overflow, unit editing,
Undo/project persistence and nine-format export bounds. The amount is millimeters
per side, default zero. This implements geometric overstitching in the sense
described by [Hatch's pull-compensation documentation](https://hatch.embroideryhelp.net/v4/en/OnlineHelp/Hints/hints_digitize/Pull_compensation.htm),
not tested fabric presets or a claim of matching another digitizer's output.
Physical fabric/thread/stabilizer calibration and corner-overlap optimization
remain open. Compensated row endpoints outside the source shape use jumps.

`tests/test_underlay.py` checks legacy default sequences, edge inset bounds and
setback around holes, perpendicular sparse fill/spacing, narrow-region omission,
satin zigzag bounds/length limits and center fallback, separation from pull
compensation, validation, native property units/Undo, persistence, and nine-format
exports. Inset edge runs retain the offset polygon vertices to avoid resampling
across rounded corners toward holes. Small resulting edge stitches, fabric-specific
recipes, and physical sew-out performance still require quality work and testing.

`tests/test_contour_fill.py` checks closed inward layers and spacing, rotation,
holes/disjoint components without source sewn bridges, command limits, native
controls/Undo/persistence, and nine-format export bounds. Offsets are calculated
from the original normalized geometry to avoid accumulating layer-by-layer error.
Each loop starts with a jump; format-specific jump normalization still applies.
Small features can disappear under insetting. Seam placement, continuous routing,
additional decorative fill types and physical sew-out quality remain open.

`tests/test_motifs.py` checks physical motif size and repeat spacing, rotations,
closed-guide distribution, short-guide behavior, repeat/command bounds, actual
stitch hit selection, native controls/units/Undo/persistence and nine-format export
bounds. Motifs are rigid and centered on the guide tangent, with explicit jumps;
they can overlap or extend beyond the guide. The guide is dotted when selected
and hidden during normal stitch preview. Curvature deformation,
continuous routing and physical sew-out quality remain open.

`tests/test_custom_motifs.py` checks independent open/closed outline capture,
standalone files and embedded project round trips, validation, atomic save failure,
asymmetric motif reflections, orientation retained through point/Bezier rebasing,
native capture/apply/Undo, saving selected versus captured motifs, and nine-format
decoded sewn-point bounds. Templates contain normalized vector paths, up to 64
paths/2,000 points, and use the guide's thread color. Source artwork remains the
editing surface: edit it and recapture to revise a template. Templates are snapshots,
not live-linked symbols. Multi-color stitch motifs and curvature deformation remain
open.

`tests/test_cleanup.py` checks redundant short-point removal, retained run endpoints,
sharp corners/reversals/controls, bounded geometric error across successive removals,
shortcut length limits, generated-design reduction, finishing ties, unchanged manual
stitches, native units/Undo/persistence, and nine-format export behavior. Cleanup
runs before generated finishing ties. It does not force all stitches above a minimum:
required structural points can remain short. Tracked removed points bound total
shortcut error to 0.01 mm, with a 64-point cap before retaining another point.

`tests/test_simulation.py` checks indexed event timing/positions, playback prefixes,
non-motion commands, thread identity and forced repeated-color runs, empty-block
exclusion, bounded previous/next control navigation, rendered markers, isolated
thread-run rendering, playback/reset behavior and unchanged project/history.
Overlays show Morale's command stream; machine writers can normalize commands.
Timing is command-based and is not a machine-duration estimate.

`tests/test_comparison.py` checks source/decoded counts, bounds and lengths,
explicit coordinate displacement without registration, unavailable pointwise
distance for mismatched command sequences, separate sewn/travel paths, independent
rendered overlays, nine-format decoded comparisons and native open/cancel without
changing the project or files. The dialog compares decoder output, not physical
machine execution. Matching counts, bounds or RGB order alone never establish
equivalent sewing; colors and controls can be normalized by each format.

`tests/test_stitch_edit.py` covers command editing, insertion/deletion, non-motion
command positions, project round trips, invalid coordinates, a 100,001-row virtual
table, cancellation and decimal input through a real native delegate. Application
tests verify converting a generated object into edited manual stitches and undoing
back to its source geometry without changing the project on invalid edits.

`tests/test_measurements.py` checks unit switches without geometry/history changes,
inch edits converted to millimeters, lower-bound rounding, custom-field persistence
and undo, unchanged-dialog precision, invalid fields, and native mouse measurement.

`tests/test_templates.py` checks A4/Letter tile coverage, exact 10 mm overlap,
shared registration marks, inclusion of compensated stitches beyond the hoop,
hidden-object exclusion, atomic PDF publication, project preservation and native
export/cancel. Linux Poppler checks verify PDF page dimensions/counts and measure
a rendered 20 × 10 mm outline and 50 mm calibration ruler at 254 dpi. Those
external PDF inspection checks skip where Poppler is unavailable; platform-neutral
layout/export tests still run. Physical printers remain untested. The template
does not perform multi-hoop stitch splitting. PDF writing uses
[Qt QPdfWriter](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPdfWriter.html).

`tests/test_threads.py` verifies sewn/travel lengths across command boundaries,
thread metadata through project/pattern/PES round trips, same-RGB/different-catalog
sequencing, CSV metadata and formula escaping. Native tests check metadata edits
and undo after recoloring. Path length is not a calibrated consumption estimate.

`tests/test_catalogs.py` checks bundled fixed-palette metadata, nearest RGB matches
and stable ties, CSV leading-zero codes/Unicode/quoted fields/deduplication, reuse
of exported Morale thread charts, malformed input, a virtual 10,000-row table,
search-limited matching, custom-catalog switching, per-object application, metadata
independence, persistence, Undo, rejection and cancellation. Catalogs are files;
the current window remembers its last choice. Built-ins come from pyembroidery's
PEC/JEF format tables and are not asserted to be current manufacturer inventories.
RGB distance is not perceptual or physical thread-color calibration.

`tests/test_lettering.py` covers compound fill/connector behavior around holes,
nested islands and separate components, matching canvas hole rendering, text
editing and saved-contour fidelity, invalid input, a native dialog and export
through all nine writers. A native application test checks text replacement and
undo. These establish system-font outline digitizing, not specialty embroidery
font quality or physical legibility at small sizes.

The lettering tests also cover positive/negative/zero curvature, editable layout
persistence, monogram proportions and spacing, invalid initials, native controls,
resized text parameters, and curved/monogram exports in all nine formats. Arc
layout bends outlines; it is not arbitrary-path placement of rigid glyphs.

`tests/test_reference.py` covers embedding independent of the source file, unchanged
machine commands, reference edit/undo, atomic rejection of damaged images, raster
readers, pixel/metadata limits, dialog precision, and history count/memory bounds.
References are tracing guides, not automatically digitized objects.

`tests/test_svg_import.py` checks physical units and viewBox sizing, nested
transforms, color/order/spacing, nonzero versus even-odd holes, local references,
hidden elements, cubic/quadratic/arc strokes, small closed cubic loops, editable
project round trips, merge/Undo and failed-import atomicity, and nine-format hole
exports. Parsing uses [svgelements](https://github.com/meerk40t/svgelements), with
strict parser errors and explicit rejection of unsupported effects and external
references. Strokes become running centerlines with a notice; filled curves are
persisted as compound polygon contours. Partial transparency becomes opaque
thread color with a notice. This is not complete SVG rendering or optimized
automatic embroidery digitizing. SVG parsing/generation is still synchronous.

`tests/test_arrange.py` checks world-coordinate mirrors at several rotations,
reversibility, project persistence, imported command preservation, rotated bounds
alignment, and rebasing after reflection. Native tests cover Undo and point edits
following a mirror. `tests/test_selection.py` extends coverage to native modifier
selection/drag, sequence-list selection, multi-object clipboard/duplicate/delete,
persistent groups and member selection, independent copied groups, center
distribution, collective alignment/mirroring, sequence order, palette recoloring,
and movement-limit clamping that preserves relative positions.

`tests/test_transform.py` checks uniform and nonuniform selection scale/rotation
against explicit point transforms, mirrored and rotated objects, shared-center
placement, Bezier controls, satin rails, compound holes, manual command retention,
fill direction, identity operations and invalid parameters. Nine-format round
trips check sewn bounds within 0.15 mm. Native selection tests verify linked and
independent physical dimensions, lettering-to-outline conversion, Undo and atomic
rejection of transforms exceeding limits. Unequal scaling preserves the current
primitive outline vertices and converts primitives to polygons; Bezier curves
retain their controls. Text settings are removed on nonuniform lettering scaling.

`tests/test_canvas_tools.py` checks enclosed/additive marquee selection, hidden
object exclusion, Escape cancellation, snapped creation and collective dragging,
unsnapped measurement, quarter-inch defaults and physical custom-grid persistence
across display-unit changes. Snapping to objects and guides remains open.

`tests/test_geometry.py` checks closed-outline union/subtraction/intersection,
holes without sewn bridges, separate components and nested islands, reflected and
rotated source geometry, settings retention, project persistence, native sequence
replacement and Undo, and atomic rejection of empty results. Nine writer round
trips preserve a test hole's exclusion of sewn points. Operations use Qt's
[path set operations](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainterPath.html);
results are persisted polygon contours. Source-specific lettering parameters are
removed after combining outlines.

`tests/test_contours.py` checks hole movement, transformed contour rebasing,
unchanged-coordinate precision, malformed input, native contour switching with
correctable errors, add/remove/cancel, project persistence, atomic application,
and Undo. The contour editor includes a live outline preview and selected-point
marker.

`tests/test_canvas_nodes.py` checks native mouse dragging of polygon, running-path,
satin and compound nodes; transformed geometry, independent hole nodes, grid
snapping, one-step Undo, click/Escape/mode-switch cancellation, playback and
multi-selection exclusion, and atomic rejection of crossed satin rails. Node
movement is available on the main canvas; insertion/deletion use numeric editors.
Canvas keyboard node movement remains open.

`tests/test_bezier.py` checks adaptive cubic subdivision against an analytic curve,
collinear reversal handling, open/closed conversion, persisted handles, malformed
controls, curved fill boundaries, numeric precision, native handle and anchor
dragging, enable/Undo behavior, conversion to compound/manual geometry, and nine
machine exports. Bezier controls remain editable after project save/reopen;
Boolean and manual-stitch conversions retain their resulting geometry instead.
Handles are independent; smooth/symmetric constraints and direct curve drawing
gestures remain open. Initial paths/polygons are converted through Enable Bezier
handles without changing their straight geometry.

`tests/test_clipboard.py` covers editable geometry/settings preservation, fresh
IDs, malformed payloads, copy/cut/paste and Undo, transfer between native windows,
native text-field behavior, and atomic rejection of project-limit violations.

`tests/test_applique.py` checks stage order, two operator pauses, a hollow cover
band, visibility and metadata, inappropriate source rejection, saved/CSV stage
instructions, and pause preservation through all nine writers. A DST regression
checks that the header's color-change count includes encoded operator pauses.
Native tests cover replacing a selected shape with stages and Undo.

`tests/test_batch.py` runs real conversion subprocesses and deliberately stalled
workers. It checks mixed success/failure queues, cancellation, timeout termination,
dialog closure during work, existing/colliding destinations, publication races,
failure cleanup, and exclusive-rename fallback when hard links are unavailable.
Linux fallback execution is tested here. Windows/macOS APIs and actual USB media
still require platform tests. Batch isolation is not a security sandbox.

`tests/test_library.py` checks real project and nine-format preview subprocesses,
unchanged originals, temporary-output cleanup, corrupt input, stalled-worker timeout,
selection replacement/cancellation, filename filtering, changed-file rejection,
browser closure with a running process, and unsaved-change protection when opening.
Only the selected file is decoded; folders are explored on demand. This is a
folder browser with previews, not an indexed library or thumbnail grid. Opening
the selected file still uses the ordinary synchronous loading path. Preview
subprocess isolation is not a security sandbox.

Publication API references: [Linux exclusive rename](https://man7.org/linux/man-pages/man2/renameat2.2.html),
[Python Windows rename behavior](https://docs.python.org/3/library/os.html#os.rename),
and [Apple exclusive rename support](https://developer.apple.com/documentation/foundation/urlresourcevalues/volumesupportsexclusiverenaming).

## Findings carried forward

- DST/TBF writers require 16-byte ASCII names to prevent shifted fixed headers.
  Morale constrains the exported label while keeping the editable project name.
- PES v6 retains RGB colors; v1/PEC/JEF use fixed palettes. DST/EXP/U01 require a
  separate thread chart. RGB equality with a placeholder is not color fidelity.
- An initial needle selection is setup, not a new color block. Imported needle
  numbers are normalized to color blocks with a notice; exports reassign needles.
- VP3's upstream writer ignores STOP. Morale translates it to a same-color
  boundary. Other formats can encode pauses as thread changes, or decode repeated
  colors as STOP. Tests assert preserved operator pauses as well as geometry.
- The installed VP3 writer omits explicit JUMP records. PES/PEC encoding can add
  sewn landing points at jumps. The cleanup export fixture exposes these differences
  between source sewn bounds, travel bounds and decoded sewn bounds; format-specific
  export notes now describe them. These are not evidence of travel-path fidelity
  or validated physical sewing behavior. The comparison dialog exposes these
  source/decoded differences; physical interpretation remains unverified.
- Parsers may accept partial/corrupt streams. File-size and post-parse limits do
  not replace parser isolation/timeouts or external golden-file validation.
- Imported stitch designs are not editable source vectors. Resizing retains
  stitch count and changes density; recovering digitizing intent is separate work.

## Remaining evidence from outside this workstation

Later, collect small, shareable designs exported by other software with known
dimensions, thread order, machine/hoop model, and screenshots or sew-out notes.
Prioritize reader-only formats and proprietary variants. Keep originals unchanged
and record their provenance. Do not assume proprietary editable EMB/ART support:
neither has a reader in the installed library. This missing corpus does not block
work on the outstanding feature areas above.

Next implementation priority: digitizing and sew-out quality, then lettering and
artwork workflows, alongside the remaining native editing and reliability gates.
