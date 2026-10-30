# Sew-out validation

Morale's automated tests prove that its software does what it intends. They cannot
prove that the result sews well. That needs real machines, fabric, thread and
stabilizer. This page describes how to collect that evidence so Morale's
settings and guidance can be based on measured results.

Until results exist, every threshold in Morale (fabric guidance, minimum satin
width, join overlap, density limits) is a **provisional starting point**. A rule
only becomes an automatic recommendation after sew-outs support it.

## 1. Make the coupons

The first available physical test machines are a Brother and a Bernina, supplied
by the project owner. Exact models, firmware, hoops and transfer methods remain
to be recorded before selecting test exports. Availability is not yet evidence
of successful loading or sewing on either machine.

A coupon is a small single-colour design that tests one thing. Build all of them:

```sh
python -m morale.coupons --output my-coupons
```

or one at a time with `--coupon NAME`. `python -m morale.coupons --list` shows the
names:

| Coupon | What it tests |
| --- | --- |
| `satin-width` | Satin columns 0.4–6 mm wide: straight, gently curved, tight bends |
| `pull-compensation` | Satin and fill with 0–0.5 mm compensation |
| `fill-density` | Fill row spacing 0.3–0.6 mm |
| `fill-angles` | Fill angles 0°, 30°, 45°, 60°, 90° on identical squares |
| `underlay` | Satin and fill with each underlay type, and none |
| `small-fills` | Squares and circles from 1 to 25 mm² |
| `stitch-length` | Straight stitches 4–12 mm long |
| `tiny-stitches` | Stitches 0.1–1 mm long |
| `layering` | 1 to 4 stacked fills and satins |
| `jumps` | Jumps of 5–40 mm, with and without trims |
| `lettering` | Capitals and lowercase in an embroidery font at 6–15 mm |
| `branch-joins` | Satin branches joined with exact, 0.3 mm and 0.6 mm overlaps |
| `satin-corners` | Sharp satin corners from 120° to 30°, 2 and 4 mm wide |
| `decorative-stitches` | Blanket, meander and cross-stitch, and satin sewn smooth, as S-stitch and as open zigzag |

Each coupon folder holds machine files (PES, PES v1, EXP, DST), the editable
project, an actual-size placement PDF, a thread chart, `metadata.json`,
`evaluation.json` and a README. Every coupon has a **10 mm square with a crosshair**
in its lower-left corner, so measurements can be taken from photos.

The generated `report.json` also records reopened-file verification for every
machine export and its SHA-256 hash. The README includes the checks and any
differences requiring review. A failed or incomplete check retains the file for
inspection; it does not count as a successful verification. Review these results
before transferring files, and confirm format and hoop support for your exact
machine model. Passing software checks does not establish physical compatibility.

The command prints CHECKS PASSED or REVIEW NEEDED for each export, followed by
any detected differences. For automated validation, add `--require-verification`
to exit nonzero if any export needs review. Generated files and evaluation forms
are retained in either mode; the default exit status reports generation success.

## 2. Sew

- Use the fabric, stabilizer and thread you want to learn about. Record them.
- Sew the machine file unchanged; do not adjust density or size on the machine.
- Watch the first run: the coupons are generated and have not all been sewn.

## 3. Capture the result

Photograph or scan the **front and back**, square-on, with the scale square in the
picture. A flatbed scanner is best; a phone photo taken straight down in even
light also works.

## 4. Record it

Fill in `metadata.json`: machine, hoop, needle, upper and bobbin thread, fabric,
stabilizer, speed, date. Leave unknown fields empty.

Fill in `evaluation.json`. Each test object is listed with its target. For each,
set `status` to `pass`, `marginal` or `fail`, add any measurements, and a note.
For example:

```json
{
  "object": "Straight 0.8 mm",
  "target": {"shape": "straight", "width_mm": 0.8},
  "status": "marginal",
  "measured": {"width_mm": 0.62},
  "notes": "coverage acceptable, weak edge definition"
}
```

Useful measurements: finished width, gaps, puckering, thread breaks, bobbin
showing on top, overlap ridges, and registration between parts.

## 5. Keep everything together

Put the photos, both JSON files and the exact machine file you sewed in one
folder, named like `satin-width-001-brother-cotton`. To share it with the
project, attach the folder (zipped) to an issue on
[GitHub](https://github.com/vomitselfie/Morale/issues).

## What happens with results

Results are compared per coupon across machines and fabrics. When enough agree,
Morale's provisional thresholds are changed, and the change references the
results that justify it. Morale does not claim fabric-specific "intelligence"
before that evidence exists.

The `fabric-profiles` coupon compares Morale's three experimental fabric recipes
on one piece of fabric: fill squares across the top and 4 mm satin columns below.
Generate it with `python -m morale.coupons --output DIR --coupon fabric-profiles`.
Use the placement sheet to identify columns, and record fabric, stabilizer,
thread and machine in the metadata form. Evaluation targets include nominal
dimensions and applied stitch settings. Compare coverage, puckering, measured
size and visible underlay. This is a whole-recipe comparison; use the individual
density, compensation and underlay coupons to isolate causes afterward.

For an editable design without using the command line, choose **File → Load
fabric comparison sampler**. It opens the same 100 × 100 mm design with the scale
marker and six comparison samples. Save a project, export a placement PDF and
choose a machine export through the usual File actions. The command-line coupon
pack additionally supplies blank evaluation and machine/material metadata forms.

**File → Load sewout coupon…** provides a native picker for every calibration
design, including satin width, density, fill angles, compensation, underlay,
small details, stitch length, tiny stitches, layering, jumps, lettering, branch
joins and fabric profiles. Cancel leaves the current design intact; loading a
choice uses the normal unsaved-work prompt. These open editable test designs,
not previously measured or machine-certified results.

Generated coupon packs also include **evaluation.pdf**, a printable sheet with
sample names, target settings, blank measurements and machine/material fields.
Use it beside the machine, then transfer observations to `evaluation.json` for
structured comparisons. It is separate from the actual-size placement sheet.

For an edited coupon or any current design, use **File → Export sewout worksheet
(PDF)…**. This records included objects and their current stitch settings, with a
project snapshot hash for identification. Hidden objects are omitted. Width and
height describe source geometry before rotation and compensation; record actual
sewn dimensions in the blank measurement fields. The worksheet does not certify
an export or a physical result.

Current-design worksheets also list generated width/height and needle penetration
count. Generated dimensions are axis-aligned bounds after rotation and stitch
generation, including compensation, underlay and ties, but before machine-format
rounding. Compare these with the actual sewn size; source dimensions remain
listed separately. These bounds do not predict fabric deformation.

### Ripple spacing coupon

Choose **Ripple spacing** in File → Load sewout coupon, or generate a complete
pack with `python -m morale.coupons --output OUTPUT --coupon ripple-spacing`.
The six 20 mm squares have 4 mm cutouts. Columns compare 0.5, 1 and 2 mm spacing;
rows compare centered circles with a -60% X center offset. Underlay is disabled
and short-stitch cleanup is 0.3 mm. Compare one row or column at a time, recording
row separation, cutout clearance, puckering and thread breaks. These decorative
open fills do not have a solid-coverage target. Use the included evaluation form
and record the actual machine model, hoop and materials before sewing.

### Export a complete standard pack from the desktop

Use **File → Export standard sewout pack…**, choose a coupon, then choose a parent
folder. Morale creates a named subfolder with machine files, the editable project,
placement/evaluation PDFs and blank metadata/results forms. Existing pack folders
are refused so previous measurements remain intact. The completion dialog lists
any files needing export review; expand its details for the individual checks.
This exports a fresh standard coupon. To document your edited design, use
**Export sewout worksheet (PDF)…** and the regular machine export command.

An interrupted export retains an `INCOMPLETE.txt` marker in its folder. Do not
sew files from that pack; generate a new pack in another folder. The marker is
removed only after all pack files have been written. Its absence does not replace
export verification or physical validation.

Desktop pack export runs in a separate worker while a progress dialog remains
responsive. Cancel (or close the progress window) stops the worker. Exports have
a 60-second limit; a timeout reports failure. Cancelled/failed packs may retain
partial files with the incomplete marker; choose a new folder when retrying.
