"""Review editable fabric stitch settings before applying to a selection."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLabel,QComboBox,QDoubleSpinBox,QDialogButtonBox,QPushButton,QFileDialog,QMessageBox,QScrollArea,QWidget,QLayout
from .fabric import PROFILES
from PySide6.QtWidgets import QCheckBox


class FabricDialog(QDialog):
    def __init__(self,parent=None,initial_settings=None):
        super().__init__(parent)
        self.setWindowTitle('Fabric settings')
        outer=QVBoxLayout(self)
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        content=QWidget();layout=QVBoxLayout(content)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll.setWidget(content);outer.addWidget(scroll)
        self.resize(560,650)
        note=QLabel('Experimental starting points for selected fill and satin objects. Adjust after a test sewout on your fabric and stabilizer. Other stitch types keep their settings.')
        note.setWordWrap(True);layout.addWidget(note)
        self.context=QLabel('Starting-point values shown. Applying replaces the selected objects’ fabric settings.' if initial_settings is None else 'Current selection settings shown.')
        self.context.setWordWrap(True);layout.addWidget(self.context)
        form=QFormLayout();layout.addLayout(form)
        self.profile=QComboBox();self.profile.addItems(PROFILES)
        self.profile.setAccessibleName('Fabric starting point');form.addRow('Fabric',self.profile)
        self.fields={}
        for key,label,low,high,step in (
            ('spacing','Cover row spacing',.2,5,.05),
            ('pull_compensation','Pull compensation per side',0,2,.05),
            ('underlay_inset','Underlay inset',0,3,.1),
            ('underlay_spacing','Underlay row spacing',.5,10,.1)):
            spin=QDoubleSpinBox();spin.setRange(low,high);spin.setDecimals(2);spin.setSingleStep(step);spin.setSuffix(' mm')
            spin.setAccessibleName(label);form.addRow(label,spin);self.fields[key]=spin
        self.style=QComboBox()
        for label,value in [('Edge run','edge'),('Edge and sparse fill','edge_sparse'),('Sparse fill','sparse')]:self.style.addItem(label,value)
        self.style.setAccessibleName('Fill underlay');form.addRow('Fill underlay',self.style)
        self.underlay=QCheckBox('Enable underlay');self.underlay.setChecked(True);form.addRow(self.underlay)
        self.underlay.toggled.connect(self.update_underlay_controls)
        hint=QLabel('Satin uses a center run for Edge run, or center + zigzag for the other choices. Existing gradient spacing and finishing settings are retained.')
        hint.setWordWrap(True);layout.addWidget(hint)
        for title,callback in [('Load fabric preset…',self.load_file),('Save fabric preset…',self.save_file)]:
            button=QPushButton(title);button.clicked.connect(callback);layout.addWidget(button)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Apply to selection')
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);outer.addWidget(buttons)
        self.profile.currentTextChanged.connect(self.load_profile);self.load_profile(self.profile.currentText())
        if initial_settings is not None:
            self.set_settings(initial_settings)
            self.context.setText('Current selection settings shown.')
        for key,field in self.fields.items():field.valueChanged.connect(lambda _,key=key:self.edited(key))
        self.style.currentIndexChanged.connect(lambda _:self.edited('underlay_style'))
        self.underlay.toggled.connect(lambda _:self.edited('underlay'))

    def update_underlay_controls(self,enabled):
        for widget in (self.style,self.fields['underlay_inset'],self.fields['underlay_spacing']):widget.setEnabled(enabled)

    def edited(self,key):
        if getattr(self,'_loading',False):return
        if self._exact_settings is not None:self._exact_settings.pop(key,None)
        self.profile.blockSignals(True);self.profile.setCurrentIndex(-1);self.profile.blockSignals(False)
        self.context.setText('Custom values shown. Applying replaces the selected objects’ fabric settings.')

    def set_settings(self,settings):
        from .fabric import validate_settings
        settings=validate_settings(settings)
        self._loading=True
        self._exact_settings=dict(settings)
        for key,field in self.fields.items():field.setValue(settings[key])
        self.style.setCurrentIndex(self.style.findData(settings['underlay_style']))
        self.underlay.setChecked(settings.get('underlay',True))
        self.profile.blockSignals(True);self.profile.setCurrentIndex(-1);self.profile.blockSignals(False)
        self._loading=False

    def load_profile(self,name):
        self._loading=True
        self._exact_settings=None
        self.context.setText('Starting-point values shown. Applying replaces the selected objects’ fabric settings.')
        spacing,pull,style,inset,underlay=PROFILES[name]
        for key,value in dict(spacing=spacing,pull_compensation=pull,underlay_inset=inset,underlay_spacing=underlay).items():self.fields[key].setValue(value)
        self.style.setCurrentIndex(self.style.findData(style))
        self.underlay.setChecked(True)
        self._loading=False

    def settings(self):
        values={key:field.value() for key,field in self.fields.items()}
        original=getattr(self,'_exact_settings',None)
        if original:
            for key in values:
                if key in original:values[key]=original[key]
        result=dict(values,underlay_style=self.style.currentData())
        if not self.underlay.isChecked():result['underlay']=False
        return result

    def load_file(self):
        from .fabric_presets import load_preset
        path,_=QFileDialog.getOpenFileName(self,'Load fabric preset','','Morale fabric presets (*.morale-fabric.json)')
        if not path:return
        try:settings=load_preset(path)
        except (ValueError,OSError) as exc:
            QMessageBox.warning(self,'Fabric preset',str(exc));return
        self.set_settings(settings)
        self.context.setText('Loaded custom preset values shown.')

    def save_file(self):
        from .fabric_presets import save_preset
        path,_=QFileDialog.getSaveFileName(self,'Save fabric preset','fabric.morale-fabric.json','Morale fabric presets (*.morale-fabric.json)')
        if not path:return
        try:save_preset(path,self.settings())
        except (ValueError,OSError) as exc:QMessageBox.warning(self,'Fabric preset',str(exc))
