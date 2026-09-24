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
| Object editing | Multi-select, clipboard, group, transform, mirror, align/distribute, snap | Multi/marquee selection, flat groups, clipboard, uniform/nonuniform transforms, alignment/distribution and configurable grid snapping tested. Object edge/center snapping during selection dragging is tested; nested groups and user-defined guide snapping remain pending |
| Stitch editing | Select individual stitches, move/insert/delete, change travel/trim/stop commands | Virtual command table, numeric movement, insertion/multi-row deletion, command dropdowns and dialog-local Undo/Redo tested. Main-canvas point picking/dragging, coincident-point cycling, keyboard navigation/nudging, snapping and cancellation tested. Multi-stitch selection, marquee, movement and deletion within one object are tested; cross-object stitch selection remains pending |
| Running stitches | Single/triple runs and controlled corners along open/closed paths | Single/triple running and corner preservation tested |
| Satin | Digitize rails, vary width, handle corners, split excessive spans | Paired-rail drawing, numeric editing, interpolation, local crossing rejection, split length, center underlay tested; acute corner optimization/global overlap checks pending |
| Fill generation | Predictable tatami coverage of concave shapes/holes, variable angles/density | Scanline fill supports compound even-odd contours, holes, nested islands, and disjoint components with interior-tested connectors. Bounded fill-run routing and fill-angle travel search tested; arbitrary entry/exit routing remains pending |
| Sew-out quality | Tie stitches, trims, minimum-length filtering, compensation, underlay, overlaps | Ties/trims, conservative short-stitch cleanup, inset edge/sparse-fill and center/zigzag underlay, and fill/satin compensation tested. Covered-fill removal with allowance and boundary-coincidence regression tested. Fabric presets and physical sew-outs pending |
| Lettering | Editable text, font choice, sizing/spacing, curved layouts, monograms | Straight/arc-bent system-font text and center-enlarged three-letter monograms, editable settings, portable contours and nine-format export tested. Drawn-path shaped-glyph placement now tested; purpose-digitized embroidery fonts pending |
| Artwork | Reference image, SVG import with units/transforms/holes, editable tracing | Embedded raster references, SVG solid-fill/running-outline import, and raster color-region tracing with editable contours and Undo tested. Smooth shared-boundary raster tracing, fitted SVG export, stroke expansion, dashed borders, positive pathLength calibration and paint order tested; clipping, masks and gradient paints remain pending |
| Automatic digitizing | Turn raster/vector artwork into editable objects; expose correction tools | Solid SVG fills generate tatami and SVG strokes generate running outlines. Raster color reduction and smooth shared-boundary tracing preserve holes with cancellable source/vector/stitch previews. Initial physical-width running/satin/fill suggestions with per-region overrides tested; branch splitting, travel reduction and fill-angle search tested. Photographic digitizing and broader automatic routing remain pending |
| Appliqué | Placement, tack-down, cover stitches, operator stops, fabric instructions | Editable placement/tack-down/tatami-cover stages, pauses, instructions, Undo and nine-format pause preservation tested. Automatic satin outer/cutout covers with explicit tatami fallback tested; physical fabric validation pending |
| Decorative stitches | Motifs, programmable fills, contour/ripple/stipple and gradient/radial effects | Contour fill, built-in/custom outline repeats and clipped area motif fills, plus linear tatami spacing gradients tested. Ripple/stipple fills, gradient color blending and radial fills remain pending |
| Thread tools | Thread catalogs, color mapping, palette editing, usage estimates | Metadata, sequencing, charts/path lengths, PEC/JEF fixed palettes, searchable CSV catalogs and RGB-distance matching tested. Oklab screen-color matching and raster palette reduction tested. Verified manufacturer libraries, physical color matching and calibrated consumption estimates pending |
| Simulation | Scrub/play actual commands, travel/trim/stop overlays, per-color inspection | Indexed playback, command overlays/navigation, isolated thread runs and source-versus-decoded file comparison tested. Physical timing simulation and machine-behavior validation pending |
| Measurements | Custom hoops, units, rulers/guides, measurement tools, calibrated printing | Custom fields, mm/in display, rulers, drag measurement and actual-size tiled placement PDFs tested. Printer/physical scale validation, guides and screen calibration pending. Point/stitch dialogs remain explicitly mm |
| Multi-hooping | Split oversized designs into sewable fields with alignment/placement aids | Native worker planning, nonoverlapping sewn cores in overlapping fields, seam splitting, temporary paired alignment crosses, global pauses, ZIP bundles and placement maps tested. Physical alignment/sew-outs, seam reinforcement and nonrectangular hoop planning remain unverified/pending |
| Machine setup | Profiles with supported formats/versions, hoop fields, needle setup | Generic format/hoop controls; no claimed machine profiles yet |
| Design management | Browse library, thumbnails, search, printable catalogs/templates | Native folder tree, filename filtering, cancellable recursive path search, isolated selected-file stitch previews and tiled placement PDFs tested. Visible search-result thumbnails tested; printable catalogs now tested; persistent metadata indexing pending |
| Reliability | Background generation/import, cancellation, autosave/recovery, corrupt input checks | Main-window preview/property-refresh workers with versioned results, cancellation/retry and timeouts; batch, folder, tracing and multi-hoop workers; bounded history and local recovery tested. Pre-commit generation checks, ordinary file decoding and some dialogs/exports remain synchronous and can delay checkpoints |
| Accessibility | Keyboard-complete editing, screen-reader labels, contrast, large-text checks | Native widgets and some labels; full audit pending |
| Distribution | Repeatable platform builds, license bundle, install/uninstall, release checks | Native bundle self-test and report retention wired into manual build matrix; Linux execution checked. Windows/macOS execution, installers, complete license bundle and signing remain pending |

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
nine-format export. The comparison pixel tracer samples at most 256 pixels.
`tests/test_smooth_trace.py` additionally checks fitted curve compactness and
analytic circle error, shared-edge gaps/overlaps, asymmetric source padding,
physical SVG units/reimport, foreground color budgets, transparent speckles,
SVG save/invalidation and all nine export formats. Smooth tracing samples up to
1024 pixels. Omitted regions become empty space. Native fill contours are
flattened from fitted curves; exported SVG retains curves. Automatic stitch-type
selection now covers eligible unbranched columns, with per-region overrides and
reasons. `tests/test_auto_digitize.py` covers rotation/width classification,
curved columns, holes/branches retained as fill, reconstruction, persistence,
nine-format satin export and real image-worker override/application/Undo.
`tests/test_curved_columns.py` additionally covers open 270-degree ribbons,
physical-width selection across rotations, outline reconstruction, rasterized
artwork and nine-format curved satin export. A bounded boundary-chain planner
handles eligible ribbons. `tests/test_closed_bands.py` covers circular/elliptical
bands, winding/order independence, exact seam closure, empty-center sewn-segment
checks, raster-derived rings and nine-format exports. Two-contour bands can use
satin or closed running paths. Per-region seam percentages and marked preview
starts are implemented; tests cover positions around the loop, closure, area,
invalid settings and native preview/persistence. Optional branch partitioning
now creates independently editable columns from suitable single-contour shapes.
`tests/test_branch_regions.py` covers rotated T shapes, a fork, coverage/overlap,
semantic boundaries, native raster preview/application/Undo and nine-format sewn
bounds. General skeleton branching, join treatment, multiple holes and ambiguous
end caps remain open. `tests/test_trace_routing.py` checks optional
travel reduction within thread-color runs, unchanged per-object stitches, overlap
order, semantic boundaries and nine-format exports. The real preview test checks
ordering status and region overrides. Optional direction planning regenerates
open-path/satin alternatives and solves both candidate orders by dynamic
programming. `tests/test_trace_directions.py` checks an exhaustive fixed-order
reference, measured travel, satin coverage, semantic/seam boundaries and
nine-format bounds. Global ordering and automatic closed-seam optimization
remain open. `tests/test_trace_quality.py` checks measured jump/sewn lengths,
short versus zero-length stitches, non-movement commands, size-dependent detail
flags and report ordering. Native worker tests check report identity/order and
invalidation. Thresholds are review aids; local density maps and fabric-aware
assessment remain open. `tests/test_trace_threads.py` covers CSV and fixed-chart
matching, thread metadata persistence, unchanged geometry/stitches, source/match
reporting and nine-format sewn bounds. Native tests cover chart changes and
region-override retention. `tests/test_perceptual_color.py` verifies Oklab primary coordinates, the
published inverse transform across the sRGB gamma knee, metric selection and a
chart case with different Oklab/RGB matches. Native tests cover switching metrics
and retaining region choices. `tests/test_image_profiles.py` checks linear-sRGB
transfer values, alpha/source preservation, profile-aware tracing, untagged/sRGB
identity and Display P3/Adobe RGB PNG round trips. Qt-supported embedded profiles
are converted to sRGB before tracing. Physical thread appearance, HDR and
calibrated display/gamut management remain open. `tests/test_trace_finishing.py`
checks automatic design-end and inter-region tie/trim flags, short-transfer
retention, thread/control boundaries, existing flags, thresholds and nine-format
sewn containment. Native tests check preview application and reporting. Internal
jump trimming is now optional through a persisted object threshold and the
trace finishing controls. `tests/test_internal_trims.py` checks trim placement,
local locks, consecutive jump lengths, disabled/short/terminal travel, native
persistence, invalid values and nine-format sewn-gap containment. Fabric-specific
lock validation and physical machine trim behavior remain open. See
[IMAGE_DIGITIZING.md](IMAGE_DIGITIZING.md).

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
By default only the selected file is decoded; enabling thumbnails also decodes
visible results. Folders are explored on demand. This is a
folder browser with recursive filename search and visible-result thumbnails, without a persistent metadata index. Opening
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

## Generated image conversion benchmark

`python -m morale.image_benchmark --output artifacts/image-benchmark-v1` creates
a review PDF, native/vector/image artifacts and nine-format exports for eight
internal artwork cases. `tests/test_image_benchmark.py` exercises all 72 exports,
report completeness, explicit fidelity metrics, failure reporting and protection
against overwriting an existing review. The gates and limitations are documented
in [IMAGE_DIGITIZING.md](IMAGE_DIGITIZING.md). These results do not close the
remaining parity items or constitute external-format/physical certification.

## JEF trim encoding and decoding

Morale enables the upstream writer’s explicit trim convention: three stationary
jump records. Import recognizes those markers without inferring trims from long
or merely multi-record travel. `tests/test_jef_trims.py` checks raw encoded markers,
trim recovery, long-travel preservation and short stationary-jump runs. The
convention follows the [upstream JEF writer](https://github.com/EmbroidePy/pyembroidery/blob/main/pyembroidery/JefWriter.py);
physical execution still depends on machine support/settings. VP3 explicit-jump
loss remains unresolved and is still reported separately.

## VP3 block-position correction

The VP3 import adapter restores each encoded color-block start before decoding
its stitch deltas, including starts on either axis and returns to the origin.
The upstream reader skips these moves when either coordinate is zero. A bounded
metadata pass validates block positions/lengths and limits color blocks to 500;
upstream thread/stitch decoding is retained without global monkey-patching.
`tests/test_vp3_positions.py` proves the upstream displacement on generated
fixtures, corrects axis/origin/negative starts, retains ordinary starts and rejects
truncated metadata. Layout reference: [upstream VP3 reader](https://github.com/EmbroidePy/pyembroidery/blob/main/pyembroidery/Vp3Reader.py).
This fixes block placement, not the writer’s omission of explicit intra-block jumps.
External VP3 producers and physical sewing remain unverified.

## Binary writer text lengths

PES v6 and VP3 thread text uses UTF-8 byte counts rather than Python character
counts. PES fields are truncated at complete characters within their 255-byte
limit. PEC’s fixed machine label (also embedded in PES) uses an eight-character
ASCII label; the native project and PES v6 extended name retain Unicode within
their own limits. Isolated helper bindings reuse upstream encoding without
modifying installed modules or process-global writer functions.
`tests/test_writer_text.py` checks Unicode metadata/name recovery, over-limit
UTF-8, following-field alignment, PEC/PES v1 readability, unchanged source models
and byte-identical ASCII exports. Physical machine font/display support remains
unverified. Reference: [upstream PES writer](https://github.com/EmbroidePy/pyembroidery/blob/main/pyembroidery/PesWriter.py).

## Retained digitizing reference

The trace workflow can embed its sampled sRGB source at the original physical
page size. Objects/reference apply atomically with Undo; existing references are
preserved unless replacement is explicitly selected. `tests/test_trace_reference.py`
checks physical aspect ratio despite rounded sampling, source immutability,
reopening after the source moves, unchanged machine commands, reference
replacement defaults and atomic rejection of damaged reference data.

## Assisted SVG digitizing

The artwork dialog accepts SVG without raster tracing and exposes the same
stitch/thread/routing/finishing workflow. `tests/test_vector_artwork.py` checks
physical page scaling, transforms, preserved stroke controls, holes, secure
content rejection, explicit raster-tracer bypass, native controls/Undo, reference
retention and all nine machine exports. Optional stroke expansion uses geometric
outlines before transforms; `tests/test_svg_strokes.py` checks physical border
width, caps, joins/miter limits, nonuniform scaling, holes, fill/border order,
native invalidation and nine-format export. Suitable borders enter the existing
satin planner. SVG effects and complete SVG 2 coverage remain open.

## Artwork overlap removal

Optional covered-fill removal subtracts later filled silhouettes before stitch
selection, with a 0–2 mm edge allowance. `tests/test_trace_overlap.py` checks
visible coverage, holes, rotated and disconnected regions, three-layer stacks,
physical allowance, semantics boundaries, expanded SVG borders, native Undo and
nine-format exports. Conversion checks expose removed area/region counts.
Compensation-aware density optimization, fabric presets and physical seams remain
open; this pass operates on artwork geometry.

## Sampled sewn-path fidelity

`tests/test_path_fidelity.py` verifies detection of lost travel and missing sewing,
independence from stitch subdivision, quantization tolerance, negative-coordinate
cell boundaries, explicit budget exhaustion, and native difference markers.
An installed-writer VP3 fixture demonstrates equal sewn-point bounds with a
connecting decoded segment across the intended gap. This exposes an unresolved
compatibility defect; it does not claim VP3 jump encoding is repaired. Sampling
is bidirectional and reports partial checks, but is not an exact geometric proof,
thread-order check, or physical sew-out validation.

## Physical artwork detail filtering

`tests/test_trace_details.py` verifies optional physical-area filtering after
occlusion: disconnected components, net area with holes, nested islands,
order/winding independence, scale sensitivity, protected sewing semantics,
native option invalidation and overlap-remnant worker/Undo behavior. Zero keeps
all details. This complements pixel speckle filtering but does not replace
fabric-aware minimum-feature or density analysis.

## Artwork needle-density review

The conversion worker now produces a physical 1 mm² needle-penetration map and
summary. `tests/test_density_review.py` checks repeated points, control-command
exclusion, negative/boundary coordinates, object identity, generated underlay/ties,
hidden objects, deterministic bounded hotspot reporting, relative map colors and
native preview invalidation. Fabric-calibrated limits remain open. The sewn-length view below complements
penetration counts.

## Sewn-length density

`tests/test_thread_density.py` verifies length conservation for horizontal,
diagonal and arbitrary segments; grid-edge ownership; travel/control exclusion;
satin spans with no interior penetrations; overlapping objects; and honest partial
maps on budget exhaustion. Worker and native invalidation checks cover both map
images. Physical thread take-up, bobbin use and calibrated fabric limits remain
unverified.

## Development-bundle self-test

`python scripts/check_bundle.py --output artifacts/bundle-self-test` runs the
platform's built executable with an isolated new output directory. It requires
both a successful report and a frozen executable. Seventeen checks exercise the
native offscreen window/icon, save/reopen, generation subprocess, smooth raster
and expanded SVG conversion with reference/density assets, insertion Undo, and
all nine exports reopening with sewn commands. `tests/test_self_test.py` exercises
the source subprocess workflow, existing-directory protection and failure logs.

The manually triggered desktop matrix invokes this on its Linux, Windows and
macOS runners and retains logs/reports with bundles even on failure. Local Linux
execution is evidence only for this Linux environment. No Windows/macOS CI run,
installer, signing/notarization, physical sew-out or external fixture result is
implied. Export smoke checks establish decodability, not command/path fidelity.

## Multiple needle positions on the canvas

In Stitch points mode, Ctrl-click toggles individual motion commands, Shift-click
adds an index range excluding trim/stop controls, and Shift+[ / ] extends selection
through adjacent needle positions. Dragging an already selected point or nudging
moves the set by a shared delta, with the active point used for snapping. The
preview shows changed connecting sewn/travel segments. A move commits once and
normalizes following trim/stop positions. Generated objects become manual only
on an actual move; Undo restores the original geometry.

`tests/test_multi_stitch_canvas.py` checks selection, motion/control fidelity,
relative offsets, snapping, cancellation, atomic rejection and generated-object
conversion/Undo. Existing individual-stitch and export regressions still apply.
Selection stays within one object; cross-object stitch editing remains open.
Box selection was added with the checks described below.

## Stitch box selection

Dragging from empty canvas space in Stitch points mode selects enclosed stitch
and jump commands. Ctrl/Shift adds; Alt-drag subtracts and can start over a point.
The box normalizes both drag directions and examines every motion command,
independent of sampled display dots. Escape, tool changes and design refreshes
cancel the active box. Keyboard nudging is suppressed during a box gesture.
`tests/test_multi_stitch_canvas.py` also verifies additive/subtractive selection,
empty boxes, cancellation, unchanged project/history on selection, and moving a
box-selected set with Undo. Object selection remains unchanged.

## Canvas stitch deletion

Ctrl+A selects needle positions when the stitch canvas has focus; text widgets
keep their own Select All behavior. Delete removes selected stitch/jump commands
in one Undo step, retaining and normalizing non-motion controls. Removing the
first entry can synthesize an initial jump at the first remaining motion position,
with an explicit status message. Removing every motion position is rejected; the
separate Delete object action remains available. Generated geometry becomes manual
only on editing, and Undo restores it. Deletion reconnects the remaining path.

`tests/test_delete_needle_positions.py` checks control retention, entry synthesis,
invalid/non-motion selections, source immutability and all-motion rejection.
Canvas integration tests cover keyboard selection/deletion, history, restored
geometry, remaining selection and entry adjustment.

## Recursive library filename search

The library's Search subfolders action scans filenames and relative paths in a
separate cancellable process. Case-insensitive results include native projects
and registered machine extensions without decoding file contents. Selecting one
result invokes the existing isolated preview; refresh and changed-file protection
still apply before opening. Folder changes, close and Folder view cancel search.
Hidden entries and symbolic links are skipped. Searches are capped at 200,000
entries, 5,000 results and the runner's 30-second timeout; result truncation and
unreadable entries are reported. This is a bounded live scan, without a persistent metadata index.
The visible-result thumbnail view is described below.

`tests/test_library_search.py` covers nested paths, case handling, extension-only
search of invalid file contents, hidden/symlink behavior, limits, query validation,
worker cleanup/cancellation and native preview/open. The packaged self-test now
includes recursive library search; the thumbnail check below brings it to fifteen
checks total at that milestone. Persistent metadata indexing remains open; printable catalogs are covered in the later catalog milestone below.

## Visible library thumbnails

Search results now offer a native thumbnail grid. One dedicated preview subprocess
loads visible tiles sequentially; selected-file previews remain independent.
At most 200 visible rows and cached icons are retained per pass. Offscreen items
are not decoded; scrolling schedules new work and cancels a now-offscreen request.
Size/mtime fingerprints detect changed files, and Refresh preview retries a
selected tile. Failed files get an error marker and do not block the next tile.
Turning thumbnails off, changing folders/results, returning to Folder view or
closing cancels work. The cache is memory-only and evicts old icons.

`tests/test_library_thumbnails.py` checks visible-only decoding, scrolling,
selection/open readiness, bad files, toggle/folder/close cancellation, changed
files and cache eviction. The bundle self-test now exercises two visible native
thumbnails, bringing it to fifteen checks at that milestone. Persistent metadata
indexing remains open; printable catalogs are covered below.

## Preview-result validation

The shared library/tracing preview reader validates metadata before emitting it
to desktop consumers: dictionary shape, names, bounded command/color counts,
finite dimensions from 0 to 20,000 mm, file fingerprints and text notes. Metadata is
limited to 64 MB and image files to 8 MB; PNG dimensions must be at most 2048 ×
2048 before pixel decoding. Corrupt images and malformed/deep JSON become normal
preview failures with temporary-output cleanup. Trace-specific extension fields
remain available to their own validators.

`tests/test_preview_output.py` covers valid extended results, missing/invalid
fields, boolean/nonnumeric values, NaN/infinity, oversized files, image bounds,
corruption and failure-signal cleanup. This is process-output validation, not a
security sandbox or a physical-file compatibility guarantee.

## Conversion review PDF

`tests/test_conversion_report.py` verifies visual/measurement pages, long-text
pagination, final-line retention where a PDF text extractor is available, source
snapshot preservation, source-path omission, legacy pixel-mode support, native
save/invalidation and failed-write cleanup with an existing destination intact.
The packaged self-test now generates this PDF, bringing it to sixteen checks.
This supports review before physical testing; it does not establish sewing quality
or replace actual-size placement templates.


## Aligned conversion review panels

The PDF comparison now renders artwork, prepared vectors and generated stitches
in one physical coordinate frame. It includes the original page and every
generated motion point, with padding, so offsets remain visible and out-of-page
stitches are not cropped. Dashed page boundaries and numerical frame bounds
provide scale context. Prepared SVG is rasterized for this overview; separate
SVG export retains its vector geometry.

`tests/test_review_panels.py` checks shared colored bounds, asymmetric padding,
page aspect ratio, out-of-page commands, unchanged snapshots and invalid physical
dimensions. The report remains an overview, not an actual-size template.

## Automatic fill directions

`tests/test_trace_angles.py` verifies reduced measured jump travel, neighbor
transfers, underlay inclusion, preserved holes/metadata/geometry, protected
non-fill/gradient/group cases, empty-sewing rejection, explicit partial budgets,
native option/Undo, and nine-format exported bounds. The optional pass leaves
final angles editable. Fabric-aware direction choice, global joint optimization,
corner density and physical validation remain open.

## Disconnected fill-run routing

`tests/test_fill_routing.py` checks reduced travel for connected and unconnected
island fills, exact undirected sewn-segment retention, command count, fixed entry
and exit, unchanged inputs, small-run reversal, run/control guards, legacy defaults,
boolean validation, finishing presence, native property/Undo, worker persistence
and nine-format exported bounds. The flag stays editable on native fill objects;
conversion to manual stitches clears it. The transformation precedes existing
cleanup/finishing. Global optimality, routing beyond the bounded run count and
physical sewing behavior remain open.


## Integrated routed-fill acceptance

`tests/test_routed_fill_finishing.py` combines rotation, reflection, density
gradients, edge/sparse underlay, short-stitch cleanup, ties, internal trims and
operator stops. It checks every final sewn segment against material boundaries,
control coordinates against the preceding motion, trim-to-jump transitions,
unchanged entry/exit, nonincreasing jump travel and native save/reload fidelity.

The generated image corpus adds a rotated holed fill using angle selection, run
routing and finishing together. That case gates native sewn containment and
exports to all nine writers, bringing the corpus to eight cases/72 exports.
Decoded path differences remain diagnostic and visible; bounds acceptance still
does not prove machine-command fidelity or physical sewing quality.


## Automatic satin appliqué covers

The native appliqué dialog defaults to automatic satin covers. Normalized cover
geometry is split into filled components with their holes; suitable closed bands
use the existing validated rail planner. Unsupported geometry remains tatami,
with a named fallback and reason. Outer and cutout borders can become separate
cover objects while placement/tack-down retain exactly two operator stops.
The previous tatami mode remains available. Project capacity is checked against
the actual number of generated objects before committing.

`tests/test_applique_satin.py` checks band-area coverage, rectangle/ellipse/cutout
cases, fallback geometry, hidden objects, thread metadata, native default/Undo,
object-limit rejection and pause counts in all nine exports. The bundle self-test
now checks automatic satin appliqué and Undo, for seventeen checks total. Physical
seams, fabric handling and machine-specific pause execution remain unverified.

## Whole-set appliqué cover validation

Automatic cover planning now checks the combined painted union and repeated
coverage, both after component separation and after satin planning. Individual
contour parity alone cannot detect duplicated cover objects. Separation must
retain the original band within numerical tolerance; planned geometry uses the
existing 0.02 mm² / 1% coverage tolerance and rejects repeated area above
0.0001 mm². Failed checks retain the original tatami cover with a stated reason.

`tests/test_applique_cover_set.py` covers sharp stars at narrow/wide border widths,
missing cutout borders, duplicate pieces, damaged planned geometry, preserved
fallback geometry and operator stops. These are geometric checks, not physical
corner-density or fabric validation.

## Perceptual raster color reduction

Raster conversion now offers bounded, population-weighted Oklab palette fitting
before tracing, with RGB comparison and independent thread-chart matching. The
native dialog defaults to Oklab; direct API calls retain their RGB default.
Smooth tracing consumes the same quantized labels as connected-patch filtering.
Palette changes invalidate region choices. The conversion review identifies
the method, sample size and iteration count.

`tests/test_raster_palette.py` verifies reduced perceptual error on a grayscale
ramp, exact small palettes, population weighting, deterministic ordering, bounded
fitting with complete color assignment, transparent framing in both trace modes,
invalid settings and worker/native control propagation. The packaged raster
self-test now requires the Oklab result. Physical color matching and photographic
digitizing remain open.

## Conversion stitch settings

Optional native controls now expose fill/satin spacing, stitch length, pull
compensation and underlay before artwork insertion. Settings apply after stitch
selection and before travel planning; the generated preview, density maps and
conversion review use the adjusted result. Disabled controls preserve the
existing generated defaults. Region stitch choices survive these changes.

`tests/test_trace_stitch_settings.py` checks actual stitch-count changes with
retained geometry, independent satin settings, running-path preservation, invalid
settings, worker propagation with angle search, matching density measurements,
native option disabling and insertion Undo. The packaged raster self-test also
requires custom satin spacing and disabled underlay. These controls do not yet
provide tested fabric profiles or physical sew-out validation.

## Conversion workspace layout

Conversion settings now use four native tabs, with persistent progress/action
controls and automatic navigation to Preview on generation. The default window
is 940 × 700. The existing 44 affected conversion tests passed after regrouping;
a populated native preview was inspected at that size, with all three images,
region choices and insertion controls inside the window. Tab navigation retained
the generated project. Screenshots are in `artifacts/conversion-tabs/`. This is
Linux/offscreen layout evidence, not complete platform or accessibility validation.

## Shared physical frame in native conversion previews

Native source/vector/stitch panels now share the physical frame already used
in conversion review PDFs. Rendering occurs in the worker using its generated
blocks; the dialog displays the resulting images directly. Original padding,
out-of-page motion and closed-band start markers are retained.
`tests/test_review_panels.py` now checks worker/native off-center alignment, no
UI-thread regeneration, supplied block reuse and marker rendering, in addition
to existing frame/overflow checks. Packaged raster/SVG checks require all three
aligned previews. This is comparison geometry, not physical sew-out evidence.

## Native artwork overlay inspection

“Inspect and overlay” opens the aligned conversion images in a native view with
pan, zoom, fit and source/vector/stitch selection. Layer opacity blends the
selected result over the source without changing the view position or scale.
This magnifies the 640 × 640 preview snapshot; it does not add image detail.
Invalidated or failed conversions clear the available inspection result.
Tests cover rendered blending, retained zoom, fitting, snapshot ownership,
malformed images and native invalidation. The packaged self-test now exercises
the inspector and captures a screenshot, for eighteen checks total.

## Scalable inspection geometry

The inspector now uses worker-prepared SVG layers for vectors and sewn stitches,
with native SVG caching disabled for detail at increased zoom. Prepared curves,
physical placement, jump gaps and closed-band starts are retained. Source images
remain sampled raster data; older results retain image-based inspection. Tests
check SVG curves, high-resolution stitch/gap rendering, matching raster/geometry
frames, uncached native items, opacity and layer switching. The eighteen-check
packaged self-test now requires scalable geometry in the inspector.

## Combined perceptual palette and stitch-settings benchmark

The generated image corpus now has nine cases and 81 artwork exports. The new
case reduces six grayscale regions to three editable fills using Oklab, applies
0.65 mm fill spacing, 3.5 mm stitch length, 0.15 mm pull compensation and disabled
underlay, then runs travel routing and finishing. Gates inspect actual resulting
object settings, palette reduction, geometry and all nine exported bounds.

`artifacts/image-benchmark-perceptual-settings/` contains the nine-page review,
native projects and detailed comparisons; its report is recorded in
`docs/image-benchmark-report.json`. The new case passes all nine bounds checks,
with zero identical command sequences and a sampled sewn-path difference in VP3.
These fidelity differences remain visible rather than being treated as bounds
failures or silently ignored. The packaged worker produced the same 1,083
commands as the source case; evidence is in `artifacts/packaged-perceptual-settings/`.
No external-machine corpus or physical sew-out was added.

## Object edge and center snapping

View → Snap to object edges and centers enables selection-drag alignment within
eight screen pixels. The moving selection uses combined outline bounds, so
relative object positions are retained. Visible stationary objects supply edge
and center targets; hidden or inspection-filtered objects are excluded. On a
matched axis, object alignment takes priority over grid snapping. Dashed blue
guides show the target coordinates. Bounds are cached within a drag and cleared
on design refresh/new press. Drawing/node/stitch snapping continues to use the
existing grid behavior; user-defined guides and geometry-node magnets remain open.

`tests/test_object_snapping.py` covers grouped edge alignment, zero-width paths,
center matching, threshold misses, native drag with grid priority, Undo, hidden
objects, inspection filtering, zoom-dependent tolerance and Escape cancellation.

The packaged Linux check now exercises snapped group alignment and Undo, bringing
the bundle test to nineteen checks. Its report and guide screenshot are in
`artifacts/bundle-self-test-object-snapping/`.

## Snapping transformed stitch designs

Manual stitch objects now snap using transformed needle-motion bounds rather
than the corners of their rotated rectangular selection box. Trim/stop coordinates
do not add bounds. Editable shapes continue to use artwork outline bounds.
Regression checks include a diagonal manual design rotated 45° (zero-width
needle bounds instead of a 28 mm selection envelope), reflected/rotated polygon
bounds, control exclusion and refresh of cached bounds after rotation. The
packaged snapping check now also exercises the rotated manual design.

## Portable conversion presets

The native conversion dialog can save/load reusable tracing, palette, stitch
and travel settings. Per-artwork size, reference handling, external chart paths
and region decisions are excluded. Load validates the complete versioned preset
before changing controls, updates dependent controls, clears geometry decisions
and invalidates previews. Save uses atomic replacement.
`tests/test_trace_presets.py` covers portability, actual native worker options,
SVG mode preservation, malformed/range/type inputs, file-size limits, failed
atomic publication and dependent-control states. The packaged self-test now
round-trips a preset and captures the dialog, bringing it to twenty checks.
These are user-authored settings, not validated fabric presets.

## Border-connected white background removal

Raster conversion can preserve enclosed white details while removing near-white
connected to the page edge through white/transparency. The original sampled
reference is retained; interior white enters normal palette reduction and tracing.
The option is exposed in the native dialog, quality report and portable preset,
with backward-compatible defaults for existing presets. Four-neighbor topology
is evaluated at the sampled resolution, not the original full-resolution image.

`tests/test_background_removal.py` covers enclosed white, transparent channels,
diagonal contact, both tracing modes, source preservation, worker/native options
and legacy presets. The packaged raster fixture now includes an enclosed white
detail and requires both its retention and removal of the surrounding background.

## Light-thread inspection contrast

White and other light thread colors now receive a preview-only gray outline,
retaining the original color in the core. Shared-frame panels, scalable stitch
SVGs, thumbnails and benchmark/PDF stitch renderings use the same policy.
`tests/test_light_thread_preview.py` checks light-color selection, white cores,
visible raster/vector geometry, blank jump gaps and unchanged input commands.
The packaged raster check requires contrast for its retained white detail.
The outline is a display aid, not an additional stitch or thread-width estimate.

## Band seam control eligibility

Closed-band metadata now requires strict contour nesting rather than merely two
contours. Separate islands no longer show irrelevant seam controls; touching,
overlapping and duplicate contours are also excluded. The native seam control
is disabled for explicit fill and fixed outlines, and retained for retries of
automatic band planning. Tests cover contour order/winding, nesting edge cases,
unchanged island fills, and worker/native control states.

The interrupted band-control build was revalidated on 2026-09-12: all 100
affected tests and twenty packaged Linux checks passed. Separate packaged-worker
fixtures confirmed that disjoint islands retain fill without band metadata,
while a nested band becomes satin with band metadata. Evidence is in
`artifacts/packaged-band-controls/` and
`artifacts/bundle-self-test-band-controls-resumed/`.

## Long sewn-span diagnostics

Conversion review now measures maximum sewn length per region and globally,
counts spans above 6 mm, and provides bounded command/coordinate locations.
Stationary controls and travel are excluded; previous needle position carries
across object blocks. The 6 mm threshold is labeled as a review aid.
`tests/test_long_stitch_review.py` checks threshold boundaries, non-motion
controls, jump exclusion, location limits with complete totals, empty designs,
block transitions and older report compatibility. The packaged raster/SVG
checks require the new measurements in their result metadata.

## Long-span inspection overlay

The conversion worker supplies an optional transparent SVG overlay of every
sewn span above the shared review threshold. The native inspector exposes it
as an orange highlight on the stitch layer. Jumps and stationary controls are
excluded, and the overlay is independent of the twenty-location text cap.
Tests compare full highlight counts with diagnostics, inspect rendered pixels,
check threshold/control exclusions and verify layer/view state and legacy
snapshots. The packaged self-test now exercises a long-span inspector, bringing
it to twenty-one checks.

## Split long sewn spans in the native stitch editor

The stitch editor can subdivide all sewn spans or only selected commands to a
chosen 0.5–12 mm maximum. It inserts collinear needle positions and retains
original endpoints, jumps, trims and stops. The complete change is preflighted
against the 250,000-command cap before mutation and recorded as one local
Undo/Redo action. Applying retains the existing conversion-to-manual behavior
and main-window Undo. This adds penetrations; it is not automatic sew-out repair.
Tests check path length/endpoints, travel/control preservation, selected scope,
no-ops, atomic capacity/type rejection, native control use, save/reload and both
Undo levels. The packaged self-test now exercises splitting and Undo, for
twenty-two checks.

## Exported first sewn spans

Testing split stitches exposed an encoder default in EXP, JEF, PEC and PES: it
jumped to the first stitch endpoint after explicit travel, removing the preceding
short sewn span from decoded geometry. Export now explicitly disables that
full-jump policy. Native travel already supplies the sewing start. Regression
checks verify exact nonzero sewn segments at design start and after trim, stop
and thread changes in those formats. Text-adapter byte comparisons use identical
encoder settings on both sides.

The splitting tests additionally round-trip a continuous 20 mm run through all
nine writers, checking retained length, endpoint and bounded sewn spans. The
packaged splitting check repeats that export case. This does not resolve VP3's
missing jump records or certify arbitrary oversized spans or physical sew-outs.

The full conversion matrix also exposed PEC's synthetic needle point before
a diagonal stitch after travel. The isolated PEC adapter (also used by PES)
omits that added point while retaining upstream binary command encoding and
color-change behavior. Tests check both axial and diagonal first spans; all
81 format conversion pairs and text-adapter checks pass with this correction.
The adapted encoder's upstream MIT notice is included in THIRD_PARTY_NOTICES.md.

Cleanup export tests now require original sewn needle bounds for PEC/PES too;
their former exception for synthetic travel-landing needle points was removed.
Updated synthetic format and image reports are recorded in the existing JSON
reports; the current image review is in `artifacts/image-benchmark-sewn-starts/`.

## Oversized sewn spans during export

Export now subdivides sewn spans before displacement encoding, using the chosen
writer's declared maximum stitch length minus one encoder unit for rounding.
Subdivision preserves the original path and endpoints, leaves jumps/control
commands intact, and does not change the native project. The prepared
command count is checked against 250,000 before a destination file is staged;
writer-added control and jump records can increase the final encoded count.
Export notes disclose that additional needle positions can be written.

Testing also exposed VP3's forced first-block origin. The isolated writer adapter
now uses the actual first-block coordinate, just as the upstream writer already
does for subsequent blocks. It does not invent jump records within a block.
`tests/test_export_long_spans.py` checks axis-aligned and diagonal oversized runs
in all nine formats, retained endpoints/lengths, format bounds, source/control
preservation and atomic rejection. The packaged self-test repeats a large
diagonal export in every format, bringing it to twenty-three checks.

VP3 motion coordinates are rounded to the encoder grid, and color-block offsets
use the same integer center written into the design header. This avoids
accumulating independent truncation errors at fractional centers. Regression
checks preserve fractional source positions within 0.051 mm and retain the
existing sampler/image-benchmark bounds tolerance.

Final verification for export subdivision: 1,590 tests and twenty-three packaged
Linux checks passed. The refreshed format report covers 81 conversion pairs
with no bounds/block-count failures, and the nine-case image report passes its
existing gates. Current artifacts are in `artifacts/bundle-self-test-export-spans/`
and `artifacts/image-benchmark-export-spans/`. Intra-block VP3 travel fidelity
and physical-machine validation remain open.

## Export preparation counts

Successful exports now return source/prepared stitch counts, the number of
needle positions added by subdivision, and the maximum prepared span. The
native export message/status and batch report notes display these measurements.
They explicitly distinguish preparation counts from later writer-added stitches
and controls. Tests verify exact counts, unchanged source projects, native
messages and batch reports. The packaged oversized-path checks require
consistent counts for all nine formats.

## Multi-hoop export preparation counts

Placement manifests now retain per-tile export preparation measurements alongside
the existing native stitch count. `placements.csv` lists center coordinates,
native/prepared counts, added needle positions and the machine filename. The
coordinate pages of the placement PDF show both counts; notes distinguish them
from further writer-added commands. Native-only bundles leave export columns
blank. Registration stitches are included in native counts.
Tests cover registration on/off, actual native-tile counts, JSON/CSV/ZIP contents,
PDF text and native-only output. The packaged self-test now runs the multi-hoop
worker and verifies its counts, bringing it to twenty-four checks.


### Drawn-path lettering

Edit → Add lettering along path now uses a selected path/polygon (including
flattened Bezier paths) as an independent saved baseline. Qt shapes the text
before rigid placement of glyph clusters, retaining ligatures and combining
marks. Baseline direction controls orientation. Text is centered by ink width
and rejected if it exceeds the baseline length. Editing keeps baseline world
coordinates through rotation, flips and uniform resizing. The original guide
can be hidden in the same undoable insertion.

`tests/test_path_lettering.py` covers saved/editable baselines, transformed edits,
replacement world-coordinate baselines, shaped horizontal outlines, validation,
native insertion/edit Undo and bounds through all nine writers. These are
synthetic tests; tight bends can overlap letters or separate connected scripts.
Automatic collision adjustment and purpose-digitized embroidery fonts remain open.


### Dashed SVG border expansion

Assisted SVG conversion expands numeric and absolute-length dash patterns into
editable filled contours. Odd patterns repeat in full; signed offsets wrap;
subpaths restart the pattern. All-zero patterns are solid, while zero-length
painted dashes receive explicit round/square caps (Qt's stroker omits these).
Dash expansion uses enlarged geometry to reduce curve flattening errors.

Tests cover analytic dash intervals, gaps in native sewn segments, caps, local
references/inherited styles, nonuniform transforms, curved-outline comparison
with SVG rendering, source/project persistence, worker conversion, and all nine
writers' sewn bounds. They do not establish jump preservation in every writer
or physical sew-out quality. Percentage/font-relative lengths and zero-valued `pathLength`
calibration remain unsupported; ordinary unexpanded dashed imports still reject.

References: [SVG stroke dashing](https://www.w3.org/TR/SVG2/painting.html#StrokeDashing)
and [Qt path stroker](https://doc.qt.io/qt-6/qpainterpathstroker.html).


Positive `pathLength` calibration is now supported for expanded SVG borders.
The converter measures the complete untransformed path, including all subpaths,
then scales dash lengths and offsets by measured/authored length. Width and caps
remain unchanged; dash patterns still restart on each subpath. Local references
retain their own calibration; group attributes are not inherited. Tests include
analytic lines and a cubic with known length, nonuniform transforms, dots,
multiple subpaths, inherited-attribute exclusion, local references, workers and
nine-writer bounds. The packaged dashed-border fixture now exercises calibration.
Zero `pathLength` remains explicitly unsupported, rather than passing infinite
lengths into Qt. Reference: [SVG distance calibration](https://www.w3.org/TR/SVG2/paths.html#PathLengthAttribute).


### SVG paint order

Direct SVG import and assisted conversion preserve `paint-order`, including
inherited group styles, local overrides and shorthand with omitted components.
Expanded strokes and normal running centerlines are placed before/after their
own fill as specified, while preserving order relative to neighboring shapes.
The normalized preview explicitly separates stroke-first shapes into layers.
Covered-fill removal therefore cuts the intended lower color.

`tests/test_svg_paint_order.py` covers preview pixels, source/project persistence,
geometry and thread sequence, overrides, overlap removal, invalid values, worker
conversion, and layer widths/order after all nine writers. Formats without stored
thread colors are verified geometrically rather than by RGB. The packaged native
check additionally verifies conversion insertion and Undo. Marker shapes remain
unsupported. Reference: [SVG paint-order](https://www.w3.org/TR/SVG2/painting.html#PaintOrder).


### First physical test targets

The user has Brother and Bernina machines available. Prioritize these for the
first sew-out pack; exact models, supported transfer methods and hoop dimensions
are not yet supplied. Brand availability is not machine-format certification.
Do not assume a model, assign a hoop, or mark hardware validation complete.


### Regression checkpoint after SVG and overlap work

Full offscreen Linux suite: **1,713 passed in 110.16 seconds**, using
`QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/morale-cache python -m pytest -q`
in the morale environment. This includes recent SVG dash/calibration/paint-order,
color-placement benchmark and coincident-hole overlap regressions.

The current ten-case image report also has complete bidirectional sampled sewn-path
comparisons for all twenty PES/EXP exports, with no samples outside 0.15 mm at
0.25 mm spacing. This is sampled synthetic geometry evidence, not exact command
identity, machine-profile certification or physical sew-out validation. Brother
and Bernina model-specific validation remains pending.


### Strict image-export gate

The current image benchmark is **not passing overall**: all ten artwork cases
and all ninety bounds comparisons pass, but six VP3 cases fail sampled sewn-path
fidelity. Eighty-four of ninety sampled path checks pass. The report and CLI now
require complete, nonempty bidirectional comparisons with no out-of-tolerance
samples for an overall pass. The known VP3 limitation remains a failure rather
than an exception. `tests/test_image_benchmark.py` verifies both missing/partial
comparison rejection and the current failure inventory. Earlier all-pass image
reports used a bounds-only export gate and do not prove sewn-path fidelity.


### Printable design catalogs

The native library can select 1–100 files, prepare isolated preview snapshots
sequentially with cancellation/timeouts, and save a six-entry-per-page A4 PDF.
Entries include filename/folder, thumbnail, command dimensions, stitch count and
RGB-color count; failed files remain listed. Previews are not actual-size sewing
templates. Files changed during decoding are rejected. PDFs use atomic replacement,
and cancellation ignores late worker results. Tests cover real worker responsiveness,
failed-file continuation, native action wiring, pagination/text extraction, and
preserving an existing destination after output failure. The packaged self-test
prepares three previews and writes a catalog. Large library indexing and full
printer/Windows/macOS validation remain pending.


Catalog lifecycle checks additionally verify closing the native window during
preview preparation, ignoring a late successful result after close, and replacing
a changed-file preview with an explicit failure entry. Changed-file failures
remain printable rather than silently using stale thumbnails. All fourteen
catalog tests pass in the Linux offscreen environment.


### Regression checkpoint after catalog and hole filtering

Full Linux offscreen suite: **1,759 passed in 107.33 seconds**, using the morale
Python environment with `QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/morale-cache
python -m pytest -q`. This includes routing result/fallback reporting, small-hole
filling with occupied-region protection, and catalog preparation, indexing of
printed filenames, cancellation and source-destination guards. The catalog index
is a PDF file listing, not a persistent searchable metadata database.

Passing the regression suite does not mean the strict image-export benchmark
passes: six known VP3 cases still fail its sampled path-fidelity gate. Physical
Brother/Bernina tests and Windows/macOS execution remain pending.


### Enclosed-white benchmark extension

The current image corpus has eleven cases and 99 exports. All artwork and bounds
checks pass; 92 sampled path checks pass and seven VP3 checks fail. The added case
verifies interior white color geometry through tracing and planned fills while
removing page-edge white. This supersedes earlier ten-case counts, without changing
the strict overall failure status or claiming physical white-thread coverage.


### INF and EDR thread palettes

Both native thread-catalog selection and conversion matching now accept INF/EDR
files in addition to CSV. Bounded parsing rejects truncated records, inconsistent
INF byte lengths/counts, invalid UTF-8 and excessive metadata. INF descriptions
and chart fields are preserved; EDR supplies RGB only. Order and duplicate colors
are retained. Tests include independently assembled Unicode records, malformed
files, matching without source mutation and the installed writer's ASCII output.
The packaged conversion worker exercises EDR matching. Automatic association
with stitch files, companion export and model-specific Bernina/Brother validation
remain pending; this does not claim machine-profile support.

The thread catalog also exports its filtered, displayed palette to INF or EDR.
Export preserves order and duplicate colors, writes INF string lengths in UTF-8
bytes, and replaces the destination atomically. INF retains descriptions/chart
names; EDR contains RGB only. The native dialog explains omitted metadata and
disables catalog export while showing proposed matches. This is catalog export;
exporting a design's sewing-order companion palette remains pending. Regression
checks reopen Unicode INF output through the installed pyembroidery reader.

### Conversion underlay controls

Image/SVG conversion exposes the engine's fill edge/sparse combinations and satin
center/zigzag combinations, with separate type overrides, inset and spacing.
Tests exercise mixed stitch types, preserved artwork/source identity, regenerated
support paths, native worker output and Undo, invalid values, preset round trips
and older preset defaults. Physical support effectiveness remains unvalidated.
