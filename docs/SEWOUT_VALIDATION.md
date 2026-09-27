# Sew-out validation

Morale's automated tests prove that its software does what it intends. They cannot
prove that the result sews well. That needs real machines, fabric, thread and
stabilizer. This page describes how to collect that evidence so Morale's
settings and guidance can be based on measured results.

Until results exist, every threshold in Morale (fabric guidance, minimum satin
width, join overlap, density limits) is a **provisional starting point**. A rule
only becomes an automatic recommendation after sew-outs support it.

## 1. Make the coupons

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

Each coupon folder holds machine files (PES, PES v1, EXP, DST), the editable
project, an actual-size placement PDF, a thread chart, `metadata.json`,
`evaluation.json` and a README. Every coupon has a **10 mm square with a crosshair**
in its lower-left corner, so measurements can be taken from photos.

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
