# Toward a full embroidery studio

The active acceptance checklist and evidence are in [V1_PARITY.md](V1_PARITY.md).
Machine-file import/merging and nine export formats are now implemented; the
compatibility report tracks synthetic coverage separately from external fixtures.

The long-term benchmark is advanced hobbyist digitizing, as represented by
[Hatch Digitizer](https://hatchembroidery.com/products/hatch-embroidery/digitizer).
Morale uses its own interface and implementation; no proprietary code or assets.

## 0.1 — Native foundation (implemented)

Qt desktop workspace, basic vector shapes and paths, running/tatami stitches,
thread sequence, numeric transforms, undo/redo, hoop checks, playback, editable
projects, four machine export formats, and automated tests.

## Current priority — Image to embroidery

Feature parity remains the acceptance target. Image digitizing takes priority
within that work: smooth vector regions and SVG export, followed by stitch-type
selection, routing and measurable conversion quality. See
[IMAGE_DIGITIZING.md](IMAGE_DIGITIZING.md). External-file collection follows the
feature work; synthetic fixtures do not establish physical sewing quality.

## Next — Reliable sew-outs

1. Identify the first real machine, hoops, fabric, stabilizer, and thread setup.
2. Create small reference sew-outs and a regression collection of machine files.
3. Extend the implemented ties, object trims, and interior-tested fill connectors
   with optimized routing, minimum stitch filtering, inset/zigzag underlay, and
   pull compensation.
4. Extend implemented satin rails, point editing, and split lengths with acute
   corner treatment, global overlap checks, and interactive rail handles.
5. Move generation to cancellable background jobs; add performance benchmarks.
6. Validate packages on Windows, Linux, and macOS, then provide signed installers,
   collected license notices, and a release process.

## Creative digitizing

- Node/Bezier editing, snapping, align/distribute, multi-selection, grouping.
- Artwork reference images and secure SVG import with explicit unit handling.
- Extend stitch-file compatibility with externally produced fixtures and stitch-level editing.
- Digitized embroidery fonts, text layout, monograms, curved baselines.
- Appliqué placement/tack-down/cover sequences, motifs, and programmable fills.
- Real thread catalogs with color matching, fabric presets, and print templates.

## Advanced workflows

- Assisted raster/vector digitizing with editable results and quality checks.
- Fill holes, overlap management, branching, and route optimization.
- Multi-hoop splitting and placement aids; machine-specific sewing fields.
- Design library, accessibility audits, localization. Local interrupted-session
  recovery is implemented; background generation/import remains open.

Feature parity is a long-term program, not a claim about this first release.
