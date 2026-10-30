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
| Native desktop | Launch and complete create/save/reopen/export on Windows, Linux, macOS | Native test suite and packaged bundle self-test run in CI on Linux, Windows and macOS; v0.3.0 release bundles built on all three. Hands-on use on Windows/macOS desktops remains unreported |
| File compatibility | Open, combine, transform, save, reopen, convert machine designs | 40 registered readers; 9 writers and 81 conversion pairs checked synthetically; one workspace PES probed read-only through 81 conversion chains, with unknown provenance and no physical validation; broader external corpus pending |
| Project fidelity | Preserve geometry, settings, stitch commands, thread order, and undo history semantics | Schema v3 groups object settings and retains imported stitches; v1/v2 loading supported; undo/save/reopen tests |
| Batch workflows | Convert many files with per-file results, cancellation, and no source overwrites | Native queue and CLI; process isolation, timeouts, reports, collision/race protection and cancellation tested. Windows/macOS and actual removable-drive execution pending |
| Manual digitizing | Draw/edit open and closed Bezier paths, holes, nodes, entry/exit points | Open/closed Bezier editing, smooth/symmetric handle dragging, compound editing and outline Boolean operations available. Running/triple start-anchor and direction controls, satin station reversal and contour sewing order tested. Persistent per-node constraints, arbitrary curve-segment starts and fill entry/exit routing pending |
| Object editing | Multi-select, clipboard, group, transform, mirror, align/distribute, snap | Multi/marquee selection, flat groups, clipboard, uniform/nonuniform transforms, alignment/distribution and configurable grid snapping tested. Object edge/center snapping during selection dragging is tested; persistent layout guides, ruler dragging and selection edge/center guide snapping are tested; nested groups remain pending |
| Stitch editing | Select individual stitches, move/insert/delete, change travel/trim/stop commands | Virtual command table, numeric movement, insertion/multi-row deletion, command dropdowns and dialog-local Undo/Redo tested. Main-canvas point picking/dragging, coincident-point cycling, keyboard navigation/nudging, snapping and cancellation tested. Multi-stitch selection, marquee, movement and deletion within one object are tested; cross-object stitch selection remains pending |
| Running stitches | Single/triple runs and controlled corners along open/closed paths | Single/triple running and corner preservation tested |
| Satin | Digitize rails, vary width, handle corners, split excessive spans | Paired-rail drawing, numeric editing, interpolation, local crossing and nonadjacent overlap rejection on source and compensated sampled rails, split length, center underlay tested. Corners tighter than the column width are reconstructed as fans around the inner corner (rail loops clipped, crossing rungs pivoted, including after compensation) with alternating short stitches; swapped rails and long overlaps are still rejected. Underlay passes are planned to start and end at the column start. Physical validation of corner fans pending |
| Fill generation | Predictable tatami coverage of concave shapes/holes, variable angles/density | Scanline fill supports compound even-odd contours, holes, nested islands, and disjoint components with interior-tested connectors. Bounded fill-run routing and fill-angle travel search tested; arbitrary entry/exit routing remains pending |
| Sew-out quality | Tie stitches, trims, minimum-length filtering, compensation, underlay, overlaps | Ties/trims, conservative short-stitch cleanup, inset edge/sparse-fill and center/zigzag underlay, and fill/satin compensation tested. Covered-fill removal with allowance and boundary-coincidence regression tested. Editable fabric starting points, portable custom presets and selection application with Undo/Redo tested; three profiles checked across nine writers. Physical calibration and sew-outs pending |
| Lettering | Editable text, font choice, sizing/spacing, curved layouts, monograms | Straight/arc-bent system-font text and center-enlarged three-letter monograms, editable settings, portable contours and nine-format export tested. Drawn-path shaped-glyph placement tested. Automatic satin-column lettering from any system font tested. 122 purpose-digitized embroidery fonts (converted from Ink/Stitch, with kerning and designed size ranges, including XL families) tested; rigid-glyph arc layout for embroidery fonts tested; drawn-path embroidery-font placement tested; sew-out validation pending |
| Artwork | Reference image, SVG import with units/transforms/holes, editable tracing | Embedded raster references, SVG solid-fill/running-outline import, and raster color-region tracing with editable contours and Undo tested. Smooth shared-boundary raster tracing, fitted SVG export, stroke expansion, dashed borders, positive pathLength calibration and paint order tested; user-space and object-bounds fill/stroke clipping and reusable symbols are tested. Native SVG color tracing supports linear/radial gradients, hard stops, inherited colors, physical units, linear-light interpolation, and isolated object/group opacity. Local alpha/luminance masks and nested masks are supported in rendered conversion; broader mask styles/resources, CSS, and radial edge cases remain pending |
| Automatic digitizing | Turn raster/vector artwork into editable objects; expose correction tools | Solid SVG fills generate tatami and SVG strokes generate running outlines. Optional rendered-SVG color tracing passes through the native worker, editable regions, saved presets, and software export checks. Raster color reduction and smooth shared-boundary tracing preserve holes with cancellable source/vector/stitch previews. Initial physical-width running/satin/fill suggestions with per-region overrides tested; crotch-chord branch splitting at oblique angles, travel reduction with bounded adjacent-swap refinement and fill-angle search tested. Candidate columns are checked with requested stitch settings; retained-fill fallbacks are explained in previews and reviews. Photographic digitizing and broader automatic routing remain pending |
| Appliqué | Placement, tack-down, cover stitches, operator stops, fabric instructions | Editable placement/tack-down/tatami-cover stages, pauses, instructions, Undo and nine-format pause preservation tested. Automatic satin outer/cutout covers with explicit tatami fallback tested; physical fabric validation pending |
| Decorative stitches | Motifs, programmable fills, contour/ripple/stipple and gradient/radial effects | Contour fill, built-in/custom outline repeats and clipped area motif fills, plus linear tatami spacing gradients tested. Circular ripple fill with editable center, compound clipping and boundary-aware short-stitch cleanup is tested; stipple fills, gradient color blending and radial fills remain pending |
| Thread tools | Thread catalogs, color mapping, palette editing, usage estimates | Metadata, sequencing, charts/path lengths, PEC/JEF fixed palettes, searchable CSV catalogs and RGB-distance matching tested. Oklab screen-color matching and raster palette reduction tested. Verified manufacturer libraries, physical color matching and calibrated consumption estimates pending |
| Simulation | Scrub/play actual commands, travel/trim/stop overlays, per-color inspection | Indexed playback, command overlays/navigation, isolated thread runs and source-versus-decoded file comparison tested. Physical timing simulation and machine-behavior validation pending |
| Measurements | Custom hoops, units, rulers/guides, measurement tools, calibrated printing | Custom fields, mm/in display, rulers, drag measurement and actual-size tiled placement PDFs tested. Persistent millimeter guides, visibility, snapping and ruler creation with Undo/Redo are tested. Printer/physical scale validation and screen calibration remain pending. Point/stitch dialogs remain explicitly mm |
| Multi-hooping | Split oversized designs into sewable fields with alignment/placement aids | Native worker planning, nonoverlapping sewn cores in overlapping fields, seam splitting, temporary paired alignment crosses, global pauses, ZIP bundles and placement maps tested. Physical alignment/sew-outs, seam reinforcement and nonrectangular hoop planning remain unverified/pending |
| Machine setup | Profiles with supported formats/versions, hoop fields, needle setup | Generic format/hoop controls; no claimed machine profiles yet |
| Design management | Browse library, thumbnails, search, printable catalogs/templates | Native folder tree, filename filtering, cancellable recursive path search, isolated selected-file stitch previews and tiled placement PDFs tested. Visible search-result thumbnails tested; printable catalogs tested. Persistent design notes, worksheet inclusion, library previews and bounded on-demand `notes:` search are tested; persistent metadata indexing remains pending |
| Reliability | Background generation/import, cancellation, autosave/recovery, corrupt input checks | Main-window preview/property-refresh workers with versioned results, cancellation/retry and timeouts; batch, folder, tracing and multi-hoop workers; bounded history and local recovery tested. Pre-commit generation checks, ordinary file decoding and some dialogs/exports remain synchronous and can delay checkpoints |
| Accessibility | Keyboard-complete editing, screen-reader labels, contrast, large-text checks | Automated audit of the main window and 13 dialogs for accessible names and keyboard focus; WCAG AA text contrast and 3:1 control borders; visible focus; text sized from the system font; unique menu accelerators; arrow-key object nudging. Keyboard drawing supports shapes, polygons, paths and paired satin rails with grid snapping and draft cancellation. Screen-reader testing with NVDA/VoiceOver/Orca and a complete keyboard workflow audit remain pending |
| Distribution | Repeatable platform builds, license bundle, install/uninstall, release checks | Native bundle self-test and report retention wired into release builds and regular Python 3.12 CI on all three platforms; v0.3.0 release bundles built and self-tested on Linux, Windows and macOS. Installers, complete license bundle and signing remain pending |

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

Before the VP3 adapter fix, the image benchmark was **not passing overall**: all ten artwork cases
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
disables catalog export while showing proposed matches. This is catalog export.
Machine export of EXP now also writes a sewing-order companion INF built from the
exported thread list, so pauses encoded as duplicate colors stay aligned; tests
compare its color count with the reopened EXP. Machine display of the INF has not
been checked on a Bernina. Regression
checks reopen Unicode INF output through the installed pyembroidery reader.

### Conversion underlay controls

Image/SVG conversion exposes the engine's fill edge/sparse combinations and satin
center/zigzag combinations, with separate type overrides, inset and spacing.
Tests exercise mixed stitch types, preserved artwork/source identity, regenerated
support paths, native worker output and Undo, invalid values, preset round trips
and older preset defaults. Physical support effectiveness remains unvalidated.

### Crotch-chord branch splitting

Branch splitting now also cuts along interior chords between inside corners.
Y, X, five-arm star and K outlines at 0°, 17° and 40° become all-satin pieces
(previously up to nine pieces with 54% satin area), and a leaf with a stem
separates into one satin stem and one fill body without running slivers.
Traced 25 mm raster versions give the same result in 0.3–1.6 s per region. The
shared scanline area measurement now sweeps active edges, reducing the full
Linux offscreen suite from 126 to 92 seconds (1,818 passed). Join overlap, tie
treatment and sew-out validation of bent satins through junctions remain open.

### Branch join overlap

Split branches can now overlap at their joins (0–1 mm; dialog default 0.3 mm,
legacy presets 0). Every join of the Y, X, star and K fixtures at 0°, 17° and 40°
is overlapped, all pieces stay within the source outline and remain satin, and
the added area is bounded by the overlap times the cut length. T-junction partial
contacts are detected, and an overlapped tee exported to DST stays inside its
silhouette. Full Linux offscreen suite: 1,837 passed. Physical join behaviour
under pull and tie treatment at joins remain unvalidated.

### Branch-join sew-out pack

`python -m morale.sewout_pack` creates a single-colour 100 × 100 mm design with
Y (exact, 0.3 mm, 0.6 mm joins), K and star (exact and 0.3 mm), T-junction and
leaf-with-stem cells, exported to PES v6/v1, EXP and DST with a placement PDF,
thread chart and instructions. A retained copy is in `examples/branch-sewout/`.
Tests check that every cell splits, that every join is overlapped whenever overlap is enabled, that the design
fits the field and that all four files reopen with their stitches. Junction wedges
under 4 mm² now merge into a neighbouring satin. This is a test pack, not a sew-out
result: Brother/Bernina runs remain pending.

### Coverage layers and fabric guidance

Conversion previews now measure distinct-object coverage layers from rasterized
sewn footprints and report overlapping object pairs with shared area, shown as a
fixed-scale map in the density review and review PDF. Five fabric profiles apply
starting-point thresholds for stacked layers, sewn-thread density, satin width and
fill area to stored measurements. Tests cover separate, overlapping, three-way and
touching objects, the empty case, guidance findings and a clean single-layer
design, and the worker, dialog and PDF integration. Full Linux offscreen suite:
1,851 passed. The thresholds are uncalibrated until fabric sew-outs exist.

### Whole-palette thread planning and thread grouping

Traced colors can now be matched to a chart as one assignment problem, keeping
clearly different colors on different threads with minimum area-weighted color
distance; nearly identical colors may share. The assignment solver is checked
against brute force, and tests cover collisions, conflict-free equivalence with
nearest matching, area priority, sharing and small-chart fallback. Optional thread
grouping cuts thread changes (for example 5 → 1 for alternating separate regions)
while preserving every overlapping pair's order and all stop/stage/group barriers.
Full Linux offscreen suite: 1,866 passed. Greedy grouping is not guaranteed optimal.

### Satin-column lettering

Lettering can sew as satin columns planned from system-font outlines. Glyph
components are grouped with their holes; non-band holes are opened with two short
interior cuts, then split at crotches with 0.3 mm join overlap. In DejaVu Sans at
15 mm, at least 80% of lowercase pieces are satin (tested), and 'b' is entirely
satin. Plans are stored in the object's normalized frame, validated on load, move
with the object, re-plan on text edits and fall back to fill when lettering becomes
plain outlines. Full Linux offscreen suite: 1,881 passed. Sew-outs of small satin
text remain pending.

### Accessibility audit

`tests/test_accessibility.py` opens the main window and, through their real
commands, the point, stitch, routing, appliqué, transform, thread catalog,
lettering, template, both hoop, batch, library and artwork-conversion dialogs, and
requires every interactive control to have an accessible name (own, label buddy or
form label) and keyboard focus. Stylesheet text meets 4.5:1 contrast and input and
button borders 3:1; focused controls show a 2 px border. Text sizes are points
derived from the system font, so operating-system text scaling applies. Every menu
entry has an accelerator. Arrow keys nudge the selection by 0.1 mm, 1 mm with
Shift, or one grid step, each an Undo step. Drawing new shapes still needs a
pointer; numeric properties and point editors are the keyboard alternative.

### Engineering review: validation before features

Following an engineering review (validate before adding features):

- **Sew-out coupons:** `morale/coupons.py` builds twelve single-variable coupons
  with a 10 mm scale square, machine files, metadata and evaluation templates;
  tests check that each fits the field and keeps clear of the scale square.
  The process is in docs/SEWOUT_VALIDATION.md. No sew-out results exist yet.
- **Revisions:** dirty state, stale previews and discard prompts compare revision
  numbers; one edit serializes the project at most twice (tested). Revisions are
  never reused after undo, and undo back to the saved state reads as saved.
- **Save validation:** `Project.validate()` applies the loader's rules before any
  write; every built-in and example project round-trips byte-for-byte.
- **Design checks:** `morale/design_check.py` returns structured `DesignIssue`
  records; preflight uses it, and Design → Check design shows and navigates them.
Full Linux offscreen suite: 1,937 passed.
- **Export verification:** exports are reopened with the real reader and compared
  (counts, thread changes, bounds within 0.3 mm, sampled path within 0.15 mm).
  PES, DST, EXP, JEF and XXX verify for the wildflower example; VP3 fails, with
  about 270 mm of stitching displaced, so the known VP3 limitation affects
  ordinary designs, not only edge cases.

### VP3 jump fix: strict image-export gate passes

VP3 jumps are now written as long-form moves to their landing (following
Embroidermodder) and read back as jumps; sewn spans are split below 12.7 mm.
The eleven-case image benchmark now passes overall: all 99 exports pass bounds
and sampled sewn-path checks, including the seven VP3 cases that failed before.
The retained report is docs/image-benchmark-report.json. Physical Husqvarna/Pfaff
sew-outs remain the outstanding evidence.

### October 3 regression checkpoint

The full Linux offscreen suite passes: **1,947 tests in 128.53 seconds**.
The rebuilt native Linux bundle passes **33 self-test checks**, recorded in
`artifacts/bundle-self-test-review-pagination-oct03/report.json`. This checkpoint
includes the conversion underlay controls/reports and line-by-line PDF pagination.
It does not establish Windows/macOS execution or physical sew-out quality.
A subsequent October 3 image-benchmark rerun passes all eleven artwork cases
and all 99 bounds/path comparisons with the current VP3 adapter. Evidence is in
`artifacts/image-benchmark-oct03-current/`; earlier VP3 failure counts above
are historical, not current gate results.

### Reopened export control checks

Export verification now rejects incomplete/empty sampled path comparisons and
flags decreased decoded stop/trim counts. A same-thread two-run fixture with one
trim and one stop is exercised through all nine writers. PES, PEC, U01, TBF and
JEF reopen with the explicit stop; VP3, XXX, EXP and DST reopen with an additional
thread change instead. These four cases remain review results, with the possible
pause normalization explained rather than silently treated as equivalent. All
nine retain at least one decoded trim in this fixture. Command location/order
and physical machine pause/cut behavior remain unverified by these count checks.

Batch conversion runs reopened-file verification inside each isolated worker.
Results retain structured verification data and human-readable notes. Native
results distinguish converted files with passed checks, files needing review,
and older unchecked results. A successful conversion is not itself a fidelity
verdict. For automation, opt into a nonzero exit code on review/unchecked results:

```sh
python -m morale.batch input.pes --output converted --format dst --require-verification
```

The strict option retains exported files for inspection; default exit behavior
continues to report conversion success independently of verification. Per-file
JSON output always includes available verification results. Subprocess tests
exercise both exit modes with a real PES-to-DST trim-count difference.

### Regression checkpoint after SVG and export verification

Full Linux offscreen suite: **2,004 passed in 162.54 seconds**. The rebuilt Linux
bundle passes its 33 checks in `artifacts/bundle-self-test-svg-exports/`.
A separate frozen tracing-worker run in `artifacts/packaged-non-scaling-stroke/`
excludes transparent/metadata content, retains a 2 mm non-scaling border under
nonuniform transformation and produces automatic satin. This verifies the
packaged software path, not physical sew-out quality or Windows/macOS execution.

### Minimal control-encoding probe

`artifacts/control-encoding-probe/` retains a native source with two internal
travels, only one of them explicitly trimmed, plus six exported files and their
reopened verification results. PES/PEC and VP3 decode two trims from that one-trim
source; DST, EXP and JEF decode one in this fixture. Inspection of the current
adapters identifies distinct causes: PEC encoding emits trim-jump records for
all noninitial jumps and ignores explicit TRIM; VP3 emits a trim record for END
as well as TRIM. The DST reader's jump-run trim inference is a separate mechanism.
These findings identify encoding work still required; they do not certify how
any machine will cut thread, nor authorize suppressing all reported differences.

PES/PEC control correction: the isolated PEC encoder now writes ordinary jumps
as jump records and explicit trims as stationary trim-jump records. The minimal
mixed-travel probe reopens with exactly its one trim at the original location;
the wildflower PES export now passes the control checks. The current batch
PES-to-DST fixture instead exposes DST-inferred extra trims, replacing the older
three-lost-trims observation above. 115 writer, verification, batch, sewn-start
and long-span tests pass. Physical Brother trim execution remains unverified.

The follow-up PES/PEC boundary checks cover final trims, trims without following
travel, trim-before-pause and pause-before-trim for PES v1/v6 and PEC. They check
combined control order as well as per-type counts/positions. An isolated
normalizer preserves actual trim state across STOP so an explicit following
TRIM survives. All 22 writer-text tests pass. The retained image report now comes
from `artifacts/image-benchmark-pec-controls/`, with eleven artwork cases and
99/99 sampled path checks passing. The updated minimal control probe is in
`artifacts/control-encoding-probe-pec-fixed/`; PES/PEC retain exactly one trim,
while VP3 still reports its additional end trim for review.

### Region controls and packaged regression checkpoint

The Linux offscreen suite ran 2,051 tests: 2,050 passed and one SVG-border
expectation still assumed VP3 had no added controls. That test now requires the
known extra-end-trim review result, with no other verification problems allowed.
The affected SVG-stroke and export-verification modules then passed all 70 tests.
No production verification threshold was relaxed.

The rebuilt Linux desktop bundle passes all 33 self-tests in
`artifacts/bundle-self-test-region-controls/`. A separate frozen tracing-worker
probe in `artifacts/packaged-region-controls/verification.json` confirms that
region spacing (1.2 and 0.4 mm) and a locked 17-degree fill angle survive sewing
order reversal. The unlocked neighbor still participates in automatic angle
selection. The native preview was inspected at
`artifacts/region-angle-preview/preview.png`; both rows and their controls are
visible. Windows/macOS execution and physical machine behavior remain untested
by this checkpoint.

### Branch sew-out pack with export verification and result capture

`artifacts/sewout-results-oct04.zip` contains the native project, PES v6/PES v1,
EXP and DST candidates, actual-size placement PDF, thread chart, README,
generation report and blank per-cell results CSV. All ten archived files were
compared byte-for-byte with the generated folder. The nine-cell design has 2,921
stitches and sewn bounds [-40.00, -40.01, 40.86, 42.15] mm in its 100 mm field.
All four machine exports pass the current reopened-file checks; SHA-256 hashes
in the report identify those exact files. This is software evidence only.

The results sheet leaves machine, material, loading, completion, gap, ridge,
thread-break and photo observations blank. Ten pack tests cover generation,
reopening, reports, hashes, blank observations and a reader failure that retains
the files and allows the other checks to finish. Physical sewing and exact
Brother/Bernina model compatibility remain unverified.

Full calibration-coupon export probe: `artifacts/coupons-verified-oct04/`
contains twelve coupons and 48 machine exports, with hashes checked against
their reports. `verification-summary.json` records 42 passed software checks and
six review results. Five DST coupons (jumps, pull compensation, stitch length,
tiny stitches and underlay) reopen with additional inferred trims. The branch-join
coupon's PES v1 file reopens with one fewer thread change and one additional stop.
These are retained differences, not exemptions from verification. Physical
behavior remains untested; the PES v1 sequence needs further encoder inspection.

Follow-up traced that PES v1 result to the branch coupon's unintended thread
identity change: its scale marker and imported branch objects had identical RGB
but different descriptions. The branch coupon now uses its own thread identity
for both. A regression confirms one native thread run and verified PES v1/v6
exports with no added stop; all sixteen coupon tests pass. The retained full-set
artifact above predates this correction. General same-colour thread-change
representation in PES v1 remains format/reader-dependent and is not exempted
from export verification.

### October 4 integrated checkpoint

The complete Linux offscreen suite passes **2,073 tests in 250.80 seconds** after
the region correction/reset controls, scrollable conversion preview, report
sewing-order mapping, iterable angle-lock fix and verified calibration-pack
changes. The rebuilt Linux desktop passes all **33 frozen self-tests** in
`artifacts/bundle-self-test-oct04/`. These checks do not establish Windows/macOS
execution, external-format fidelity or physical Brother/Bernina behavior, and
the remaining feature-parity requirements above stay open.

### Curved purpose-digitized lettering

The native lettering dialog now offers straight and curved layouts for bundled
embroidery fonts. Each glyph rotates/translates as a unit along the arc; its
satin rails, fill contours and running paths retain their internal dimensions.
Stored planned geometry remains portable through save/reopen. Zero curvature
preserves straight geometry. Monogram and drawn-path options remain unavailable
for these fonts. Curvature may bring neighboring glyphs into overlap, so inspect
spacing; this does not establish sew-out quality. Seventy-seven font, lettering
and accessibility tests pass, including positive/negative arcs and sampled sewn
geometry checks through all nine machine writers. Format-specific additional
trim reports remain visible.

A full-library arc probe is retained at `artifacts/font-arc-audit/report.json`.
At each font's lower supported height, three available glyphs at a 60-degree arc
generated and reopened successfully for 119 of 120 fonts. Califragilistic's `y`
contains 5,529 running pieces and exceeds the existing 2,000-piece lettering
limit in straight and curved layouts. That glyph remains unsupported pending
source/conversion investigation; the editor now identifies the font and character
before attempting layout. This sample is not exhaustive glyph or sew-out testing.

Califragilistic repair: the importer had selected a `GlyphLayer-y` inside an SVG
clip-path definition before reaching the actual glyph. Definition-only layers
are now excluded. Regeneration from upstream embroidery-fonts revision
`c7e3a05c3d6f5c77b881c50f257851af9a8e9cb8` changed only `y` (5,529 pieces to four);
all other glyphs, font metadata and license bytes match the former bundle.
Source hashes and the comparison are retained in
`artifacts/califragilistic-repair/`. The repaired bundled glyph generates and
roundtrips in straight and curved layouts; all 32 embroidery-font tests pass.
The earlier full-library audit is historical and predates this repair.

The repaired-library audit at `artifacts/font-arc-audit-repaired/report.json`
passes all 120 bundled fonts with three available glyphs per font at a 60-degree
arc and each font's lower supported height rounded up to 0.01 mm. Generated
stitches match exactly after project serialization/reopening. Each result
records the tested compressed font's SHA-256 hash. This closes the observed
sample failure, not exhaustive glyph coverage or physical sew-out validation.

The rebuilt Linux bundle passes 34 packaged checks in
`artifacts/bundle-self-test-curved-font/`, including a new bundled-font check:
load repaired Califragilistic `y`, generate curved text, compare generated
stitches after save/reopen, and accept an unchanged native lettering edit
without changing the object. The source self-test's three regression cases also
pass. Other platforms and physical sew-outs remain unverified.

### Embroidery fonts on drawn paths

The lettering dialog now permits selecting a bundled embroidery font for a
drawn baseline. Whole glyphs follow the local path tangent without deforming
their internal pieces. Text wider than the baseline is rejected. The baseline
is stored with the object and remains fixed in world coordinates when editing
rotated or mirrored text. Tight corners can overlap neighboring glyphs and need
visual review. Native selection, serialization and nine-writer sampled geometry
checks pass within 124 font, lettering and path-lettering tests; physical
sew-outs remain pending.

### Repeatable font-layout audit

Run `python -m morale.font_audit --output NEW_DIRECTORY` to test three available
glyphs per bundled font in straight, 60-degree arc and drawn-path layouts at the
lower designed height (rounded up to 0.01 mm). Each case must generate sewing
stitches and reproduce its command blocks exactly after save/reopen. The command
refuses an existing destination, records compressed-font hashes and per-layout
failures, and exits nonzero if any sample fails. It does not test every glyph,
every size, machine export or physical sewing.

The first retained run in `artifacts/font-layout-audit/report.json` passes
**360/360 samples across all 120 fonts**.

The direct-file audit now enumerates bundled data instead of the filtered font
picker. Its run in `artifacts/font-layout-audit-direct/` found **122 font files**:
360/366 layout samples pass. Initials XL and Ondulamarif XL require minimum
heights above the application's 100 mm lettering limit and are hidden by the
picker; all three layouts for each are reported as failures. Thus earlier
120-font results cover selectable fonts, not every bundled file. Empty and
corrupt libraries are also regression-tested to fail rather than be omitted.
The two oversized font families need an explicit support/distribution decision.

### XL embroidery-font sizes

Embroidery-font height now supports the font's metadata range up to the existing
500 mm object-dimension limit. Computer-font lettering retains its 100 mm cap;
finished geometry and command limits still apply. Initials XL and Ondulamarif XL
are selectable, retain their >100 mm size through native editing, and generate
identical commands after save/reopen. The direct-file audit now passes all
**366/366 layout samples for 122 bundled fonts** in
`artifacts/font-layout-audit-xl/report.json`. The 118 font, lettering and save
validation tests pass. These sizes still require a suitable hoop or multi-hooping;
no physical XL sew-out or machine-profile compatibility is established here.

XL export regression: the Initials XL `A` at its minimum designed height is
rejected before file creation in the default 100 mm hoop. In a declared 300 mm
field, all nine writers reopen with complete sampled geometry comparisons and
bounds differences no greater than 0.3 mm. Only additional-trim review messages
are permitted in this fixture. Eleven XL-focused tests pass. A declared field
is not a verified machine/hoop profile, and these checks do not validate sewing.

### Integrated Linux verification after XL lettering and source fingerprints

The complete source suite passes **2,155 tests** (164.42 seconds) with Qt's
offscreen backend. This run includes drawn-path embroidery lettering, XL font
sizes, region corrections, source-content change detection and captured artwork
fingerprints in conversion PDFs. The report fingerprint identifies the artwork
used at conversion time, even if the source file changes before saving the PDF.

A fresh PyInstaller Linux build passes all **34 packaged smoke checks**; evidence
is retained in `artifacts/bundle-self-test-xl-source-digest/report.json`. Direct
inspection also confirms the packaged raster and SVG workers' source digests
match SHA-256 hashes of their input files. The executable is `dist/Morale/Morale`;
its entire adjacent bundle directory is required. The packaged smoke suite is
smaller than the source suite and does not independently cover every XL/path
lettering case. Windows/macOS execution, external format fixtures and physical
Brother/Bernina sew-outs remain outstanding, alongside the feature gaps in the
acceptance ledger. This is a development test build, not completed Hatch parity.

### Designed-font monograms

The native lettering dialog now offers three-letter monograms for designed
embroidery fonts. Initials remain in entered order, with a vertically centered
middle letter 1.4 times the size of the outer letters. The height control sets
the middle letter's design height; the permitted range is narrowed so the
outer letters also remain within the font metadata's designed range. Fonts
whose range cannot accommodate both sizes are rejected with an explanation.
Glyph rails, fills and running paths retain their geometry under uniform scaling
and translation. Character spacing controls the clear gap between initials.

Regression coverage includes proportions, separation, spacing, native creation
and editing, save/reopen command equality, invalid initials, range enforcement
and all nine machine writers' sampled sewn geometry. Physical monogram sew-outs
remain unverified. The preceding Linux bundle predates this addition.

The bundled-font monogram audit in `artifacts/font-monogram-audit/report.json`
generates and exactly round-trips commands for **118 fonts**, sampling the first
three alphabetic glyphs at the minimum permitted monogram height. It records
compressed-font hashes and does not claim every glyph or export is covered.
Four files are unavailable to this sampled layout: `circular_3letters_monogram`
and `ellenika` have no single-character alphabetic glyph keys, while
`emilio_20_tricolore` and `paquerette` have insufficient designed size ranges for
both letter sizes. The latter two now have native-dialog regressions checking
the explanation and recovery when switching back to straight lettering.

### Greek embroidery-font recovery

The converter's Latin-only whitelist had silently removed Ellenika's Greek
letters. It now retains printable, non-whitespace single-character Unicode
glyphs; contextual/multi-character glyph shaping is still unsupported. Ellenika
was regenerated from Ink/Stitch embroidery-fonts revision
`c7e3a05c3d6f5c77b881c50f257851af9a8e9cb8` and now contains 115 glyphs (previously
43) and 128 kerning pairs (previously 40). Source and output hashes are retained
in `artifacts/ellenika-unicode-repair/source.json`; its license is unchanged.
All 43 prior glyphs retain identical geometry. The cap-height calculation now
recognizes flat-topped Greek capitals, using Η for this font instead of the
highest punctuation mark. This changes sizing for newly generated lettering;
saved projects keep their embedded stitch geometry until edited.

Regression coverage generates Greek ΑΒΓ in straight, curved, drawn-path and
monogram layouts, verifies exact command equality after save/reopen and checks
native editing/character coverage. The earlier monogram audit's Ellenika
exclusion is historical and no longer describes the repaired font. It does not
establish shaping support for every script, nor physical sew-out quality.

Greek machine-export regression now exercises the accented monogram ΆΒΩ with a
Greek project name and filename through all nine writers. Each export reopens
with complete sampled sewn-path comparisons and bounds differences at most
0.3 mm; only additional-trim review messages are allowed in this fixture.
Designed-font input and live character coverage normalize canonically equivalent
Unicode text to NFC, so decomposed Greek accents resolve to the same glyphs and
commands as precomposed letters. This normalization does not add contextual
shaping or glyphs absent from a font. Native straight/monogram editing covers
both representations.

### Geometric SVG fill clipping

Local `clipPath` references using `userSpaceOnUse` now resolve to editable fill
geometry before import or assisted digitizing. Geometry follows the cumulative
intersection of ancestor clips; each clip's child shapes are unioned, respecting
`clip-rule` holes. Transforms, SVG viewBox scaling, local use instances and
unclipped siblings are regression-tested. The previous translated-group failure
now imports a 20 × 20 unit visible region instead of its 40 × 40 source rectangle.
Clip geometry ignores fill paint and opacity, as specified by
[CSS Masking](https://www.w3.org/TR/css-masking-1/#ClippingPaths).

This is partial clipping support. Clipped strokes, objectBoundingBox units,
percentage clip coordinates and references within clip definitions still produce
explicit conversion errors. Masks and gradient paints remain unsupported.
Boolean operations flatten curves at enlarged coordinates and enforce geometry
limits; the result remains editable but does not retain the original clip tree.
Tests include the actual conversion worker and ensure its sewing stays within
the clipped fill's bounds. Physical sew-out validation is still pending.

Clipped strokes are now expanded with the existing stroke-outline engine and
intersected with the clip before digitizing. This supports caps, joins, supported
dash patterns (with stroke expansion enabled), transforms and non-scaling
strokes. Fill/stroke paint order and colors remain distinct. Direct import also
uses filled borders for clipped strokes and reports that conversion explicitly;
unclipped strokes keep their established behavior. Regression cases cover dash
gaps, scaled/non-scaling thickness, paint order and actual worker-generated
sewing confined to the visible region. Bounding-box clip coordinates, masks and
gradients remain pending.

Object-bounding-box clip coordinates now scale against each referencing shape or
group's original geometry bounds, excluding stroke width. Group bounds include
child transforms, and clips are resolved in the referencing element's local
axes before its world transform. Shared definitions adapt independently to each
object. Fractional and percentage coordinates are tested, as are rotated shapes
and transformed groups. Zero-width/height geometry ignores the bounding-box
clip, following [SVG's object bounding box rules](https://www.w3.org/TR/SVG11/coords.html#ObjectBoundingBox).
User-space percentage coordinates and references within clip definitions remain
unsupported; masks and gradients also remain pending.

### Clipped artwork through machine export

`artifacts/clipped-artwork-machine-review/` retains source/prepared SVGs, a PNG
preview, the editable project, nine machine files and verification results for a
red fill with a square cutout crossed by a clipped blue border. Regression tests
check that complete native sewn segments avoid the cutout, stay within the clip
bounds and reproduce exactly after project save/reopen. All nine writers pass
complete sampled path comparisons and bounds differences within 0.3 mm.
Seven files have no verification differences; VP3 adds one trim and TBF adds two,
which remain explicit review-required results. Geometry success does not erase
these control differences. The clipping suite passes 36 tests; physical sewing
and external machine files remain unverified.

The clipped-border review exposed a preview artifact: touching outer/hole edges
left by Boolean intersection produced faint antialiased lines across an otherwise
empty cutout. Canonicalizing the resulting paths removes those coincident edges
before SVG serialization. A regression first reproduced the artifact, then
verified every pixel in the interior cutout is transparent while both visible
border pieces remain opaque. The corrected preview is retained in
`artifacts/clipped-artwork-preview-corrected/`. All 146 SVG tests pass, including
the nine-writer geometry regressions after canonicalization.

### Packaged clipping check

The Linux executable was rebuilt after SVG clipping and Unicode/monogram
lettering changes. All **35 packaged smoke checks pass**; evidence is in
`artifacts/bundle-self-test-svg-clipping/report.json`. The new clipping check
runs the actual frozen tracing worker, imports an object-bounds clip with a
cutout, checks physical width and contours, verifies save/reopen command equality,
and rejects needle penetrations inside the cutout. The broader source clipping
tests additionally check full sewn segments and all nine export formats. The
three self-test harness tests pass. Windows/macOS execution and physical sewing
remain outstanding; these smoke checks do not establish full feature parity.

Local `use` references within clip definitions now support basic shapes and
paths, including href/xlink:href, x/y offsets and transforms. Referenced geometry
is validated before expansion; a clip on a referenced shape remains an explicit
unsupported case rather than being silently dropped. Original reference
geometry is captured before paint-opacity normalization, since clipping ignores
paint opacity while ordinary painted uses must retain their visibility. Regressions
cover the same transparent shape used both as a clip and as painted artwork.
References to groups, chains of uses and nested clip references remain pending.

Clip-reference visibility regressions now distinguish a transparent painted blue
shape from a shape with no paint, ensuring the ordinary use truly remains
invisible while its geometry supplies a clip. Explicit display:none and hidden
visibility still suppress clip geometry; an opaque child cannot revive a
zero-opacity painted group when clipping normalization is active. All 45 clipping
tests pass. No production change was needed for these visibility cases.

### Integrated verification after clipping references

The complete source suite passes **2,238 tests in 172.47 seconds** with Qt's
offscreen backend. New native tests exercise both direct SVG import and assisted
preview/add for clipped artwork: they retain the hole, preserve the source file,
reproduce stitch commands after project serialization and restore exact project
state through Undo/Redo. This integrates the recent SVG clipping, clip-reference,
monogram and Greek-font changes. The latest 35-check Linux bundle predates clip
references; no Windows/macOS or physical-machine validation is implied.

Overlapping curved clips in object-bounds coordinates exposed early Boolean
flattening error: two normalized circles enlarged to 100 mm deviated by about
0.342 mm at contour-segment midpoints. The clip union now runs at increased
precision before scaling to physical artwork coordinates. A regression checks
the boundary against the analytic union of two circles and requires less than
0.02 mm error at every segment midpoint. Existing clip geometry limits remain
active; this fixture is evidence for that case, not a global curve-error bound.

Nested clip references now resolve by geometric intersection on clip definitions,
clip children and reused basic shapes. Child regions within one clip still union;
ancestor/nested restrictions intersect. Regression cases distinguish these two
operations and cover a bounding-box clip on a reused shape. Direct/indirect
cycles fail explicitly, and dependency depth is limited to 64 levels. Group use
references and user-space percentage clip coordinates remain pending, alongside
masks and gradients. The latest packaged executable predates this extension.

Nested clipping now propagates the enclosing clip's Boolean-operation precision
into referenced clips. Without this, a user-space curved clip nested inside an
object-bounds clip was flattened too early, then enlarged. The regression
reproduced a boundary error above 0.14 mm; both cold and previously populated
cache cases now require every sampled segment midpoint to stay within 0.02 mm
of the analytic boundary at 100 mm artwork size. Cache keys include precision
so a prior coarse use cannot degrade a later normalized use. This remains a
fixture-specific accuracy check, not a general geometric proof.

User-space clip percentages now resolve against the root viewport's viewBox
width/height, or viewport dimensions when no viewBox exists. Percentage circle
radii use the normalized diagonal, per [SVG 2 units](https://www.w3.org/TR/SVG2/coords.html#Units).
Explicit resolution avoids the underlying parser's incorrect percentage-radius
result on rectangular viewports. Regressions cover percentage rectangles,
viewBox scaling and circular clips. Percentage user-space clips in documents
with nested SVG viewports still fail explicitly until viewport-context handling
is implemented. This extension is not yet included in the retained Linux bundle.

Percentage clipping now has worker-level equivalence tests for rectangles,
circles and ellipses in a scaled viewBox. Each percentage version and its
absolute-coordinate counterpart produce identical prepared SVG, raster preview,
thread colors and generated stitch sequences; source files remain unchanged.
These three tests validate the current root-viewport implementation and do not
cover nested viewport percentage semantics.

Percentage user-space clips now carry the referencing element's nearest SVG
viewport dimensions through recursive clip evaluation. Cache entries include
viewport dimensions, so reuse across differently sized nested viewports does
not reuse an incorrectly sized clip. Regressions cover a nested viewBox and the
same clip used at root and nested scales. Testing also exposed svgelements
inheriting a viewport's x/y into child rectangles; missing rectangle/use positions
are now explicitly normalized to zero before parsing to prevent double offsets.
Viewport overflow clipping itself remains a separate unsupported operation.

Clips attached directly to SVG viewport elements now include that element's
viewBox mapping. Clipping normalization also restores x/y placement for nested
viewports without a viewBox, which svgelements otherwise omitted. Regressions
compare clips on the viewport with equivalent clips on its content group and
assert physical bounds in both cases. These corrections apply to the clipping
normalization path; they do not establish implicit viewport-overflow clipping
or exhaustive support for arbitrary nested SVG documents.

### Explicit SVG viewport cropping

SVG viewport `overflow="hidden"`/`scroll` now intersects artwork with the viewport
rectangle before digitizing. Cropping handles nested viewport positions and
viewBox transforms, and combines with explicit clip paths by intersection.
Slice-aligned viewBoxes crop their overflow unless `overflow="visible"` is
explicit. Tests assert physical bounds, filled/stroked clipping regressions and
prepared-preview pixels. Implicit browser stylesheet overflow defaults are not
yet modeled; masks and gradient paints remain pending. This feature is not yet
in the retained Linux executable.

Viewport-cropped borders now have worker-to-machine regression coverage across
all nine writers. A round-capped stroke extends beyond both page edges; the
worker must produce an 80 × 8 mm filled border. Export readback must preserve
sampled sewn geometry within the existing 0.3 mm bounds gate, with decoded needle
positions confined to the cropped rectangle within 0.1 mm quantization tolerance.
Only added-trim warnings are permitted in this fixture; they remain review
results rather than suppressed differences. All nine cases pass. These checks
do not establish actual machine behavior or physical sewing quality.

Nested SVG viewports now default to hidden overflow, matching the
[SVG 2 user-agent stylesheet](https://www.w3.org/TR/SVG2/styling.html#UAStyleSheet).
Explicit presentation-attribute or inline-style visible overflow overrides that
default. All nested viewports pass through geometry normalization, including
visible ones, so their positions are not dependent on an unrelated clip being
present. Missing SVG x/y positions also default to zero instead of inheriting
parent offsets. The 194 SVG regression cases pass before the final visible-only
normalization refinement; its five focused default/override/position cases pass.
Root viewport defaults are unchanged; masks and gradient paints remain pending.

### Reusable SVG symbols

Local symbol/use instances now expand into bounded SVG viewports before geometry
parsing. Instances retain x/y placement, width/height, viewBox aspect-ratio sizing,
transforms and paint inheritance. Definitions do not paint directly, and their
children remain available by ID. Expansion is limited to 10,000 visited elements
and 64 symbol-reference levels; existing circular-use validation remains active.
Regression cases cover differently sized/colored instances, cropped symbol
overflow, nested symbols and circular references. Masks and gradient paints
remain unsupported. The latest packaged Linux app predates symbol support.

Symbol support now has actual worker-to-export coverage: two differently sized
and colored instances of a ring symbol retain their cutouts, order and physical
widths, preserve source bytes and reproduce stitch commands after save/reopen.
All nine machine writers pass complete sampled geometry comparisons with bounds
differences no greater than 0.3 mm. Only additional-trim review messages are
permitted in this fixture. All 13 symbol tests pass; physical sewing remains
unverified.

Repeated symbol instances now receive unique internal IDs and rewritten local
href/xlink:href and URL references. This avoids duplicate document IDs after
expansion and keeps each instance's clip definitions local. Regressions verify
unique IDs, per-instance percentage clipping, quoted inline-style URLs, internal
shape references and collisions with existing generated-looking IDs. Source
symbol definitions remain available for external local references.

Zero-sized nested SVG/symbol viewports are now removed from rendering before
svgelements parsing. Previously, a zero-sized symbol could suppress unrelated
visible siblings. Negative viewport dimensions now fail explicitly instead of
producing mirrored geometry. Regression coverage checks width and height with
zero unitless, millimeter and percentage values, plus negative instance sizes.
The source dimensions are validated before conversion; no machine interpretation
of zero or negative sizes is relied upon.

### Packaged symbol and viewport update

The Linux development app was rebuilt with the latest clipping, viewport and
symbol changes. All **36 packaged smoke checks pass**; the retained report is
`artifacts/bundle-self-test-svg-symbols/report.json`. The new symbol check runs
the frozen tracing worker on two differently sized/colored symbol instances with
internal percentage clips, then checks physical widths and save/reopen stitch
identity. All three self-test harness tests pass. The executable remains
`dist/Morale/Morale`, with its adjacent bundle files required. Windows/macOS,
external-file corpus and physical sew-outs remain outstanding.

### Gradient rendering foundation (not enabled in import)

`morale/svg_gradients.py` introduces a linear-gradient brush for painting validated
geometry. It supports stop colors/opacity, object-bounds or user-space coordinates,
percentages, gradient transforms and pad/repeat/reflect spread. A pixel regression
shows geometric clipping removes outside pixels while retaining the same colors
inside the clip, avoiding the Qt SVG renderer's clip-loss problem. Six tests pass.
This is a rendering component only: gradient SVG import/color tracing is still
unsupported. Paint-preserving integration, inherited/radial gradients, coincident
stop handling, native controls and worker/export validation remain unfinished.

### Local gradient template resolution (import integration pending)

The gradient rendering foundation now resolves local `href` and legacy
`xlink:href` template chains without changing source XML. Own stops replace
inherited stops; coordinates inherit only between matching gradient types,
while shared gradient attributes can cross types. Descriptive children do not
prevent stop inheritance. Duplicate IDs, missing/non-gradient targets, external
references, cycles, unsupported children, and chains beyond 64 levels fail
explicitly. These rules follow the SVG 2 paint-server template model:
https://www.w3.org/TR/SVG2/pservers.html#PaintServerTemplates

The gradient tests include pixel equivalence between inherited and explicit
linear gradients under object transforms and clipping. This is still a renderer
component, not enabled SVG gradient import. Radial brushes, hard color stops,
ancestor style handling, paint-preserving geometry integration, native controls,
and conversion/export validation remain unfinished.

### Radial gradient brush foundation (import integration pending)

`gradient_brush` now constructs linear and extended radial Qt brushes. Radial
coordinates support object bounds and user-space percentages, including the
normalized viewport diagonal for radius percentages. The focal point defaults
to the resolved center; explicit focal circles use Qt's extended constructor.
Pixel tests cover elliptical rings on rectangular bounds, shifted highlights,
clipping without moving colors, equivalent percentage/absolute radii, focal
circle interiors, coincident circles, and invalid coordinates/radii.

This remains internal rendering work. SVG gradient import is still disabled;
external-focus cone behavior and boundary spread behavior need further SVG 2
conformance checks before integration. Reference:
https://www.w3.org/TR/SVG2/pservers.html#RadialGradients

Gradient brush validation now runs before empty-stop and solid-color shortcuts.
Zero-area object bounds and singular gradient transforms produce no paint,
rather than accidentally becoming solid fills or identity-transformed colors.
Nonfinite bounds/world transforms and invalid spread modes fail explicitly.
The focused gradient suite has 33 passing tests. This does not enable gradient
import or establish physical embroidery quality.

### Validated geometry handoff for gradient painting

The SVG validator/clipping pipeline now accepts an internal paint sink. Each
visible fill or expanded stroke is delivered in paint order with its unclipped
source element and local viewport. This permits a gradient brush to retain the
original shape bounds and transform after clipping. The ordinary SVG import
path keeps its existing serialized output behavior.

Integration tests paint a gradient through actual validated/transformed SVG
clip geometry, check original versus visible bounds and transparent pixels,
check stroke-first ordering and expanded stroke bounds, and cover symbol
expansion with hidden artwork. Gradient references are not yet accepted by the
public importer; source paint mapping, raster conversion, and native controls
remain to be connected.

### SVG paint rendering reaches editable regions (native integration pending)

`svg_render.render_svg_artwork` maps local gradient paints through the validated
geometry sink, restores brushes in original coordinates, and paints a bounded
raster with clipping, expanded strokes, transforms, and symbol viewports.
Temporary paint identifiers avoid explicit solid-color collisions.
`trace_svg_artwork` feeds that raster into the existing color-region tracer,
returns editable objects, retains the source filename as the project name, and
cleans its temporary PNG. An integration test verifies clipped gradient regions,
source preservation, and identical generated commands after project reopening.

This is not yet wired to the assisted-conversion worker or native controls.
Partial object/group opacity explicitly fails because isolated compositing is
unfinished. Hard gradient stops, ancestor gradient styles, and radial boundary
conformance also remain open. Do not claim general SVG gradient compatibility
or physical machine validation from these component tests.

Rendered SVG tracing is now available inside the conversion worker through the
explicit boolean `render_svg` option. Existing SVG vector conversion remains
the default. The new path runs through the same region finishing, stitch
settings, reference image, aligned preview, and source fingerprint pipeline.
A worker integration test verifies editable fill objects, all three review
panels, a retained reference image, and rejection when the source digest changes.
The native dialog does not yet expose this option; renderer limitations above
still apply. No new physical compatibility claim is implied.

### Native SVG color tracing control

The assisted conversion dialog now exposes **Trace SVG colors and gradients**.
It enables palette/resolution/method controls, hides direct stroke expansion
because rendered strokes already retain width, and dispatches the worker's
explicit rendered-SVG path. Returning to vector mode restores existing controls
and invalidates previews/corrections. This per-artwork mode is intentionally
separate from portable tracing presets for now.

A native integration test runs the real conversion worker, verifies editable
output and reference retention, applies it to a window, and confirms Undo
restores the prior project. The targeted renderer/vector suite passes 31 tests.
Renderer limitations documented above remain; packaged execution and export
verification for this new mode are still pending.

### Packaged Linux gradient conversion evidence

The rebuilt Linux application passes all 37 packaged smoke checks, including
`svg_gradient_color_conversion`. The frozen trace worker converts a clipped
linear gradient into multiple editable color regions, preserves generated
commands through project save/reopen, and keeps needle positions out of the
clipped-away half. Evidence: `artifacts/bundle-self-test-svg-gradients/report.json`
and `gradient.morale` in that directory. The source smoke-test suite also passes
3 tests. This check does not yet verify gradient-specific machine exports,
Windows/macOS execution, external files, or physical sew-outs.

### Gradient-specific machine export review

The clipped gradient project produced by the frozen Linux worker was exported
and reopened in PES, PEC, JEF, DST, EXP, VP3, U01, TBF, and XXX. All nine completed
path comparison and retained sewn bounds within the verifier tolerance. Seven
passed without reported differences. VP3 inserted one trim and TBF inserted two;
both remain review-required, not verified. The report includes source/output
SHA-256 hashes: `artifacts/gradient-machine-export-review/report.json`.
The renderer suite now passes 21 tests, including nine worker-to-machine export
cases and explicit reopened needle-position bounds. These are generated-file
software checks, not external corpus or physical Brother/Bernina validation.

Gradient definitions now resolve ancestor `color` and `color-interpolation`
properties (including inline styles and inherit/unset/initial values) before
painting. Referenced template stops use the consuming gradient's color context;
the shape referencing the gradient does not supply that color. Pixel tests
verify both ancestor colors and template isolation. This covers those inherited
properties, not a general CSS cascade. SVG 2 reference:
https://www.w3.org/TR/SVG2/pservers.html

### Hard gradient transitions

Coincident gradient stops are now accepted. The renderer retains the first
color immediately before a shared offset and the last color at/after it, using
adjacent floating-point offsets so Qt does not collapse the incoming color.
Decreasing offsets are clamped to the previous offset before this handling.
Pixel tests cover three coincident colors, decreasing offsets, and duplicate
stops at zero. This supersedes earlier hard-stop limitations; masks and partial
group compositing remain unsupported. Boundary pixels remain subject to Qt's
raster sampling precision.

### Full source regression and transparent gradient colors

The full source suite passed 2,361 tests in 183.21 seconds after native gradient
tracing, inherited colors, hard stops, and export checks were added. A subsequent
rendering probe found Qt's default premultiplied color interpolation discarded
the RGB contribution of a transparent gradient stop. Gradient brushes now use
component interpolation, matching SVG's separate RGB/alpha interpolation.
A midpoint pixel regression checks transparent red to opaque blue. The full
suite result predates this final interpolation change; focused gradient/render
checks cover that change separately. The last packaged bundle also predates
inherited colors, hard stops, and this interpolation fix.

The Linux bundle has now been rebuilt with inherited gradient colors, hard
transitions, and component color interpolation. All 38 packaged checks pass,
including a new pixel-level `svg_gradient_styles_and_interpolation` check.
Evidence: `artifacts/bundle-self-test-gradient-styles/report.json` and its
`gradient-rendering.png`. Source self-test coverage passes 3 tests. The bundle
includes the latest gradient work; other-platform runs and physical validation
remain outstanding.

### SVG tracing mode in portable presets

Presets now include the boolean `render_svg` mode. Loading a preset for SVG
restores direct/vector versus rendered/color controls before applying the
tracing method. Older presets default to direct vectors. Raster dialogs can
reuse the remaining settings without dispatching the SVG renderer. A native
round-trip regression covers restored pixel tracing controls, worker options,
legacy defaults, and raster reuse. This supersedes the earlier per-artwork-only
preset limitation.

Gradient coordinates now accept absolute px, mm, cm, in, pt, pc, and Q lengths
at the SVG 96-pixel/inch scale, for both linear coordinates and radial centers,
foci, and radii. Pixel-equivalence tests compare seven linear unit forms and a
mixed-unit radial gradient against numeric user-space coordinates. Percentages
retain their existing viewport/bounding-box interpretation. Font-relative
lengths remain unsupported.

Single-stop radial gradients now paint the single stop as a solid color before
radial-circle degeneracy handling. Previously, coincident circles or an external
focus could create transparent regions even though the gradient had only one
color. Four rendered-image regressions cover ordinary, zero-radius,
coincident-circle, and external-focus cases while preserving shape boundaries.

### SVG paint opacity

Rendered SVG color tracing now retains partial fill/stroke opacity. Solid paints
carry their alpha directly; gradient brushes multiply stop alpha by the source
paint opacity at rendering time. Pixel regressions cover translucent solid and
gradient red over blue artwork and combined stroke/stop alpha with an empty
center. Direct vector import keeps its existing opaque-thread notice. Partial
whole-object/group opacity still fails explicitly pending isolated compositing.

### Isolated object and group opacity

Rendered SVG conversion now emits opacity-layer boundaries alongside validated
paint geometry. The renderer paints each translucent object/group to a separate
image and composites it once onto its parent, preserving fill/stroke overlap and
nested group opacity. Active layer allocation is bounded to 64 megapixels;
all active painters are closed on failure. Pixel regressions distinguish group
opacity from per-child alpha, verify shared fill/stroke opacity, and nested
half-opacity groups. This supersedes the earlier partial-group-opacity
limitation. Masks and general CSS remain unfinished; direct vector import
continues to report opaque thread interpretation separately.

The group-opacity worker regression now checks actual palette-reduced colors:
overlapping red children at half group opacity over blue produce one purple
region plus the remaining blue background. Antialiased boundary pixels slightly
shift the reduced blue swatch, so the test allows that measured quantization
while keeping purple-channel checks tight. PES and EXP exports both reopen with
complete path comparison and no verifier differences; generated commands survive
project save/reopen and source SVG bytes remain unchanged. Physical thread color
and machine behavior are not established by these tests.

### SVG paints in the image-conversion quality corpus

The generated artwork benchmark now contains 13 cases, including a hard
red/blue SVG gradient and overlapping half-opacity red children over blue.
Both use rendered-SVG worker conversion and compare resulting editable color
geometry against independently specified design objects. All artwork gates and
117 machine export path/bounds checks pass. The five benchmark tests pass in
16.39 seconds. Preserved evidence and visual review:
`artifacts/image-benchmark-svg-paints/report.json` and `review.pdf`.
These gates measure geometry/color-region fidelity for generated fixtures, not
exact control-command preservation, outside artwork, or physical sew-outs.

### Linear-light gradient interpolation

Gradient brushes now accept `color-interpolation="linearRGB"` using adaptive
sRGB samples of the linear-light RGB interpolation curve; alpha remains linear.
Subdivision targets a quarter of an 8-bit channel at midpoint, with bounded
recursion and expanded stop count. Pixel tests compare a black/white ramp to the
sRGB transfer function and check translucent red/blue midpoint channels.
`auto` uses sRGB. This supports gradient color interpolation specifically;
linear-light compositing between separate objects is not implemented.

Repeated references to one gradient now share a single resolved definition and
temporary paint identifier per render. Brushes still use each shape's original
bounds and transform. A regression counts definition resolution and checks
colors on differently sized instances. A local 400-rectangle/shared-gradient
probe rendered at 512 pixels in 0.052 seconds (one observation, not a portable
performance guarantee). The SVG renderer suite passes 41 tests.

### Regular CI native bundle checks

Regular CI now builds and runs the frozen app's smoke checks on the Python 3.12
Linux, Windows, and macOS jobs, preserving the self-test evidence as artifacts.
Previously these packaged checks only ran in the release workflow.
`python packaging/build.py --bundle-only` uses the release PyInstaller spec and
self-test while omitting distribution archives/installers. The new command was
executed locally on Linux and all 38 packaged checks passed; evidence is in
`artifacts/bundle-self-test/report.json`. Workflow edits are local and have not
been executed on Windows/macOS, so native validation on those systems remains
unproven. Installer validation is still separate.

### Mask compositing foundation (not enabled in SVG import)

`svg_masks.apply_mask` combines aligned source/mask images using alpha or
luminance, including mask alpha and source alpha. Luminance supports sRGB or
linear-light channels. It preserves input images and bounds work to four
megapixels. Eight tests cover black alpha-versus-luminance behavior, white and
colored luminance masks, alpha multiplication, linear-light gray, and mismatched
sizes. This is a compositor component only: mask geometry/units/reference
resolution and native conversion integration remain unfinished. Model reference:
https://www.w3.org/TR/css-masking-1/#MaskValues

Mask coordinate preparation now resolves independent `maskUnits` and
`maskContentUnits`, default extended regions, viewport percentages, original
object bounds, and document transforms. Zero-sized regions remain empty;
nonfinite/negative dimensions and unsupported units fail. The mask suite passes
12 tests. This remains preparatory code; masks are not yet accepted by the native
SVG conversion path.

Mask-child rendering now uses the validated SVG renderer with an independent
content viewport and transform, then restricts the rendered mask to its region.
Local gradient definitions can be supplied, and the resulting mask can be
composited through the alpha/luminance helper. Two integration tests cover
bounding-box percentage content with region cropping and a gradient luminance
mask aligned to the source image; all 14 mask tests pass. Document-level mask
references and nested-mask processing are not yet connected to native import.

### Local SVG masks integrated into rendered conversion

Rendered SVG preprocessing now retains local mask definitions and routes mask
boundaries through the geometry/layer pipeline. Masks render against original
shape/group bounds, apply to the combined layer, and precede object/group
opacity. Nested mask references share a 16-level cycle/depth guard and a total
64-megapixel rendering budget. Integration tests cover a bounding-box group
mask, nested masks plus half opacity, and circular reference rejection.
The existing native SVG color-tracing path uses this renderer; direct vector
import still rejects masks. Broader inherited mask styles/resource layouts,
mask-specific worker/export checks, and packaged validation remain open.

### Mask worker, export, and packaged evidence

The mask suite passes 26 tests, including real worker conversion followed by all
nine machine exports and readback. Each export completes path comparison,
retains bounds within tolerance, and leaves needle positions in the visible
half; only added-trim differences are permitted by these regressions. Project
reopening retains commands and source SVG bytes are unchanged.
The rebuilt Linux app passes all 39 packaged smoke checks, including
`svg_masked_color_conversion`; current evidence is
`artifacts/bundle-self-test/report.json` and `masked.morale`. These generated
fixtures do not establish external-file or physical machine compatibility.

Mask rendering now retains only outermost definition subtrees as resources,
avoiding duplicate nested definitions while preserving their style ancestors.
Cloned mask content receives unique IDs and rewritten local `href`/paint URLs,
so gradient and shape resources inside masks do not collide with their original
definitions. A rendered regression combines nested defs, a local gradient,
a named rectangle, and a use instance inside a bounding-box mask.

Mask definitions and copied resource subtrees now retain their inherited color,
fill/stroke paint, fill/stroke opacity, fill rule, stroke width, and interpolation
context. CSS-wide inherit/unset/initial values are resolved for those properties.
The referencing shape's paint does not replace the mask definition's context.
Rendered regressions cover inherited white mask fill and a currentColor gradient
resource whose color comes from the SVG root. This is explicit presentation/
inline-style handling, not stylesheet selector support.

Mask resource collection now includes outermost mask, gradient, clipPath, and
symbol definitions outside defs containers, while preserving inherited styles
and avoiding duplicate nested resources. A regression renders nested masks with
a root-level currentColor gradient and verifies the visible/hidden halves.

### Mask cutout conversion benchmark

The generated quality corpus now has 14 cases and 126 export combinations.
The added SVG luminance mask removes a central square from a colored fill;
independent expected contours verify visible area and color geometry. All five
benchmark tests pass. A further mask-specific run also verifies every native
sewn segment stays inside the traced material (including connectors), and all
nine export path/bounds gates pass. Its evidence is
`artifacts/image-benchmark-mask-cutout/report.json` and `review.pdf`.
The full 14-case test run predates that added containment gate; the focused run
covers it. Physical coverage and fabric behavior remain unverified.

### Embedded SVG stylesheet cascade

A bounded stylesheet pass now uses tinycss2 and cssselect2 to resolve embedded
rules before both SVG import paths. It handles selector specificity, source
order, inline precedence, and important declarations, then removes style nodes
and passes normalized paints through existing validation. Tests cover direct
vector colors, gradient stops, masks/group opacity, and unsupported CSS errors.
External stylesheets/at-rules, media queries, pseudo-elements, and variables are
explicitly unsupported. Dependencies are declared in pyproject.toml; the installed
tinycss2/cssselect2/webencodings license texts are included in third-party notices.
The rebuilt Linux application passes all 40 packaged checks, including a styled
SVG with conflicting class/ID colors and an object-bounding-box mask converted
through the actual embroidery worker. This verifies the new stylesheet
dependencies in the frozen app. Evidence is in
`artifacts/bundle-self-test/report.json`. Windows/macOS execution, external
machine files, and physical Brother/Bernina sewouts remain unverified.

### Integrated regression gate after SVG stylesheet support

The full source suite passes: **2,423 tests in 192.05 seconds**, using the morale
Conda environment with Qt's offscreen platform. This run includes the current
gradient interpolation, mask rendering, stylesheet cascade, 40-check self-test,
and 14-case image benchmark with the mask containment gate. It supersedes earlier
partial-suite evidence for these changes; it does not establish physical stitch
quality or cross-platform execution. The full v1 acceptance scope remains open.

### Inline CSS syntax color fidelity

Inline styles now pass through the CSS parser even without an embedded stylesheet
or a literal `!important` substring. This fixes valid spaced/commented important
flags and comments within paint values silently rendering red artwork black.
CSS comments are removed during tokenization before normalized values reach the
geometry parser. Regression checks exercise both direct vector import and rendered
color tracing, plus embedded stylesheet comments. The SVG-focused suite passes
286 tests in 22.19 seconds. The earlier full-suite and frozen-bundle runs predate
this correction. Syntax reference: [CSS Syntax Level 3](https://www.w3.org/TR/css-syntax-3/).

### Styled symbol instances through machine export

An end-to-end regression now combines embedded CSS, per-instance currentColor,
repeated symbols, and symbol-local clip references. Independent pixel probes
verify both colors and clipped-out areas. The conversion worker preserves two
separate 20 mm regions placed 60 mm apart (within 0.5 mm tracing tolerance), with
palette channels within two levels of the source colors and unchanged source
bytes. Project save/reload retains generated commands. All nine machine writers
pass complete decoded-path comparison and 0.3 mm bounds checks; only additional
trim-command differences are allowed by this test, not arbitrary discrepancies.
All 13 stylesheet tests pass in 1.47 seconds. These are synthetic software checks;
external-file and physical-machine validation remain open.

### Modern SVG CSS colors

The shared stylesheet pass now normalizes modern RGB/HSL/HWB and explicit sRGB
color expressions for the geometry parser, including slash alpha and the
rebeccapurple keyword. This applies to presentation attributes, inline styles,
embedded rules, gradient stops and inherited color. Attribute selector matching
still sees the original source values. Unsupported color spaces (including
Display P3 and OKLCH) produce explicit errors instead of silently painting black;
wide-gamut conversion remains open. The SVG-focused suite passes 308 tests in
22.99 seconds; two additional selector/direct-vector regressions are covered by
the subsequent 36-test stylesheet run. A test-fixture correction ensures this
module creates QApplication before invoking conversion workers, preventing a
QGuiApplication-only instance from breaking later widget tests. Full-suite and
packaged validation predate this change.

### Packaged modern SVG color conversion

The rebuilt Linux bundle passes all 41 checks. The new real conversion-worker
check combines space-separated RGB, HSL, and a commented important declaration;
it checks two independent regions, thread palette channels within two levels of
red/blue, and 40 mm widths within 0.5 mm. The project is retained alongside the
report in `artifacts/bundle-self-test/modern-colors.morale` and
`artifacts/bundle-self-test/report.json`. This also verifies inclusion of the
CSS color parser in the frozen app. Windows/macOS execution, wide-gamut color
conversion, external machine files, and physical sewouts remain open.

### Editable fabric starting points

Edit → Fabric settings (also in object properties) now opens a native review
of stable-woven, stretch-knit, and textured/pile starting points. Users can adjust
cover row spacing, compensation per side, underlay inset/spacing and fill underlay
before applying to selected fill/satin objects. Satin maps the support choice to
center or center-plus-zigzag. Running, manual and other stitch types retain their
settings. Changes validate and generate before one undoable document mutation;
settings persist as ordinary editable object properties. Existing gradient end
spacing and finishing settings are retained, as stated in the dialog.

These are Morale-authored experimental values, not vendor recipes or physically
calibrated profiles. Stabilizer/thread-specific presets, reusable custom profiles,
new-object defaults, and physical calibration remain open. The workflow follows
the general relationship between spacing, compensation and underlay described in
[Hatch fabrics and densities](https://hatch.embroideryhelp.net/v4/en/OnlineHelp/Basics/customize_settings/Fabrics_densities.htm).
All 29 fabric/underlay tests pass, including profile generation, source preservation,
selection scope, project round-trip, Undo/Redo and failed-setting atomicity.
Packaged validation predates this feature.

### Fabric profile export and accessibility checks

All three experimental fabric profiles now have mixed fill/satin export checks
across all nine writers (27 combinations). Every decoded export passes complete
path comparison and bounds tolerance of 0.3 mm; the only permitted discrepancies
are extra trim commands. The generated commands differ from the unmodified
source, and applying a profile leaves the source snapshot intact. All 30 fabric
tests pass in 2.21 seconds. The native fabric dialog is also included in the
accessible-name/keyboard-focus audit; all eight accessibility tests pass in
2.42 seconds. These checks do not calibrate fabric recipes or substitute for
manual screen-reader and physical sewout testing.

### Portable custom fabric presets

The fabric dialog now saves and loads `.morale-fabric.json` files for reusing
sewout-adjusted settings across projects. Versioned files contain the five editable
settings in millimeters, with strict shape/type/finite-number/range validation and
an 8 KB input limit. Successful load clears the built-in profile selection so
custom values are not presented as a built-in recipe. Loading does not mutate the
project until Apply; invalid files preserve the dialog's current values. Saves
use same-directory temporary files and atomic replacement, with cleanup on failure.
The dialog's minimum cover spacing is corrected to the model's 0.2 mm limit.
All 45 fabric/accessibility tests pass in 4.84 seconds, including native custom
preset round-trip, invalid-load preservation, malformed-setting rejection before
write, and replacement-failure preservation/cleanup. Physical calibration,
new-object defaults and packaged validation remain open.

### Packaged fabric workflow

The rebuilt Linux app passes all 42 packaged checks. The added check creates the
native fabric dialog, customizes a profile, saves/reloads its portable preset,
applies it through the main window, verifies generated stitches after project
serialization, and verifies Undo/Redo. Evidence is retained in
`artifacts/bundle-self-test/report.json`, `fabric.morale`, and
`custom.morale-fabric.json`. This establishes local frozen-app integration;
Windows/macOS execution and physical calibration remain open.

### Reviewing existing fabric settings

Reopening Fabric settings now starts from common selected fill/satin settings
when those settings can be represented without changing the underlay choice.
Mixed selections, disabled underlay, and unsupported underlay combinations
explicitly show starting-point values. Applying unchanged representable values is
a no-op; unedited numeric precision survives the dialog's rounded display.
Loaded presets and built-in starting points have distinct context messages.
The 48 fabric/accessibility tests cover native reopen/apply preservation, mixed
selection detection, and sub-display precision alongside the prior export gates.
Packaged checks predate this extension.

### Integrated regression baseline after fabric workflows

The complete source suite passes **2,491 tests in 205.70 seconds** in the morale
Conda environment with Qt offscreen. This includes modern SVG colors and inline
CSS syntax, styled-symbol exports, fabric profiles across nine writers, portable
presets, and selection-aware fabric review with precision preservation. The
process exits successfully. This supersedes the earlier partial source-suite
results for these changes; the 42-check Linux bundle predates selection-aware
fabric review. Cross-platform execution, external files, physical calibration,
and the remaining feature-parity scenarios stay open.

### Fabric presets in artwork conversion

Digitize artwork now loads portable fabric presets into the existing editable
conversion controls. Spacing maps to both cover types, fill underlay retains the
preset style, and satin maps to center/center-plus-zigzag. Compensation and support
spacing/inset are transferred while unrelated conversion settings remain intact.
Existing preview/region corrections are invalidated before regeneration. The
native worker-option regression checks these mappings and retained size, color
count and stitch length; invalid settings leave controls unchanged. All 31
conversion-preset/accessibility tests pass in 2.55 seconds. Packaged execution of
this new entry point and physical calibration remain open.

### Fabric-to-conversion worker evidence

A native conversion regression now saves/reloads a custom fabric preset, loads it
into Digitize artwork, and sends the dialog's actual options to the conversion
worker. A two-region SVG independently produces both fill and satin. All three
supported fabric underlay choices retain the expected type-specific support,
spacing, inset and compensation in the resulting editable objects. Project
serialization preserves generated commands, source artwork bytes stay unchanged,
and PES/EXP decoded exports pass complete-path and 0.3 mm bounds checks with no
reported discrepancies. All 49 conversion stitch-setting tests pass in 3.63
seconds. This is software evidence for the intended Brother/Bernina test path;
it does not establish compatibility with their still-unspecified models or
physical stitch quality.

### Fabric custom-value state and deliberate edits

Editing any fabric field now clears the built-in profile selection and identifies
its values as custom. Reselecting a built-in profile restores its values and
label. Loaded/current numeric precision is retained only until that field is
edited; changing a value and returning to its rounded display now retains the
user's deliberate choice rather than restoring hidden original digits. This also
avoids relying on Python and Qt using identical numeric rounding. All 50
fabric/accessibility tests pass in 4.74 seconds, including these edit transitions
and preservation of unedited fields. Packaged execution predates this correction.

### Packaged fabric-to-artwork integration

The rebuilt Linux application passes all 43 packaged checks. The new check loads
the saved fabric preset into the native conversion dialog and runs its options
through the frozen conversion subprocess. Both fill and satin retain their
expected spacing, compensation and type-specific underlay. This bundle includes
the selection-aware review and custom-value editing fixes; those transitions
remain covered by source tests rather than dedicated packaged assertions.
Evidence: `artifacts/bundle-self-test/report.json` and
`artifacts/bundle-self-test/fabric-conversion/preview.json`. Windows/macOS and
physical machine validation remain open.

### Preserve region corrections when changing fabric

Loading fabric settings now updates only the relevant stitch controls and
invalidates generated previews, without rerunning tracing-mode initialization.
Region stitch choices, seams, spacing and angles survive this change. The dialog
explains that per-region spacing overrides the fabric default. Whole conversion
preset loading retains its existing correction-reset behavior. All 73 conversion
preset/stitch-setting tests pass, including retained corrections and cleared
preview/review state. This supersedes the earlier fabric-loading reset behavior;
packaged checks predate this adjustment.

### Region correction precedence through fabric conversion

The native-dialog-to-worker regression now covers retained manual region choices,
a 0.9 mm region spacing override against a 0.6 mm fabric default, and a locked
17-degree fill angle. The first region keeps its corrections while the second
uses the fabric spacing; both receive the chosen underlay and compensation.
The worker's review metadata reports the effective region spacing, and project
round-trip preserves generated commands. All 74 conversion stitch-setting/preset
tests pass in 3.90 seconds. This confirms precedence in generated objects beyond
the prior control-state checks; physical coverage remains unverified.

### Fabric preset malformed-input handling

Fabric preset JSON now rejects duplicate fields instead of silently accepting the
last value. Numeric range checks precede float finiteness conversion, so an
oversized integer produces an ordinary validation error instead of OverflowError.
Regression cases cover duplicate root/nested fields, boolean versions, excessive
nesting, oversized files, invalid encoding and a thousand-digit stitch spacing.
All 73 fabric/conversion-preset tests pass in 2.66 seconds. Packaged validation
predates these input-handling changes.

### Large-text fabric dialog visual review

Offscreen visual inspection at 16-point text exposed overlapping labels and
compressed controls in the fabric dialog. Its settings now live in a scrollable
area with a minimum-size content layout; Apply/Cancel stay outside the scroll
area. The corrected rendering shows separated, readable fields. Screenshots are
retained in `artifacts/ui-review/fabric-large.png` (before) and
`artifacts/ui-review/fabric-large-fixed.png` (after). A regression checks scrolling,
control minimum heights and visible action placement at a constrained dialog
height. This is a local Qt/offscreen visual check, not manual screen-reader or
cross-platform verification.

### Conversion actions at large text sizes

Visual inspection at 16-point text showed the single conversion action row
forcing the dialog to 1,123 pixels wide. Add/Cancel now occupy a separate row,
and the preset explanation can wrap. The same local Qt setup now fits the dialog
at 940 × 730 with readable actions and scrollable settings. Before/after captures
are `artifacts/ui-review/conversion-large.png` and
`artifacts/ui-review/conversion-large-fixed.png`. Automated accessibility and
conversion-preset checks pass (32 tests). Smaller screens, other platform styles,
and manual screen-reader use still require verification.

### Conversion review table text sizing

The 16-point Preview-tab review exposed clipped Band seam and Spacing headers.
Region columns now size to their contents (the explanation column still fills
remaining space), and row heights size to their controls. A corrected screenshot
is retained at `artifacts/ui-review/conversion-preview-fixed.png`; the Stitches
tab was also visually inspected without a new layout defect. All 58 accessibility
and conversion stitch-setting tests pass. Populated-table visual inspection on
other native platforms remains open.

### Populated conversion-table review

Real fill/satin worker results exposed oversized rows caused by wrapped decision
explanations. The table now keeps rows compact; selecting a region displays its
full explanation below the table in plain text, and cells also provide tooltips.
The explanation refreshes with regenerated results. Before/after 16-point
captures are `artifacts/ui-review/conversion-populated.png` and
`artifacts/ui-review/conversion-populated-fixed.png`; the latter shows both rows
and editable controls together. All 58 accessibility/stitch-setting tests passed
before the final one-line selected-explanation refresh addition. Packaged and
other-platform visual verification remain open.

### Region explanation lifecycle

Invalidating a conversion now replaces the selected-region explanation with a
request to regenerate. Selecting another cell in retained correction rows cannot
revive an obsolete explanation. A real-worker regression checks initial selection,
refresh after regenerated decision text, and stale-result suppression after
invalidation. All 83 conversion stitch-setting, preset and accessibility tests
pass in 6.52 seconds, including the earlier final refresh addition. Packaged
validation still predates the recent review-layout changes.

### Fabric profile physical comparison coupon

The coupon generator now includes `fabric-profiles`: three columns of paired
20 mm fill squares and 4 × 25 mm satin columns, using the same experimental
profiles as the native dialog. Each evaluation target records the profile,
nominal dimensions, spacing, compensation and actual type-specific support.
A 10 mm scale marker and blank machine/fabric/stabilizer metadata accompany the
placement PDF and evaluation form. This compares whole recipes rather than
isolating individual variables; measured results remain blank.

Generated evidence is in `artifacts/fabric-profile-coupons/fabric-profiles/`.
The 100 mm field contains 3,520 stitches. PES v6, PES v1 and EXP pass export
verification; DST requires review because it adds five trim commands (8 → 13).
All 19 coupon tests pass, including field bounds and clearance around the scale
marker. No machine-load or physical-sewout success is claimed.

### Fabric coupon evaluation fidelity

A dedicated regression now checks all six fabric coupon evaluation records
against the saved project's actual cover spacing, compensation, underlay and
nominal geometry. It verifies the complete profile set, blank physical results,
and decoded paths/bounds for all four exports. Only DST's additional trim controls
are permitted discrepancies. All 20 coupon tests pass in 10.78 seconds. This
protects the measurement form from drifting away from the generated design as
profiles evolve; actual measurements are still required.

### Native fabric sampler entry point

File → Load fabric comparison sampler now opens the editable calibration design
using the existing discard/save guard. The native regression verifies that Cancel
preserves the current document, accepted loading produces the 100 mm field with
six samples plus scale markers, and project serialization retains generated
stitches. The standard save, placement and machine-export actions are available;
blank measurement forms remain part of the command-line coupon pack. Packaged
validation predates this menu entry.

### Native picker for all calibration designs

File → Load sewout coupon now exposes the entire coupon registry in a native
picker. The fabric shortcut reuses the same loading path. Picker cancellation
preserves the current project, selected loading uses the discard guard, and
unknown coupon keys report a normal error. The picker regression verifies the
full registry and loads a density test design with its intended settings.
Coupon generation stays unchanged; physical measurements and calibration remain
open. Packaged validation predates the picker.

### Packaged native coupon loading

The rebuilt Linux app passes all 44 packaged checks, including loading the fabric
comparison through the main-window coupon action, validating its 100 mm field,
generating stitches and retaining the editable project. Evidence is in
`artifacts/bundle-self-test/report.json` and `fabric-coupon.morale`. This bundle
also includes recent fabric input handling and conversion review layouts, whose
focused source/visual checks remain their detailed evidence. Windows/macOS
execution, physical sewouts and remaining parity work stay open.

### Printable sewout observations

Every generated coupon pack now includes `evaluation.pdf`, with escaped sample
names/target values, blank measurement and defect fields, and machine/material
identification. It is separate from actual-size placement printing. Both pages of
the fabric comparison sheet were visually inspected; all six targets are readable
and table headers repeat on the second page. Evidence is in
`artifacts/fabric-printable-coupons/fabric-profiles/`; PES v6/v1 and EXP pass export
checks, while DST retains its five-extra-trim review requirement. All 22 coupon
tests pass in 10.67 seconds. Printing scale and physical results remain unverified.

### Evaluation PDF publication failures

Evaluation sheets now render to a same-directory temporary file, check for a PDF
header and final EOF marker after writer shutdown, and atomically replace the
destination. Incomplete output or failed replacement raises an error, preserves
an existing sheet and removes the temporary file. These structural checks detect
missing/truncated output, not full PDF semantic validity; visual inspection
remains separate evidence. All 25 coupon tests pass in 11.08 seconds, including
incomplete-output and replacement-failure regressions.

### Packaged evaluation-sheet generation

The rebuilt Linux application passes all 45 packaged checks. The new frozen-app
check generates the fabric comparison evaluation PDF and verifies its header and
completion marker. The output is retained at
`artifacts/bundle-self-test/fabric-evaluation.pdf`, with the report alongside it.
This confirms bundled Qt document/PDF support; source-rendered visual inspection
and failure-preservation tests provide the separate content/publication evidence.
Windows/macOS execution and physical validation remain open.

### Native worksheet for current designs

File → Export sewout worksheet now creates the printable form from the current
project's included objects, including modified spacing and compensation. It uses
a validated snapshot, records stable object IDs and a snapshot SHA-256, and omits
irrelevant density fields on manual/running objects. Geometry dimensions are
explicitly described as pre-rotation/pre-compensation. The native regression
checks edited values, hidden-object exclusion, snapshot identity and source
preservation. All 34 coupon/accessibility tests pass. Packaged execution of this
new menu entry remains open.

### Worksheet continuation identity

Rendered current-design worksheets retain readable target fields and the snapshot
hash. Continuation-page table headers now repeat the design title and a blank
run/date field, helping keep printed pages with the correct sewout. The updated
PDF is `artifacts/ui-review/current-design-worksheet-fixed.pdf`; page two was
visually inspected. Qt may split a long sample row across pages, so row pagination
still needs refinement. All 26 coupon tests pass in 10.74 seconds; packaged
validation predates the current-design worksheet changes.

### Measured worksheet pagination

Evaluation PDFs now measure each sample block before drawing it and start a new
page when the complete block fits on a fresh page but not the current one. The
design/run heading and page numbers repeat. Exceptionally tall content can still
span pages; an overlarge heading raises a normal error. The current-design fabric
worksheet was rendered and page two visually checked: sample blocks stay intact.
Evidence is `artifacts/ui-review/worksheet-paginated.pdf` and its page-two PNG.
All 26 coupon tests pass. Packaged PDF execution predates this renderer change.

### Worksheet pagination failure checks

Real-renderer regressions now simulate failure to allocate a continuation page
and reject a heading too tall for a page. Both paths report ordinary errors,
preserve an existing worksheet and clean up temporary output. All 28 coupon tests
pass. These supplement visual pagination review and structural PDF checks; the
packaged renderer still needs its updated execution check.

### Packaged current-design worksheet

The rebuilt Linux application passes all 46 packaged checks, including the
current-project worksheet and the measured evaluation renderer. The resulting
`artifacts/bundle-self-test/current-design-worksheet.pdf` contains the snapshot
identifier, object settings and blank measurements across three pages; PDF text
extraction confirms the final satin sample is present. Source-rendered visual
checks remain the pagination appearance evidence. The report is retained in the
same directory. Other-platform execution and physical validation remain open.

### Generated dimensions on sewout worksheets

Current-design worksheets now record each included object's generated needle
penetration count and axis-aligned stitch bounds, alongside source dimensions
and stitch length. Guidance distinguishes rotated/compensated generated extents
(including support/ties) from source geometry and machine-file quantization. A
regression verifies a 20 mm source width produces a 20.6 mm generated width with
0.3 mm per-side compensation, and checks height/count against actual commands.
All 29 coupon tests pass in 10.93 seconds. Physical deformation remains unknown;
packaged validation predates these added fields.

### Optional underlay in fabric presets

Fabric settings now include an Enable underlay switch. Disabling it keeps the
support parameters for later reuse while disabling their controls; applying the
preset turns off support for selected fill/satin objects. Portable presets accept
an optional boolean `underlay` field, defaulting to enabled for older files.
Loading such a preset into artwork conversion explicitly disables both fill and
satin support. Representable disabled selections can be reviewed without enabling
support. All 84 fabric, conversion-preset and accessibility tests pass in 4.84
seconds. Built-in recipes remain enabled; physical suitability is uncalibrated.

### Underlay-off conversion command evidence

A paired native-dialog/worker regression converts the same two-region artwork
with fabric support enabled and disabled. Both fill and satin preserve source
contours, cover spacing and compensation. Enabled objects generate support;
disabled objects generate none and produce fewer total commands. Project
serialization preserves the disabled result. All 52 conversion stitch-setting
tests pass in 4.30 seconds. This proves generated support removal, not physical
suitability of sewing without underlay.

### Underlay-switch preset compatibility

Additional regressions check that legacy version-one fabric files without an
underlay flag still enable support, and that numeric, string, null and container
values cannot masquerade as a boolean switch or overwrite an existing preset.
All 83 fabric/conversion-preset tests pass. These checks establish software file
compatibility, not physical calibration.

### Integrated regression baseline after sewout tools

The complete current source suite passes **2,530 tests in 209.51 seconds**, with a
successful process exit in the morale Conda environment using Qt offscreen. This
includes native coupon selection, fabric preset compatibility and underlay-off
conversion, preserved region corrections, review explanations/layouts, current-
design measurements and atomic paginated worksheet PDFs. This supersedes earlier
partial source-suite evidence for these changes. The latest 46-check Linux bundle
predates the underlay-off option and generated worksheet measurements; cross-
platform execution, physical sewouts and outstanding feature-parity work remain
open.

### Variable-density worksheet targets

Current-design worksheets now include fill angle and, when enabled, the density
gradient's end spacing and reversal flag. This avoids representing variable-density
fills with only their starting spacing. A regression exercises all four settings;
all 30 coupon tests pass. These values describe the generator inputs and do not
claim measured physical density.

### Keyboard drawing cursor

Drawing tools now accept arrows to move a visible cursor (1 mm; Shift 10 mm;
Alt 0.1 mm; grid step when snapping is enabled). Home returns to the origin.
Space places polygon/path/satin vertices or the two corners of a rectangle,
ellipse or leaf. Enter uses existing path completion; Backspace removes the last
point and Escape cancels the draft. Playback blocks keyboard drawing. The canvas
accessible description documents the shortcuts and status messages give position.
Tests cover shape corners, path removal/completion/cancellation, and native
editable rectangle creation with Undo. All 13 keyboard-drawing/accessibility tests
pass. Satin/polygon keyboard scenarios, screen-reader announcement behavior,
other-platform operation and packaged checks still need verification.

### Keyboard polygon/satin generation and export

Native keyboard scenarios now create polygon and paired-rail satin objects using
2 mm grid steps, generate stitches, export PES/EXP and verify decoded paths and
bounds. An incomplete satin pair does not commit; completing the pair succeeds,
and Undo removes the resulting object. Playback ignores drawing cursor/placement
keys; path completion now also refuses to commit an existing draft during
playback. All 17 keyboard-drawing/accessibility tests pass. Physical sewing,
manual screen-reader testing and packaged keyboard scenarios remain open.

### Packaged keyboard drawing acceptance

The rebuilt Linux executable passes 47 native self-test checks. The new keyboard
scenario sends Qt key events to the canvas to create polygons and paired satin
rails, rejects incomplete satin pairs, regenerates saved projects, compares
PES/EXP decoded paths and bounds, and checks Undo/Redo. It retains both editable
projects and machine exports in `artifacts/bundle-self-test/keyboard-*`.
The three source self-test tests also pass. The bundle includes the current
fabric controls and worksheet pagination changes. This offscreen Linux run does
not establish complete keyboard navigation, screen-reader behavior, Windows/macOS
operation, or physical sew-out quality; those acceptance gates remain open.

### Editable circular ripple fill

Closed vector objects now offer Circular ripple fill in native properties. Rows
are concentric around the object center, spaced in millimeters and clipped using
even-odd contours; holes, nested islands and disconnected regions retain jump
travel between separated sewn runs. Circle chords respect stitch length and a
0.02 mm geometric deviation bound before optional short-stitch cleanup. Existing
underlay and finishing settings remain available; tatami compensation, density
gradients and fill routing do not apply. Clipping work and command counts are
bounded. Editable project persistence and native Undo/Redo are tested.

101 focused ripple, contour, motif-fill, save-validation and coupon tests pass.
All nine writers preserve the tested ripple path and bounds; VP3 adds one trim
and remains flagged for control review. A cutout preview, editable project and
PES/EXP samples are retained in `artifacts/ripple-fill/`. Custom centers, warped
ripples, packaged execution and physical stitch-quality validation remain open.

### Adjustable ripple centers

Ripple properties now include X/Y center offsets as percentages of object width
and height (-100% through 100%; 50% reaches the positive edge). The center follows
object translation, rotation, reflection and resizing. Circle seams and direction
also follow rotation/reflection. Off-outline centers create clipped sweeping arcs.
Existing projects default to a centered effect. Project validation rejects invalid
centers; worksheets record both offsets. Native edits support Undo and persistence.

78 ripple, save-validation, coupon and accessibility tests pass, including exact
transformed-path comparison, legacy defaults, invalid values, and PES/EXP decoded
path checks for an external center with a cutout. A visually inspected preview,
editable project and exports are in `artifacts/ripple-offset/`. Warped ripples,
packaged ripple execution and physical validation remain outstanding.

### Ripple anchor preservation during geometry editing

Contour and polygon point edits, Bezier conversion/handle edits, and Boolean
outline operations now preserve the ripple center in world coordinates when
rebasing the editable geometry. Boolean results inherit the first object's
center. Nonuniform selection transforms apply the same affine transform to the
center as to the outline. If rebasing would exceed the supported center range,
the operation rejects the candidate rather than silently clamping or shifting
the pattern; native point-edit rejection and Undo preserve the original project.

All 120 ripple, contour, transform and Bezier tests pass. This preserves the
center, not exact needle placement: regenerated circular rows remain circular
after nonuniform transforms, and geometry rebasing can change the row seam.
Full affine deformation of the ripple pattern remains outside this implementation.

### Full regression after ripple integration

The complete source suite passes: **2,575 tests in 211.41 seconds**, using the
Morale conda Python with Qt offscreen. This includes ripple generation/centers,
geometry editing, project validation, native controls, generation/import workers,
SVG/raster conversion and machine-format tests. No code changed during this run.
The latest frozen Linux bundle remains the earlier 47-check build and does not
include ripple changes. Windows/macOS execution, physical sew-outs and the other
open acceptance-ledger requirements remain unproven.

### Packaged ripple acceptance

The rebuilt frozen Linux app passes **48 checks**, including native ripple type
selection, center editing, Undo/Redo, project reload with identical generated
stitches, sampled sewn-segment containment around a cutout, and full decoded
PES/EXP path comparisons. The source self-test's three tests also pass.
`artifacts/bundle-self-test/` retains `ripple.morale`, PES/EXP exports, a native
window screenshot and the frozen report. This supersedes the earlier bundle
that lacked ripple. Windows/macOS, physical sew-outs and remaining feature-parity
gates are still open.

### Region-aware ripple cleanup

Short-stitch cleanup now accepts a segment constraint; ripple generation uses it
to retain points whenever removing them would create a sewn shortcut across a
hole or outside the outline. The check clips the entire proposed segment rather
than sampling points, and retains the existing clipping work limit. Other stitch
types retain their existing cleanup behavior.

69 cleanup/ripple tests pass. A deliberately constructed shallow detour proves
that the ordinary 0.01 mm path-error allowance alone can bridge a tiny cutout;
unit and generation-integration regressions retain that detour. Nine real ripple
cases combine three center offsets and three cleanup thresholds and check full
sewn-segment containment. This is software geometry evidence, not physical
minimum-feature validation. The current 48-check bundle predates this cleanup fix.

### Clipped contour/motif cleanup

Contour and area-motif fills now use the same full-segment region constraint as
ripple fill during short-stitch cleanup. A proposed shortcut must remain inside
the even-odd region, including its holes. Outline motifs and compensated tatami
retain their distinct existing behavior; this constraint is applied only to the
three fill modes whose generated paths are clipped to the source region.

119 cleanup, contour, motif-fill and ripple tests pass. The additions include
synthetic narrow-cutout integration regressions for both fill modes and six real
generation cases checking full sewn-segment containment at three cleanup
thresholds. Existing export tests in these suites also pass. Frozen validation
and physical sewing of this cleanup change remain outstanding.

### Ripple physical-test preparation

The native coupon picker and CLI now include a six-sample ripple spacing/center
comparison in a 100 mm field, plus the existing scale marks. All 32 coupon tests
pass, including target/settings agreement and decoded export comparisons.
`artifacts/ripple-sewout/ripple-spacing/` contains the editable design, placement
and evaluation PDFs, blank material/results records, and PES v6/v1, EXP and DST.
The generated pack has 4,467 stitches, nine objects and bounds
[-45, -32, 40, 45] mm. All four exports pass software path/control checks.
No physical results have been entered; Brother/Bernina model-specific and actual
sewing validation remain pending.

### Native standard sewout pack export

File → Export standard sewout pack now offers every registered coupon, chooses
a parent folder and builds the existing complete pack without replacing the open
design or changing its saved state. Existing folders are refused. The completion
dialog surfaces unverified exports and includes individual verification details.
43 coupon/accessibility tests pass, including actual ripple pack creation,
preservation of existing physical-result files, and cancellation at either picker.
Generation currently runs synchronously; background progress/cancellation and
packaged/manual UI validation remain pending. This workflow does not mark any
coupon physically tested.

### Interrupted coupon export status

Coupon export writes an INCOMPLETE marker before generation and removes it only
after all pack artifacts are written. Native errors identify the destination and
say its files are incomplete. Unknown coupons are rejected before folder creation;
existing destinations remain protected. All 39 coupon tests pass, with injected
generation, machine-writing and PDF failures retaining the marker and completed
exports removing it. This is explicit incomplete-output status, not atomic folder
publication or a guarantee against arbitrary filesystem failure.

### Responsive standard-pack export

Native standard-pack export now runs through `--coupon-worker` in a separate
process with an indeterminate progress dialog, Cancel and a 60-second timeout.
Cancellation/window closing terminates the process before the operation returns;
startup errors, worker errors and timeout failures are reported. Output logs and
report reads are bounded. The open project remains unchanged; existing folders
remain protected and partial outputs retain the incomplete marker.

All 39 coupon tests pass. Six worker scenarios cover real export while a GUI
timer continues firing, Cancel, window close, timeout, failed startup and an
unknown coupon. Worker/accessibility checks pass together (14 tests). This
supersedes the synchronous native-export limitation above. Frozen worker dispatch
and Windows/macOS execution still require validation.

### Frozen standard-pack worker acceptance

The rebuilt Linux bundle passes **49 checks**. Its coupon worker exports a real
ripple pack while a GUI timer continues firing, retains all expected project/PDF/
metadata artifacts, removes the incomplete marker, and verifies all four machine
exports. The three source self-test tests also pass. The bundle now includes the
region-aware cleanup changes and native pack workflow. Generated worker artifacts
are retained under `artifacts/bundle-self-test/ripple-sewout-pack/`.
Windows/macOS execution, frozen cancellation/failure scenarios, physical sewing
and the remaining parity requirements are still open.

### SVG style-variable conversion

Added bounded token-level CSS custom-property substitution before SVG geometry
import and native rendering. Stylesheet/inline cascade, case-sensitive names,
computed-value inheritance, nested fallback values, function arguments and
initial/inherit/unset are supported. Cycles, unresolved variables and rollback
keywords fail explicitly; presentation-attribute variables and full invalid-value
CSS semantics remain unsupported. Limits are 32 nested levels, 16 KB per expanded
value and 2 MB accumulated expanded styles/environments.

44 SVG style tests and 166 SVG import/gradient/mask/render tests pass, including
red color fidelity in both import paths, inherited aliases, important precedence,
fallbacks and expansion limits. Semantics were checked against
https://www.w3.org/TR/css-variables-1/ . Packaged conversion and broader CSS
conformance remain open.

### Variable artwork through conversion and export

Two native conversion-worker scenarios (direct vector and rendered SVG) now verify
variable-based red/blue artwork with a cutout, immutable source files, editable
region geometry, saved-project stitch regeneration and all nine machine writers.
Rendered palette reduction shifts the red slightly; an equivalent literal-color
SVG produces exactly identical colors and contours, distinguishing that existing
quantization behavior from variable substitution. All 48 SVG style tests pass.

Variables in `<use>`-referenced subtrees now fail explicitly because definition-
context substitution could bake incorrect colors into instances. Tests cover
symbol and group references with conflicting per-instance colors. Proper instance
custom-property resolution, full CSS invalid-value behavior and packaged variable
conversion remain pending.

### SVG presentation-paint variables

Paint presentation attributes now resolve custom properties and fallbacks using
the element's cascaded environment. Attributes are updated only after all selector
matching, so selectors can still match the original source attribute value. Style
paint declarations override presentation attributes, including unresolved ones.
Variable detection is token-based and recognizes escaped CSS function names.
Empty custom properties no longer silently disappear and inherit a parent color;
unsupported empty resolved paints/properties produce an explicit import error.
Expanded attributes count toward the existing total style-size limit.

141 style/gradient/render tests pass; after extending attribute size accounting,
107 style/import tests pass. Coverage includes both import paths, fallback without
any stylesheet, selector preservation, overriding an unresolved attribute and
reused-element rejection. This supersedes the earlier limitation on presentation-
paint variables; variables in reusable instances remain unsupported.

### Packaged SVG variable acceptance

The rebuilt frozen Linux application passes **50 checks**, including variable
paint attributes, inherited custom properties and nested fallbacks through both
direct-vector and rendered conversion workers. The scenario checks two editable
color regions, a retained cutout, saved-project stitch fidelity, and full decoded
PES/EXP path/bounds comparisons. The three source self-test tests pass as well.
Variable sources, editable projects and exports are retained under
`artifacts/bundle-self-test/variables*`. Windows/macOS execution, reused-element
variable semantics and the remaining parity/physical acceptance gates stay open.

### SVG variable opacity and stroke presentation

Extended presentation-attribute substitution beyond colors to opacity controls,
stroke width/caps/joins/dashes, fill/clip rules, local clipping/masking references,
display/visibility, paint order and color interpolation. Normalization remains
color-specific and mutations still follow selector matching.

98 SVG style/stroke tests pass. Variable gradient-stop, group and fill opacity
produce an image identical to literal values; variable stroke width, round caps
and dash spacing produce identical expanded editable contours. A fallback-only
opacity attribute works without any stylesheet. Existing resolved-feature limits
remain in force; this does not add unsupported filters or external resources.
The frozen bundle predates this attribute extension.

### SVG missing-dependency fallbacks

Custom properties whose dependencies are missing now retain an invalid computed
value so a consuming `var()` can use its fallback. Unused invalid definitions no
longer block otherwise valid artwork. Invalid inherited aliases remain invalid
when a child introduces a formerly missing dependency; they are not incorrectly
recomputed in the child's context. A consumed missing value without a fallback
still fails explicitly. Cycles and unsupported rollback semantics remain errors.
All 63 SVG style tests pass, including fallback color fidelity in native rendering
and editable vector import. Packaged validation of this refinement remains open.

### Full regression after SVG variables and coupon worker

The complete source suite passes **2,636 tests in 217.53 seconds**, with Qt
offscreen in the Morale conda environment. No code changed during the run. This
covers the current SVG variable/presentation/fallback implementation, cancellable
coupon worker, region-aware cleanup and the existing editor/conversion/export
regressions. The frozen Linux bundle remains the 50-check build preceding the
latest non-color presentation and missing-dependency fallback refinements.
Physical, external-file, Windows/macOS and remaining parity gates remain open.

### Dependency license collection in development bundles

Corrected the stale MIT label in THIRD_PARTY_NOTICES to match Morale's existing
GPL-3.0-or-later metadata and LICENSE. Builds now collect available installed
package license texts into `dependency-licenses/`, recording versions, original
metadata paths, SHA-256 hashes and explicit gaps. A focused test verifies exact
bytes, versions, missing-text reporting and existing-output protection.

The rebuilt Linux bundle passes its 50 checks; all six collected license files
were independently read from the bundle and matched to their manifest hashes.
This environment lacks metadata-provided license files for PySide6, Shiboken and
VTracer; split PySide6 distribution metadata is absent in this conda installation.
Python/Qt/native-library notices and source/relinking provisions still require
review. The manifest explicitly does not claim release compliance. The rebuild
also includes the latest SVG attribute/fallback implementation.

### Conda package-cache license collection

The collector now also reads the active environment's conda records for Python,
PySide6 and qt6-main and copies their retained upstream `info/licenses` texts.
Each record includes version/build, the conda-declared license expression and
cache provenance; missing caches stay explicit. Two collector tests pass,
covering exact copying, missing metadata/texts, existing-output protection and
conda provenance. The local audit collected three additional texts (Python,
PySide6 and Qt), retained in `artifacts/dependency-license-conda-audit/`.
This will be included by subsequent builds; the prior bundle contains only the
six wheel-metadata texts. VTracer and comprehensive native-library/source review
remain outstanding; copied primary licenses do not prove release compliance.

### Bundle notice-integrity gate

Bundle checking now compares Morale's LICENSE/notices against build sources,
verifies collected dependency texts against manifest hashes, rejects manifest
paths outside the notice directory, and verifies every bundled font license
against its source file. The collector/checker tests pass (seven cases), including
changed/missing texts and an escaping path. The rebuilt Linux bundle passes all
50 application checks plus this separate gate: nine dependency license texts and
122 font licenses verified. `artifacts/bundle-self-test/notice-integrity.json`
retains the result and unresolved metadata gaps. This verifies file integrity,
not complete dependency coverage or release compliance. Windows/macOS path/layout
execution still needs verification.

### Current native getting-started guide

Replaced the fixed message box with a scrollable, keyboard-selectable native guide.
It now explains keyboard drawing, artwork conversion/review, bundled embroidery
fonts, ripple/fabric controls and background sewout packs; removed the stale claim
that purpose-digitized fonts are still unavailable. Nine accessibility tests pass,
including opening the guide from the main window and 18-point text at 500×400:
content scrolls, keyboard navigation reaches the end and Escape closes it.
Screen-reader and packaged help-dialog verification remain open.

### Visible keyboard drawing cursor

Keyboard drawing now pans the canvas as necessary to keep its cursor inside a
40-pixel viewport margin; Home also brings the origin back into view. Draft points
remain in world coordinates and are not moved by panning. Grid movement now clamps
to the last supported grid point within ±1,000 mm after snapping, fixing cases
such as a 3 mm grid rounding a clamped coordinate beyond the editable range.
All 21 keyboard-drawing/accessibility tests pass, including panning at high zoom,
retained draft coordinates, Home visibility and positive/negative grid limits.
Packaged and manual screen-reader testing remain outstanding.

### Keyboard-accessible tool selection

A Tools menu now exposes the same exclusive actions as the drawing toolbar with
menu accelerators. Choosing a mode assigns keyboard focus to the canvas, and the
getting-started guide explains the route. All 22 keyboard/accessibility tests
pass, including native menu Enter activation followed by keyboard rectangle
creation and Undo. The test checks the window's focus target and explicitly
restores window activation because Qt offscreen leaves a hidden popup active;
actual window-manager activation and platform-specific menu access remain manual
verification work.

### Drawing shortcut isolation

Drawing cursor/placement handling now leaves Ctrl- and Command-modified keys to
normal shortcut processing. These combinations cannot silently remove a draft
point, add a point, return its cursor to the origin or pan it. Shift/Alt arrow
precision controls remain available. All 30 keyboard/accessibility tests pass,
including unchanged draft/cursor/view state for eight modified-key combinations.
Native operating-system shortcut delivery remains part of manual platform checks.

### Modified nudge/completion isolation

Ctrl/Command arrows no longer nudge selected objects, and Ctrl/Command Enter no
longer commits a drawing draft. Ordinary arrows and Enter retain their existing
behavior. All 32 keyboard/accessibility tests pass, including preservation of
an unfinished path and absence of movement signals for modified arrows.
Native platform shortcut delivery remains unverified.

### Build source fingerprint

Development bundles now embed a SHA-256 manifest of application code, assets,
fonts, build scripts and top-level package documents. Newly added/uncommitted
source files participate; user designs and bytecode caches do not. Bundle checking
compares the embedded manifest with current inputs before running self-tests and
retains it beside the report. Two tests cover changes/new files, cache/design
exclusion and symlink rejection. The rebuilt Linux app passes all 50 checks and
the notice gate, with 377 fingerprinted input files and source digest
`ab11ee7692abb1f15aee20fb6dad78fb5b1eeaa79bb9e50619c18e551da94d49`.
This is source identification, not a source archive, complete dependency lock or
proof of reproducible binary output. The build also includes the latest help and
keyboard changes; their full manual platform behavior remains unverified.

### Persistent layout guides

View → Layout guides now edits horizontal/vertical design-space guides in
millimeters. Guides render as purple dashed lines across the viewport and survive
project save/reopen, Undo and Redo. Older projects default to no guides. Validation
bounds them to 100 entries within ±1,000 mm; guides generate no sewing commands.
The initial editor accepts one `x position` or `y position` per line. Input errors
and cancellation preserve the project; existing numeric precision is retained.

28 guide/save/accessibility tests pass, followed by all nine guide tests after
input-validation/precision refinements. Guide snapping, direct ruler dragging,
visibility controls and packaged validation remain pending.

### Guide visibility and snapping

View now toggles layout-guide visibility and snapping independently. Visible
guides attract mouse drawing/edit points and dragged object centers within eight
screen pixels, with guide coordinates taking priority over the grid. Existing
object-edge/center snapping takes precedence when it also matches. Hidden guides
do not attract points. Keyboard cursor steps bypass magnetic guide snapping so
arrows can leave a nearby guide rather than becoming stuck.

All 43 guide/keyboard/accessibility tests pass, including zoom-dependent tolerance,
grid precedence, hidden-guide behavior, object-center snapping without the grid
and keyboard movement away from a guide. Guide-edge/group-bound snapping,
direct ruler dragging and packaged validation remain open.

### Selection-bound snapping to layout guides

Layout guides now snap a dragged selection's outer edges and center, using the
union of visible selected-object bounds. All members receive the same translation.
Grid snapping remains the baseline, guides override matching axes, and enabled
object snapping takes precedence only on axes where it finds a match. Matched
coordinates use the existing snap indicators. Hidden guides do not attract.
All 23 guide/object-snapping tests pass, including group-edge placement and mixed
object/guide precedence on separate axes. Direct ruler dragging, manual platform
interaction and packaged verification remain pending.

### Ruler guide creation

Dragging from the left or top ruler previews a vertical or horizontal layout guide. Releasing inside the canvas commits it through project history; Escape or releasing over a ruler cancels. Guides persist in the project and support Undo/Redo. Offscreen native-widget checks cover both axes, preview painting without committing, cancellation, snapping, and save validation: 68 tests passed across guides, keyboard drawing, accessibility, object snapping, and save validation. This change has not yet been rebuilt into the frozen bundle or tested on Windows/macOS.

### Integrated guide and bundle verification

The full source suite passed 2,676 tests in 215.09 seconds after persistent guides and ruler dragging were added. A subsequent native self-test extension verifies both ruler axes, draft painting, guide save/reopen, unchanged generated stitches, Undo/Redo and Escape cancellation. The self-test and accessibility tests then passed together (12 tests). The rebuilt Linux bundle passed all 51 application checks, including the new guide workflow, plus source-manifest and notice-integrity checks. Evidence is in `artifacts/bundle-self-test/report.json`; its `physical_sewouts` and `external_files` fields remain false. Windows/macOS execution and complete release licensing remain open.

### Fine fill-angle travel search

The optional conversion angle search now follows coarse candidates with six nearby directions at five-degree intervals, within the same global work limits. A triangular region at 32 × 21 mm demonstrates generated jump travel decreasing from 49.69 mm after coarse search to 48.63 mm after refinement, without changing artwork geometry. The 31 angle tests pass, covering partial budgets, locked regions, neighbor transfers, underlay, native conversion and nine export writers. This does not establish better physical fill appearance; the Linux bundle predates this refinement.

### Expanded conversion angle benchmark

The generated artwork corpus now has 15 cases and 135 format exports. Broad fill, adjacent colors, holed fill and a new triangular region exercise angle optimization. All artwork and decoded sewn-path gates pass in `artifacts/angle-refinement-benchmark/report.json`, with a visual review PDF beside it. A dedicated injected-regression test proves increased reported angle travel fails the overall benchmark. The six benchmark tests passed (five corpus/report tests plus the new gate test). This is synthetic software evidence, not external-file or physical validation.

### Angle-search review and refreshed Linux bundle

Conversion review now distinguishes evaluation-limit stops from generated-command-limit stops and reports evaluated and rejected candidates. Older reports without the new reason field use a generic work-limit explanation. Angle, quality and conversion-report tests pass (50 tests). The Linux bundle was rebuilt with fine angle refinement and these diagnostics; all 51 application self-checks plus source/notice integrity checks pass. This supersedes the earlier note that the bundle predates refinement. Physical, external-file, Windows/macOS and release-license gates remain open.

### Global source-rail satin overlap validation

Strict satin generation now rejects positive-area overlap between nonadjacent convex source rail cells. Bounding-box pruning precedes separating-axis tests; shared edges, closed seams and tapered tips remain permitted. Tests cover looping columns, translation/rotation/mirroring, and the existing lettering opt-out. Related geometry, automatic-digitizing and lettering runs passed (50 tests initially; 146 in the expanded geometry/appliqué/branch suites), followed by all six benchmark tests, including the 15-case/135-export corpus. This checks source rails before pull compensation, not compensated stitch overlap or fabric behavior. Purpose-digitized lettering retains its existing non-strict path. The frozen bundle predates this change.

### Satin editor rejection and export regression coverage

A native main-window test now proves that an overlapping rail edit is rejected before commit, preserving project data, history and an existing Redo operation. A valid closed satin seam is exercised through all nine export writers with complete path comparison and bounds checks. Eight have no verification problems for this fixture; VP3 adds one trim, and the test explicitly requires that warning rather than classifying it as a clean control match. The satin geometry and export-verifier suites pass together (48 tests). No physical sewout is implied.

### Integrated satin and angle-search regression run

The full source suite passes 2,699 tests in 230.17 seconds, including global source-rail satin overlap validation, rejected-edit history preservation and refined conversion angle search. The rebuilt Linux bundle passes all 51 application checks and its source/notice integrity gates. This supersedes earlier notes that the bundle predates satin overlap validation. Windows/macOS execution, complete release licensing, external-file validation and physical sewouts remain open; this run does not close those gates.

### Browse all designs recursively

The native library now accepts a blank query for Search subfolders, listing all supported design filenames under the chosen folder for thumbnail browsing and catalog selection. Nonempty queries still filter relative paths. Existing result/entry limits, process cancellation, hidden-file and symlink exclusions remain in place; searching does not decode file contents. Search, thumbnail and catalog suites pass together (36 tests), including native blank-query worker integration and bounded empty/whitespace queries. Persistent metadata indexing remains pending. The frozen bundle predates this change.

### Recursive search query invalidation

Editing the library query while viewing recursive results now cancels the current search and thumbnail/selected-preview work, clears the old results, and asks the user to run the new search. Late results with a different query are ignored. Native tests cover edits during a live worker, late-result rejection, completed-result invalidation and a subsequent blank search. The library/search/thumbnail/catalog suites pass together (54 tests). The frozen bundle predates this change.

### Keyboard library search and result activation

Enter in the search field now runs recursive search, including blank queries. Automatic default-button activation is disabled in this dialog to avoid unrelated actions. Enter on a selected, previewed result opens that design through the existing validated open path; mouse activation remains available. The search field has an accessible description explaining the action. Native key-event tests and library/accessibility suites pass together (41 tests). Screen-reader runtime validation remains open.

### Packaged library workflow verification

The native self-test now sends Enter to an empty library search field, verifies recursive results include saved and converted projects, and confirms query changes clear results and reject stale responses without opening a design. Source self-test tests pass (3 tests). The rebuilt Linux application passes all 52 packaged checks plus source/notice integrity gates. Earlier notes that the bundle predates library improvements are superseded. Windows/macOS and screen-reader execution remain unverified.

### Satin overlap sweep orientation

Global source-cell overlap checking now sweeps the longer bounding-box axis. This avoids retaining every cell of a narrow vertical column in the active comparison list. Both horizontal and vertical 1,000-pair columns (the project point limit) generate successfully; the geometry/digitizing suites pass together (50 tests). A local ten-run average for the 1,000-pair vertical fixture was 0.06402 s with the previous fixed-X sweep versus 0.00145 s with adaptive orientation. These are local microbenchmark measurements, not cross-platform timing guarantees. The geometric separating-axis test is unchanged.

### Lock a displayed conversion fill direction

Conversion review now offers Lock selected fill angle, preserving the current displayed direction without requiring a value change. The native dialog/worker integration test confirms the exact value survives automatic angle search. Stitch-settings and accessibility suites pass (62 tests). No-selection and unavailable-angle cases retain settings and explain the required selection. The bundle predates this change.

### Release one conversion angle lock

Lock/unlock controls now sit together in conversion review. Unlock selected fill angle removes only the chosen region’s angle override and invalidates its preview, preserving spacing, stitch choices, seam corrections and neighboring angle locks. No-selection and repeated-unlock cases leave settings intact. Stitch-settings and accessibility suites pass together (63 tests). The packaged bundle predates both selected-angle actions.

### Bundle refresh after selected-angle controls

The Linux application was rebuilt with selected-region angle lock/unlock actions and adaptive satin overlap sweep orientation. All 52 existing packaged checks pass, alongside source-manifest and notice-integrity verification. Dedicated source tests cover the new angle actions (63 stitch-settings/accessibility tests) and long satin columns (50 geometry/digitizing tests); the bundled self-test does not separately invoke the new angle buttons. Earlier bundle-staleness notes for these changes are superseded. This remains a development bundle; platform, licensing and physical-validation gaps remain open.

### Visible conversion angle-lock state

Region angle controls now display a locked suffix and an accessible description when their direction is protected from automatic search. Locking, unlocking, numeric edits and preview regeneration refresh the state. Native worker/dialog integration verifies the label survives regeneration and clears on unlock; stitch-settings/accessibility suites pass (63 tests). This is accessible metadata coverage, not screen-reader runtime validation. The bundle predates this presentation change.

### Collected notice manifest completeness gate

Bundle notice verification now compares the packaged dependency manifest with `build/dependency-licenses/manifest.json` before checking individual file hashes. Omitted package/file records, changed metadata and missing manifests can no longer pass by shrinking the verification list. This requires the collection manifest from the same build to remain available. Thirteen license/source-manifest tests pass; the existing Linux bundle also passes this stronger notice check with 9 collected dependency texts and 122 font licenses. Collection/compliance gaps remain explicitly unresolved.

### Workspace PES compatibility probe

The pre-existing `design.pes` (26,375 bytes; SHA-256 `420aceb699bde0024464d8aae516c4a68cf9774c85e84972fb4d1c207a1b1533`) was read without modification. Provenance is unknown, so this is not a confirmed manufacturer-authored fixture or machine validation. Import produced four objects, 2,233 stitches, 370 jumps and 366 trims. All nine exports completed sampled path comparison but all flagged trim-count differences. PES/EXP/DST/JEF/PEC/U01/XXX lose three explicit trims at the previous objects’ final positions; VP3 loses the same three and adds a final trim; TBF adds trims at the three object boundaries. Reports and converted files are in `artifacts/workspace-pes-compatibility/`, including `trim-differences.json`. These control differences remain review findings, not passing command equivalence.

### Thread-boundary trim loss diagnosis

Inspection of the installed shared encoder shows that color changes set its trimmed state; a subsequent explicit trim before sewing resumes can be omitted. A minimal two-color manual-stitch fixture reproduces this loss in PES, EXP, DST, JEF, PEC, U01 and XXX. Export verification now adds boundary-specific context when trim loss coincides with these source commands, retaining the failed verification result and the original command order. All 38 export-verifier tests pass. This explains the workspace PES observation without declaring implicit cutting equivalent to explicit trims; machine behavior remains unverified.

### Preserve explicit PES/PEC boundary trims

The existing PES/PEC normalizer now retains explicit source trims even when encoder state was already marked trimmed by a preceding color change. Commands remain after the color change and before sewing resumes; no artificial needle penetration is inserted. Sixty export-verifier/writer tests pass, including ordering and unchanged stitch-count checks. Re-exporting the untouched workspace PES as PES v6, PES v1 and PEC now passes all software verification checks, with no trim loss (`artifacts/pes-explicit-trim-preservation/report.json`). Other writer boundary differences remain open, as does physical validation. The bundle predates this encoder change.

### EXP explicit trim preservation

A shared per-pattern normalizer now preserves explicit source trims for EXP as well as PES/PEC, without patching installed modules or moving controls across thread changes. PES/PEC retain their existing pause-state handling. The minimal boundary fixture confirms trim placement before resumed sewing and identical stitch counts. The untouched workspace PES exported to EXP passes software verification with all 2,233 stitches (`artifacts/exp-explicit-trim-preservation/report.json`). Export-verifier/writer suites pass (60 tests), followed by formats/sewout-pack/coupon suites (157 tests). Other writers’ control differences and physical Bernina/Brother validation remain open. The bundle predates these trim fixes.

### JEF/U01/XXX explicit boundary trims

Explicit-trim normalization now also applies to JEF, U01 and XXX. The minimal two-color fixture verifies placement after the thread change, before resumed sewing, with unchanged stitch counts. The unchanged workspace PES passes all software export-verification checks in these three formats (`artifacts/additional-explicit-trim-preservation/report.json`). Format and export-verifier suites pass (146 tests). Applying the same wrapper to DST did not preserve the trim through decoding; that attempted change was removed, and DST remains explicitly reported as a loss. VP3/TBF differences and physical-machine behavior remain unresolved. The bundle predates the writer changes.

### DST boundary trim sequence preservation

DST export now retains explicit trims through normalization. Import first recognizes the writer’s exact (+2,+2), (-4,-4), (+2,+2) encoder-unit jump sequence as a trim, before applying the existing three-jump inference to other travel. This preserves the sequence immediately after a color change, where upstream inference otherwise suppresses it. Exact-signature tests reject near-matches; 146 format/export tests and four signature tests pass. The workspace PES exported to DST now passes software verification (`artifacts/dst-explicit-trim-preservation/report.json`). DST still has no dedicated trim opcode: this is a recognized convention, not proof of cutting on a machine. The bundle predates this change.

### Integrated explicit-trim regression run

All 2,724 source tests pass in 236.44 seconds after the PES/PEC/EXP/JEF/U01/XXX/DST explicit-trim changes and DST sequence recognition. The rebuilt Linux app passes all 52 existing packaged checks and source/notice integrity verification. It includes the shared writer normalizer, angle-lock labels and stronger license-manifest comparison. Dedicated boundary-order tests remain source tests, not separate packaged self-test entries. VP3/TBF control differences, physical machine execution, Windows/macOS validation, remaining parity and licensing work remain open.

### Avoid unintended TBF cuts from stationary jumps

TBF preparation now omits jumps whose quantized displacement is zero, because its reader interprets that opcode as a trim. Explicit source trim records and nonzero travel remain in the prepared pattern. A manual-stitch regression proves idle jumps no longer add cuts and stitch count is unchanged. Format/export suites pass (151 tests); the final quantization adjustment was separately rechecked with the targeted regression. The workspace PES now passes software TBF verification (`artifacts/tbf-stationary-jumps/report.json`). TBF still uses upstream needle-change normalization, which may place a trim before the needle change; passing count/position verification is not proof of exact control ordering or physical execution. The bundle predates this change.

### Thread-relative control ordering gate

Export verification now compares the interleaved thread-change/stop/trim sequence when their counts match. This catches a trim moved across a thread change even when its count and position remain unchanged. A real TBF round-trip regression demonstrates the mismatch; format/verifier suites pass (152 tests). Rechecking the workspace TBF now correctly produces a review finding (`artifacts/tbf-stationary-jumps/order-aware-report.json`), superseding its earlier weaker verification pass. The stationary-jump fix remains valid, but TBF boundary ordering remains unresolved. The bundle predates this stronger verifier.

### VP3 explicit boundary trim preservation

VP3 now uses the explicit-trim normalizer, preserving a source trim after a thread change instead of discarding it. The minimal fixture verifies placement before resumed sewing. The workspace PES retains all 366 source trims in VP3, with the writer’s additional terminal trim still flagged (367 decoded); see `artifacts/vp3-explicit-trim-preservation/report.json`. All 63 export-verifier/writer tests pass. This resolves the observed missing boundary trims without hiding the remaining extra control or asserting exact command equivalence. The bundle predates this change.

### Packaged boundary-trim compatibility gate

The rebuilt Linux bundle passes 53 application checks, including a new nine-writer two-color boundary-trim fixture. Seven formats must preserve thread-relative trim order and stitch count; VP3’s extra trim and TBF’s control-order mismatch must be reported. Per-format results are retained at `artifacts/bundle-self-test/boundary-trims/verification.json`. Source self-test tests also pass (3 tests), and bundle source/notice integrity checks pass. Earlier bundle-staleness notes for writer/control-order changes are superseded. Passing this gate includes accurate reporting of known differences; it does not mean all nine formats have identical controls or verified machine behavior.

### Export review scope presentation

Successful export review now states when the stop/trim sequence relative to thread changes is unchanged. The statement requires an explicit positive result; legacy reports without that field do not receive it. The existing limitation on full stitch order, thread identity and physical-machine verification remains visible. Export-verifier, batch and sewout-pack suites pass together (72 tests). The bundle predates this text update.

### Format notes reconciled with current adapters

Export notes no longer describe the upstream VP3 omission of jumps or the removed synthetic PES/PEC jump-landing stitch as current Morale behavior. They explain Morale’s long-form VP3 travel, explicit trim preservation, remaining terminal VP3 trim, DST jump-based trim convention and TBF needle-change ordering caveat. Format, writer and verifier suites pass together (176 tests). These notes accompany software comparison results and do not establish machine compatibility.

### Workspace-file nine-by-nine conversion matrix

The unchanged workspace PES was exported to each of nine formats, then each intermediate was imported and exported to all nine writers. All 81 conversions completed bidirectional sampled path comparison without decode/export exceptions. Against each intermediate, 62 passed all checks; against the original, 47 passed. Findings were trim additions or thread-relative trim reordering, including three added trims on PES→JEF and PEC→JEF. The distinction prevents a clean second conversion from hiding changes already introduced by its intermediate. Full per-step and end-to-end results are in `artifacts/workspace-pes-conversion-matrix/report.json`. The source fingerprint remains recorded; provenance and physical behavior are unknown. These results identify remaining controls work rather than establishing universal compatibility.

### Prevent trim multiplication in PES/PEC-to-JEF conversion

JEF preparation now omits quantized no-motion jumps, as TBF preparation already does. This prevents idle records around a source trim from joining JEF’s stationary-jump trim sequence and creating another cut on decode. Explicit trims and nonzero travel remain. Both minimal PES→JEF and PEC→JEF chain regressions pass with unchanged source data and thread-relative trim order; format/verifier suites pass (156 tests). Rechecking the two workspace-file chains preserves all 366 trims with no verification problems (`artifacts/jef-stationary-jumps/report.json`). The prior 81-pair matrix is historical and has not been rerun in full. The bundle predates this fix.

### Reproducible supplied-file conversion matrix

Run `python -m morale.file_matrix SOURCE --output NEW_DIRECTORY` to preserve first exports and every two-step conversion, with checks against both the intermediate and original. The command refuses existing output directories, fingerprints the source before/after, retains an incomplete marker on interrupted runs, and exits nonzero when any original-file comparison requires review. Two tests cover source preservation, output collision and failed intermediate propagation. The workspace PES rerun (`artifacts/workspace-pes-matrix-current/report.json`) completes all 81 paths without exceptions: 64 intermediate comparisons and 49 original comparisons pass, improving from 62/47 after the JEF fix. Known VP3/TBF controls differences remain review findings; a nonzero exit for this report is expected. Provenance and physical validation remain unverified.

### Conversion matrix spreadsheet review

Supplied-file matrix runs now write `review.csv` beside the detailed JSON. Each row separates verification against the intermediate from verification against the original, retains exact findings/errors and labels physical validation unverified. Existing output is never overwritten, and formula-like error strings are escaped for spreadsheet display. Three matrix tests pass, including inherited-loss presentation and CSV quoting. The current 81-pair workspace report has a review sheet generated from its existing evidence; the conversion run itself was not repeated for this presentation change.

### Preserve line details during hole cleanup

Small-hole filling now also protects voids intersected by visible running or triple-running artwork. A microscopic geometric stroke tests the line itself, so an outline surrounding an otherwise empty hole does not protect its interior accidentally. Hidden and distant lines do not prevent cleanup. Detail/hole suites pass (49 tests), covering both stitch types, source preservation and the surrounding-outline case. This protects source centerlines, not modeled thread thickness or physical coverage. The bundle predates this change.

### SVG line-detail cleanup integration

The SVG worker is now tested with identical 10 mm artwork with and without a running line inside a 4 mm² hole. Cleanup fills the empty hole but preserves the occupied hole and running object; the quality report explains retention. Project reload regenerates identical stitches, and PES/EXP exports pass full available verification in both cases. Hole-filter and quality suites pass together (37 tests). This establishes pipeline integration, not physical thread coverage. The bundle predates the line-detail protection.

### Integrated conversion cleanup and compatibility validation

The complete suite passes 2,742 tests in 238.07 seconds. The rebuilt Linux application passes all 53 packaged checks and source/notice integrity gates with the latest JEF stationary-jump fix, thread-relative control reporting, format notes, and line-detail hole protection. The supplied-file matrix utility has dedicated source tests; it is a development command, not a native menu feature. Prior bundle-staleness notes for these changes are superseded. Remaining feature parity, Windows/macOS execution, complete release licensing and physical sewouts are still open.

### Persistent design notes

Design → Design notes opens a native multiline editor for fabric, stabilizer, thread and adjustment notes. Notes are saved in `.morale` projects with a 10,000-character limit; older projects default to empty notes. Edits participate in Undo/Redo and cancellation preserves the project. Notes do not change generated stitches. Project-note, save-validation and accessibility suites pass together (26 tests). Notes are not yet included in worksheet PDFs or indexed by the library. The bundle predates this feature.

### Design notes on sewout worksheets

The current-design sewout worksheet now includes saved design notes, preserving line breaks and escaping markup. Notes use the existing paginated introduction before sample targets and blank observation fields. A Qt PDF extraction test confirms all 102 lines survive a multipage worksheet, including literal markup characters, without changing the project. Project-note/coupon suites pass (47 tests). Library note indexing remains pending; the bundle predates project notes and worksheet inclusion.

### Saved design notes in library previews

The library preview worker includes saved project notes. A read-only plain-text pane displays them before opening a design, preserves literal markup and clears when the preview is cancelled or selection changes. Empty notes remain hidden; preview metadata rejects invalid or oversized notes. Library, thumbnail, accessibility and project-note tests pass together (39 tests). Notes are viewable but not yet searchable through a metadata index. The packaged application predates this addition.

### Integrated project-note validation and refreshed Linux build

The complete source suite passes 2,751 tests in 233.15 seconds. The rebuilt Linux application passes all 53 packaged checks plus source and notice integrity verification. A separate invocation of the frozen preview worker preserves multiline project notes and literal markup without modifying its source project (`artifacts/bundled-project-notes/report.json`). The worker requires a pre-existing output directory, as provided by the native preview runner. The build now includes project notes, worksheet inclusion and library previews, superseding their earlier bundle-staleness notes. These checks do not establish Windows/macOS execution, physical sewouts or complete release licensing; dependency metadata gaps remain recorded in `artifacts/bundle-self-test/notice-integrity.json`.

### Validate satin geometry after pull compensation

Strict satin generation now shares local-fold and global-overlap validation between source rail cells and the expanded sampled rails. Excessive compensation on a tight curved column is rejected with actionable guidance; source points remain unchanged. Rotated/mirrored cases, modest compensation, closed seams and tapered tips pass. The existing lettering opt-out is preserved. Satin geometry tests pass (32), including compensated closed-band exports through all nine writers with complete path comparison and the existing VP3 terminal-trim finding. Compensation/underlay checks and curved-column, applique, lettering and image benchmark suites also pass (73 and 63 tests respectively; the 73-test run predates the nine additional compensated export cases). This is geometric rejection, not automatic acute-corner reconstruction or physical validation. The packaged build predates this change.

### Conversion selection checks requested stitch settings

The artwork worker now supplies conversion stitch settings when evaluating candidate columns. Invalid configured columns retain the original fill geometry with the generation error in the per-region explanation, rather than failing later after selection. Settings remain unchanged and are subsequently applied to the fallback fill. Real SVG-worker regressions cover automatic selection and explicit satin overrides: a small closed band selects satin without compensation, retains fill when compensation folds its rails, reloads successfully and passes PES/EXP export verification without changing the artwork file. Stitch-setting, curved-column and auto-digitizing suites pass together (112 tests). The packaged application predates this integration.

### Surface column fallbacks in conversion review

Stitch decisions now carry an explicit fallback flag for rejected candidates and unavailable satin/running overrides. Ordinary automatic fill choices and retained SVG outlines are not flagged. The native preview summarizes the number of fallback regions; selecting a region exposes the detailed reason. Saved conversion reviews label flagged decisions with their requested choice. Native regressions exercise compensation-driven fallback for automatic and explicit satin selection. Stitch-setting, auto-digitizing and conversion-report suites pass together (98 tests). The packaged application predates this presentation change.

### Refine inter-region travel beyond nearest neighbor

Travel planning now compares the original and greedy orders with bounded adjacent-swap refinements (four passes per order, 2,048 evaluations total). Swaps preserve semantic barriers, thread runs and overlapping layer order; acceptance measures the full route, including travel to subsequent regions. Direction optimization considers all four candidates. A five-region regression improves nearest-neighbor travel from 129.40 mm to 118.72 mm, preserving source data and every per-object stitch block; reported distance is checked against regenerated endpoints. Routing, direction, thread-planning and image benchmark suites pass together (62 tests). This is local optimization, not continuous branch routing or a global optimum. The packaged build predates this change.

### Packaged conversion and routing refresh

The rebuilt Linux application passes all 53 packaged checks and source/notice integrity gates. Additional invocations of its frozen SVG worker exercise the new behavior directly: a small closed band selects satin with zero compensation, falls back to fill with an explicit reason at 1.5 mm compensation, and a five-region artwork route improves from 187.47 mm to 118.72 mm with 16 refinement evaluations. Inputs, previews and results are retained under `artifacts/bundled-conversion-refinement/`. This supersedes bundle-staleness notes for satin compensation validation, configured candidate selection, fallback presentation and travel refinement. The last complete source-suite result remains 2,751 tests from before these changes; subsequent focused results are recorded above. Windows/macOS execution, physical sewing and complete release licensing remain unverified.

### Search saved project notes from the native library

The library accepts `notes: linen` (case-insensitive) to find text in saved `.morale` design notes recursively. Ordinary queries remain filename/path searches. Note searches use the existing cancellable subprocess, skip non-native machine files, count malformed metadata as unreadable, and stop with an incomplete-search result when their total 64 MB read budget is exhausted (one extra byte detects exhaustion). Empty note queries report an error. The native placeholder and accessible description explain the syntax. Tests cover content-only matching, legacy files, malformed JSON, budget exhaustion and a real native worker result without source modification. Library search, preview and accessibility suites pass together (45 tests). This is bounded on-demand search, not a persistent metadata index; the packaged build predates this feature.

### Keep note searches useful around oversized projects

Saved-note search now skips individual projects larger than 20 MB, counts them as unreadable and continues to smaller files. A bounded read also handles files that grow after the size check. Total read-budget exhaustion is distinguished from entry/result limits and tells users to choose a smaller folder; narrowing the text alone would not reduce metadata reads. Search limits reject nonpositive or noninteger values. Library/search suites pass (41 tests), including sparse oversized files, exact read accounting, invalid limits and native limit messaging. The packaged build predates note search and these refinements.
