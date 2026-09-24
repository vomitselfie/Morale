"""Preview-only contrast for light thread colors on light backgrounds."""
from PySide6.QtGui import QColor,QPen
from .perceptual_color import oklab


def needs_contrast(color):
    return oklab(QColor(color).name())[0]>.85


def draw_stitch_path(painter,path,color,width):
    if needs_contrast(color):
        painter.setPen(QPen(QColor('#666666'),width*2.2));painter.drawPath(path)
    painter.setPen(QPen(QColor(color),width));painter.drawPath(path)
