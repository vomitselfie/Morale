# Image digitizing

Image-to-embroidery quality is the current priority within the full feature-parity
program. The native desktop application remains the product on all platforms.

## Implemented

PNG/JPEG/BMP/WebP artwork can be converted through smooth shared-boundary color
tracing. The native dialog compares sampled source, fitted vectors and generated
stitches before adding editable objects with Undo. It can embed the sampled
sRGB artwork as an aligned reference image in the native project. This is enabled
by default when no reference exists; replacing an existing reference requires
selecting the explicitly labeled option. Source padding and original physical
aspect ratio are retained even when sampling rounds the pixel dimensions. The
reference survives moving/deleting the external source file, is editable through
the existing reference controls and contributes no machine stitches. Objects and
reference are applied/undone together. The embedded image is the sampled guide,
not an archival copy of the full-resolution original. SVG export retains fitted
curves, physical units and source padding. Native embroidery fill objects use
flattened contours, including holes; they do not yet retain compound Bezier handles.
The preview now defaults to automatic stitch selection, with an all-fill option
and per-region automatic/fill/satin/running overrides. Each result includes a
reason. Changing a choice requires a fresh worker preview before applying it.

The initial planner slices an unbranched region along its principal axis. Columns
below 0.8 mm maximum width become centerline running stitches; columns up to
6 mm become paired-rail satin when at least twice as long as their maximum width.
These are current software heuristics, not fabric/thread recommendations. Wider,
compact regions remain fill. Branched regions remain fill unless the optional
branch-splitting pass can partition them into useful columns. Eligible closed bands with one inner
contour can become satin or a closed running path; multiple holes remain fill. Open curved ribbons can also
use a boundary-chain planner when the principal-axis method cannot fit them.
It identifies candidate end caps, samples both sides by relative arc length,
and checks the resulting rail cells and reconstruction. Cap detection is bounded
to twelve candidates; rounded, ambiguous or complex ends can still require
manual digitizing. A 0.005 mm contour simplification consolidates tiny flattened
segments before cap detection; the final area check uses the original contour. Requested satin/running
overrides also require an eligible column; otherwise the preview explains why
fill was retained. Running stitches replace the original filled width.

Rail reconstruction is checked against source area before generation, and satin
rail cells must pass the existing engine validation. End stations are inset by
at most 0.0001 mm to avoid ambiguous vertex intersections. Geometry differences
above the greater of 1% area or 0.02 square millimeters reject the conversion.
Automatic columns retain editable points, original color and object identity.

Closed-band fitting normalizes contour winding, checks nesting, chooses a shared
seam and samples the two loops by relative arc length. The last rail pair exactly
repeats the first. The fitter tries contour simplification at 0.005, 0.02, 0.05
and 0.1 mm to remove small notches that prevent valid rail cells, accepting the
first result that passes the same original-area check. This can smooth small
details; it is not exact boundary preservation. Disjoint contours and multiple
holes retain fill. The per-region Band seam control positions the start by percentage of outer
boundary length, clockwise from its rightmost point in the artwork view. Blue
circles in the stitch preview mark closed-band starts. Seam changes invalidate
the preview; chart, metric and travel changes retain them, while geometry-setting
changes clear them. Resulting rail/path points persist in the native design.

The pipeline reserves white background separately from the requested foreground
color budget, reduces foreground colors, filters connected patches, fits cutout
curves with VTracer, then imports the resulting solid regions into the embroidery
engine. Original anti-aliased color samples reach the curve fitter. Patches below
the square of the minimum detail size are removed before tracing, including at
transparent boundaries. Removed patches become empty space.

Smooth sampling supports up to 1024 pixels on the longest side without upscaling.
Curve simplification is expressed in millimeters at the intended artwork size;
it is not a bound on total tracing error. Increasing it can erase details or
reduce accuracy. The original pixel-region tracer remains available for comparison.
Near-white exclusion applies to all near-white regions, including interior areas.

The thread-chart selector can keep artwork colors or match them to PEC/JEF fixed
palettes or a user-selected CSV catalog. Matching defaults to Oklab perceptual distance, with the original RGB-distance
matcher available for comparison. Oklab decodes sRGB to linear light before the
D65 transform; reported distances are Euclidean Oklab distances multiplied by
100, not CIEDE2000. Swatches are assumed to be sRGB. Neither method models
physical thread appearance. Supported embedded image profiles are converted
to 8-bit sRGB by Qt before resampling, tracing and matching. Untagged images,
or profiles the decoder cannot expose as usable, assume sRGB without changing
numeric colors. The conversion report records the source profile or assumption.
Source files remain unchanged. Wide-gamut values can be clipped when converted
to sRGB; HDR/tone mapping, calibrated display output and physical thread profiling
remain open. See [Qt color conversion](https://doc.qt.io/qt-6/qimage.html#convertedToColorSpace).
The implementation follows [Björn Ottosson’s reference](https://bottosson.github.io/posts/oklab/)
and is checked against primary coordinates and the published inverse transform. Thread numbers
and catalog metadata persist in the editable project. Different artwork colors
may match one thread; objects remain separate. The source/vector preview and
exported SVG retain artwork colors, while the stitch preview uses matched colors.
Conversion checks list source/matched colors, thread names/numbers and distances.
CSV parsing runs in the preview worker and is bounded to 2 MB / 10,000 rows.
Changing charts preserves region overrides and requires a fresh preview.

The optional **Split suitable branching shapes** pass partitions single-contour
silhouettes at changes in cross-section count or abrupt broad/narrow transitions.
It tries horizontal, vertical and principal-axis cuts, and separately cuts along
short interior chords at the branch crotches. Crotches are inside corners of at
least 35 degrees, measured 0.6 mm either side of the vertex so rounded traced
curves still qualify. Each chord joins two crotches or crosses the arm from one
crotch, lies wholly inside the region and separates boundary at least twice its
own length on both sides. Cuts are applied greedily, shortest first, when they
create a satin-width (at least 0.8 mm) column; pieces under 0.3 mm² are
rejected. Chord pieces share exact cut edges, so no clipping is involved. The
candidate with the most satin area wins, then the fewest pieces; running-stitch
slivers earn no credit. Arms may continue through a junction as one bent satin
rather than meeting a separate junction patch. T, Y, X, five-arm star, K and
leaf-with-stem fixtures are covered at oblique rotations, both as polygons and
traced antialiased raster artwork. This is not a medial-axis router.

**Branch join overlap** (0–1 mm, 0.3 mm by default in the dialog) extends one
piece of each shared cut into its neighbor so adjacent columns overlap rather
than abut. Shared cuts are found from collinear, opposite-running piece edges,
including partial T-junction contacts. The cut edge p–q is replaced by a band
p–p′–q′–q offset into the neighbor; a corner that would leave the neighbor (for
example at a crotch) slides along the cut in steps of half the overlap, up to a
third of the cut length. Extensions are built without Qt booleans, which dropped
whole pieces when the band met cut ends exactly, and always stay inside the
original artwork. The later piece in sewing order is extended first; if that
breaks its satin fit the earlier piece is tried, otherwise the join stays exact.
The preview status reports how many joins were overlapped. Zero keeps exact
joins, as do presets saved before this setting. Overlap is geometric, not a
fabric-tested value; tie-offs at joins follow the normal finishing settings. Splits retain the source coverage within
0.02 square millimeters, remove clipping tails and avoid area overlap. The pass
is bounded to twelve cuts and twenty-four pieces per region, within the project
object limit. Existing usable columns, holes, groups and explicit stage/control
boundaries are retained. Each piece is independently editable, has a stitch
override and can be reordered by the travel pass. Inspect branch joins: automatic
join tie/overlap treatment and branch-aware continuous routing remain open.

An optional travel-ordering pass reorders separated regions within each contiguous
thread-color run. It uses generated entry/exit coordinates, preserves order for
overlapping bounds (including stitches and compensation), and respects stops,
explicit color breaks, groups, stage instructions and manual stitch objects.
Only a reduction in total inter-object travel is accepted. The reported distance
starts at the artwork origin; it excludes travel inside each object and does
not predict placement relative to an existing design. Region choices stay tied
to their original region numbers; the review table also shows sewing position.
Optional direction planning compares both orientations of open running/triple
paths and satin columns using regenerated entry/exit coordinates. Dynamic
programming chooses directions for both the original order and the proposed
order; the shorter complete route is accepted only if it improves on the
original. Closed starts/seams, groups, stops and explicit stage boundaries retain
their direction. The review table identifies reversed regions. Direction choice
is optimal for each of the two fixed orders, not for all possible object orders.
Global ordering, color consolidation and closed-seam optimization remain open.

Optional automatic finishing runs after thread matching and ordering. It sets
editable object tie-in/tie-off/trim flags at design ends and separates transfers
longer than the selected threshold (0.5–50 mm), thread changes, explicit color
breaks and stops. Existing flags are preserved. Short same-thread transfers do
not receive additional separation. The existing engine applies object ties to
internal sewn runs too. **Also trim long travel inside regions** applies the
same threshold to internal jump sequences, with local locks before/after each
inserted trim. Travel is measured along the sequence, not just between endpoints;
initial/final travel without sewn runs on both sides is retained. The editable
object property **Trim internal travel above** stores this threshold (zero disables).
Imported manual stitches retain their existing commands. Review locks and joins
for the intended fabric. Machine formats differ in trim support.

The **Conversion checks** window lists measurements in sewing order: sub-0.5 mm
stitches, zero-length penetrations, jumps over 5 mm, total jump travel and bounds
under 1 mm in either dimension. These fixed thresholds are review aids, not
fabric/machine limits or a density analysis. Ties can intentionally create short
stitches. Travel includes internal jumps and starts at the artwork origin; trim
and stop records do not move the measured needle position. The read-only report
can be selected/copied and is invalidated with the preview.

Tracing and stitch previews run in a cancellable subprocess with a 30-second
limit. File, image, geometry and command limits still apply. Settings changes
invalidate the candidate and its SVG export.

The backend is pinned to **vtracer==1.0.0a4**, an upstream alpha release, to use
its shared-boundary cutout and curve-simplification API. It is not represented as
a stable dependency. Source/API: https://github.com/visioncortex/vtracer/tree/master/crates/vtracer-py
Changing versions requires rerunning geometry, palette, worker and packaging checks.

## Evidence and remaining work

Automated fixtures cover analytic circular boundaries, holes, adjacent colors,
foreground palette budgets, transparent speckles, physical dimensions, padding,
SVG reimport and native preview/save behavior. A circle regression compares
length-weighted radial error with the pixel tracer and checks that the fitted
SVG uses fewer segments. This is a fixture-specific result, not a general image
quality score. Flattened native contours can have more points than pixel contours.
Planner tests cover physical width across rotations, curved columns and open ribbons bending through 270 degrees, closed circular/elliptical bands, seam closure, sewn-segment hole clearance, contour winding/order, holes and
branches, size changes, source immutability, persistence, overrides and the full
image-worker/apply/Undo workflow. Travel tests check measurable improvement,
unchanged per-object stitches, overlap order, semantic/thread boundaries and
nine-format output.
Nine-format export checks cover decoded sewn points and bounds, not full machine
travel equivalence or physical sewing quality.

Next work, while retaining the broader parity ledger:

1. Extend crotch-chord branch partitioning with continuous branch routing,
   junction patches for wide hubs and ambiguous rounded ends.
2. Extend perceptual chart matching with palette-wide color planning and display/
   gamut management, and improve region ordering, travel and overlap control.
3. Calibrate the fabric guidance thresholds with sew-outs, and add per-region
   density suggestions (for example, recommended spacing changes).
4. Expand generated artwork and logo quality comparisons before external-file
   collection; validate fabric, thread and machine behavior through later sew-outs.
5. Develop photographic embroidery separately from flat artwork tracing.

Current conversion produces fill regions and eligible running/satin columns;
smooth outlines and initial stitch heuristics alone do not establish
Hatch parity or production-ready automatic digitizing. Windows/macOS packages and
physical sew-outs remain unverified.

## Repeatable internal benchmark

Run `python -m morale.image_benchmark --output artifacts/image-benchmark-v1`
with the output directory absent (choose a new directory for subsequent runs).
On headless Linux, set `QT_QPA_PLATFORM=offscreen` and a writable font cache.
The runner writes generated source PNGs, traced SVGs, editable native projects,
stitch previews, all nine machine formats, a JSON report and a nine-page PDF
review. It records dependency versions, a hash of the Python implementation and
source-image hashes. Generated artifacts are excluded from Git.

Cases cover broad fill, a closed band, a curved ribbon, a thin running column,
asymmetric padding, a branching T, adjacent colors and a rotated holed fill with
angle search, run routing and finishing combined. A ninth case reduces six grayscale
regions to three perceptual colors with custom spacing, stitch length, compensation
and disabled underlay, followed by routing and finishing. Gates are expected stitch
types, at most 8% symmetric vector-area difference, and decoded sewn bounds within
0.15 mm for each export. These are explicit regression criteria for this corpus,
not a general quality rating or physical acceptance limits. The combined holed
case additionally requires native sewn segments to remain inside traced material.
The reduced-palette case requires the requested palette method, a non-increasing
fitting error and retained custom stitch settings in the resulting objects.
The report separately
records command sequence, counts, sewn/travel lengths, colors and control notes;
a bounds pass does not imply command fidelity. External artwork/files and
physical sew-outs are not included.

The recorded run is in [image-benchmark-report.json](image-benchmark-report.json).
Its local PDF review is `artifacts/image-benchmark-integrated-fill/review.pdf`; the three
artwork/vector/stitch panels use the same 40 mm canvas for direct comparison.

## Direct SVG digitizing

**File → Digitize artwork** accepts SVG alongside raster images. SVG paths are
normalized with transforms and local references resolved, then imported directly
at the requested page width; no raster tracing is involved. A rasterized guide
is generated only for preview/reference use. Page aspect ratio and padding are
preserved, solid fills enter the automatic column/fill planner, and SVG strokes
retain editable running outlines with Bézier controls by default. Optional stroke
expansion is described below. Interpretation notes are shown in Conversion checks.
Raster color reduction, speckle filtering and smoothing controls are hidden for
SVG input. Thread matching, branching, routing, finishing and reference retention
remain available. Save prepared SVG exports the normalized curves at the chosen
physical size. The existing secure SVG subset and 2 MB/geometry limits apply;
text, effects, gradients and external content still require conversion to paths
or another supported form. Ordinary SVG import remains available separately.

SVG input also offers **Expand SVG strokes into satin or fill regions** (off by
default). Borders are outlined geometrically before transforms, preserving
nonuniform scaling, butt/round/square caps, bevel/round/miter joins and SVG miter
limits. The prepared SVG keeps cubic outline curves; native regions retain
flattened contours and holes. Suitable narrow borders enter the satin planner,
while wide or unsuitable borders remain fill. Changing expansion clears region
choices and band seams. Source files are unchanged.

The implementation uses [Qt's path stroker](https://doc.qt.io/qt-6/qpainterpathstroker.html)
and its [SVG miter join](https://doc.qt.io/qt-6/qt.html#PenJoinStyle-enum).
Fill then border order is preserved. Optional covered-fill removal is described
below; inspect edge density before sewing. Dashed strokes, special vector effects and unsupported
SVG 2 joins need conversion to plain paths first. This is not complete SVG 2
coverage. Closed-band planning now simplifies dense input contours before its
2,000-point planning limit; coverage and rail checks still apply.

## Covered-fill removal

**Remove fill covered by later artwork** optionally subtracts later filled
silhouettes before automatic stitch selection. The default overlap allowance is
0.2 mm, adjustable from 0 to 2 mm: lower fill remains under the edge of the upper
region by that distance. These values are geometry settings, not fabric presets.
Zero allowance gives exact geometric cutouts. Holes in upper artwork leave lower
fill visible; disconnected remnants stay editable compound contours. Completely
covered regions can be removed. Original painting/sewing order and source IDs
for retained regions are preserved.

The pass uses original upper silhouettes throughout a stack, respects explicit
stop/color-break/stage/group boundaries, and does not treat running outlines,
manual stitches or invisible objects as filled occluders. It runs before branching,
stitch selection, thread matching and routing. Changing removal or allowance
clears region overrides and band seams. Conversion checks report removed area and
region count. Prepared SVG and reference images remain the original artwork;
the stitch preview shows the reduced layers. Adding the result remains one Undo
operation. Compensation and underlay may extend beyond the cut geometry; physical
seam behavior and density still need sew-outs.

## Exported sewn-path comparison

The source-versus-decoded comparison now samples sewn segments in both directions,
including when command sequences differ. Midpoint samples are spaced at most
0.25 mm apart and tested against exact opposite-path segments within 0.15 mm.
It reports estimated length outside that tolerance, with up to 100 marked sample
locations per direction. This catches additional sewing across a gap even when
stitch-point bounds and endpoint locations match. Harmless segment subdivision
and small quantization shifts do not require command alignment.

The check is bounded (100,000 samples/index entries and a bounded distance-query
budget per direction). Exhaustion is explicitly reported as a partial check.
Short excursions between samples can be missed. The comparison ignores thread
identity and sewing order; existing command/color reports remain necessary.
An apparent decoded connecting stitch is evidence about the reader/writer
round trip, not proof of physical needle behavior. In particular, the installed
VP3 writer omits jumps, and its round-trip path differences remain unresolved.
The benchmark JSON and review PDF now expose sampled path differences separately
from bounds acceptance; a bounds pass is still not a fidelity pass.

## Physical filled-detail cleanup

**Minimum filled detail** is an optional 0–25 mm² area threshold, disabled at zero.
It runs after overlap removal and before branching/stitch selection, for both
raster and SVG artwork. Each disconnected filled island is measured separately,
subtracting its holes; an island nested inside a hole is another component.
Retained holes stay empty. This can omit thin remnants created by an overlap
cut even when the earlier image-pixel speckle filter could not see them.

Running outlines, invisible artwork and explicit stop/color-break/stage/group
semantics are preserved. Changing the threshold clears region choices and band
seams. Conversion checks report component count and area omitted, and adding the
result remains undoable. The source guide and prepared SVG retain the artwork
for comparison. This deliberately removes detail when enabled; it is not an
automatic judgment of what a given fabric or machine can sew. Long thin regions
with area above the threshold remain, and physical density analysis is still open.

## Needle-penetration density review

After generating artwork, **Density review…** opens a map of actual stitch-command
endpoints in fixed 1 × 1 mm cells anchored at design origin. Counts include underlay,
ties and repeated needle positions; jump, trim and stop commands add no penetrations.
The report gives total penetrations, peak count per cell, occupied-cell count,
cells shared by multiple object IDs, and the twenty highest-count cell locations.
Conversion checks include the summary. Changing conversion settings clears the map.

The map uses a relative light-to-dark scale within the current design. At overview
scale, higher-count subpixel cells are drawn last; quantitative counts always use
the original physical grid. Grid placement affects local counts. Shared cells can
come from neighboring boundaries as well as overlapping objects. This view is a needle
penetration diagnostic. The separate sewn-length view is described below; neither
is a fabric stress prediction, calibrated danger threshold or proof of sewability.

The **Sewn thread length** density view splits each sewn segment at grid boundaries
and accumulates its planar length per 1 mm² cell. It includes thread crossing a
cell even when both needle endpoints are outside it, which is useful for satin
coverage. Jumps are excluded; underlay, ties and repeated sewn passes contribute.
The report includes peak mm/mm², total and mapped length, shared-object cells and
twenty hottest locations. Both maps retain fixed origin and relative color scales.

Traversal is bounded to two million cell pieces. If that budget is exceeded, the
map and report explicitly say partial, while still reporting the full sewn-path
length and the mapped subset separately. This estimates planar coverage, not
thread consumption through fabric, bobbin usage or safe fabric-specific density.

## Coverage layers and fabric guidance

**Density and coverage review…** adds a third view, **Coverage layers**: the number
of distinct objects sewn over each point, on a fixed scale (one layer, two, three,
four or more). Each object's footprint is its fill/satin outline plus a 0.4 mm
band along every sewn segment, so pull compensation, underlay and running paths
count. Footprints are rasterized at up to 10 pixels per millimetre (at most four
million pixels) and added together, so an object's own passes count once.
Touching objects therefore show a thin shared seam; exact joins in the sew-out
pack measure well under 1 mm² while 0.3 mm branch overlaps measure about 2 mm².
Conversion checks list the overlapping object pairs with shared area (up to 2,000
candidate pairs) and the review PDF gains a coverage page.

**Fabric for guidance** applies starting-point thresholds for medium woven,
lightweight woven, knit, heavy woven or pile fabric to the stored measurements,
without regenerating: stacked layers, 1 mm² cells above a sewn-thread density
(one satin layer with underlay measures about 5–6 mm/mm², a 0.45 mm fill about
2.3), satins narrower than a minimum width and fills below a minimum area. Each
finding names its location or object. The thresholds are review aids chosen from
those measurements and common practice, not calibrated limits; sew-outs on the
named fabrics are needed to tune them.

## Shareable conversion review

**Save conversion review PDF…** exports the completed preview snapshot: sampled
artwork, prepared vectors when available, generated stitches, needle-penetration
and sewn-length maps, conversion measurements and per-region stitch choices.
Measurements paginate rather than being cut off. The comparison panels share a
physical frame and scale; dashed lines mark the original artwork page. The report
explicitly states that it is not an actual-size placement template
or a sew-out validation. It records only the source filename, not its parent path.

Changing settings or failing a preview invalidates the export. The report uses
captured images and metrics rather than rereading the original artwork. PDF
publication replaces the destination only after generation succeeds; a failed
write preserves an existing file. Reviews are bounded to 200 text pages.

## Optional fill-angle search

**Choose fill angles with less travel** compares actual generated paths while
keeping object order fixed. Candidates include 30-degree orientations around the
full circle and principal-axis orientations from the region's geometry. The
original angle remains unless another candidate reduces total jump travel,
including origin-to-first-object and transfers to neighboring objects. Generated
underlay participates in the measurement. Empty-sewing candidates and candidates that exceed the combined 250,000-command
limit are rejected.

The pass runs after stitch selection and before later routing/finishing. It
preserves geometry, object identity, thread metadata and non-fill objects; it
leaves density gradients, lettering and explicit groups/stages alone. Changed
angles remain editable after adding the objects. Conversion checks and the review
PDF report angle changes and travel reduction. The search is bounded to 512
candidate evaluations and a two-million generated-command budget (one candidate
can consume the remaining budget); partial searches are explicitly reported.
This is a single ordered pass over finite candidates, not a global optimization
or fabric preset. Fill grain and local penetration patterns change, so inspect
appearance and density before sewing.

## Routing disconnected fill runs

**Reduce travel between fill runs** reorders and, where useful, reverses existing
connected sewn runs inside each fill. It keeps the first run's entry and the last
run's exit fixed. Every transfer between runs remains a jump: it does not add sewn
bridges across holes. A greedy candidate is accepted only if its internal jump
travel is shorter than the original scanline order. The run-level transformation
retains the same sewn segment geometry and command count before the existing
short-stitch cleanup and finishing passes.

The option also appears in native fill properties and persists in projects; old
projects default to off. It applies only to the top fill, leaving underlay routing
alone. Three to 2,000 runs are compared; larger fills keep scanline order. This
bounded heuristic is not a global optimum, and reversed sewing direction can
change physical behavior. Review the resulting travel, ties and trims. Machine
formats may still change travel on export, including the documented VP3 issue.

## Perceptual raster palettes

The native raster dialog defaults to Oklab palette reduction, before region
tracing and separately from thread-chart matching. RGB reduction remains
available for comparison; the programmatic tracing default remains RGB.
Changing palette reduction clears region overrides because region boundaries
can change. Both smooth and pixel tracing support the choice. Smooth tracing
feeds the selected perceptual colors to the vectorizer so patch filtering and
vectorization use the same color assignments.

The palette fitter retains source-color populations, starts from an RGB
median-cut palette and refines swatches for up to eight iterations in Oklab.
Up to 4,096 colors are fitted directly; larger histograms use population-weighted
means in 4-bit RGB bins (at most 4,096). Final assignment evaluates every sampled
source color against the palette. Candidate swatches include the old center,
so each refinement preserves or lowers the fitting objective. This is a bounded
approximation, not a globally optimal palette or photographic digitizing.
The unchanged sampled source remains available for visual comparison.

The report identifies the palette method and fitting size. A 256-step grayscale
ramp with three colors reduces mean squared Oklab error from 0.011167 to 0.007845
compared with RGB reduction (about 30%); this synthetic measurement does not
predict physical thread appearance or sew-out quality.

## Adjust stitches before insertion

Enable “Customize generated stitch settings” to choose independent fill/satin
spacing, stitch length, pull compensation and original/off/automatic underlay.
These are explicit settings, not fabric presets. They apply after geometry-based
stitch selection and before fill-angle search, travel routing and finishing, so
those planners and both density maps use the requested stitch settings.
Underlay and compensation apply to fill/satin; running paths retain their
underlay state. Manual command objects are preserved. Palette/geometry choices
remain unchanged and per-region stitch choices survive these adjustments.
A new preview is required before insertion, and the conversion PDF records the
requested settings. Insertion and Undo retain the normal atomic behavior.

## Native conversion workspace

Artwork, Stitches, Travel and finishing, and Preview now have separate native
tabs. Settings pages scroll independently; preview comparisons and region
choices have their own page. Generate preview opens that page automatically.
Progress and the generate/cancel/insert actions remain outside the tabs. Moving
between tabs preserves the result; editing settings retains the existing
invalidation rules. The default window is 940 × 700 pixels.

## Aligned native comparison

The worker now supplies source, prepared vector and stitch panels rendered in
one physical frame. The frame includes the original artwork page and every
generated motion point, so compensation or other sewing beyond that page stays
visible. The dashed border marks the original page. Blue circles retain the
closed-band sewing start indicators. The native dialog displays these prepared
images without regenerating stitches; changing tabs does not change their scale.
The PDF uses the same frame renderer, without sewing-start markers.

Use “Inspect and overlay” on the Preview tab to pan and zoom the aligned images.
Choose source, vectors or stitches, and adjust opacity to blend a result over
the sampled source. Layer changes preserve the view, and Fit returns to the
whole frame. Vectors and sewn stitches render as scalable geometry when available; the
sampled source retains its image resolution. Older snapshots use preview images. Regenerating or invalidating conversion clears the old
inspection snapshot.

Scalable inspection layers are prepared in the conversion worker. The vector
layer retains prepared SVG curves and uses the same physical frame as the source.
The stitch layer contains an independent line for each sewn segment, with jumps
remaining gaps and controls contributing no motion. Closed-band start markers
remain visible. Native SVG items disable raster caching so zoom redraws geometry.
Pixel tracing supplies scalable stitches with its existing vector-placeholder
image. These inspection layers do not alter the saved embroidery commands.

## Reusable conversion presets

Load preset and Save preset store reusable tracing, palette, stitch, overlap,
routing and finishing choices in a `.morale-trace.json` file. Artwork width,
source/reference data, per-region overrides and thread-chart selection remain
separate choices for each conversion. Presets store settings, not a sew-out-tested
fabric profile. Loading requires a fresh preview and clears region/seam choices
whose geometry may have changed. SVG input keeps its vector mode when loading
a raster preset. The versioned format validates all values before changing the
dialog, limits files to 32 KB, and saves atomically.

## Preserve enclosed white details

With near-white exclusion enabled, “Preserve enclosed white details” removes
only near-white connected to the sampled page boundary. Connectivity uses four
neighbors and can pass through transparent pixels. Enclosed white remains in
the palette/tracing input and can become an editable white-thread region.
A limited palette or detail filter can still merge/remove it; inspect the result.
The sampled reference remains unchanged. This operates after image sampling,
so narrow openings can change connectivity at different resolutions.

The option works with smooth and pixel tracing, appears in the quality review
and is stored in conversion presets. Earlier version-one presets default it
to disabled, preserving their original exclusion behavior.

## Light-thread visibility

Light thread colors receive a thin gray contrast outline in stitch previews,
scalable inspection layers, thumbnails and review PDFs. The inner stroke retains
the thread color. This is a display treatment; it does not add sewn segments,
change stored thread colors or bridge jump gaps. Source and vector artwork keep
their original appearance. Inspection tooltips and the PDF caption identify the
contrast treatment. The current threshold is Oklab lightness above 0.85; this is
a preview heuristic, not a physical thread or fabric measurement.

Band seam controls require two strictly nested contours. Separate islands,
intersecting contours, touching contours and duplicate loops do not qualify.
Explicit fill and fixed running outlines disable seam editing because those
choices do not use the band planner. Automatic/satin/running band requests retain
the control even after a fill fallback, allowing a different seam to be tried.

Conversion measurements include the maximum sewn-span length and a count above
a 6 mm review threshold. Jumps, trims and stops do not count as sewn spans.
The report lists the first twenty long-span locations per region, with one-based
command numbers and physical endpoints; totals still include all spans. This
threshold is a review aid, not a fabric or machine limit, and does not modify
stitches. Older report snapshots remain readable without the new measurements.

The inspector can highlight sewn spans longer than 6 mm in orange. This overlay
uses the same threshold as conversion measurements and includes every flagged
span, even when the textual location list is capped. It appears only on the
stitch layer, retains pan/zoom when switching layers, and adds no background
that could conceal the source. Older snapshots without diagnostic geometry
disable the control. Highlights are display-only and do not alter stitches.


## Color placement benchmark

The internal benchmark measures visible color regions as well as overall shape.
Upper artwork covers lower artwork before comparison; overall coverage uses a
union, so overlapping shapes cannot cancel through even-odd fill rules. Each
traced color is matched to the nearest expected source color within an Oklab ×100
distance of 2. Unmatched color area and per-color symmetric geometry differences
contribute to an 8% gate relative to the visible source area. A misplaced color
can count in both its missing and extra regions; this ratio can exceed 100%.
This catches swapped colors even when the overall silhouette is unchanged.
The intentionally reduced-palette case retains its separate palette checks.
A nested two-color fixture exercises occlusion; these generated cases still do
not validate photographs, physical thread appearance or sew-outs.


The benchmark also repeats color-region comparison on final planned fill objects,
after stitch selection, routing and finishing. The same 8% area criterion applies.
A regression test swaps only planned-object colors and confirms failure while
traced-vector checks still pass. Running and satin representations do not encode
filled area in the same way, so this gate explicitly skips those cases. Intentional
palette reduction retains its separate checks. This measures planned outlines,
not thread coverage or physical sewing behavior.


Covered-fill removal clips each cutter to actual material before subtraction.
This prevents a coincident boundary at an existing hole from filling that hole
inside Qt's Boolean result and masking another real overlap. The removed area
must agree with the measured intersection within 0.001 mm²; inconsistent results
are rejected before insertion. A raster-to-vector regression covers a nested
color region plus a separate 8 mm² overlap, preserving the source and both holes.


Inter-region travel optimization now refines intersecting bounding boxes with
artwork plus generated sewn-span footprints, including underlay and compensation.
A 0.001 mm margin treats touching geometry as a conflict. Separate regions inside
holes can therefore reorder within the same thread run without reversing actual
layer intersections. Objects with more than 2,000 combined contour points and
commands keep the conservative bounding-box lock. Thread changes and explicit
sewing boundaries retain their existing barriers. This reduces jumps in additional
cases; it does not claim optimal routing or physical collision prediction.


When a route changes both region order and stitch direction, it now checks the
final generated footprints for every pair whose layer order was reversed. New
intersections reject that candidate and restore the original design and travel
report. Tests cover crossing-path rejection and atomic fallback; normal routing
and the image corpus retain their existing fidelity checks. This is a geometric
ordering safeguard, not a fabric simulation.


Conversion checks and PDF reviews now record inter-region routing outcomes:
improved, unchanged, or rejected. Rejected candidates include a reason and retain
the original travel values; the native preview status also shows that reason.
Reports distinguish these inter-region distances from total jump travel, which
also includes transfers inside regions. Older snapshots without outcome fields
remain readable.


## Machine export fidelity gate

The overall image benchmark now requires both export bounds and bidirectional
sampled sewn-path agreement. Each direction must be complete, have nonzero
samples, and have no samples outside its 0.15 mm tolerance. Missing or partial
comparisons fail. Artwork-only checks have a separate result and cannot turn a
failed export into a passing overall benchmark. The CLI exits nonzero on failure.

The current eleven-case corpus passes all artwork checks and 99 bounds checks,
but only 92 of 99 sampled sewn-path checks. Seven VP3 exports fail because of
extra sewn travel; this known limitation is not exempted from the overall gate.
The other eight writers pass these generated cases. Sampling at 0.25 mm is not
exact path equivalence or physical machine validation.


## Optional small-hole filling

“Fill holes smaller than” closes filled-artwork voids below a chosen physical
area (0–25 mm²), before small-island filtering and stitch selection. Zero keeps
all holes, including when loading older conversion presets. Immediate material
islands merge into a filled hole; deeper holes keep their boundaries unless they
independently meet the threshold. Running outlines and explicit grouped/staged
sewing regions are retained. Reports give the number of holes and added area.
This intentionally changes artwork and can cover meaningful details; compare
against the source. It is not a fabric-calibrated minimum-hole recommendation.


Small-hole filling retains a void when any part is occupied by another visible
fill region, regardless of color or whether that region is above or below it.
This avoids adding an unnecessary layer beneath existing colored detail. Hidden
regions do not protect holes. Earlier additions in the same pass protect later
regions, preventing a shared hole from being filled twice. Conversion checks
report the retained-hole count. Running/manual stitches are not interpreted as
filled silhouettes by this test.


Detail-filter reviews now identify each changed source region by name and report
its filled-hole or omitted-island count and physical area change. Entirely
omitted regions are labeled explicitly. The worker retains source object IDs in
these change records; later routing or branch splitting does not rewrite their
identity. Older snapshots without names use one-based source-region labels.
The native conversion checks and paginated PDF use the same detail listing.


The enclosed-white benchmark fixture adds a white interior detail within a colored
shape on a white page. Border-connected exclusion must remove the page while
retaining the interior white region. Both traced and planned color-region geometry
are gated, followed by all nine machine writers. The fixture currently passes its
artwork checks and eight writers' sampled path checks; VP3 remains a failure.

## Underlay choices during conversion

Custom stitch settings now expose separate fill and satin underlay choices.
Fill supports edge run, sparse fill, or both; satin supports center run, zigzag,
or both. Each type can use the general underlay choice or override it, including
turning support off. Underlay inset (0–3 mm) and spacing (0.5–10 mm) are applied
before routing and finishing, and stored on the editable objects. Running paths
and imported manual stitches do not receive these underlay changes. A fresh
preview includes the generated support stitches in its quality/density checks.
The controls are saved in conversion presets; older version-one presets default
to the general choice, zero inset and 2 mm support spacing. These are software
settings, not fabric-tested recommendations. For satin, spacing controls zigzag
support; a center run uses the stitch-length setting.

Conversion measurements and saved review PDFs identify each fill/satin region's
resolved underlay style and relevant physical settings. Automatic underlay is
reported as edge run for fills or center run for satin. Disabled support is
explicit; center-only support omits unused inset/zigzag-spacing values. Requested
choices use readable names without measurement units. Older report snapshots
without per-region underlay data remain readable.
