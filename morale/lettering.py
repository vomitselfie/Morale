"""System-font outlines stored in projects for portable, editable lettering."""
from copy import deepcopy
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontInfo, QFontMetricsF, QPainterPath, QTransform, QFontDatabase
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QFontComboBox, QDoubleSpinBox, QDialogButtonBox, QLabel, QMessageBox, QComboBox, QCheckBox

from .model import DesignObject, Project
from .engine import generate


def lettering_font(text,family,height,spacing):
    if not isinstance(text, str) or not text.strip() or len(text) > 80 or any(c in text for c in "\n\r\t"):
        raise ValueError("Enter a single line of 1–80 visible characters.")
    if not math.isfinite(height) or not 1 <= height <= 100 or not math.isfinite(spacing) or not 50 <= spacing <= 200:
        raise ValueError("Use height 1–100 mm and character spacing 50–200%.")
    font = QFont(family)
    font.setPixelSize(100)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, spacing)
    actual_family = QFontInfo(font).family()
    metrics = QFontMetricsF(font)
    missing = [c for c in text if not c.isspace() and not metrics.inFontUcs4(ord(c))]
    if missing:
        raise ValueError("This font lacks some characters. Choose another font: " + " ".join(dict.fromkeys(missing)))
    return font,actual_family


def make_lettering(text, family, height=15., spacing=100., previous=None, *, layout="straight", curve=60., baseline=None):
    if layout=="path":
        from .path_lettering import make_path_lettering
        return make_path_lettering(text,family,height,spacing,previous,baseline=baseline)
    font,actual_family=lettering_font(text,family,height,spacing)
    if layout not in {"straight", "curved", "monogram"} or not math.isfinite(curve) or not -180 <= curve <= 180:
        raise ValueError("Choose a supported layout and a curve between −180° and 180°.")
    if layout == "monogram" and (len(text) != 3 or not text.isalpha()):
        raise ValueError("A monogram requires three letters in left-to-right order; the middle letter is enlarged.")
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    if layout == "monogram":
        cursor = 0.
        for index, letter in enumerate(text):
            glyph = QPainterPath()
            glyph.addText(0, 0, font, letter)
            if index == 1:
                glyph = QTransform().scale(1.4, 1.4).map(glyph)
            bounds = glyph.boundingRect()
            glyph = QTransform().translate(cursor - bounds.left(), -bounds.center().y()).map(glyph)
            path.addPath(glyph)
            cursor += bounds.width() + 12 * spacing / 100
    else:
        path.addText(0, 0, font, text)
    path = QTransform().scale(.25, .25).map(QTransform().scale(4, 4).map(path).simplified())
    bounds = path.boundingRect()
    if bounds.isEmpty():
        raise ValueError("The font produced no usable outlines.")
    ratio = height / bounds.height()
    # Flatten at enlarged coordinates for sub-millimeter outline fidelity.
    polygons = path.toSubpathPolygons(QTransform().scale(4, 4))
    world_rings = []
    radius = bounds.width() / math.radians(curve) if layout == "curved" and abs(curve) > .001 else None
    for polygon in polygons:
        ring = []
        raw_points = [(p.x() / 4, p.y() / 4) for p in polygon]
        sampled = []
        if radius is not None:
            for a, b in zip(raw_points, raw_points[1:] + raw_points[:1]):
                count = max(1, math.ceil(math.dist(a, b) / 4))
                sampled.extend((a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count) for i in range(count))
        else:
            sampled = raw_points
        for px, py in sampled:
            x, y = px - bounds.center().x(), py
            if radius is not None:
                if (radius - y) / radius <= .1:
                    raise ValueError("This curve folds the letters across the arc center. Reduce the angle or use longer text.")
                angle = x / radius
                x, y = (radius - y) * math.sin(angle), radius - (radius - y) * math.cos(angle)
            ring.append([x * ratio, y * ratio])
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring.pop()
        if len(ring) >= 3:
            world_rings.append(ring)
    xs, ys = zip(*[point for ring in world_rings for point in ring])
    width, total_height = max(xs) - min(xs), max(ys) - min(ys)
    if width > 500 or total_height > 500:
        raise ValueError("Lettering exceeds 500 mm. Reduce height or text length.")
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    contours = [[[(x - cx) / width, (y - cy) / total_height] for x, y in ring] for ring in world_rings]
    obj = deepcopy(previous) if previous else DesignObject()
    obj.name = text[:200]
    obj.kind = "compound"
    obj.width, obj.height = max(.1, width), max(.1, total_height)
    obj.points, obj.stitch_data = [], []
    obj.contours = contours
    obj.lettering = {"text": text, "family": actual_family, "height": height, "spacing": spacing, "layout": layout, "curve": curve, "layout_height": total_height}
    if obj.stitch_type not in {"fill", "running", "triple"}:
        obj.stitch_type = "fill"
    if previous is None:
        obj.underlay = False
    Project.loads(Project(objects=[obj]).dumps())
    generate(Project(objects=[obj]))
    return obj


class LetteringDialog(QDialog):
    def __init__(self, obj=None, parent=None, *, baseline=None):
        super().__init__(parent)
        self.setWindowTitle("Lettering")
        self.previous = obj
        self.baseline = deepcopy(baseline)
        self.candidate = None
        settings = obj.lettering if obj else {}
        layout = QVBoxLayout(self)
        note = QLabel("Create fill or running lettering from an installed font. These are not purpose-digitized embroidery fonts. Small text needs a sew-out test. Saved outlines travel with the project; editing requires a font on this computer.")
        note.setWordWrap(True)
        layout.addWidget(note)
        if settings and settings["family"] not in QFontDatabase.families():
            missing = QLabel(f"The saved font '{settings['family']}' is unavailable. Choose a replacement before applying; Cancel keeps the saved outlines.")
            missing.setWordWrap(True)
            layout.addWidget(missing)
        form = QFormLayout()
        self.text = QLineEdit(settings.get("text", "Morale"))
        self.text.setMaxLength(80)
        self.font = QFontComboBox()
        if settings:
            self.font.setCurrentFont(QFont(settings["family"]))
        self.height = QDoubleSpinBox()
        self.height.setRange(1, 100)
        current_height = settings.get("height", 15)
        if obj:
            current_height *= obj.height / settings.get("layout_height", settings.get("height", obj.height))
        self.height.setValue(current_height)
        self.height.setSuffix(" mm")
        self.spacing = QDoubleSpinBox()
        self.spacing.setRange(50, 200)
        self.spacing.setValue(settings.get("spacing", 100))
        self.spacing.setSuffix(" %")
        self.layout_choice = QComboBox()
        for title, value in [("Straight", "straight"), ("Curved", "curved"), ("Three-letter monogram", "monogram")]:
            self.layout_choice.addItem(title, value)
        if baseline is not None or settings.get("layout") == "path":
            self.layout_choice.addItem("Along drawn path", "path")
        self.layout_choice.setCurrentIndex(self.layout_choice.findData(settings.get("layout", "path" if baseline is not None else "straight")))
        self.curve = QDoubleSpinBox()
        self.curve.setRange(-180, 180)
        self.curve.setValue(settings.get("curve", 60))
        self.curve.setSuffix("°")
        self.curve.setEnabled(self.layout_choice.currentData() == "curved")
        self.layout_choice.currentIndexChanged.connect(lambda: self.curve.setEnabled(self.layout_choice.currentData() == "curved"))
        for title, widget in [("Text", self.text), ("Font", self.font), ("Letter height", self.height), ("Character spacing", self.spacing), ("Layout", self.layout_choice), ("Curve angle", self.curve)]:
            widget.setAccessibleName(title)
            form.addRow(title, widget)
        layout.addLayout(form)
        hint = QLabel("Monograms use the entered left-to-right order and enlarge the center letter. Curved layout bends the outlines along an arc.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.keep_baseline = QCheckBox("Keep baseline path visible and stitchable")
        if baseline is not None:
            layout.addWidget(self.keep_baseline)
        if baseline is not None or settings.get("layout") == "path":
            path_note = QLabel("Lettering stores its own baseline copy. Inspect tight bends for overlapping letters.")
            path_note.setWordWrap(True)
            layout.addWidget(path_note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(470, 300)

    def accept(self):
        try:
            self.candidate = make_lettering(self.text.text(), self.font.currentFont().family(), self.height.value(), self.spacing.value(), self.previous, layout=self.layout_choice.currentData(), curve=self.curve.value(), baseline=self.baseline)
        except ValueError as exc:
            QMessageBox.warning(self, "Lettering", str(exc))
            return
        super().accept()
