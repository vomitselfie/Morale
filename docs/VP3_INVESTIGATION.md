# VP3 internal-jump investigation

The current export path loses information before decoding. Two otherwise identical
one-color designs have commands at these physical X coordinates (Y is zero):

| Design | Jump | Sew | Internal jump | Sew |
| --- | --- | --- | --- | --- |
| A | 0 mm | 1 mm | 4 mm | 12 mm |
| B | 0 mm | 1 mm | 8 mm | 12 mm |

The exported VP3 files are byte-for-byte identical. Their bounds and command
counts are the same, while the intended final sewn segments are 4→12 and 8→12.
Thus a reader cannot uniquely recover both intended landings from these outputs.
The PES and EXP exports differ and pass both sampled sewn-path comparisons.

Reproduce with `python -m morale.vp3_probe --output NEW_DIRECTORY`. The command
refuses an existing directory and saves both native sources, six machine files,
SHA-256 hashes and source/decoded comparisons. The retained run is
`artifacts/vp3-internal-jump-probe/report.json`. `tests/test_vp3_probe.py` verifies
this minimal reproducer; it records a known failure rather than certifying VP3.
No external files or machine execution were used.

The installed pyembroidery 1.5.1 writer's `write_stitches_block` skips JUMP records
without updating its last encoded position. It encodes the subsequent STITCH
relative to that earlier position. The current upstream
[writer](https://raw.githubusercontent.com/EmbroidePy/pyembroidery/main/pyembroidery/Vp3Writer.py)
and [reader](https://raw.githubusercontent.com/EmbroidePy/pyembroidery/main/pyembroidery/Vp3Reader.py)
also use the 80 01 / signed-16-bit coordinates / 80 02 form for sewn motion.
An older [reverse-engineering note](https://www.jasonweiler.com/VP3FileFormatInfo.html)
calls that form a jump. That disagreement is insufficient evidence for changing
all long-form stitches into jumps: doing so would discard intentional long sewn
spans that the current writer encodes in the same form.

The next encoding investigation needs independently generated VP3 examples with
known short and long sewn spans, internal travel both with and without trims,
and multiple sewn runs of the same color. They should preserve source commands
or a reliable authoring preview. Do not fix this by guessing landings, treating
all long records as travel, or inserting artificial color changes. Other formats,
image quality and native parity work can continue while this remains unresolved.
