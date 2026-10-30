"""Choose the setting and values for test swatches of the selection."""
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout

from .swatches import MAX_SWATCHES, SETTINGS

# Suggested range around the selection's current value.
SUGGESTED = {"spacing": (-.1, .1), "pull_compensation": None, "stitch_length": (-1, 1), "angle": None}
FIXED = {"pull_compensation": (0, .4), "angle": (0, 90)}


class SwatchDialog(QDialog):
    def __init__(self, selected, parent=None):
        super().__init__(parent)
        self.selected = selected
        self.setWindowTitle("Test swatches")
        layout = QVBoxLayout(self)
        note = QLabel("Makes a new design with copies of the selected parts, each sewn with a different "
                      "value of one setting and labelled with it. Sew it on your real fabric and "
                      "stabilizer, then use the value that looks best. Your current design stays open "
                      "until you choose to replace it.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        self.setting = QComboBox(); self.setting.setAccessibleName("Setting to test")
        for key, (title, *_rest) in SETTINGS.items():
            self.setting.addItem(title, key)
        self.start = QDoubleSpinBox(); self.start.setAccessibleName("First value")
        self.stop = QDoubleSpinBox(); self.stop.setAccessibleName("Last value")
        self.count = QSpinBox(); self.count.setAccessibleName("Number of swatches")
        self.count.setRange(2, MAX_SWATCHES); self.count.setValue(5)
        self.labels = QCheckBox("Sew each value beside its swatch"); self.labels.setChecked(True)
        form.addRow("Setting", self.setting)
        form.addRow("From", self.start)
        form.addRow("To", self.stop)
        form.addRow("Swatches", self.count)
        form.addRow(self.labels)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setting.currentIndexChanged.connect(self.setting_changed)
        self.setting_changed()

    def setting_changed(self, *args):
        key = self.setting.currentData()
        _, low, high, types = SETTINGS[key]
        decimals = 0 if key == "angle" else 2
        for box in (self.start, self.stop):
            box.setDecimals(decimals); box.setRange(low, high); box.setSingleStep(1 if key == "angle" else .05)
        if key in FIXED:
            start, stop = FIXED[key]
        else:
            using = [obj for obj in self.selected if obj.stitch_type in types]
            current = getattr(using[0], key) if using else (low + high) / 2
            below, above = SUGGESTED[key]
            start, stop = max(low, current + below), min(high, current + above)
        self.start.setValue(start); self.stop.setValue(stop)

    def request(self):
        return {"key": self.setting.currentData(), "start": round(self.start.value(), 3),
                "stop": round(self.stop.value(), 3), "count": self.count.value(), "labels": self.labels.isChecked()}
