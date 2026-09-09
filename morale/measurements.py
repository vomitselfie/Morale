"""Unit presentation only: all document and machine geometry stays in mm."""
import math
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, QDialogButtonBox, QLabel


def factor(unit):
    return 25.4 if unit == "in" else 1.


def dimension(value, unit):
    return f"{value / factor(unit):.3f}".rstrip("0").rstrip(".") + f" {unit}"


def validate_hoop(width, height):
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not 20 <= v <= 500 for v in (width, height)):
        raise ValueError("Hoop dimensions must be between 20 and 500 mm.")


class HoopDialog(QDialog):
    def __init__(self, width, height, unit="mm", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom sewing field")
        self.unit = unit
        self.original = (width, height)
        layout = QVBoxLayout(self)
        note = QLabel("Enter the usable rectangular sewing field, not the hoop's outer size.\nThe app does not certify compatibility with a particular machine.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        self.fields = []
        for title, value in zip(("Width", "Height"), self.original):
            spin = QDoubleSpinBox()
            spin.setDecimals(4 if unit == "in" else 2)
            spin.setRange(20 / factor(unit), 500 / factor(unit))
            spin.setSuffix(f" {unit}")
            spin.setValue(value / factor(unit))
            spin.setAccessibleName(f"Sewing field {title.lower()}")
            self.fields.append(spin)
            form.addRow(title, spin)
        self.initial = [spin.value() for spin in self.fields]
        layout.addLayout(form)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)

    def dimensions(self):
        return tuple(original if spin.value() == initial else min(500, max(20, spin.value() * factor(self.unit)))
                     for spin, original, initial in zip(self.fields, self.original, self.initial))
