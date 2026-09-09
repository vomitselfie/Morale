from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox, QComboBox, QDialogButtonBox, QCheckBox


class TransformDialog(QDialog):
    def __init__(self, count, parent=None, selection_size=None):
        super().__init__(parent)
        self.setWindowTitle("Transform selection")
        self.selection_size = selection_size
        layout = QVBoxLayout(self)
        note = QLabel(f"Scale and rotate {count} selected object(s) together. Digitized shapes regenerate stitches; scaling manual stitches changes their density. Unequal axis scales convert primitives and lettering to editable outlines; Bezier curves remain editable. Sizes describe source geometry before rotation, excluding stitch compensation and motif extensions.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        self.scale = QDoubleSpinBox()
        self.scale_y = QDoubleSpinBox()
        for widget, name in ((self.scale,"Horizontal selection scale"),(self.scale_y,"Vertical selection scale")):
            widget.setRange(5, 1000)
            widget.setDecimals(4)
            widget.setValue(100)
            widget.setSuffix(" %")
            widget.setAccessibleName(name)
        self.lock = QCheckBox("Keep proportions")
        self.lock.setChecked(True)
        form.addRow(self.lock)
        form.addRow("Horizontal scale",self.scale)
        form.addRow("Vertical scale",self.scale_y)
        self.target_width = QDoubleSpinBox()
        self.target_height = QDoubleSpinBox()
        if selection_size is not None:
            for widget, size, name in zip((self.target_width,self.target_height),selection_size,("Width before rotation","Height before rotation")):
                widget.setDecimals(4)
                widget.setRange(size*.05,size*10)
                widget.setValue(size)
                widget.setSuffix(" mm")
                widget.setEnabled(size>0)
                widget.setAccessibleName(name)
                form.addRow(name,widget)
        self.rotation = QDoubleSpinBox()
        self.rotation.setRange(-360, 360)
        self.rotation.setSuffix("°")
        self.rotation.setAccessibleName("Selection rotation")
        self.origin = QComboBox()
        self.origin.addItem("Selection bounds center", "selection")
        self.origin.addItem("Sewing-field center", "hoop")
        self.origin.setAccessibleName("Transformation center")
        form.addRow("Rotation",self.rotation)
        form.addRow("About",self.origin)
        layout.addLayout(form)
        self.scale.valueChanged.connect(lambda value:self.changed(0,value))
        self.scale_y.valueChanged.connect(lambda value:self.changed(1,value))
        self.lock.toggled.connect(lambda checked:self.changed(0,self.scale.value()) if checked else None)
        if selection_size is not None:
            self.target_width.valueChanged.connect(lambda value:self.dimension_changed(0,value))
            self.target_height.valueChanged.connect(lambda value:self.dimension_changed(1,value))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def dimension_changed(self, axis, value):
        size = self.selection_size[axis]
        if size:
            (self.scale,self.scale_y)[axis].setValue(value/size*100)

    def changed(self, axis, value):
        if self.lock.isChecked():
            other = (self.scale_y,self.scale)[axis]
            other.blockSignals(True)
            other.setValue(value)
            other.blockSignals(False)
        if self.selection_size is not None:
            for widget,size,scale in zip((self.target_width,self.target_height),self.selection_size,(self.scale,self.scale_y)):
                widget.blockSignals(True)
                widget.setValue(size*scale.value()/100)
                widget.blockSignals(False)
