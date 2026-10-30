"""Preview raster digitizing in a cancellable subprocess before applying it."""
import base64
import json
import sys
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt,QRectF,QSignalBlocker
from PySide6.QtGui import QImage,QPixmap,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QSpinBox,QDoubleSpinBox,QComboBox,QCheckBox,QPushButton,QDialogButtonBox,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QHeaderView,QPlainTextEdit,QScrollArea,QWidget,QStackedWidget,QTabWidget

from .library import PreviewRunner
from .model import Project


class TraceRunner(PreviewRunner):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.options={}

    def command(self,path,directory):
        args=[path,directory,json.dumps(self.options)]
        return (sys.executable,['--trace-worker',*args]) if getattr(sys,'frozen',False) else (sys.executable,['-m','morale.raster_trace','--worker',*args])


class TraceDialog(QDialog):
    def __init__(self,path,parent=None):
        super().__init__(parent)
        self.path=path
        self.project=None
        self.source_fingerprint=None
        self.source_digest=None
        self.source_corrections_reset=False
        self.svg=''
        self.overrides={}
        self.region_spacing={}
        self.region_angles={}
        self.seams={}
        self.quality=None
        self.runner=TraceRunner(self)
        self.runner.ready.connect(self.ready)
        self.runner.failed.connect(self.failed)
        self.setWindowTitle('Digitize artwork')
        main_layout=QVBoxLayout(self)
        self.tabs=QTabWidget();self.tabs.setAccessibleName('Artwork conversion steps')
        main_layout.addWidget(self.tabs,1)
        def settings_page(title):
            page=QWidget();page_layout=QVBoxLayout(page);form=QFormLayout()
            page_layout.addLayout(form);page_layout.addStretch()
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page)
            self.tabs.addTab(scroll,title)
            return form
        artwork_form=settings_page('Artwork')
        stitch_form=settings_page('Stitches')
        travel_form=settings_page('Travel and finishing')
        self.preview_page=QWidget();layout=QVBoxLayout(self.preview_page)
        self.preview_scroll=QScrollArea();self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setAccessibleName('Artwork conversion preview')
        self.preview_scroll.setWidget(self.preview_page)
        self.tabs.addTab(self.preview_scroll,'Preview')
        text=QLabel('Convert logos and illustrations into editable embroidery. Compare the artwork, fitted shapes and stitches before adding them to your design.')
        text.setWordWrap(True)
        main_layout.insertWidget(0,text)
        form=artwork_form
        self.method=QComboBox()
        self.method.addItem('Smooth color trace','smooth')
        self.method.addItem('Pixel regions (comparison)','pixels')
        self.method.setAccessibleName('Tracing method')
        form.addRow('Tracing method',self.method)
        form=stitch_form
        self.stitch_mode=QComboBox()
        self.stitch_mode.addItem('Automatic: running, satin or fill','auto')
        self.stitch_mode.addItem('Fill every region','fill')
        form.addRow('Stitch selection',self.stitch_mode)
        self.custom_stitches=QCheckBox('Customize generated stitch settings')
        form.addRow(self.custom_stitches)
        self.stitch_settings={}
        for key,title,low,high,default in [('fill_spacing','Fill row spacing',.2,5,.45),
                ('satin_spacing','Satin spacing',.2,5,.45),('stitch_length','Stitch length',.5,6,2.5),
                ('pull_compensation','Pull compensation',0,2,0),
                ('underlay_inset','Underlay inset',0,3,0),('underlay_spacing','Underlay spacing',.5,10,2)]:
            control=QDoubleSpinBox();control.setRange(low,high);control.setDecimals(2)
            control.setSingleStep(.05);control.setValue(default);control.setSuffix(' mm')
            control.setAccessibleName(title);control.setEnabled(False)
            self.stitch_settings[key]=control;form.addRow(title,control)
            self.custom_stitches.toggled.connect(control.setEnabled)
            control.valueChanged.connect(self.invalidate_preview)
        self.trace_underlay=QComboBox()
        for title,value in [('Keep generated underlay','keep'),('Disable underlay','off'),('Automatic underlay','auto')]:self.trace_underlay.addItem(title,value)
        self.trace_underlay.setEnabled(False);self.trace_underlay.setAccessibleName('Converted fill and satin underlay')
        form.addRow('Underlay',self.trace_underlay)
        self.custom_stitches.toggled.connect(self.trace_underlay.setEnabled)
        self.underlay_choices={}
        for key,title,styles in [('fill_underlay','Fill underlay',[('Automatic','auto'),('Edge run','edge'),('Sparse fill','sparse'),('Edge run and sparse fill','edge_sparse')]),
                ('satin_underlay','Satin underlay',[('Center run','auto'),('Zigzag','zigzag'),('Center run and zigzag','center_zigzag')])]:
            control=QComboBox()
            for label,value in [('Use general underlay choice','keep'),('Disabled','off'),*styles]:control.addItem(label,value)
            control.setEnabled(False);control.setAccessibleName(title)
            control.setToolTip('Overrides the general underlay choice for this stitch type. Inset and spacing apply to support stitches; preview before applying.')
            self.underlay_choices[key]=control;form.addRow(title,control)
            self.custom_stitches.toggled.connect(control.setEnabled)
            control.currentIndexChanged.connect(self.invalidate_preview)
        self.custom_stitches.setToolTip('Apply these values after stitch selection, before travel planning. Spacing and compensation affect fill/satin; underlay does not add stitches to running paths. Inspect the regenerated preview and density maps.')

        form=artwork_form
        self.branching=QCheckBox('Split suitable branching shapes into editable pieces')
        self.branching.setToolTip('Try separate columns at branch joins. Inspect joins after generation. Changing this setting clears region overrides.')
        form.addRow(self.branching)
        self.branch_overlap=QDoubleSpinBox();self.branch_overlap.setRange(0,1);self.branch_overlap.setSingleStep(.1)
        self.branch_overlap.setValue(.3);self.branch_overlap.setSuffix(' mm');self.branch_overlap.setEnabled(False)
        self.branch_overlap.setSpecialValueText('Exact joins')
        self.branch_overlap.setToolTip('Extend one piece across each branch cut so satin columns overlap instead of just meeting. Extensions stay inside the artwork. Zero leaves exact joins, which can gap under fabric pull.')
        form.addRow('Branch join overlap',self.branch_overlap)
        form=travel_form
        self.optimize_angles=QCheckBox('Choose fill angles with less travel')
        self.optimize_angles.setToolTip('Compare generated travel, including transfers to neighboring objects. Changes the visual grain of fill; inspect the preview. Final angles remain editable.')
        form.addRow(self.optimize_angles)
        self.route_fill=QCheckBox('Reduce travel between fill runs (up to 2,000 per region)')
        self.route_fill.setToolTip('Reorder and reverse disconnected sewn runs while keeping entry/exit and sewn segment geometry. Transfers remain jumps. Larger fills keep scanline order.')
        form.addRow(self.route_fill)
        form=artwork_form
        self.remove_overlap=QCheckBox('Remove fill covered by later artwork')
        self.remove_overlap.setToolTip('Reduce stacked fill layers while retaining a seam allowance under upper regions. Review the stitch preview; the prepared SVG retains the original artwork.')
        form.addRow(self.remove_overlap)
        self.overlap_allowance=QDoubleSpinBox();self.overlap_allowance.setRange(0,2);self.overlap_allowance.setSingleStep(.1)
        self.overlap_allowance.setValue(.2);self.overlap_allowance.setSuffix(' mm');self.overlap_allowance.setEnabled(False)
        form.addRow('Overlap allowance',self.overlap_allowance)
        self.minimum_fill_area=QDoubleSpinBox();self.minimum_fill_area.setRange(0,25);self.minimum_fill_area.setSingleStep(.1)
        self.minimum_fill_area.setSuffix(' mm²');self.minimum_fill_area.setSpecialValueText('Keep all filled details')
        self.minimum_fill_area.setToolTip('After overlap removal, omit filled islands smaller than this physical area, subtracting their holes. Running outlines are retained. Inspect lost detail in the stitch preview.')
        form.addRow('Minimum filled detail',self.minimum_fill_area)
        self.minimum_hole_area=QDoubleSpinBox();self.minimum_hole_area.setRange(0,25);self.minimum_hole_area.setSingleStep(.1)
        self.minimum_hole_area.setSuffix(' mm²');self.minimum_hole_area.setSpecialValueText('Keep all holes')
        self.minimum_hole_area.setToolTip('Close holes below this physical void area before stitch selection. This adds material and can cover detail; compare against the source.')
        form.addRow('Fill holes smaller than',self.minimum_hole_area)
        form=stitch_form
        thread_row=QHBoxLayout()
        self.thread_catalog=QComboBox()
        from .catalogs import BUILTIN_CATALOGS
        for title,value in (('Keep artwork colors',''),*((name,name) for name in BUILTIN_CATALOGS)):
            self.thread_catalog.addItem(title,value)
        self.thread_catalog.setAccessibleName('Trace thread chart')
        self.thread_catalog.setToolTip('Built-ins are machine palettes; import CSV, INF or EDR to use your own thread palette. The traced SVG retains artwork colors.')
        thread_row.addWidget(self.thread_catalog,1)
        load_threads=QPushButton('Import palette…');load_threads.clicked.connect(self.load_thread_chart)
        thread_row.addWidget(load_threads);form.addRow('Thread chart',thread_row)
        self.color_metric=QComboBox()
        self.color_metric.addItem('Perceptual (Oklab)','oklab');self.color_metric.addItem('RGB distance (comparison)','rgb')
        self.color_metric.setToolTip('Oklab compares estimated lightness and color differences from sRGB swatches. Neither method predicts physical thread appearance.')
        form.addRow('Color matching',self.color_metric)
        self.distinct_threads=QCheckBox('Keep different artwork colors on different threads')
        self.distinct_threads.setChecked(True)
        self.distinct_threads.setToolTip('Plan the whole palette at once so two clearly different colors never share a thread, choosing the combination with the least total color error. Colors that are nearly identical may still share. With no conflicts this matches nearest-thread matching.')
        self.distinct_threads.toggled.connect(self.invalidate_preview)
        form.addRow(self.distinct_threads)
        form=travel_form
        self.group_colors=QCheckBox('Group regions by thread to reduce color changes')
        self.group_colors.setToolTip('Move regions that do not overlap anything in between so each thread sews in fewer runs. Overlapping regions keep their layer order; stops and appliqué stages are not crossed.')
        form.addRow(self.group_colors)
        self.route=QCheckBox('Reduce travel within each thread-color run')
        self.group_colors.toggled.connect(self.invalidate_preview)
        self.route.setToolTip('Reorder separated regions using generated stitch endpoints. Overlapping regions keep their order. Distances start at the artwork origin.')
        form.addRow(self.route)
        self.reverse_travel=QCheckBox('Allow open columns and paths to sew in reverse')
        self.reverse_travel.setEnabled(False)
        self.reverse_travel.setToolTip('Compare generated entry/exit points in both directions. Closed-band seams and explicit stage/group boundaries are preserved.')
        form.addRow(self.reverse_travel)
        finishing_row=QHBoxLayout()
        self.finishing=QCheckBox('Add ties and trims between separated regions')
        self.finishing.setToolTip('Tie the design ends and separate long transfers, thread changes and stops. Object ties also lock internal sewn runs. Enable internal trimming below to trim within regions too.')
        finishing_row.addWidget(self.finishing)
        self.trim_threshold=QDoubleSpinBox();self.trim_threshold.setRange(.5,50);self.trim_threshold.setValue(5);self.trim_threshold.setSuffix(' mm')
        self.trim_threshold.setAccessibleName('Long transfer trim threshold');self.trim_threshold.setEnabled(False)
        finishing_row.addWidget(self.trim_threshold);form.addRow(finishing_row)
        self.internal_trims=QCheckBox('Also trim long travel inside regions')
        self.internal_trims.setEnabled(False);form.addRow(self.internal_trims)
        form=artwork_form
        self.width=QDoubleSpinBox()
        self.width.setRange(1,300)
        self.width.setValue(80)
        self.width.setSuffix(' mm')
        self.width.setAccessibleName('Traced artwork width')
        form.addRow('Artwork width',self.width)
        self.colors=QSpinBox()
        self.colors.setRange(1,16)
        self.colors.setValue(6)
        self.colors.setAccessibleName('Maximum trace colors')
        form.addRow('Maximum colors',self.colors)
        self.palette_metric=QComboBox()
        self.palette_metric.addItem('Perceptual (Oklab)','oklab');self.palette_metric.addItem('RGB (comparison)','rgb')
        self.palette_metric.setAccessibleName('Raster palette reduction')
        self.palette_metric.setToolTip('Reduce sampled artwork colors before tracing. Oklab fits a population-weighted palette using up to 4,096 color bins; compare against the source for lost detail.')
        form.addRow('Palette reduction',self.palette_metric)
        self.resolution=QComboBox()
        for size in (64,128,256,512,1024): self.resolution.addItem(f'{size} pixels',size)
        self.resolution.setCurrentIndex(3)
        self.resolution.setAccessibleName('Trace sampling resolution')
        form.addRow('Longest sampled side',self.resolution)
        self.smoothing=QDoubleSpinBox()
        self.smoothing.setRange(0,1); self.smoothing.setDecimals(2); self.smoothing.setSingleStep(.05); self.smoothing.setValue(.25); self.smoothing.setSuffix(' mm')
        self.smoothing.setAccessibleName('Curve simplification tolerance')
        self.smoothing.setToolTip('Simplify fitted curves at the intended embroidery size. Larger values remove more small contour detail; this is not a total tracing-error guarantee.')
        form.addRow('Curve simplification',self.smoothing)
        self.minimum=QSpinBox()
        self.minimum.setRange(1,100)
        self.minimum.setValue(4)
        self.minimum.setAccessibleName('Minimum region pixels')
        self.minimum_label=QLabel('Minimum detail size (pixels)')
        self.minimum.setToolTip('Smooth tracing filters patches smaller than approximately this size squared in pixels. Pixel-region tracing uses a pixel-area threshold instead.')
        form.addRow(self.minimum_label,self.minimum)
        self.white=QCheckBox('Exclude near-white background')
        self.white.setChecked(True)
        form.addRow(self.white)
        self.border_white=QCheckBox('Preserve enclosed white details')
        self.border_white.setToolTip('Remove near-white only where it connects to the page edge through white or transparency. Enclosed white enters color reduction; allow enough palette colors to retain it.')
        form.addRow(self.border_white)
        existing_reference=bool(getattr(getattr(parent,'project',None),'reference',{}))
        self.keep_reference=QCheckBox('Replace existing reference with sampled artwork' if existing_reference else 'Keep sampled artwork as a reference image')
        self.keep_reference.setChecked(not existing_reference)
        self.keep_reference.setToolTip('Embed the sampled sRGB artwork at its traced physical size for later comparison. It does not add machine stitches.')
        form.addRow(self.keep_reference)
        self.expand_strokes=QCheckBox('Expand SVG strokes into satin or fill regions')
        self.expand_strokes.setToolTip('Use the drawn border width, caps, joins and dash pattern (numbers or absolute lengths). Inspect overlaps with adjacent fills. Changing this setting clears region overrides.')
        form.addRow(self.expand_strokes)
        form.setRowVisible(self.expand_strokes,Path(path).suffix.lower()=='.svg')
        self.artwork_form=artwork_form
        self.render_svg=QCheckBox('Trace SVG colors and gradients')
        self.render_svg.setToolTip('Reduce rendered SVG colors to editable thread-color regions. Clips, masks, opacity and stroke widths are rendered before color reduction.')
        form.addRow(self.render_svg)
        form.setRowVisible(self.render_svg,Path(path).suffix.lower()=='.svg')
        if Path(path).suffix.lower()=='.svg':
            self.method.setItemText(0,'SVG vectors (no raster tracing)');self.method.setEnabled(False)
            self.stitch_mode.setItemText(1,'Fill regions; retain SVG outlines')
            for widget in (self.colors,self.palette_metric,self.resolution,self.smoothing,self.minimum,self.white,self.border_white):form.setRowVisible(widget,False)
        images=QHBoxLayout()
        self.original=QLabel('Sampled source')
        self.vector_preview=QLabel('Vector outlines')
        self.preview=QLabel('Generated stitch preview')
        self.preview.setToolTip('Blue circles mark sewing starts on closed satin bands and closed running paths.')
        for title,label in (('Sampled source',self.original),('Traced vectors',self.vector_preview),('Embroidery stitches',self.preview)):
            column=QVBoxLayout()
            heading=QLabel(title); heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(heading)
            label.setMinimumSize(240,280)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(label,1)
            images.addLayout(column,1)
        layout.addLayout(images,1)
        self.decisions=QTableWidget(0,7)
        self.decisions.setWordWrap(False)
        self.decisions.setHorizontalHeaderLabels(['Region','Use','Result','Reason','Band seam','Spacing (mm)','Fill angle'])
        self.decisions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.decisions.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        self.decisions.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.decisions.setMinimumHeight(110)
        self.decisions.setMaximumHeight(160)
        self.decisions.setAccessibleName('Region stitch choices')
        layout.addWidget(self.decisions)
        self.region_reason=QLabel('Select a region to read its stitch explanation.')
        self.region_reason.setWordWrap(True)
        self.region_reason.setTextFormat(Qt.TextFormat.PlainText)
        self.region_reason.setAccessibleName('Selected region stitch explanation')
        layout.addWidget(self.region_reason)
        self.decisions.currentCellChanged.connect(self.show_region_reason)
        self.reset_selected_region=QPushButton('Reset selected region corrections')
        self.reset_selected_region.setEnabled(False)
        self.reset_selected_region.setToolTip('Clear stitch choice, band seam, spacing and angle overrides for the selected artwork region. Other regions keep their corrections.')
        self.reset_selected_region.clicked.connect(self.reset_region_corrections)
        self.decisions.currentCellChanged.connect(lambda row,*_:self.reset_selected_region.setEnabled(row>=0))
        layout.addWidget(self.reset_selected_region)
        reset_spacing=QPushButton("Reset region spacing to global settings")
        reset_spacing.clicked.connect(self.reset_region_spacing);layout.addWidget(reset_spacing)
        self.lock_selected_angle=QPushButton('Lock selected fill angle')
        self.lock_selected_angle.setToolTip('Keep the selected region’s displayed fill direction during automatic angle search, without changing its value.')
        self.lock_selected_angle.clicked.connect(self.lock_region_angle)
        angle_actions=QHBoxLayout();angle_actions.addWidget(self.lock_selected_angle)
        self.unlock_selected_angle=QPushButton('Unlock selected fill angle')
        self.unlock_selected_angle.setToolTip('Release only this region’s angle lock. Keep spacing, stitch choice and other regions’ corrections.')
        self.unlock_selected_angle.clicked.connect(self.unlock_region_angle)
        angle_actions.addWidget(self.unlock_selected_angle);layout.addLayout(angle_actions)
        reset_angles=QPushButton("Reset region fill angles")
        reset_angles.clicked.connect(self.reset_region_angles);layout.addWidget(reset_angles)
        self.status=QLabel('Generate a preview. Changing settings invalidates the previous result. Each worker has a 30-second limit.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        main_layout.addWidget(self.status)
        row=QHBoxLayout()
        generate=QPushButton('Generate preview')
        generate.clicked.connect(self.generate)
        row.addWidget(generate)
        stop=QPushButton('Cancel tracing')
        stop.clicked.connect(self.invalidate)
        row.addWidget(stop)
        self.save_svg_button=QPushButton('Save traced SVG…')
        if Path(path).suffix.lower()=='.svg':self.save_svg_button.setText('Save prepared SVG…')
        self.save_svg_button.setEnabled(False); self.save_svg_button.clicked.connect(self.save_svg)
        row.addWidget(self.save_svg_button)
        self.quality_button=QPushButton('Conversion checks…')
        self.quality_button.setEnabled(False);self.quality_button.clicked.connect(self.show_quality)
        row.addWidget(self.quality_button)
        self.inspection_geometry={}
        self.aligned_images={}
        self.inspect_button=QPushButton('Inspect and overlay…');self.inspect_button.setEnabled(False)
        self.inspect_button.clicked.connect(self.inspect_artwork);layout.addWidget(self.inspect_button)
        self.density_image=QImage();self.thread_density_image=QImage();self.layers_image=QImage()
        from .coverage_review import FABRICS
        fabric_row=QHBoxLayout();fabric_label=QLabel('Fabric for guidance');fabric_row.addWidget(fabric_label)
        self.fabric=QComboBox();self.fabric.setAccessibleName('Fabric for density and detail guidance')
        for key,limits in FABRICS.items():self.fabric.addItem(limits['label'],key)
        self.fabric.setToolTip('Choose the fabric to review stacked layers, thread density and small details against. Guidance updates without regenerating; thresholds are starting points, not calibrated limits.')
        fabric_label.setBuddy(self.fabric);fabric_row.addWidget(self.fabric,1);layout.addLayout(fabric_row)
        self.density_button=QPushButton('Density and coverage review…');self.density_button.setEnabled(False)
        self.density_button.clicked.connect(self.show_density);layout.addWidget(self.density_button)
        self.review_snapshot=None
        self.review_button=QPushButton('Save conversion review PDF…');self.review_button.setEnabled(False)
        self.review_button.clicked.connect(self.save_review);layout.addWidget(self.review_button)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Add traced objects')
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        main_layout.addLayout(row)
        main_layout.addWidget(self.buttons)
        for widget in (self.width,self.colors,self.minimum,self.smoothing): widget.valueChanged.connect(self.invalidate)
        self.resolution.currentIndexChanged.connect(self.invalidate)
        self.white.toggled.connect(self.invalidate)
        self.white.toggled.connect(self.border_white.setEnabled)
        self.border_white.toggled.connect(self.invalidate)
        self.palette_metric.currentIndexChanged.connect(self.invalidate)
        self.method.currentIndexChanged.connect(self.method_changed)
        self.stitch_mode.currentIndexChanged.connect(self.invalidate)
        self.route.toggled.connect(self.invalidate_preview)
        self.route.toggled.connect(self.reverse_travel.setEnabled)
        self.reverse_travel.toggled.connect(self.invalidate_preview)
        self.thread_catalog.currentIndexChanged.connect(self.invalidate_preview)
        self.color_metric.currentIndexChanged.connect(self.invalidate_preview)
        self.custom_stitches.toggled.connect(self.invalidate_preview)
        self.trace_underlay.currentIndexChanged.connect(self.invalidate_preview)
        self.branching.toggled.connect(self.invalidate)
        self.branching.toggled.connect(self.branch_overlap.setEnabled)
        self.branch_overlap.valueChanged.connect(self.invalidate)
        self.optimize_angles.toggled.connect(self.invalidate_preview)
        self.route_fill.toggled.connect(self.invalidate_preview)
        self.remove_overlap.toggled.connect(self.overlap_allowance.setEnabled)
        self.remove_overlap.toggled.connect(self.invalidate)
        self.overlap_allowance.valueChanged.connect(self.invalidate)
        self.minimum_hole_area.valueChanged.connect(self.invalidate)
        self.minimum_fill_area.valueChanged.connect(self.invalidate)
        self.finishing.toggled.connect(self.trim_threshold.setEnabled)
        self.finishing.toggled.connect(self.internal_trims.setEnabled)
        self.finishing.toggled.connect(self.invalidate_preview)
        self.trim_threshold.valueChanged.connect(self.invalidate_preview)
        self.internal_trims.toggled.connect(self.invalidate_preview)
        self.keep_reference.toggled.connect(self.invalidate_preview)
        self.expand_strokes.toggled.connect(self.invalidate)
        self.render_svg.toggled.connect(self.svg_render_changed)
        self._preset_controls={
            'method':self.method,'stitch_mode':self.stitch_mode,'colors':self.colors,'resolution':self.resolution,
            'minimum_region':self.minimum,'smoothing':self.smoothing,'palette_metric':self.palette_metric,
            'color_metric':self.color_metric,'underlay':self.trace_underlay,'ignore_white':self.white,'border_white':self.border_white,
            'split_branches':self.branching,'branch_overlap':self.branch_overlap,'optimize_fill_angles':self.optimize_angles,'route_fill':self.route_fill,
            'remove_overlap':self.remove_overlap,'overlap_allowance':self.overlap_allowance,'minimum_fill_area':self.minimum_fill_area,'minimum_hole_area':self.minimum_hole_area,
            'reduce_travel':self.route,'group_colors':self.group_colors,'distinct_threads':self.distinct_threads,'reverse_for_travel':self.reverse_travel,'finish_regions':self.finishing,
            'internal_trims':self.internal_trims,'trim_threshold':self.trim_threshold,'expand_strokes':self.expand_strokes,'render_svg':self.render_svg,
            'custom_stitches':self.custom_stitches,**self.stitch_settings,**self.underlay_choices}
        preset_row=QHBoxLayout()
        preset_label=QLabel('Reuse tracing and stitch settings');preset_label.setWordWrap(True)
        preset_row.addWidget(preset_label,1)
        for title,slot in [('Load preset…',self.load_preset),('Save preset…',self.save_preset),('Load fabric…',self.load_fabric_preset)]:
            button=QPushButton(title);button.clicked.connect(slot)
            button.setToolTip('Presets contain tracing, stitch and travel settings. Choose artwork size, reference handling and thread chart separately.')
            preset_row.addWidget(button)
        main_layout.insertLayout(1,preset_row)
        self.resize(940,730)

    def preset_settings(self):
        from .trace_presets import validate
        settings={}
        for key,control in self._preset_controls.items():
            settings[key]=control.currentData() if isinstance(control,QComboBox) else control.isChecked() if isinstance(control,QCheckBox) else control.value()
        return validate(settings)

    def apply_preset(self,settings):
        from .trace_presets import validate
        settings=validate(settings)
        blockers=[QSignalBlocker(control) for control in self._preset_controls.values()]
        try:
            for key,value in settings.items():
                control=self._preset_controls[key]
                if key=='method' and Path(self.path).suffix.lower()=='.svg' and not settings['render_svg']:continue
                if isinstance(control,QComboBox):control.setCurrentIndex(control.findData(value))
                elif isinstance(control,QCheckBox):control.setChecked(value)
                else:control.setValue(value)
        finally:
            for blocker in blockers:blocker.unblock()
        self.border_white.setEnabled(self.white.isChecked())
        self.reverse_travel.setEnabled(self.route.isChecked())
        self.overlap_allowance.setEnabled(self.remove_overlap.isChecked())
        self.branch_overlap.setEnabled(self.branching.isChecked())
        self.trim_threshold.setEnabled(self.finishing.isChecked());self.internal_trims.setEnabled(self.finishing.isChecked())
        for control in [*self.stitch_settings.values(),self.trace_underlay,*self.underlay_choices.values()]:control.setEnabled(self.custom_stitches.isChecked())
        if Path(self.path).suffix.lower()=='.svg':self.svg_render_changed()
        else:self.method_changed()
        self.status.setText('Preset loaded. Review artwork size, reference handling and thread chart, then generate a new preview.')

    def apply_fabric_preset(self,settings):
        from .fabric import validate_settings
        settings=validate_settings(settings)
        changes=dict(custom_stitches=True,fill_spacing=settings['spacing'],satin_spacing=settings['spacing'],
                        pull_compensation=settings['pull_compensation'],underlay_inset=settings['underlay_inset'],
                        underlay_spacing=settings['underlay_spacing'],underlay='auto',fill_underlay=settings['underlay_style'],
                        satin_underlay='auto' if settings['underlay_style']=='edge' else 'center_zigzag')
        if not settings.get('underlay',True):changes.update(underlay='off',fill_underlay='off',satin_underlay='off')
        blockers=[QSignalBlocker(self._preset_controls[key]) for key in changes]
        try:
            for key,value in changes.items():
                control=self._preset_controls[key]
                if isinstance(control,QComboBox):control.setCurrentIndex(control.findData(value))
                elif isinstance(control,QCheckBox):control.setChecked(value)
                else:control.setValue(value)
        finally:
            for blocker in blockers:blocker.unblock()
        for control in [*self.stitch_settings.values(),self.trace_underlay,*self.underlay_choices.values()]:control.setEnabled(True)
        self.invalidate_preview()
        self.status.setText('Fabric settings loaded. Region corrections are retained; per-region spacing overrides fabric spacing. Generate a new preview before applying.')

    def load_fabric_preset(self):
        path,_=QFileDialog.getOpenFileName(self,'Load fabric preset','','Morale fabric presets (*.morale-fabric.json)')
        if not path:return
        try:
            from .fabric_presets import load_preset
            self.apply_fabric_preset(load_preset(path))
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'Fabric preset not loaded',str(exc))

    def load_preset(self):
        path,_=QFileDialog.getOpenFileName(self,'Load conversion preset','','Morale conversion preset (*.morale-trace.json)')
        if not path:return
        try:
            from .trace_presets import load_preset
            self.apply_preset(load_preset(path))
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'Preset not loaded',str(exc))

    def save_preset(self):
        path,_=QFileDialog.getSaveFileName(self,'Save conversion preset','conversion.morale-trace.json','Morale conversion preset (*.morale-trace.json)')
        if not path:return
        try:
            from .trace_presets import save_preset
            save_preset(path,self.preset_settings())
            self.status.setText(f'Saved conversion preset: {Path(path).name}')
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'Preset not saved',str(exc))

    def svg_render_changed(self):
        enabled=self.render_svg.isChecked()
        self.method.setEnabled(enabled)
        self.method.setItemText(0,'Smooth color trace' if enabled else 'SVG vectors (no raster tracing)')
        if not enabled:self.method.setCurrentIndex(0)
        self.stitch_mode.setItemText(1,'Fill regions' if enabled else 'Fill regions; retain SVG outlines')
        for widget in (self.colors,self.palette_metric,self.resolution,self.smoothing,self.minimum,self.white,self.border_white):
            self.artwork_form.setRowVisible(widget,enabled)
        self.artwork_form.setRowVisible(self.expand_strokes,not enabled)
        self.save_svg_button.setText('Save traced SVG…' if enabled else 'Save prepared SVG…')
        self.method_changed()

    def method_changed(self):
        smooth=self.method.currentData()=='smooth'
        self.minimum_label.setText('Minimum detail size (pixels)' if smooth else 'Omit regions below (pixel area)')
        self.smoothing.setEnabled(smooth)
        if not smooth and self.resolution.currentData()>256: self.resolution.setCurrentIndex(2)
        for index in range(self.resolution.count()):
            self.resolution.model().item(index).setEnabled(smooth or self.resolution.itemData(index)<=256)
        self.invalidate()

    def invalidate(self,*args):
        self.overrides={};self.seams={};self.region_spacing={};self.region_angles={}; self.decisions.setRowCount(0)
        self.invalidate_preview()

    def invalidate_preview(self):
        self.inspection_geometry={}
        self.aligned_images={};self.inspect_button.setEnabled(False)
        self.review_snapshot=None;self.review_button.setEnabled(False)
        self.density_image=QImage();self.thread_density_image=QImage();self.layers_image=QImage();self.density_button.setEnabled(False)
        self.quality=None;self.quality_button.setEnabled(False)
        self.runner.cancel()
        self.project=None
        self.show_region_reason(-1)
        self.svg=''; self.save_svg_button.setEnabled(False)
        self.vector_preview.setText('Vector outlines')
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.preview.setText('Generate a new preview')
        self.status.setText('Preview invalidated or tracing cancelled. Generate a preview to apply these settings.')

    def generate(self):
        self.tabs.setCurrentWidget(self.preview_scroll)
        self.source_corrections_reset=False
        if self.source_fingerprint is not None:
            try:
                current=Path(self.path).stat()
                if [current.st_size,current.st_mtime_ns]!=self.source_fingerprint:
                    self.invalidate();self.source_fingerprint=None
                    self.source_digest=None
                    self.source_corrections_reset=True
            except OSError as exc:
                self.failed(self.path,str(exc));return
        self.invalidate_preview()
        self.runner.options={'width':self.width.value(),'colors':self.colors.value(),'resolution':self.resolution.currentData(),
                             'ignore_white':self.white.isChecked(),'minimum_region':self.minimum.value(),
                             'method':self.method.currentData(),'smoothing':self.smoothing.value(),
                             'stitch_mode':self.stitch_mode.currentData(),'stitch_overrides':dict(self.overrides),
                             'reduce_travel':self.route.isChecked()}
        self.runner.options.update(group_colors=self.group_colors.isChecked(),distinct_threads=self.distinct_threads.isChecked())
        self.runner.options['border_white']=self.border_white.isChecked()
        self.runner.options['palette_metric']=self.palette_metric.currentData()
        self.runner.options['thread_catalog']=self.thread_catalog.currentData()
        self.runner.options['color_metric']=self.color_metric.currentData()
        self.runner.options['band_seams']=dict(self.seams)
        self.runner.options['region_spacing']=dict(self.region_spacing)
        self.runner.options['region_angles']=dict(self.region_angles)
        if self.source_fingerprint is not None:
            self.runner.options['expected_source']=self.source_fingerprint
        if self.source_digest is not None:self.runner.options['expected_source_digest']=self.source_digest
        self.runner.options['split_branches']=self.branching.isChecked()
        self.runner.options['branch_overlap']=self.branch_overlap.value()
        self.runner.options.update(finish_regions=self.finishing.isChecked(),trim_threshold=self.trim_threshold.value())
        self.runner.options['internal_trims']=self.internal_trims.isChecked()
        self.runner.options['reverse_for_travel']=self.reverse_travel.isChecked()
        self.runner.options['keep_reference']=self.keep_reference.isChecked()
        self.runner.options['expand_strokes']=self.expand_strokes.isChecked()
        self.runner.options['render_svg']=Path(self.path).suffix.lower()=='.svg' and self.render_svg.isChecked()
        self.runner.options.update(remove_overlap=self.remove_overlap.isChecked(),overlap_allowance=self.overlap_allowance.value())
        self.runner.options['minimum_fill_area']=self.minimum_fill_area.value()
        self.runner.options['minimum_hole_area']=self.minimum_hole_area.value()
        self.runner.options['optimize_fill_angles']=self.optimize_angles.isChecked()
        self.runner.options['route_fill']=self.route_fill.isChecked()
        if self.custom_stitches.isChecked():
            self.runner.options['stitch_settings']={key:control.value() for key,control in self.stitch_settings.items()}
            self.runner.options['stitch_settings']['underlay']=self.trace_underlay.currentData()
            self.runner.options['stitch_settings'].update({key:control.currentData() for key,control in self.underlay_choices.items()})
        self.status.setText('Tracing in a separate process…')
        if self.source_corrections_reset:self.status.setText('Artwork changed. Region corrections cleared; tracing with current global settings…')
        self.runner.load(self.path)

    def show_region_reason(self,row,*args):
        if self.project is None:
            self.region_reason.setText('Generate a new preview to review region stitch explanations.')
            return
        item=self.decisions.item(row,3) if row>=0 else None
        self.region_reason.setText(item.text() if item else 'Select a region to read its stitch explanation.')

    def ready(self,path,info,image):
        self.inspection_geometry={}
        self.aligned_images={};self.inspect_button.setEnabled(False)
        try:
            self.project=Project.loads(info['project'])
            self.source_fingerprint=info.get('source_fingerprint')
            self.source_digest=info.get('source_digest')
            original=QImage.fromData(base64.b64decode(info['raster_png']))
            if original.isNull(): raise ValueError('The sampled source preview is damaged.')
            self.original.setPixmap(QPixmap.fromImage(original).scaled(280,280,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            self.preview.setPixmap(QPixmap.fromImage(image).scaled(280,280,Qt.AspectRatioMode.KeepAspectRatio))
            stats=info['trace_stats']
            self.quality=stats.get('quality')
            self.density_image=QImage.fromData(base64.b64decode(info.get('density_png','')))
            self.thread_density_image=QImage.fromData(base64.b64decode(info.get('thread_density_png','')))
            self.layers_image=QImage.fromData(base64.b64decode(info.get('layers_png','')))
            self.density_button.setEnabled(not self.density_image.isNull())
            self.quality_button.setEnabled(self.quality is not None)
            decisions=stats.get('stitch_decisions',[])
            routing=stats.get('routing')
            sewing_order=stats.get('sewing_order') or (routing['order'] if routing else list(range(len(decisions))))
            self.decisions.setRowCount(len(decisions))
            for row,decision in enumerate(decisions):
                reason=decision['reason']
                if routing and row in routing.get('reversed_regions',[]):reason+=' Sewing direction reversed to reduce travel.'
                for col,value in ((0,f'{row+1} (sew {sewing_order.index(row)+1})'),(2,decision['selected'].title()),(3,reason)):
                    item=QTableWidgetItem(value); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setToolTip(value)
                    self.decisions.setItem(row,col,item)
                choice=QComboBox()
                for title,key in (('Automatic','auto'),('Fill','fill'),('Satin','satin'),('Running','running')): choice.addItem(title,key)
                choice.setCurrentIndex(choice.findData(decision['requested']))
                choice.setEnabled(not decision.get('fixed_stitch',False))
                choice.setProperty('region',row)
                choice.setAccessibleName(f'Region {row+1} stitch type')
                choice.currentIndexChanged.connect(self.region_choice_changed)
                self.decisions.setCellWidget(row,1,choice)
                spacing=QDoubleSpinBox();spacing.setRange(.2,5);spacing.setDecimals(2);spacing.setSingleStep(.05)
                spacing.setValue(decision.get('spacing_mm',.45));spacing.setProperty('region',row)
                spacing.setEnabled(decision['selected'] in {'fill','satin'})
                spacing.setAccessibleName(f'Region {row+1} stitch spacing')
                spacing.setToolTip('Overrides global spacing for this region. Regenerate the preview to review density.')
                spacing.valueChanged.connect(self.region_spacing_changed);self.decisions.setCellWidget(row,5,spacing)
                angle=QDoubleSpinBox();angle.setRange(0,359.9);angle.setDecimals(1);angle.setSingleStep(15);angle.setSuffix('°')
                angle.setValue(decision.get('angle_degrees',45)%360);angle.setProperty('region',row)
                angle.setEnabled(decision['selected']=='fill');angle.setAccessibleName(f'Region {row+1} fill angle')
                angle.setToolTip('Locks this region’s fill angle during automatic angle selection. Regenerate to review.')
                angle.valueChanged.connect(self.region_angle_changed);self.decisions.setCellWidget(row,6,angle)
                self.update_angle_lock_label(row)
                if decision.get('closed_band'):
                    seam=QDoubleSpinBox();seam.setRange(0,99.9);seam.setDecimals(1);seam.setSingleStep(5);seam.setSuffix('%')
                    seam.setValue(decision.get('seam_percent',0));seam.setProperty('region',row)
                    seam.setAccessibleName(f'Region {row+1} band seam')
                    seam.setEnabled(decision['requested']!='fill' and not decision.get('fixed_stitch',False))
                    seam.setToolTip('Distance around the outer boundary from its rightmost point, clockwise in the artwork view. Regenerate to move the sewing start or retry a band that fell back to fill. Explicit fill and fixed running outlines do not use this seam.')
                    seam.valueChanged.connect(self.seam_changed);self.decisions.setCellWidget(row,4,seam)
            self.svg=info.get('trace_svg','')
            if self.svg:
                renderer=QSvgRenderer(self.svg.encode('utf-8'))
                if not renderer.isValid(): raise ValueError('Traced SVG preview is invalid.')
                vector=QImage(280,280,QImage.Format.Format_ARGB32); vector.fill(Qt.GlobalColor.white)
                painter=QPainter(vector); renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio); renderer.render(painter,QRectF(0,0,280,280)); painter.end()
                self.vector_preview.setPixmap(QPixmap.fromImage(vector))
                self.save_svg_button.setEnabled(True)
            if info.get('aligned_previews'):
                for name,label in (('source',self.original),('vectors',self.vector_preview),('stitches',self.preview)):
                    panel=QImage.fromData(base64.b64decode(info['aligned_previews'][name]))
                    if panel.isNull() or panel.size().width()!=640 or panel.size().height()!=640:
                        raise ValueError('The aligned conversion preview is damaged.')
                    self.aligned_images[name]=panel
                    label.setPixmap(QPixmap.fromImage(panel).scaled(280,280,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
                    label.setToolTip('Same physical scale and position in all three panels. Dashed border marks the original artwork page. Blue circles mark closed-band sewing starts. Light stitches have a preview-only contrast outline.')
            self.inspection_geometry=info.get('inspection_svg',{})
            self.inspect_button.setEnabled(len(self.aligned_images)==3)
            if stats.get('method')=='svg':detail='Direct SVG geometry; raster tracing settings do not apply.'
            elif stats.get('method')=='smooth':detail=f"Smooth shared-boundary trace · {stats.get('thread_colors',stats['palette'])} thread colors · {stats['smoothing_mm']:.2f} mm simplification."
            else:detail=f"{stats['omitted_pixels']} small-region pixels omitted. Pixel boundaries can be stair-stepped."
            if routing:
                detail+=f" Travel from artwork origin: {routing['before_mm']:.1f} → {routing['after_mm']:.1f} mm."
                if routing.get('status')=='rejected':detail+=' Original route retained: '+routing.get('reason','Candidate validation failed.')
            if stats.get('branch_splits'):
                splits=stats['branch_splits'];joins=sum(s.get('joins',0) for s in splits);overlapped=sum(s.get('overlapped_joins',0) for s in splits)
                detail+=f" Split {len(splits)} branching regions; {overlapped} of {joins} joins overlapped. Inspect joins."
            if self.quality: detail+=f" Conversion checks: {self.quality['review_regions']} regions to review."
            fallbacks=sum(bool(d.get('fallback')) for d in decisions)
            if fallbacks:detail+=f' Fill retained for {fallbacks} unsuitable column regions. Select those regions to review the explanations.'
            if self.source_corrections_reset:detail+=' Artwork changed; previous region corrections were cleared.'
            self.status.setText(f"{len(self.project.objects)} editable regions · {info['stitches']:,} stitches · {stats['resolution'][0]} × {stats['resolution'][1]} sampled pixels. {detail} Inspect small details and stitch routing before sewing.")
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            self.show_region_reason(self.decisions.currentRow())
            from copy import deepcopy
            self.review_snapshot=(deepcopy(info),image.copy());self.review_button.setEnabled(True)
        except (KeyError,ValueError) as exc:
            self.failed(path,str(exc))

    def override_region(self,row,value):
        self.overrides[str(row)]=value
        self.invalidate_preview()
        self.status.setText('Region choice changed. Generate a preview to review the new stitches. Unsuitable satin or running regions remain fill with a reason.')

    def region_choice_changed(self):
        choice=self.sender()
        self.override_region(choice.property('region'),choice.currentData())

    def update_angle_lock_label(self,row):
        widget=self.decisions.cellWidget(row,6)
        if widget is None:return
        locked=str(row) in self.region_angles
        widget.setSuffix('° · locked' if locked else '°')
        widget.setAccessibleDescription('Fill angle locked; automatic angle search preserves this direction.' if locked else
            'Fill angle unlocked; automatic angle search may change this direction. Editing the value locks it.')

    def lock_region_angle(self):
        row=self.decisions.currentRow()
        widget=self.decisions.cellWidget(row,6) if row>=0 else None
        if widget is None or not widget.isEnabled():
            self.status.setText('Select a generated fill region to lock its displayed angle.')
            return
        self.region_angles[str(row)]=widget.value()
        self.update_angle_lock_label(row)
        self.invalidate_preview()
        self.status.setText(f'Region {row+1} fill angle locked at {widget.value():g}°. Generate a preview to review.')

    def unlock_region_angle(self):
        row=self.decisions.currentRow();key=str(row)
        if row<0 or key not in self.region_angles:
            self.status.setText('Select a region with a fill-angle lock to release it.')
            return
        del self.region_angles[key]
        self.update_angle_lock_label(row)
        self.invalidate_preview()
        self.status.setText(f'Region {row+1} fill angle unlocked. Generate a preview to use automatic or default angles. Other corrections are retained.')

    def reset_region_angles(self):
        self.region_angles.clear();self.invalidate_preview();self.decisions.setRowCount(0)
        self.status.setText('Region angle locks cleared. Generate a preview to use automatic or default angles.')

    def reset_region_corrections(self):
        row=self.decisions.currentRow()
        if row<0:return
        key=str(row)
        for overrides in (self.overrides,self.seams,self.region_spacing,self.region_angles):
            overrides.pop(key,None)
        self.invalidate_preview()
        for column in (1,4,5,6):self.decisions.removeCellWidget(row,column)
        for column,text in ((2,'Pending'),(3,'Corrections reset. Generate a preview.')):
            item=QTableWidgetItem(text);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.decisions.setItem(row,column,item)
        self.status.setText(f'Region {row+1} corrections cleared. Generate a preview to use the current global settings. Other regions keep their corrections.')

    def region_angle_changed(self):
        widget=self.sender();self.region_angles[str(widget.property('region'))]=widget.value()
        self.update_angle_lock_label(widget.property('region'))
        self.invalidate_preview()
        self.status.setText('Region fill angle changed. Generate a preview to review the stitch direction.')

    def reset_region_spacing(self):
        self.region_spacing.clear();self.invalidate_preview();self.decisions.setRowCount(0)
        self.status.setText("Region spacing reset. Generate a preview to use the global settings.")

    def region_spacing_changed(self):
        widget=self.sender();self.region_spacing[str(widget.property('region'))]=widget.value()
        self.invalidate_preview()
        self.status.setText('Region spacing changed. Generate a preview to review the new density.')

    def seam_changed(self):
        widget=self.sender();self.seams[str(widget.property('region'))]=widget.value()
        self.invalidate_preview()
        self.status.setText('Band seam changed. Generate a preview to review the new sewing start.')

    def failed(self,path,message):
        if message.startswith('Artwork changed'):
            self.invalidate();self.source_fingerprint=None;self.source_digest=None
        self.inspection_geometry={}
        self.aligned_images={};self.inspect_button.setEnabled(False)
        self.review_snapshot=None;self.review_button.setEnabled(False)
        self.density_image=QImage();self.thread_density_image=QImage();self.layers_image=QImage();self.density_button.setEnabled(False)
        self.quality=None;self.quality_button.setEnabled(False)
        self.project=None
        self.svg=''; self.save_svg_button.setEnabled(False)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.status.setText(message)

    def save_review(self):
        if self.review_snapshot is None:return
        path,_=QFileDialog.getSaveFileName(self,'Save conversion review','conversion-review.pdf','PDF review (*.pdf)')
        if not path:return
        try:
            from .conversion_report import save_conversion_review
            save_conversion_review(path,Path(self.path).name,*self.review_snapshot,fabric=self.fabric.currentData())
            self.status.setText(f'Saved conversion review: {path}')
        except (OSError,ValueError,KeyError) as exc:QMessageBox.warning(self,'Review not saved',str(exc))

    def inspect_artwork(self):
        if len(self.aligned_images)!=3:return
        from .artwork_compare import ArtworkCompareDialog
        ArtworkCompareDialog(self.aligned_images,self,geometry=self.inspection_geometry).exec()

    def show_density(self):
        if self.density_image.isNull():return
        dialog=QDialog(self);dialog.setWindowTitle('Artwork density review')
        layout=QVBoxLayout(dialog);mode=QComboBox();mode.setAccessibleName('Density measurement')
        stack=QStackedWidget()
        for title,image in [('Needle penetrations',self.density_image),('Sewn thread length',self.thread_density_image),('Coverage layers',self.layers_image)]:
            if image.isNull():continue
            mode.addItem(title);label=QLabel();label.setPixmap(QPixmap.fromImage(image));stack.addWidget(label)
        mode.currentIndexChanged.connect(stack.setCurrentIndex)
        layout.addWidget(mode);layout.addWidget(stack)
        if self.quality is not None and self.quality.get('layers'):
            from .coverage_review import fabric_guidance
            fabric=QComboBox();fabric.setAccessibleName('Fabric for guidance')
            for index in range(self.fabric.count()):fabric.addItem(self.fabric.itemText(index),self.fabric.itemData(index))
            fabric.setCurrentIndex(self.fabric.currentIndex())
            guidance=QPlainTextEdit();guidance.setReadOnly(True);guidance.setAccessibleName('Fabric guidance');guidance.setMaximumHeight(170)
            def update(_=None):
                self.fabric.setCurrentIndex(fabric.currentIndex())
                guidance.setPlainText(fabric_guidance(self.quality,fabric.currentData())[1])
            fabric.currentIndexChanged.connect(update);update()
            layout.addWidget(fabric);layout.addWidget(guidance)
        close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);close.rejected.connect(dialog.reject);layout.addWidget(close)
        dialog.exec()

    def show_quality(self):
        if self.quality is None: return
        from .trace_quality import quality_text
        dialog=QDialog(self);dialog.setWindowTitle('Conversion checks')
        layout=QVBoxLayout(dialog)
        text=QPlainTextEdit();text.setReadOnly(True);text.setPlainText(quality_text({**self.quality,'fabric':self.fabric.currentData()}))
        text.setAccessibleName('Conversion measurements by sewing order');layout.addWidget(text)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        dialog.resize(720,520);dialog.exec()

    def load_thread_chart(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose a thread chart','','Thread catalogs and palettes (*.csv *.inf *.edr);;CSV (*.csv);;INF palette (*.inf);;EDR palette (*.edr)')
        if not path: return
        # Parsing stays in the cancellable worker; the selected file is reread
        # for each preview so no large catalog is serialized onto the command line.
        self.thread_catalog.blockSignals(True)
        while self.thread_catalog.count()>3: self.thread_catalog.removeItem(3)
        self.thread_catalog.addItem(Path(path).name,path);self.thread_catalog.setCurrentIndex(3)
        self.thread_catalog.blockSignals(False);self.invalidate_preview()

    def save_svg(self):
        if not self.svg: return
        path,_=QFileDialog.getSaveFileName(self,'Save traced vector artwork','traced-artwork.svg','SVG artwork (*.svg)')
        if not path: return
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=Path(path).parent,suffix='.tmp',delete=False) as stream:
                temporary=Path(stream.name); stream.write(self.svg)
            os.replace(temporary,path)
        except OSError as exc:
            QMessageBox.warning(self,'SVG not saved',str(exc))
        else: self.status.setText(f'Saved editable vector artwork: {path}')
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)

    def accept(self):
        if self.project is not None:
            self.runner.cancel()
            super().accept()

    def reject(self):
        self.runner.cancel()
        super().reject()

    def closeEvent(self,event):
        self.runner.cancel()
        super().closeEvent(event)

    def close(self):
        self.runner.cancel()
        return super().close()
