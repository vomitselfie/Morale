"""VP3 stitch encoding that keeps jump positions.

VP3 has no jump command. pyembroidery's writer skipped jumps without moving its
position, so the next stitch was encoded from the point *before* the jump: the
machine sewed a straight line where the design travelled (docs/VP3_INVESTIGATION.md).

Embroidermodder's libembroidery (format-vp3.c) writes every movement, and reads
the long form ``80 01 dx dy 80 02`` as a travel move; Jason Weiler's format notes
describe the long form as a jump too. Morale follows that reading:

* every jump is written in the long form, to its real landing point;
* sewn stitches are always written in the short one-byte-per-axis form, which
  export guarantees by splitting sewn spans below 12.7 mm;
* reading, the long form is a jump and the short form a stitch.

Adapted from pyembroidery's Vp3Writer/Vp3Reader (MIT, see THIRD_PARTY_NOTICES.md).
"""
from pyembroidery.EmbConstant import COMMAND_MASK, COLOR_CHANGE, END, JUMP, STITCH, TRIM
from pyembroidery.WriteHelper import write_int_8, write_int_16be, write_int_32be

# Short-form deltas are signed bytes: at most 127 tenths of a millimetre per axis.
SHORT_LIMIT = 127


def _patch_offset(f, placeholder):
    # Same as pyembroidery's vp3_patch_byte_offset: the block length from placeholder to here.
    current = f.tell()
    f.seek(placeholder, 0)
    write_int_32be(f, current - placeholder - 4)
    f.seek(current, 0)


def write_stitches_block(f, stitches, first_pos_x, first_pos_y):
    f.write(b"\x00\x01\x00")
    placeholder = f.tell()
    write_int_32be(f, 0)
    f.write(b"\x0A\xF6\x00")
    last_x, last_y = first_pos_x, first_pos_y
    for x, y, data in stitches:
        command = data & COMMAND_MASK
        if command == END:
            f.write(b"\x80\x03")
            break
        if command == TRIM:
            f.write(b"\x80\x03")
            continue
        if command not in (STITCH, JUMP):
            continue  # Colour changes divide blocks; stops are thread changes here.
        dx, dy = int(x - last_x), int(y - last_y)
        last_x += dx
        last_y += dy
        if command == JUMP:
            if dx or dy:
                f.write(b"\x80\x01")
                write_int_16be(f, dx)
                write_int_16be(f, dy)
                f.write(b"\x80\x02")
        elif -SHORT_LIMIT <= dx <= SHORT_LIMIT and -SHORT_LIMIT <= dy <= SHORT_LIMIT:
            write_int_8(f, dx)
            write_int_8(f, dy)
        else:
            raise ValueError("A VP3 sewn stitch exceeds 12.7 mm; split long spans before writing.")
    _patch_offset(f, placeholder)


def read_stitch_bytes(stitch_bytes, out):
    """Decode a VP3 stitch block: short form stitches, long form moves, 80 03 trims."""
    i = 0
    while i < len(stitch_bytes) - 1:
        x, y = stitch_bytes[i], stitch_bytes[i + 1]
        i += 2
        if (x & 0xFF) != 0x80:
            out.stitch(x, y)
            continue
        if y == 0x01:
            dx = _signed16(stitch_bytes[i], stitch_bytes[i + 1])
            dy = _signed16(stitch_bytes[i + 2], stitch_bytes[i + 3])
            i += 6  # Both deltas, then the trailing 80 02.
            out.move(dx, dy)
        elif y == 0x03:
            out.trim()


def _signed16(high, low):
    value = ((high & 0xFF) << 8) | (low & 0xFF)
    return value - 0x10000 if value > 0x7FFF else value


def read_colorblock(module):
    """A replacement for Vp3Reader.vp3_read_colorblock using ``read_stitch_bytes``."""
    def vp3_read_colorblock(f, out, center_x, center_y):
        f.read(3)  # 00 05 00
        block_end_position = module.read_int_32be(f) + f.tell()
        start_x = module.signed32(module.read_int_32be(f)) / 100
        start_y = -(module.signed32(module.read_int_32be(f)) / 100)
        abs_x, abs_y = start_x + center_x, start_y + center_y
        if abs_x != 0 and abs_y != 0:
            out.move_abs(abs_x, abs_y)
        out.add_thread(module.vp3_read_thread(f))
        f.seek(15, 1)
        f.read(3)  # 0A F6 00
        read_stitch_bytes(module.read_signed(f, block_end_position - f.tell()), out)
    return vp3_read_colorblock
