"""Render platform icon files from the Morale logo with Qt alone.

ICO and ICNS both accept PNG-encoded images, so their containers are written
directly: no image tools are needed on the build machine.
"""
import argparse
from pathlib import Path
import struct

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen
from PySide6.QtSvg import QSvgRenderer

LOGO = Path(__file__).resolve().parents[1] / "morale" / "assets" / "logo.svg"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
# ICNS chunk types for PNG payloads: (type, pixel size).
ICNS_TYPES = (("icp4", 16), ("icp5", 32), ("icp6", 64), ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024),
              ("ic11", 32), ("ic12", 64), ("ic13", 256), ("ic14", 512))


def render(size):
    """The logo on a rounded light tile, so thin needles stay visible when small."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    inset = size * .04
    tile = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    path = QPainterPath()
    path.addRoundedRect(tile, size * .2, size * .2)
    painter.fillPath(path, QColor("#fffaf3"))
    if size >= 32:
        painter.setPen(QPen(QColor("#f3cfe0"), max(1., size / 128)))
        painter.drawPath(path)
    margin = size * (.12 if size >= 48 else .08)
    QSvgRenderer(str(LOGO)).render(painter, QRectF(margin, margin, size - 2 * margin, size - 2 * margin))
    painter.end()
    return image


def png(image):
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Could not encode an icon image.")
    return bytes(data)


def write_ico(path, sizes=ICO_SIZES):
    images = [png(render(size)) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries = b""
    for size, data in zip(sizes, images):
        # A zero width/height byte means 256 pixels.
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    Path(path).write_bytes(header + entries + b"".join(images))


def write_icns(path):
    chunks = b""
    for kind, size in ICNS_TYPES:
        data = png(render(size))
        chunks += kind.encode("ascii") + struct.pack(">I", len(data) + 8) + data
    Path(path).write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)


def build_icons(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    write_ico(root / "morale.ico")
    write_icns(root / "morale.icns")
    for size in (256, 512):
        render(size).save(str(root / f"morale-{size}.png"))
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    application = QGuiApplication.instance() or QGuiApplication([])
    print(build_icons(parser.parse_args().output))
