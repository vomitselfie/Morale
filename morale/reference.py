"""Embedded raster references, independent of embroidery commands."""
import base64
import math
from pathlib import Path
import struct


def validate_reference(reference):
    if not isinstance(reference, dict):
        raise ValueError("Invalid reference image.")
    if not reference:
        return
    if set(reference) != {"png", "name", "x", "y", "width", "height", "rotation", "opacity", "visible"}:
        raise ValueError("Invalid reference image properties.")
    if not isinstance(reference["name"], str) or len(reference["name"]) > 200 or type(reference["visible"]) is not bool:
        raise ValueError("Invalid reference name or visibility.")
    for key, low, high in [("x", -1000, 1000), ("y", -1000, 1000), ("width", .1, 500), ("height", .1, 500), ("rotation", -360, 360), ("opacity", 0, 1)]:
        value = reference[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Invalid reference {key}.")
    if not isinstance(reference["png"], str) or len(reference["png"]) > 12_000_000:
        raise ValueError("Reference image exceeds its size limit.")
    try:
        raw = base64.b64decode(reference["png"], validate=True)
    except ValueError as exc:
        raise ValueError("Invalid embedded image encoding.") from exc
    if len(raw) < 24 or not raw.startswith(b"\x89PNG\r\n\x1a\n") or raw[12:16] != b"IHDR":
        raise ValueError("Embedded references must be PNG images.")
    width, height = struct.unpack(">II", raw[16:24])
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError("Embedded reference dimensions exceed 4096 pixels.")


def import_reference(path, hoop_width, hoop_height):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize
    from PySide6.QtGui import QImageReader
    path = Path(path)
    if path.stat().st_size > 20_000_000:
        raise ValueError("Reference files are limited to 20 MB. Resize this image before importing.")
    reader = QImageReader(str(path))
    if bytes(reader.format()).lower() not in {b"png", b"jpeg", b"bmp", b"webp"}:
        raise ValueError("Choose a PNG, JPEG, BMP, or WebP raster image.")
    size = reader.size()
    if size.width() <= 0 or size.height() <= 0 or size.width() * size.height() > 16_777_216:
        raise ValueError("Reference images are limited to 16 megapixels. Resize this image before importing.")
    scale = min(1, 2048 / max(size.width(), size.height()))
    reader.setScaledSize(QSize(max(1, round(size.width() * scale)), max(1, round(size.height() * scale))))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        raise ValueError("Could not decode this image: " + reader.errorString())
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise ValueError("Could not embed the reference image.")
    fit = min(hoop_width * .8 / image.width(), hoop_height * .8 / image.height())
    reference = {"png": base64.b64encode(bytes(data)).decode("ascii"), "name": path.name[:200],
                 "x": 0., "y": 0., "width": max(.1, image.width() * fit), "height": max(.1, image.height() * fit),
                 "rotation": 0., "opacity": .4, "visible": True}
    validate_reference(reference)
    return reference


def decode_reference(reference):
    from PySide6.QtGui import QImage
    validate_reference(reference)
    if not reference:
        return QImage()
    image = QImage.fromData(base64.b64decode(reference["png"]), "PNG")
    if image.isNull():
        raise ValueError("The embedded reference image is damaged.")
    return image
