from copy import deepcopy
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, QCheckBox, QDialogButtonBox, QLabel


class ReferenceDialog(QDialog):
    def __init__(self, reference, parent=None):
        super().__init__(parent)
        self.reference = deepcopy(reference)
        self.setWindowTitle("Reference image settings")
        layout = QVBoxLayout(self)
        label = QLabel(reference["name"] + "\nReference only: this image is never included in machine exports.")
        label.setWordWrap(True)
        layout.addWidget(label)
        form = QFormLayout()
        self.fields = {}
        for key, name, low, high, suffix in [("x", "X", -1000, 1000, " mm"), ("y", "Y", -1000, 1000, " mm"),
                ("width", "Width", .1, 500, " mm"), ("height", "Height", .1, 500, " mm"),
                ("rotation", "Rotation", -360, 360, "°"), ("opacity", "Opacity", 0, 1, "")]:
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(low, high)
            spin.setSingleStep(.05 if key == "opacity" else 1)
            spin.setSuffix(suffix)
            spin.setValue(reference[key])
            spin.setAccessibleName("Reference " + name.lower())
            self.fields[key] = spin
            form.addRow(name, spin)
        self.initial = {key: spin.value() for key, spin in self.fields.items()}
        self.visible = QCheckBox("Show reference")
        self.visible.setChecked(reference["visible"])
        form.addRow(self.visible)
        layout.addLayout(form)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)

    def result_reference(self):
        result = deepcopy(self.reference)
        for key, spin in self.fields.items():
            if spin.value() != self.initial[key]:
                result[key] = spin.value()
        result["visible"] = self.visible.isChecked()
        return result
