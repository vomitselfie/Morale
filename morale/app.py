"""Morale's native Qt desktop application."""
from copy import deepcopy
import math
from pathlib import Path
import sys
import uuid

from PySide6.QtCore import Qt, QTimer, QMimeData, QStandardPaths
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFormLayout, QDoubleSpinBox,
    QComboBox, QCheckBox, QLineEdit, QFileDialog, QMessageBox, QColorDialog,
    QSplitter, QSlider, QToolBar, QScrollArea, QFrame, QPlainTextEdit, QTextEdit, QAbstractSpinBox, QInputDialog)

from .canvas import Canvas
from .model import Project, DesignObject, PALETTE, demo_project, satin_sample
from .nodes import PointDialog, ContourDialog
from .routing import route_object
from .routing_dialog import RoutingDialog
from .hoop_dialog import HoopDialog
from .generation import GenerationRunner
from .stitch_edit import StitchDialog, manual_object
from .measurements import HoopDialog, factor, dimension, validate_hoop
from .threads import THREAD_FIELDS, thread_key, usage, write_chart
from .lettering import LetteringDialog
from .reference import import_reference, decode_reference
from .reference_dialog import ReferenceDialog
from .arrange import arrange_selection, transform_selection, bounds
from .transform_dialog import TransformDialog
from .recovery import RecoveryStore
from .geometry import combine_outlines, replace_contours
from .bezier import enable_handles, edit_controls
from .svg_import import import_svg
from .templates import TemplateDialog, export_template
from .comparison import ComparisonDialog
from .catalog_dialog import CatalogDialog
from .catalogs import nearest_thread
from .library import LibraryDialog
from .motifs import capture_motif,load_motif,save_motif,validate_packet
from .trace_dialog import TraceDialog
from .clipboard import MIME_TYPE, encode_objects, decode_objects
from .applique import AppliqueDialog, applique_stages
from .batch_dialog import BatchDialog
from .engine import generate, preflight
from .formats import export_machine, import_machine, file_filters, export_notes, export_summary, IMPORT_FORMATS, EXPORT_FORMATS

STYLE = """
QMainWindow, QWidget { background: #f7f8f4; color: #293e35; font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 13px; }
QToolBar { background: #ffffff; border: 0; border-bottom: 1px solid #dde4dc; padding: 8px; spacing: 7px; }
QToolButton { padding: 8px 12px; border-radius: 5px; }
QToolButton:hover, QPushButton:hover { background: #e1ebe3; }
QToolButton:checked { background: #dceadf; color: #23543d; }
QPushButton { border: 1px solid #d2ddd3; border-radius: 5px; padding: 7px 10px; background: #ffffff; }
QPushButton#primary { background: #315e49; color: white; border: 0; padding: 9px 15px; }
QLineEdit, QDoubleSpinBox, QComboBox { background: white; border: 1px solid #d7dfd5; border-radius: 4px; padding: 5px; min-height: 20px; }
QListWidget { background: transparent; border: 0; outline: 0; }
QListWidget::item { padding: 10px 5px; margin: 2px 0; border-radius: 5px; }
QListWidget::item:selected { background: #dce9dd; color: #234f3a; }
QLabel#eyebrow { color: #708271; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
QLabel#heading { font-size: 24px; font-weight: 600; }
QLabel#muted { color: #788579; }
QStatusBar { background: #ecf0e8; color: #57705e; }
QSlider::groove:horizontal { height: 5px; background: #d5dfd3; border-radius: 2px; }
QSlider::handle:horizontal { width: 13px; margin: -4px 0; background: #37664d; border-radius: 6px; }
QSplitter::handle { background: #dce3d9; width: 1px; }
QCheckBox { spacing: 7px; }
QWidget:disabled { color: #88968c; }
"""


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


class MainWindow(QMainWindow):
    @property
    def selected_id(self):
        return self._selected_id

    @selected_id.setter
    def selected_id(self, value):
        self._selected_id = value
        self.selected_ids = {value} if value else set()

    def __init__(self, recovery_root=None, *, background_generation=False):
        super().__init__()
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets" / "logo.svg")))
        self.project = demo_project()
        self.file_path = None
        self.saved = self.project.dumps()
        self.history = []
        self.future = []
        self.selected_id = self.project.objects[-1].id
        self.syncing = False
        self.unit = "mm"
        self.spin_specs = {}
        self.blocks = []
        self.generation_error = None
        self.generation_pending = False
        self._closing = False
        self.preview_revision = 0
        self.pending_snapshot = None
        self.preview_cache = None
        self.generation_runner = GenerationRunner(self) if background_generation else None
        self.preview_debounce = QTimer(self)
        self.preview_debounce.setSingleShot(True)
        self.preview_debounce.setInterval(80)
        self.preview_debounce.timeout.connect(self.start_calculation)
        if self.generation_runner:
            self.generation_runner.ready.connect(self.calculation_ready)
            self.generation_runner.failed.connect(self.calculation_failed)
        self.setMinimumSize(1000, 680)
        self.resize(1360, 880)
        self.setStyleSheet(STYLE)
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.tick)
        self.recovery = None
        self.recovery_error = ""
        self.recovery_last = None
        if recovery_root is not None:
            try:
                self.recovery = RecoveryStore(recovery_root)
            except OSError as exc:
                self.recovery_error = str(exc)
        self.recovery_timer = QTimer(self)
        self.recovery_timer.setInterval(30_000)
        self.recovery_timer.timeout.connect(self.checkpoint)
        self.recovery_idle = QTimer(self)
        self.recovery_idle.setSingleShot(True)
        self.recovery_idle.setInterval(3000)
        self.recovery_idle.timeout.connect(self.checkpoint)
        if self.recovery:
            self.recovery_timer.start()
        self.make_actions()
        self.make_ui()
        self.refresh()
        QTimer.singleShot(0, self.canvas.fit)

    def action(self, title, callback, shortcut=None):
        action = QAction(title, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        return action

    def make_actions(self):
        file = self.menuBar().addMenu("&File")
        file.addAction(self.action("&New design", self.new, QKeySequence.StandardKey.New))
        file.addAction(self.action("&Open design…", self.open, QKeySequence.StandardKey.Open))
        file.addAction(self.action("Browse design folder…",self.browse_designs))
        file.addAction(self.action("Import machine design into project…", self.import_design, "Ctrl+I"))
        file.addAction(self.action("Batch convert machine files…", self.batch_convert))
        file.addAction(self.action("Import reference image…", self.add_reference))
        file.addAction(self.action("Import SVG artwork…", self.import_svg_artwork))
        file.addAction(self.action("Digitize artwork…",self.digitize_raster))
        file.addAction(self.action("Recover interrupted session…", self.recover_session))
        file.addAction(self.action("&Save project", self.save, QKeySequence.StandardKey.Save))
        file.addAction(self.action("Save project &as…", lambda: self.save(True), QKeySequence.StandardKey.SaveAs))
        file.addSeparator()
        file.addAction(self.action("Export &machine file…", self.export, "Ctrl+E"))
        file.addAction(self.action("Export thread chart…", self.thread_chart))
        file.addAction(self.action("Export placement template (PDF)…", self.placement_template))
        file.addAction(self.action("Split for multiple hoopings…", self.multihoop_dialog))
        file.addAction(self.action("Compare machine file with design…", self.compare_machine_file))
        file.addSeparator()
        file.addAction(self.action("Load wildflower example", self.load_demo))
        file.addAction(self.action("Load satin and running sampler", self.load_satin_sample))
        file.addAction(self.action("Quit", self.close, QKeySequence.StandardKey.Quit))
        edit = self.menuBar().addMenu("&Edit")
        self.undo_action = self.action("Undo", self.undo, QKeySequence.StandardKey.Undo)
        self.redo_action = self.action("Redo", self.redo, QKeySequence.StandardKey.Redo)
        edit.addActions([self.undo_action, self.redo_action])
        edit.addSeparator()
        edit.addAction(self.action("Copy", self.copy_selection, QKeySequence.StandardKey.Copy))
        edit.addAction(self.action("Cut", self.cut_selection, QKeySequence.StandardKey.Cut))
        edit.addAction(self.action("Paste", self.paste_selection, QKeySequence.StandardKey.Paste))
        edit.addAction(self.action("Select all objects", self.select_all_objects, QKeySequence.StandardKey.SelectAll))
        edit.addAction(self.action("Duplicate object", self.duplicate, "Ctrl+D"))
        edit.addAction(self.action("Delete object", self.delete, "Ctrl+Backspace"))
        edit.addAction(self.action("Edit path / satin points…", self.edit_points, "Ctrl+Shift+P"))
        edit.addAction(self.action("Enable Bezier handles", self.enable_bezier))
        edit.addAction(self.action("Path start and direction…", self.routing_dialog))
        handles = edit.addMenu("Bezier handle dragging")
        self.handle_drag_actions = QActionGroup(self)
        for mode, title in (("free", "Independent handles"), ("smooth", "Smooth — preserve opposite length"), ("symmetric", "Symmetric — equal lengths")):
            action = self.action(title, lambda checked=False, mode=mode: self.set_handle_drag_mode(mode))
            action.setCheckable(True)
            action.setChecked(mode == "free")
            action.setData(mode)
            self.handle_drag_actions.addAction(action)
            handles.addAction(action)
        edit.addAction(self.action("Edit individual stitches…", self.edit_stitches, "Ctrl+Shift+E"))
        edit.addAction(self.action("Add lettering…", self.add_lettering, "Ctrl+L"))
        edit.addAction(self.action("Add lettering along path…", self.add_path_lettering))
        edit.addAction(self.action("Edit lettering…", self.edit_lettering))
        edit.addAction(self.action("Create appliqué stages…", self.create_applique))
        edit.addAction(self.action("Thread catalog / match colors…",self.thread_catalog_dialog))
        custom=edit.addMenu("Custom motifs")
        custom.addAction(self.action("Capture selected outline",self.capture_custom_motif))
        custom.addAction(self.action("Apply captured / loaded motif",self.apply_custom_motif))
        custom.addAction(self.action("Load motif file…",self.load_custom_motif))
        custom.addAction(self.action("Save captured / loaded motif…",self.save_custom_motif))
        custom.addAction(self.action("Save selected object's motif…",lambda:self.save_custom_motif(True)))
        outlines = edit.addMenu("Combine closed outlines")
        for operation, title in [("union", "Union selected shapes"),
                                 ("subtract", "Subtract from first in sewing order"),
                                 ("intersection", "Keep common intersection")]:
            outlines.addAction(self.action(title, lambda checked=False, op=operation: self.combine_shapes(op)))
        arrange = edit.addMenu("Arrange object")
        arrange.addAction(self.action("Group selection", self.group_selection, "Ctrl+G"))
        arrange.addAction(self.action("Ungroup selection", self.ungroup_selection, "Ctrl+Shift+G"))
        arrange.addAction(self.action("Scale / rotate selection…", self.transform_dialog))
        arrange.addAction(self.action("Mirror left/right", lambda: self.arrange_object("mirror", "horizontal")))
        arrange.addAction(self.action("Mirror top/bottom", lambda: self.arrange_object("mirror", "vertical")))
        align = arrange.addMenu("Align to sewing field")
        for alignment in ["left", "right", "top", "bottom", "horizontal center", "vertical center", "center"]:
            align.addAction(self.action(alignment.title(), lambda checked=False, a=alignment: self.arrange_object("align", a)))
        between = arrange.addMenu("Align selected objects")
        for alignment in ["left", "right", "top", "bottom", "horizontal center", "vertical center"]:
            between.addAction(self.action(alignment.title(), lambda checked=False, a=alignment: self.arrange_object("align_objects", a)))
        arrange.addAction(self.action("Distribute horizontal centers", lambda: self.arrange_object("distribute", "horizontal")))
        arrange.addAction(self.action("Distribute vertical centers", lambda: self.arrange_object("distribute", "vertical")))
        view = self.menuBar().addMenu("&View")
        view.addAction(self.action("Fit hoop", lambda: self.canvas.fit(), "Ctrl+0"))
        view.addAction(self.action("Custom sewing field…", self.custom_hoop))
        view.addAction(self.action("Reference image settings…", self.edit_reference))
        view.addAction(self.action("Remove reference image", lambda: self.set_reference({})))
        units = view.addMenu("Measurement units")
        unit_group = QActionGroup(self)
        for unit, title in [("mm", "Millimeters"), ("in", "Inches")]:
            action = QAction(title, self)
            action.setCheckable(True)
            action.setChecked(unit == "mm")
            action.triggered.connect(lambda checked, u=unit: self.set_unit(u))
            unit_group.addAction(action)
            units.addAction(action)
        ruler = QAction("Show rulers", self)
        ruler.setCheckable(True)
        ruler.setChecked(True)
        ruler.toggled.connect(lambda checked: self.toggle_rulers(checked))
        view.addAction(ruler)
        snap = QAction("Snap to grid", self)
        snap.setCheckable(True)
        snap.toggled.connect(lambda checked: self.set_snap(checked))
        view.addAction(snap)
        self.object_snap_action=QAction('Snap to object edges and centers',self)
        self.object_snap_action.setCheckable(True)
        self.object_snap_action.toggled.connect(self.set_object_snap)
        view.addAction(self.object_snap_action)
        view.addAction(self.action("Grid spacing…", self.grid_spacing_dialog))
        for key,title in [("show_travel","Show travel moves"),("show_controls","Show trims, stops and thread changes")]:
            action = QAction(title,self)
            action.setCheckable(True)
            action.toggled.connect(lambda checked,k=key: self.toggle_overlay(k,checked))
            view.addAction(action)
        view.addAction(self.action("Previous trim / stop / thread change",lambda: self.jump_control(-1)))
        view.addAction(self.action("Next trim / stop / thread change",lambda: self.jump_control(1)))
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.action("Getting started", self.help))
        help_menu.addAction(self.action("Format compatibility", self.compatibility))
        help_menu.addAction(self.action("About Morale", lambda: QMessageBox.about(self, "About Morale", "Morale 0.1 · Native embroidery studio\nOpen source · MIT license\n\nBuilt with Qt for Python and pyembroidery.\nAn early foundation for accessible embroidery digitizing.")))

    def make_ui(self):
        tools = QToolBar("Design tools", self)
        tools.setMovable(False)
        self.addToolBar(tools)
        brand = label("  morale  ", "heading")
        tools.addWidget(brand)
        tools.addSeparator()
        group = QActionGroup(self)
        self.mode_actions = {}
        for mode, title in [("select", "↖  Select"), ("nodes", "Nodes"), ("stitch_nodes", "Stitch points"), ("ellipse", "◯  Ellipse"), ("rectangle", "□  Rectangle"), ("leaf", "♧  Leaf"), ("polygon", "⬡  Polygon"), ("path", "⌁  Running path"), ("satin", "Satin rails"), ("measure", "Measure")]:
            action = QAction(title, self)
            action.setCheckable(True)
            action.setChecked(mode == "select")
            action.triggered.connect(lambda checked, m=mode: self.set_mode(m))
            group.addAction(action)
            tools.addAction(action)
            self.mode_actions[mode] = action
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        tools.addWidget(spacer)
        tools.addWidget(button("Save project", self.save))
        tools.addWidget(button("Export stitches ↗", self.export, True))
        splitter = QSplitter()
        self.setCentralWidget(splitter)

        left = QWidget()
        left.setMinimumWidth(210)
        left.setMaximumWidth(320)
        column = QVBoxLayout(left)
        column.setContentsMargins(18, 24, 18, 18)
        column.addWidget(label("YOUR WORKSPACE", "eyebrow"))
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(200)
        self.title_edit.setAccessibleName("Design name")
        self.title_edit.editingFinished.connect(self.rename_project)
        column.addWidget(self.title_edit)
        column.addSpacing(20)
        column.addWidget(label("STITCH SEQUENCE", "eyebrow"))
        column.addWidget(label("Sewn from top to bottom", "muted"))
        self.layers = QListWidget()
        self.layers.setAccessibleName("Design objects in stitch order")
        self.layers.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.layers.itemSelectionChanged.connect(self.layer_selection_changed)
        column.addWidget(self.layers, 1)
        row = QHBoxLayout()
        row.addWidget(button("↑", lambda: self.reorder(-1)))
        row.addWidget(button("↓", lambda: self.reorder(1)))
        row.addWidget(button("Copy", self.duplicate))
        row.addWidget(button("Delete", self.delete))
        for i, tip in enumerate(["Sew selected object earlier", "Sew selected object later", "Duplicate selected object", "Delete selected object"]):
            row.itemAt(i).widget().setToolTip(tip)
            row.itemAt(i).widget().setAccessibleName(tip)
        column.addLayout(row)
        column.addSpacing(16)
        column.addWidget(label("Made for the joy of making.", "muted"))
        splitter.addWidget(left)

        center = QWidget()
        middle = QVBoxLayout(center)
        middle.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.setContentsMargins(16, 10, 16, 4)
        self.hoop = QComboBox()
        for w, h in [(100, 100), (130, 180), (160, 260), (200, 200), (200, 300)]:
            self.hoop.addItem(f"Hoop · {w} × {h} mm", (w, h))
        self.hoop.setAccessibleName("Hoop size")
        self.hoop.currentIndexChanged.connect(self.change_hoop)
        top.addWidget(self.hoop)
        top.addStretch()
        self.grid = QCheckBox("Grid")
        self.grid.setChecked(True)
        self.grid.toggled.connect(self.toggle_grid)
        top.addWidget(self.grid)
        self.stitches_check = QCheckBox("Stitches")
        self.stitches_check.setChecked(True)
        self.stitches_check.toggled.connect(self.toggle_stitches)
        top.addWidget(self.stitches_check)
        self.zoom = button("Fit hoop", lambda: self.canvas.fit())
        self.zoom.setMinimumWidth(104)
        top.addWidget(self.zoom)
        self.calculate_button = button("Recalculate", self.toggle_calculation)
        self.calculate_button.setVisible(self.generation_runner is not None)
        top.addWidget(self.calculate_button)
        middle.addLayout(top)
        self.canvas = Canvas()
        self.canvas.setAccessibleName("Embroidery design canvas")
        self.canvas.selected.connect(self.select)
        self.canvas.selection_request.connect(self.canvas_select)
        self.canvas.member_request.connect(lambda object_id: self.select_many([object_id], expand_groups=False))
        self.canvas.box_selected.connect(self.select_many)
        self.canvas.moved.connect(self.move_object)
        self.canvas.node_edited.connect(self.edit_canvas_node)
        self.canvas.stitch_moved.connect(self.edit_canvas_stitch)
        self.canvas.stitches_moved.connect(self.edit_canvas_stitches)
        self.canvas.stitches_deleted.connect(self.delete_canvas_stitches)
        self.canvas.drawn.connect(self.add_shape)
        self.canvas.message.connect(self.statusBar().showMessage)
        self.canvas.measured.connect(lambda dx, dy, distance: self.statusBar().showMessage(f"Distance {dimension(distance, self.unit)} · ΔX {dimension(dx, self.unit)} · ΔY {dimension(dy, self.unit)}"))
        self.canvas.zoom_changed.connect(lambda value: self.zoom.setText(f"{value}% · Fit"))
        middle.addWidget(self.canvas, 1)
        playback = QHBoxLayout()
        playback.setContentsMargins(16, 10, 16, 14)
        self.play_button = button("▶  Preview", self.play)
        playback.addWidget(self.play_button)
        self.thread_run = QComboBox()
        self.thread_run.setAccessibleName("Thread run to inspect")
        self.thread_run.setMaximumWidth(220)
        self.thread_run.currentIndexChanged.connect(self.inspect_thread_run)
        playback.addWidget(self.thread_run)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setAccessibleName("Stitch playback position")
        self.slider.valueChanged.connect(self.seek)
        playback.addWidget(self.slider, 1)
        playback.addWidget(button("Reset", self.reset_playback))
        self.counter = label("0 stitches", "muted")
        playback.addWidget(self.counter)
        middle.addLayout(playback)
        splitter.addWidget(center)

        right = QScrollArea()
        right.setWidgetResizable(True)
        right.setFrameShape(QFrame.Shape.NoFrame)
        right.setMinimumWidth(250)
        right.setMaximumWidth(330)
        panel = QWidget()
        props = QVBoxLayout(panel)
        props.setContentsMargins(20, 24, 20, 20)
        props.addWidget(label("OBJECT PROPERTIES", "eyebrow"))
        self.selection_label = label("Select an object", "heading")
        self.selection_label.setWordWrap(True)
        props.addWidget(self.selection_label)
        self.stage_instructions = label("", "muted")
        self.stage_instructions.setWordWrap(True)
        props.addWidget(self.stage_instructions)
        props.addSpacing(12)
        self.properties = QWidget()
        form = QFormLayout(self.properties)
        self.property_form=form
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(11)
        self.fields = {}
        name = QLineEdit()
        name.setMaxLength(200)
        name.editingFinished.connect(lambda: self.update_property("name", name.text()))
        self.fields["name"] = name
        form.addRow("Name", name)
        for key, title, low, high, step, suffix in [
            ("x", "X", -1000, 1000, 1, " mm"), ("y", "Y", -1000, 1000, 1, " mm"),
            ("width", "Width", .1, 500, 1, " mm"), ("height", "Height", .1, 500, 1, " mm"),
            ("rotation", "Rotation", -360, 360, 5, "°")]:
            self.add_spin(form, key, title, low, high, step, suffix)
        self.color_button = button("Choose thread", self.choose_color)
        form.addRow("Thread", self.color_button)
        for key, title in [("brand", "Thread brand"), ("catalog_number", "Catalog number"), ("description", "Thread name")]:
            field = QLineEdit()
            field.setMaxLength(1024)
            field.setAccessibleName(title)
            field.editingFinished.connect(lambda k=key, widget=field: self.update_thread(k, widget.text()))
            if not hasattr(self, "thread_fields"):
                self.thread_fields = {}
            self.thread_fields[key] = field
            form.addRow(title, field)
        self.stitch_type = QComboBox()
        self.stitch_type.addItem("Tatami fill", "fill")
        self.stitch_type.addItem("Contour fill", "contour")
        self.stitch_type.addItem("Repeating motifs", "motif")
        self.stitch_type.addItem("Motif fill", "pattern")
        self.stitch_type.addItem("Running stitch", "running")
        self.stitch_type.addItem("Imported stitches", "manual")
        self.stitch_type.addItem("Triple running stitch", "triple")
        self.stitch_type.addItem("Paired-rail satin", "satin")
        self.stitch_type.currentIndexChanged.connect(lambda: self.update_property("stitch_type", self.stitch_type.currentData()))
        form.addRow("Stitch", self.stitch_type)
        self.motif_pattern=QComboBox()
        self.motif_pattern.setAccessibleName("Motif pattern")
        for pattern in ("diamond","box","cross","custom"):
            self.motif_pattern.addItem(pattern.title(),pattern)
        self.motif_pattern.currentIndexChanged.connect(lambda:self.update_property("motif_pattern",self.motif_pattern.currentData()))
        form.addRow("Motif",self.motif_pattern)
        self.add_spin(form,"motif_width","Motif width",.5,30,.5," mm")
        self.add_spin(form,"motif_height","Motif height",.5,30,.5," mm")
        self.add_spin(form,"motif_spacing","Motif spacing",.5,30,.5," mm")
        self.add_spin(form,"motif_row_spacing","Motif row spacing",.5,30,.5," mm")
        self.fields["motif_row_spacing"].setToolTip("Distance between rows of motifs in a motif fill. Patterns are clipped at the outline and holes; jumps separate clipped fragments. Underlay and tatami compensation do not apply.")
        self.add_spin(form, "spacing", "Row spacing", .2, 5, .05, " mm")
        self.density_gradient = QCheckBox("Gradient row spacing")
        self.density_gradient.toggled.connect(lambda checked: self.update_property("density_gradient", checked))
        form.addRow(self.density_gradient)
        self.add_spin(form,"gradient_end_spacing","End row spacing",.2,5,.05," mm")
        self.fields["gradient_end_spacing"].setToolTip("Tatami row spacing changes linearly from Row spacing to this value across the shape, perpendicular to the fill angle. Larger spacing gives sparser coverage. Underlay keeps its own settings.")
        self.gradient_reverse = QCheckBox("Reverse spacing gradient")
        self.gradient_reverse.toggled.connect(lambda checked: self.update_property("gradient_reverse", checked))
        form.addRow(self.gradient_reverse)
        self.add_spin(form, "stitch_length", "Max. length", .5, 6, .1, " mm")
        self.add_spin(form,"minimum_stitch","Short-stitch cleanup",0,1,.05," mm")
        self.add_spin(form,'jump_trim','Trim internal travel above',0,50,.5,' mm')
        self.fields['jump_trim'].setToolTip('Zero disables. Trim longer internal jump sequences and lock the surrounding sewn runs. Initial/final travel and imported manual stitches are unchanged.')
        self.fields["minimum_stitch"].setToolTip("Remove redundant short interior stitches within 0.01 mm path tolerance. Keep endpoints, sharp corners, reversals and finishing ties. Some necessary short stitches remain. Zero disables cleanup; imported manual stitches are unchanged.")
        self.add_spin(form, "angle", "Fill angle", -360, 360, 5, "°")
        self.add_spin(form, "satin_max", "Satin split limit", .5, 12, .5, " mm")
        self.add_spin(form, "pull_compensation", "Pull compensation / side", 0, 2, .05, " mm")
        self.fields["pull_compensation"].setToolTip("Extend fill row ends or satin rails by this amount on each side. Underlay and source outlines stay at their original size. Small holes can shrink or close; inspect the preview and test on your fabric.")
        self.underlay = QCheckBox("Edge-run underlay")
        self.underlay.toggled.connect(lambda checked: self.update_property("underlay", checked))
        form.addRow(self.underlay)
        self.underlay_style = QComboBox()
        self.underlay_style.setAccessibleName("Underlay style")
        for title,key in [("Default edge / center run","auto"),("Edge run","edge"),("Sparse fill","sparse"),("Edge + sparse fill","edge_sparse"),("Zigzag","zigzag"),("Center + zigzag","center_zigzag")]:
            self.underlay_style.addItem(title,key)
        self.underlay_style.currentIndexChanged.connect(lambda: self.update_property("underlay_style",self.underlay_style.currentData()))
        form.addRow("Underlay style",self.underlay_style)
        self.add_spin(form,"underlay_inset","Underlay inset",0,3,.1," mm")
        self.add_spin(form,"underlay_spacing","Underlay row spacing",.5,10,.1," mm")
        self.fields["underlay_inset"].setToolTip("Inset support stitches from the outline. Narrow fill regions can lose their underlay; fully collapsed satin support rails use a center run. Cover stitches are unchanged.")
        self.finishing = {}
        for key, title in [("connect_fill", "Connect safe fill rows"), ("route_fill", "Route disconnected fill runs (up to 2,000)"), ("tie_in", "Tie in each sewn run"), ("tie_off", "Tie off each sewn run"), ("trim_after", "Trim after object"), ("stop_after", "Operator stop after object")]:
            control = QCheckBox(title)
            control.toggled.connect(lambda checked, k=key: self.update_property(k, checked))
            self.finishing[key] = control
            form.addRow(control)
        self.points_button = button("Edit path / rail points…", self.edit_points)
        form.addRow(self.points_button)
        form.addRow(button("Edit individual stitches…", self.edit_stitches))
        self.visible = QCheckBox("Include in design")
        self.visible.toggled.connect(lambda checked: self.update_property("visible", checked))
        form.addRow(self.visible)
        props.addWidget(self.properties)
        props.addSpacing(18)
        props.addWidget(label("THREAD PALETTE", "eyebrow"))
        colors = QHBoxLayout()
        colors.setSpacing(5)
        for color in PALETTE:
            swatch = button("", lambda checked=False, c=color: self.update_property("color", c))
            swatch.setFixedSize(23, 23)
            swatch.setStyleSheet(f"background: {color}; border: 1px solid #bdc9bd; border-radius: 11px; padding: 0;")
            swatch.setToolTip(color)
            swatch.setAccessibleName(f"Set thread color to {color}")
            colors.addWidget(swatch)
        props.addLayout(colors)
        props.addSpacing(20)
        self.stats = label("")
        self.stats.setWordWrap(True)
        props.addWidget(self.stats)
        self.notice = label("")
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet("color: #95633c; font-size: 12px;")
        props.addWidget(self.notice)
        props.addStretch()
        tip = label("STUDIO NOTES\n\nDrag to move objects. Scroll to zoom. Middle-drag to pan.\n\nPolygon & path: click points, then Enter to finish. Escape cancels.", "muted")
        tip.setWordWrap(True)
        props.addWidget(tip)
        right.setWidget(panel)
        splitter.addWidget(right)
        splitter.setSizes([240, 820, 290])
        self.statusBar().showMessage("Ready · All measurements in millimeters · Files stay on your computer")

    def add_spin(self, form, key, title, low, high, step, suffix):
        self.spin_specs[key] = (low, high, step, suffix)
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(2 if key in {"spacing", "gradient_end_spacing", "pull_compensation", "minimum_stitch"} else 1)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setKeyboardTracking(False)
        spin.setAccessibleName(title)
        spin.valueChanged.connect(lambda value, k=key: self.update_property(k, min(self.spin_specs[k][1], max(self.spin_specs[k][0], value * factor(self.unit))) if self.spin_specs[k][3] == " mm" else value))
        self.fields[key] = spin
        form.addRow(title, spin)

    def selected_object(self):
        if len(self.selected_ids) != 1:
            return None
        return next((o for o in self.project.objects if o.id == self.selected_id), None)

    def selected_objects(self):
        return [obj for obj in self.project.objects if obj.id in self.selected_ids]

    def commit(self, change):
        before = self.project.dumps()
        change()
        if before != self.project.dumps():
            self.history.append(before)
            self.limit_history(self.history)
            self.future.clear()
            self.refresh()

    def refresh(self):
        if self._closing:
            return
        if self.recovery:
            self.recovery_idle.start()
        valid = {obj.id for obj in self.project.objects}
        self.selected_ids.intersection_update(valid)
        if self._selected_id not in self.selected_ids:
            self._selected_id = next((obj.id for obj in self.project.objects if obj.id in self.selected_ids), "")
        self.reset_playback()
        self.generation_error = None
        if self.generation_runner:
            snapshot = self.project.dumps()
            if self.preview_cache and self.preview_cache[0] == snapshot:
                self.preview_debounce.stop()
                self.generation_runner.cancel()
                self.preview_revision += 1
                self.generation_pending = False
                self.blocks = self.preview_cache[1]
            elif not self.generation_pending or self.pending_snapshot != snapshot:
                self.preview_revision += 1
                self.pending_snapshot = snapshot
                self.generation_runner.cancel()
                self.blocks = []
                self.generation_pending = True
                self.preview_debounce.start()
        else:
            try:
                self.blocks = generate(self.project)
            except ValueError as exc:
                self.blocks = []
                self.generation_error = str(exc)
        self.render_refresh()

    def start_calculation(self):
        self.preview_debounce.stop()
        if self._closing or not self.generation_pending or self.generation_runner is None:
            return
        if self.project.dumps() != self.pending_snapshot:
            self.refresh()
            return
        try:
            self.generation_runner.request(self.project, self.preview_revision)
        except (OSError, ValueError) as exc:
            self.generation_runner.cancel()
            self.calculation_failed(self.preview_revision, str(exc))

    def calculation_ready(self, revision, blocks):
        if revision != self.preview_revision or not self.generation_pending:
            return
        if self.pending_snapshot != self.project.dumps():
            self.refresh()
            return
        self.generation_pending = False
        self.generation_error = None
        self.blocks = blocks
        self.preview_cache = (self.pending_snapshot, blocks)
        self.render_refresh(sync_fields=False)

    def calculation_failed(self, revision, message):
        if revision != self.preview_revision or not self.generation_pending:
            return
        self.generation_pending = False
        self.generation_error = message
        self.blocks = []
        self.render_refresh(sync_fields=False)

    def toggle_calculation(self):
        if self.generation_runner is None:
            return
        if self.generation_pending:
            self.preview_debounce.stop()
            self.generation_runner.cancel()
            self.calculation_failed(self.preview_revision, "Stitch calculation cancelled. Choose Recalculate or edit the design to try again.")
        else:
            self.preview_cache = None
            self.refresh()

    def preview_available(self):
        focused = QApplication.focusWidget()
        if focused and self.isAncestorOf(focused):
            focused.clearFocus()
        if self.generation_runner and not self.generation_pending and self.preview_cache and self.preview_cache[0] != self.project.dumps():
            self.refresh()
        if self.generation_pending:
            self.statusBar().showMessage("Stitches are still being calculated. Wait for the current preview before using its commands.")
            return False
        if self.generation_error:
            self.statusBar().showMessage(self.generation_error)
            return False
        return True

    def render_refresh(self, *, sync_fields=True):
        self.syncing = True
        if sync_fields:
            self.title_edit.setText(self.project.name)
        dimensions = (self.project.hoop_width, self.project.hoop_height)
        index = self.hoop.findData(dimensions)
        if index < 0:
            self.hoop.addItem(f"Hoop · {dimension(dimensions[0], self.unit)} × {dimension(dimensions[1], self.unit)}", dimensions)
            index = self.hoop.count() - 1
        self.hoop.setCurrentIndex(index)
        self.layers.clear()
        counts = {b.object_id: sum(s.command == "stitch" for s in b.stitches) for b in self.blocks}
        for i, obj in enumerate(self.project.objects):
            count_text = "calculating…" if self.generation_pending and obj.visible else f"{counts.get(obj.id, 0):,} stitches"
            item = QListWidgetItem(f"{i + 1:02d}  {obj.name}\n      {count_text}" + (" · hidden" if not obj.visible else ""))
            pix = QPixmap(12, 12)
            pix.fill(QColor(obj.color))
            item.setIcon(QIcon(pix))
            item.setData(Qt.ItemDataRole.UserRole, obj.id)
            item.setToolTip(obj.stage_note)
            self.layers.addItem(item)
            if obj.id == self.selected_id:
                self.layers.setCurrentItem(item)
        for index in range(self.layers.count()):
            item = self.layers.item(index)
            item.setSelected(item.data(Qt.ItemDataRole.UserRole) in self.selected_ids)
        self.layers.scrollToTop()
        self.canvas.selected_id = self.selected_id
        self.canvas.selected_ids = set(self.selected_ids)
        self.canvas.set_design(self.project, self.blocks)
        self.thread_run.clear()
        self.thread_run.addItem("All thread runs")
        for index,run in enumerate(self.canvas.timeline.runs,1):
            description = run["thread"].get("catalog_number") or run["thread"].get("description") or run["color"]
            self.thread_run.addItem(f"Thread run {index} · {description}")
        commands = sum(len(b.stitches) for b in self.blocks)
        stitches = sum(counts.values())
        colors = len({b.color.lower() for b in self.blocks})
        changes = sum(thread_key(a) != thread_key(b) or b.color_break for a, b in zip(self.blocks, self.blocks[1:]))
        lengths = usage(self.blocks)
        self.stats.setText(f"{stitches:,} stitches\n{colors} RGB colors · {changes} thread changes\n{sum(r['sewn_m'] for r in lengths):.2f} m sewn path\nActual thread consumption includes fabric depth and tails.")
        issues = [] if self.generation_pending else [self.generation_error] if self.generation_error else preflight(self.project, self.blocks)
        self.notice.setText("\n".join(issues) if issues else "Fits the selected hoop.\nExperimental stitch generation: test on scrap fabric before a finished piece.")
        if self.generation_pending:
            self.stats.setText("Calculating stitch counts…")
            self.notice.setText("Calculating stitches in the background. You can keep editing or cancel the calculation.")
        self.slider.setRange(0, commands)
        self.slider.setValue(commands)
        self.counter.setText("Calculating…" if self.generation_pending else f"{stitches:,} stitches")
        ready = not self.generation_pending and not self.generation_error
        self.play_button.setEnabled(ready and commands > 0)
        self.slider.setEnabled(ready)
        self.thread_run.setEnabled(ready)
        self.calculate_button.setText("Cancel calculation" if self.generation_pending else "Recalculate")
        self.syncing = False
        self.canvas.playhead = None
        if sync_fields:
            self.sync_properties()
        self.undo_action.setEnabled(bool(self.history))
        self.redo_action.setEnabled(bool(self.future))
        self.update_title()

    def update_title(self):
        dirty = self.project.dumps() != self.saved
        self.setWindowTitle(f"{'● ' if dirty else ''}{self.project.name} — Morale")

    def sync_properties(self):
        self.syncing = True
        obj = self.selected_object()
        self.properties.setEnabled(obj is not None)
        self.properties.setVisible(obj is not None)
        self.selection_label.setText(obj.name if obj else "Make something\nlovely.")
        if len(self.selected_ids) > 1:
            self.selection_label.setText(f"{len(self.selected_ids)} objects selected")
        self.stage_instructions.setText(obj.stage_note if obj else "Use Arrange for the selection, or Alt-click one member to edit its properties." if len(self.selected_ids) > 1 else "")
        self.stage_instructions.setVisible(bool(obj and obj.stage_note) or len(self.selected_ids) > 1)
        if obj:
            for key, widget in self.fields.items():
                if isinstance(widget, QLineEdit):
                    widget.setText(getattr(obj, key))
                else:
                    widget.setValue(getattr(obj, key) / factor(self.unit) if self.spin_specs[key][3] == " mm" else getattr(obj, key))
            self.color_button.setText(obj.color.upper())
            for key, field in self.thread_fields.items():
                field.setText(obj.thread.get(key, ""))
            self.color_button.setStyleSheet(f"border-left: 12px solid {obj.color};")
            self.stitch_type.setCurrentIndex(self.stitch_type.findData(obj.stitch_type))
            self.stitch_type.setEnabled(obj.kind not in {"stitches", "satin"})
            for index in range(self.stitch_type.count()):
                mode = self.stitch_type.itemData(index)
                enabled = mode in ({"manual"} if obj.kind == "stitches" else {"satin"} if obj.kind == "satin" else {"running", "triple", "motif"} if obj.kind == "path" else {"fill", "contour", "running", "triple", "motif", "pattern"})
                self.stitch_type.model().item(index).setEnabled(enabled)
            self.fields["stitch_length"].setEnabled(obj.kind != "stitches")
            self.fields["minimum_stitch"].setEnabled(obj.kind != "stitches")
            self.fields['jump_trim'].setEnabled(obj.kind!='stitches')
            self.motif_pattern.setCurrentIndex(self.motif_pattern.findData(obj.motif_pattern))
            custom_index=self.motif_pattern.findData('custom')
            self.motif_pattern.model().item(custom_index).setEnabled(bool(obj.custom_motif_paths))
            self.motif_pattern.setItemText(custom_index,f"Custom · {obj.custom_motif_name}" if obj.custom_motif_paths else "Custom (capture or load first)")
            self.motif_pattern.setEnabled(obj.stitch_type in {"motif","pattern"})
            self.property_form.setRowVisible(self.motif_pattern,obj.stitch_type in {"motif","pattern"})
            for key in ("motif_width","motif_height","motif_spacing"):
                self.fields[key].setEnabled(obj.stitch_type in {"motif","pattern"})
                self.property_form.setRowVisible(self.fields[key],obj.stitch_type in {"motif","pattern"})
            self.fields["motif_row_spacing"].setEnabled(obj.stitch_type=="pattern")
            self.property_form.setRowVisible(self.fields["motif_row_spacing"],obj.stitch_type=="pattern")
            self.fields["satin_max"].setEnabled(obj.kind == "satin")
            self.fields["pull_compensation"].setEnabled(obj.stitch_type in {"fill", "satin"})
            self.underlay.setChecked(obj.underlay)
            self.visible.setChecked(obj.visible)
            self.fields["spacing"].setEnabled(obj.stitch_type in {"fill", "contour", "satin"})
            self.density_gradient.setChecked(obj.density_gradient)
            self.gradient_reverse.setChecked(obj.gradient_reverse)
            for widget in (self.density_gradient,self.gradient_reverse,self.fields["gradient_end_spacing"]):
                self.property_form.setRowVisible(widget,obj.stitch_type=="fill")
                widget.setEnabled(obj.stitch_type=="fill" and (widget is self.density_gradient or obj.density_gradient))
            self.fields["angle"].setEnabled(obj.stitch_type in {"fill","pattern"} or obj.stitch_type == "contour" and obj.underlay and obj.underlay_style in {"sparse","edge_sparse"})
            self.underlay.setEnabled(obj.stitch_type in {"fill", "contour", "satin"})
            self.underlay.setText("Enable underlay")
            self.underlay_style.setCurrentIndex(self.underlay_style.findData(obj.underlay_style))
            active = obj.underlay and obj.stitch_type in {"fill","contour","satin"}
            self.underlay_style.setEnabled(active)
            allowed = {"auto","zigzag","center_zigzag"} if obj.kind == "satin" else {"auto","edge","sparse","edge_sparse"}
            for index in range(self.underlay_style.count()):
                self.underlay_style.model().item(index).setEnabled(self.underlay_style.itemData(index) in allowed)
            self.fields["underlay_inset"].setEnabled(active and not (obj.kind == "satin" and obj.underlay_style == "auto"))
            self.fields["underlay_spacing"].setEnabled(active and obj.underlay_style in {"sparse","edge_sparse","zigzag","center_zigzag"})
            for key, control in self.finishing.items():
                control.setEnabled(obj.stitch_type == "fill" if key in {"connect_fill","route_fill"} else obj.kind != "stitches")
                control.setChecked(getattr(obj, key))
            self.points_button.setEnabled(obj.kind in {"path", "polygon", "satin", "compound"})
        self.syncing = False

    def select(self, object_id):
        self.select_many([object_id] if object_id else [])

    def select_many(self, object_ids, expand_groups=True):
        valid = {obj.id for obj in self.project.objects}
        ordered = list(dict.fromkeys(object_id for object_id in object_ids if object_id in valid))
        if expand_groups:
            groups = {obj.group_id for obj in self.project.objects if obj.id in ordered and obj.group_id}
            ordered.extend(obj.id for obj in self.project.objects if obj.group_id in groups and obj.id not in ordered)
        self.selected_ids = set(ordered)
        self._selected_id = ordered[-1] if ordered else ""
        self.canvas.selected_id = self.selected_id
        self.canvas.selected_ids = set(ordered)
        self.syncing = True
        for index in range(self.layers.count()):
            item = self.layers.item(index)
            item.setSelected(item.data(Qt.ItemDataRole.UserRole) in self.selected_ids)
        self.syncing = False
        self.sync_properties()
        self.canvas.update()

    def layer_selection_changed(self):
        if not self.syncing:
            self.select_many([item.data(Qt.ItemDataRole.UserRole) for item in self.layers.selectedItems()])

    def canvas_select(self, object_id, additive):
        if additive:
            selected = set(self.selected_ids)
            obj = next((obj for obj in self.project.objects if obj.id == object_id), None)
            affected = {member.id for member in self.project.objects if obj and obj.group_id and member.group_id == obj.group_id} or ({object_id} if object_id else set())
            if object_id in selected:
                selected.difference_update(affected)
            else:
                selected.update(affected)
            self.select_many([obj.id for obj in self.project.objects if obj.id in selected])
        elif object_id in self.selected_ids:
            self._selected_id = object_id
            self.canvas.selected_id = object_id
        else:
            self.select(object_id)

    def select_all_objects(self):
        focused = self.text_clipboard_target()
        if focused:
            focused.selectAll()
        elif self.canvas.hasFocus() and self.canvas.mode=='stitch_nodes':
            self.canvas.select_all_stitches()
        else:
            self.select_many([obj.id for obj in self.project.objects])

    def group_selection(self):
        objects = self.selected_objects()
        if len(objects) < 2:
            self.statusBar().showMessage("Select at least two objects to group.")
            return
        group = uuid.uuid4().hex
        def change():
            for obj in objects:
                obj.group_id = group
        self.commit(change)

    def ungroup_selection(self):
        objects = self.selected_objects()
        def change():
            for obj in objects:
                obj.group_id = ""
        self.commit(change)

    def update_property(self, key, value):
        if not self.syncing and key == "color" and len(self.selected_ids) > 1:
            objects = self.selected_objects()
            def recolor():
                for selected in objects:
                    selected.color = value
                    selected.thread = {}
            self.commit(recolor)
            return
        obj = self.selected_object()
        if not self.syncing and obj and getattr(obj, key) != value:
            if key == "stitch_type" and (value in {"manual", "satin"} or obj.kind in {"stitches", "satin"} or obj.kind == "path" and value not in {"running", "triple", "motif"}):
                return
            def change():
                setattr(obj, key, value)
                if key == "color":
                    obj.thread = {}
            self.commit(change)

    def update_thread(self, key, value):
        if key not in THREAD_FIELDS or not isinstance(value, str) or len(value) > 1024:
            raise ValueError("Invalid thread metadata.")
        obj = self.selected_object()
        if not self.syncing and obj and obj.thread.get(key, "") != value:
            def change():
                if value:
                    obj.thread[key] = value
                else:
                    obj.thread.pop(key, None)
            self.commit(change)

    def rename_project(self):
        if not self.syncing:
            self.commit(lambda: setattr(self.project, "name", self.title_edit.text().strip() or "Untitled design"))

    def choose_color(self):
        obj = self.selected_object()
        if obj:
            color = QColorDialog.getColor(QColor(obj.color), self, "Choose thread color")
            if color.isValid():
                self.update_property("color", color.name())

    def set_mode(self, mode):
        self.reset_playback()
        self.canvas.set_mode(mode)
        self.mode_actions[mode].setChecked(True)
        self.statusBar().showMessage("Click points, then Enter to finish · Escape to cancel" if mode in {"polygon", "path"} else "Drag inside the hoop to draw" if mode != "select" else "Select and drag objects · Edit precise dimensions in the properties panel")
        if mode == "satin":
            self.statusBar().showMessage("Click left, then right rail points for each pair. Add at least two pairs, then Enter. Escape cancels.")
        elif mode == "measure":
            self.statusBar().showMessage("Drag between two points to measure distance. Measurements do not change the design.")
        elif mode == "nodes":
            self.statusBar().showMessage("Drag a node on the selected polygon, path, satin column, or compound shape. Escape cancels; releasing regenerates stitches. Grid snapping applies.")
        elif mode == "stitch_nodes":
            self.statusBar().showMessage("Click or drag needle positions on one selected object. Ctrl-click toggles; Shift-click selects a range; drag empty space to box-select, Ctrl/Shift adds and Alt removes; Shift+[ / ] extends selection. Ctrl+A selects all needle positions; Delete removes selected positions. [ / ] selects adjacent positions; arrows move 0.1 mm, Shift+arrows 1 mm, or one grid step when snapping. Moving converts generated objects to manual stitches; Undo restores geometry.")

    def add_shape(self, kind, points):
        if len(self.project.objects) >= 500:
            self.error("A project may contain at most 500 objects.")
            return
        xs, ys = zip(*points)
        w, h = max(.1, max(xs) - min(xs)), max(.1, max(ys) - min(ys))
        x, y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        if w > 500 or h > 500 or abs(x) > 1000 or abs(y) > 1000:
            self.error("Please draw a smaller object nearer the hoop.")
            return
        obj = DesignObject(f"{kind.title()} {len(self.project.objects) + 1}", kind, x, y, w, h,
                           color=self.selected_object().color if self.selected_object() else PALETTE[0],
                           thread=dict(self.selected_object().thread) if self.selected_object() else {},
                           stitch_type="running" if kind == "path" else "satin" if kind == "satin" else "fill",
                           points=[[(px - x) / w, (py - y) / h] for px, py in points] if kind in {"polygon", "path", "satin"} else [])
        try:
            generate(Project(objects=[obj]))
        except ValueError as exc:
            self.error(str(exc))
            return
        self.selected_id = obj.id
        self.commit(lambda: self.project.objects.append(obj))
        self.set_mode("select")

    def multihoop_dialog(self):
        dialog = HoopDialog(self.project, self)
        try:
            dialog.exec()
        finally:
            dialog.cleanup()
            dialog.deleteLater()

    def routing_dialog(self):
        obj = self.selected_object()
        if obj is None:
            self.statusBar().showMessage("Select one running outline or satin column.")
            return
        try:
            dialog = RoutingDialog(obj, self)
            try:
                if dialog.exec() == dialog.DialogCode.Accepted:
                    self.apply_routing(dialog.plan)
            finally:
                dialog.deleteLater()
        except ValueError as exc:
            self.error(str(exc))

    def apply_routing(self, plan):
        obj = self.selected_object()
        if obj is None:
            raise ValueError("Select one running outline or satin column.")
        candidate = route_object(obj, plan)
        if candidate == obj:
            return
        combined = deepcopy(self.project)
        combined.objects[self.project.objects.index(obj)] = candidate
        generate(combined)
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def set_handle_drag_mode(self, mode):
        self.canvas.handle_drag_mode = mode
        self.statusBar().showMessage("Bezier drag mode applies to subsequent canvas handle drags. Numeric editing remains independent.")

    def enable_bezier(self):
        obj = self.selected_object()
        if not obj:
            self.statusBar().showMessage("Select one polygon or running path first.")
            return
        try:
            candidate = enable_handles(obj)
            if candidate != obj:
                combined = deepcopy(self.project)
                combined.objects[self.project.objects.index(obj)] = candidate
                generate(combined)
                self.commit(lambda: setattr(self.project, "objects", combined.objects))
            self.set_mode("nodes")
            self.statusBar().showMessage("Drag the small Bezier handles to bend segments; drag anchors to move their handles together. Undo restores the original path.")
        except ValueError as exc:
            self.error(str(exc))

    def edit_points(self):
        obj = self.selected_object()
        if not obj or obj.kind not in {"path", "polygon", "satin", "compound"}:
            self.statusBar().showMessage("Select a polygon, running path, satin column, or compound shape to edit its points.")
            return
        dialog = ContourDialog(obj, self) if obj.kind == "compound" else PointDialog(obj, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        try:
            if obj.kind == "compound":
                self.apply_contours(dialog.rings)
            else:
                self.replace_points(dialog.points())
        except ValueError as exc:
            self.error(str(exc))

    def edit_stitches(self):
        if not self.preview_available():
            return
        obj = self.selected_object()
        if not obj:
            self.statusBar().showMessage("Select an object to edit its stitches.")
            return
        try:
            block = [b for b in self.blocks if b.object_id == obj.id]
            if not block or not block[0].stitches:
                raise ValueError("This object has no visible stitches to edit.")
            dialog = StitchDialog(obj, [[s.x, s.y, s.command] for s in block[0].stitches], self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                self.replace_stitches(dialog.model.rows)
        except ValueError as exc:
            self.error(str(exc))

    def add_lettering(self):
        dialog = LetteringDialog(parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                selected = self.selected_object()
                if selected:
                    dialog.candidate.color = selected.color
                    dialog.candidate.thread = dict(selected.thread)
                self.apply_lettering(dialog.candidate)
            except ValueError as exc:
                self.error(str(exc))

    def add_path_lettering(self):
        selected = self.selected_objects()
        if len(selected) != 1 or selected[0].kind not in {"path", "polygon"}:
            self.statusBar().showMessage("Select one drawn path or polygon for the lettering baseline.")
            return
        guide = selected[0]
        baseline = list(guide.outline())
        if guide.kind == "polygon" and baseline and baseline[-1] != baseline[0]:
            baseline.append(baseline[0])
        dialog = LetteringDialog(parent=self, baseline=baseline)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                dialog.candidate.color = guide.color
                dialog.candidate.thread = dict(guide.thread)
                self.apply_lettering(dialog.candidate, hide_guide_id=None if dialog.keep_baseline.isChecked() else guide.id)
            except ValueError as exc:
                self.error(str(exc))

    def create_applique(self):
        if not self.selected_object():
            self.statusBar().showMessage("Select a closed outline first.")
            return
        dialog = AppliqueDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.apply_applique(dialog.border_width.value(),dialog.cover_mode.currentData())
            except ValueError as exc:
                self.error(str(exc))

    def apply_applique(self, border_width,cover_mode='fill'):
        obj = self.selected_object()
        if not obj:
            raise ValueError("Select a closed outline first.")
        if len(self.project.objects) + 2 > 500:
            raise ValueError("Appliqué stages would exceed the 500-object limit.")
        stages = applique_stages(obj, border_width,cover_mode)
        if len(self.project.objects)-1+len(stages)>500:
            raise ValueError('Appliqué borders would exceed the 500-object limit.')
        combined = deepcopy(self.project)
        index = self.project.objects.index(obj)
        combined.objects[index:index + 1] = stages
        generate(combined)
        self.selected_id = stages[0].id
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def combine_shapes(self, operation):
        try:
            self.apply_outline_operation(operation)
        except ValueError as exc:
            self.error(str(exc))

    def apply_outline_operation(self, operation):
        objects = self.selected_objects()
        candidate = combine_outlines(objects, operation)
        selected = {obj.id for obj in objects}
        combined = deepcopy(self.project)
        first = objects[0].id
        combined.objects = [candidate if obj.id == first else obj
                            for obj in combined.objects if obj.id == first or obj.id not in selected]
        Project.loads(combined.dumps())
        generate(combined)
        self.selected_id = candidate.id
        self.commit(lambda: setattr(self.project, "objects", combined.objects))
        self.statusBar().showMessage("Combined outlines using the first shape's thread and stitch settings. Undo restores the source shapes.")

    def edit_lettering(self):
        obj = self.selected_object()
        if not obj or not obj.lettering:
            self.statusBar().showMessage("Select a lettering object first.")
            return
        dialog = LetteringDialog(obj, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.apply_lettering(dialog.candidate, replace=True)
            except ValueError as exc:
                self.error(str(exc))

    def apply_lettering(self, candidate, replace=False, hide_guide_id=None):
        combined = deepcopy(self.project)
        if hide_guide_id is not None:
            guide = next((obj for obj in combined.objects if obj.id == hide_guide_id), None)
            if guide is None:
                raise ValueError("The lettering baseline no longer exists.")
            guide.visible = False
        if replace:
            index = next(i for i, obj in enumerate(self.project.objects) if obj.id == candidate.id)
            combined.objects[index] = candidate
        else:
            if len(combined.objects) >= 500:
                raise ValueError("Project exceeds the 500-object limit.")
            combined.objects.append(candidate)
        Project.loads(combined.dumps())
        generate(combined)
        self.selected_id = candidate.id
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def replace_stitches(self, rows):
        obj = self.selected_object()
        if not obj:
            raise ValueError("Select an object first.")
        candidate = manual_object(obj, rows)
        combined = deepcopy(self.project)
        index = self.project.objects.index(obj)
        combined.objects[index] = candidate
        generate(combined)
        self.commit(lambda: self.project.objects.__setitem__(index, candidate))

    def edit_canvas_stitch(self, object_id, index, x, y):
        obj = self.selected_object()
        block = next((b for b in self.blocks if b.object_id == object_id), None)
        if not obj or obj.id != object_id or block is None or not 0 <= index < len(block.stitches):
            return
        stitch = block.stitches[index]
        if stitch.command not in {"stitch", "jump"} or (x,y) == (stitch.x,stitch.y):
            return
        rows = [[s.x,s.y,s.command] for s in block.stitches]
        rows[index][:2] = [x,y]
        try:
            self.replace_stitches(rows)
            self.canvas.announce_stitch()
        except ValueError as exc:
            self.statusBar().showMessage(f"Stitch move rejected: {exc}")
            self.canvas.update()

    def edit_canvas_stitches(self,object_id,indices,dx,dy):
        obj=self.selected_object()
        block=next((b for b in self.blocks if b.object_id==object_id),None)
        if not obj or obj.id!=object_id or block is None:return
        if not isinstance(indices,(list,tuple)) or not indices or any(type(i) is not int or not 0<=i<len(block.stitches) or block.stitches[i].command not in {'stitch','jump'} for i in indices):return
        if (dx,dy)==(0,0):return
        rows=[[s.x,s.y,s.command] for s in block.stitches]
        for i in set(indices):rows[i][:2]=[rows[i][0]+dx,rows[i][1]+dy]
        try:
            self.replace_stitches(rows);self.canvas.announce_stitch()
        except ValueError as exc:
            self.statusBar().showMessage(f'Stitch move rejected: {exc}');self.canvas.update()

    def delete_canvas_stitches(self,object_id,indices):
        obj=self.selected_object()
        block=next((b for b in self.blocks if b.object_id==object_id),None)
        if not obj or obj.id!=object_id or block is None or not indices:return
        from .stitch_edit import delete_needle_positions
        try:
            rows,added=delete_needle_positions([[s.x,s.y,s.command] for s in block.stitches],indices)
            self.replace_stitches(rows)
            focus=min((i for i,row in enumerate(rows) if row[2] in {'stitch','jump'}),key=lambda i:abs(i-min(indices)))
            self.canvas.stitch_selection=(object_id,focus);self.canvas.stitch_multi=(object_id,{focus})
            self.canvas.update()
            self.statusBar().showMessage(f'Deleted {len(set(indices))} needle positions. Retained controls follow the preceding position.'+(' Added an entry jump at the first remaining position.' if added else ''))
        except ValueError as exc:
            self.statusBar().showMessage(f'Stitch deletion rejected: {exc}');self.canvas.update()

    def edit_canvas_node(self, object_id, rings):
        obj = self.selected_object()
        if not obj or obj.id != object_id:
            return
        try:
            if obj.kind == "compound":
                self.apply_contours(rings)
            else:
                self.replace_points(rings[0])
        except ValueError as exc:
            self.statusBar().showMessage(f"Node move rejected: {exc}")
            self.canvas.update()

    def apply_contours(self, rings):
        obj = self.selected_object()
        if not obj:
            raise ValueError("Select a compound shape first.")
        candidate = replace_contours(obj, rings)
        if candidate == obj:
            return
        combined = deepcopy(self.project)
        index = self.project.objects.index(obj)
        combined.objects[index] = candidate
        Project.loads(combined.dumps())
        generate(combined)
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def replace_points(self, points):
        obj = self.selected_object()
        if not obj or obj.kind not in {"path", "polygon", "satin"}:
            raise ValueError("Select a point-based object first.")
        if obj.handles:
            candidate = edit_controls(obj, points)
            if candidate == obj:
                return
            combined = deepcopy(self.project)
            combined.objects[self.project.objects.index(obj)] = candidate
            generate(combined)
            self.commit(lambda: setattr(self.project, "objects", combined.objects))
            return
        if not points or not all(math.isfinite(v) and abs(v) <= 1000 for p in points for v in p):
            raise ValueError("Points must be finite coordinates within ±1,000 mm.")
        xs, ys = zip(*points)
        candidate = deepcopy(obj)
        candidate.x, candidate.y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        candidate.width, candidate.height = max(.1, max(xs) - min(xs)), max(.1, max(ys) - min(ys))
        candidate.rotation = 0
        candidate.motif_reflected ^= candidate.flip_x ^ candidate.flip_y
        candidate.flip_x = candidate.flip_y = False
        candidate.points = [[(x - candidate.x) / candidate.width, (y - candidate.y) / candidate.height] for x, y in points]
        Project.loads(Project(objects=[candidate]).dumps())
        index = self.project.objects.index(obj)
        combined = deepcopy(self.project)
        combined.objects[index] = candidate
        generate(combined)
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def move_object(self, object_id, dx, dy):
        objects = self.selected_objects() if object_id in self.selected_ids else [next(o for o in self.project.objects if o.id == object_id)]
        if not objects:
            return
        dx = max(-1000 - min(obj.x for obj in objects), min(1000 - max(obj.x for obj in objects), dx))
        dy = max(-1000 - min(obj.y for obj in objects), min(1000 - max(obj.y for obj in objects), dy))
        def move():
            for obj in objects:
                obj.x += dx
                obj.y += dy
        self.commit(move)

    def arrange_object(self, operation, value):
        objects = self.selected_objects()
        if not objects:
            self.statusBar().showMessage("Select an object to arrange.")
            return
        try:
            candidates = arrange_selection(objects, operation, value, self.project.hoop_width, self.project.hoop_height)
            replacement = {obj.id: obj for obj in candidates}
            combined = deepcopy(self.project)
            combined.objects = [replacement.get(obj.id, obj) for obj in combined.objects]
            Project.loads(combined.dumps())
            generate(combined)
            self.commit(lambda: setattr(self.project, "objects", combined.objects))
        except ValueError as exc:
            self.error(str(exc))

    def transform_dialog(self):
        objects = self.selected_objects()
        if not objects:
            self.statusBar().showMessage("Select objects to transform.")
            return
        try:
            boxes = [bounds(obj) for obj in objects]
        except ValueError as exc:
            self.error(str(exc))
            return
        size = (max(b[2] for b in boxes)-min(b[0] for b in boxes), max(b[3] for b in boxes)-min(b[1] for b in boxes))
        dialog = TransformDialog(len(objects), self, size)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.apply_transform(dialog.scale.value() / 100, dialog.rotation.value(), dialog.origin.currentData(), dialog.scale_y.value() / 100)
            except ValueError as exc:
                self.error(str(exc))

    def apply_transform(self, scale, rotation, origin="selection", scale_y=None):
        candidates = transform_selection(self.selected_objects(), scale, rotation, origin, scale_y)
        replacement = {obj.id: obj for obj in candidates}
        combined = deepcopy(self.project)
        combined.objects = [replacement.get(obj.id, obj) for obj in combined.objects]
        Project.loads(combined.dumps())
        generate(combined)
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def duplicate(self):
        objects = self.selected_objects()
        if not objects:
            return
        if len(objects) + len(self.project.objects) > 500:
            self.error("Duplicating would exceed the 500-object limit.")
            return
        copies = deepcopy(objects)
        groups = {}
        dx, dy = min(3, 1000 - max(obj.x for obj in objects)), min(3, 1000 - max(obj.y for obj in objects))
        for obj in copies:
            obj.id = uuid.uuid4().hex
            if obj.group_id:
                obj.group_id = groups.setdefault(obj.group_id, uuid.uuid4().hex)
            obj.name = (obj.name + " copy")[:200]
            obj.x += dx
            obj.y += dy
        combined = deepcopy(self.project)
        index = max(i for i, obj in enumerate(combined.objects) if obj.id in self.selected_ids) + 1
        combined.objects[index:index] = copies
        try:
            generate(combined)
        except ValueError as exc:
            self.error(str(exc))
            return
        self._selected_id = copies[0].id
        self.selected_ids = {obj.id for obj in copies}
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def text_clipboard_target(self):
        focused = QApplication.focusWidget()
        if isinstance(focused, QAbstractSpinBox):
            return focused.lineEdit()
        return focused if isinstance(focused, (QLineEdit, QPlainTextEdit, QTextEdit)) else None

    def copy_selection(self):
        focused = self.text_clipboard_target()
        if focused:
            focused.copy()
            return False
        objects = self.selected_objects()
        if not objects:
            return False
        try:
            payload = encode_objects(objects)
            data = QMimeData()
            data.setData(MIME_TYPE, payload)
            data.setText("Morale objects: " + ", ".join(obj.name for obj in objects))
            QApplication.clipboard().setMimeData(data)
            return True
        except ValueError as exc:
            self.error(str(exc))
            return False

    def cut_selection(self):
        focused = self.text_clipboard_target()
        if focused:
            focused.cut()
        elif self.copy_selection():
            self.delete()

    def paste_selection(self):
        focused = self.text_clipboard_target()
        if focused:
            focused.paste()
            return
        data = QApplication.clipboard().mimeData()
        if not data or not data.hasFormat(MIME_TYPE):
            self.statusBar().showMessage("Copy a Morale object before pasting into the design.")
            return
        try:
            self.paste_objects(bytes(data.data(MIME_TYPE)))
        except ValueError as exc:
            self.error(str(exc))

    def paste_objects(self, payload):
        objects = decode_objects(payload)
        if len(self.project.objects) + len(objects) > 500:
            raise ValueError("Pasting would exceed the 500-object limit.")
        combined = deepcopy(self.project)
        index = next((i + 1 for i, obj in enumerate(combined.objects) if obj.id == self.selected_id), len(combined.objects))
        combined.objects[index:index] = objects
        generate(combined)
        self._selected_id = objects[0].id
        self.selected_ids = {obj.id for obj in objects}
        self.commit(lambda: setattr(self.project, "objects", combined.objects))

    def delete(self):
        objects = self.selected_objects()
        if objects:
            ids = {obj.id for obj in objects}
            self.selected_id = ""
            self.commit(lambda: setattr(self.project, "objects", [obj for obj in self.project.objects if obj.id not in ids]))

    def reorder(self, direction):
        if not self.selected_ids:
            return
        def move():
            objects = self.project.objects
            indices = range(1, len(objects)) if direction < 0 else range(len(objects) - 2, -1, -1)
            step = -1 if direction < 0 else 1
            for index in indices:
                if objects[index].id in self.selected_ids and objects[index + step].id not in self.selected_ids:
                    objects[index], objects[index + step] = objects[index + step], objects[index]
        self.commit(move)

    def undo(self):
        if self.history:
            self.future.append(self.project.dumps())
            self.limit_history(self.future)
            self.project = Project.loads(self.history.pop())
            self.refresh()

    def redo(self):
        if self.future:
            self.history.append(self.project.dumps())
            self.limit_history(self.history)
            self.project = Project.loads(self.future.pop())
            self.refresh()

    @staticmethod
    def limit_history(history):
        total = sum(sys.getsizeof(entry) for entry in history)
        while len(history) > 1 and (len(history) > 100 or total > 32 * 1024 * 1024):
            total -= sys.getsizeof(history.pop(0))

    def change_hoop(self):
        if not self.syncing:
            def change():
                self.project.hoop_width, self.project.hoop_height = self.hoop.currentData()
            self.commit(change)
            self.canvas.fit()

    def set_unit(self, unit):
        if unit not in {"mm", "in"}:
            raise ValueError("Choose millimeters or inches.")
        self.unit = unit
        self.syncing = True
        for key, (low, high, step, suffix) in self.spin_specs.items():
            if suffix != " mm":
                continue
            spin = self.fields[key]
            spin.setDecimals(4 if unit == "in" else 2 if key in {"spacing", "gradient_end_spacing", "pull_compensation", "minimum_stitch"} else 1)
            spin.setRange(low / factor(unit), high / factor(unit))
            spin.setSingleStep(step / factor(unit))
            spin.setSuffix(f" {unit}")
        for index in range(self.hoop.count()):
            width, height = self.hoop.itemData(index)
            self.hoop.setItemText(index, f"Hoop · {dimension(width, unit)} × {dimension(height, unit)}")
        self.syncing = False
        self.sync_properties()
        self.canvas.unit = unit
        self.canvas.update()
        self.statusBar().showMessage(f"Display units: {unit}. Project geometry stays in millimeters; point and stitch dialogs label their own units.")

    def toggle_rulers(self, checked):
        self.canvas.show_rulers = checked
        self.canvas.update()

    def set_snap(self, checked):
        self.canvas.snap_grid = checked
        self.statusBar().showMessage("Grid snapping enabled: drawing points and the dragged object's center snap to the displayed grid." if checked else "Grid snapping disabled.")

    def set_object_snap(self,checked):
        self.canvas.snap_objects=checked;self.canvas.snap_guides=(None,None);self.canvas.update()
        self.statusBar().showMessage('Object snapping enabled: drag selection bounds within 8 screen pixels of visible edges or centers. Object alignment takes priority over grid snapping on matched axes.' if checked else 'Object snapping disabled.')

    def grid_spacing_dialog(self):
        value, accepted = QInputDialog.getDouble(self, "Grid spacing", f"Spacing ({self.unit})", self.canvas.grid_step() / factor(self.unit), .1 / factor(self.unit), 100 / factor(self.unit), 4)
        if accepted:
            self.set_grid_spacing(max(.1, min(100, value * factor(self.unit))))

    def set_grid_spacing(self, millimeters):
        if not math.isfinite(millimeters) or not .1 <= millimeters <= 100:
            raise ValueError("Grid spacing must be 0.1–100 mm.")
        self.canvas.grid_spacing = millimeters
        self.canvas.update()

    def custom_hoop(self):
        dialog = HoopDialog(self.project.hoop_width, self.project.hoop_height, self.unit, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.set_hoop(*dialog.dimensions())

    def set_hoop(self, width, height):
        validate_hoop(width, height)
        def change():
            self.project.hoop_width, self.project.hoop_height = width, height
        self.commit(change)
        self.canvas.fit()

    def toggle_grid(self, checked):
        self.canvas.show_grid = checked
        self.canvas.update()

    def toggle_stitches(self, checked):
        self.canvas.show_stitches = checked
        self.canvas.update()

    def toggle_overlay(self,key,checked):
        setattr(self.canvas,key,checked)
        self.canvas.update()

    def inspect_thread_run(self,index):
        if self.syncing:
            return
        if index <= 0:
            self.reset_playback()
            return
        run = self.canvas.timeline.runs[index-1]
        self.timer.stop()
        self.play_button.setText("▶  Preview")
        self.canvas.inspection_ids = set(run["ids"])
        self.slider.blockSignals(True)
        self.slider.setRange(run["start"],run["end"])
        self.slider.setValue(run["start"])
        self.slider.blockSignals(False)
        self.seek(run["start"])

    def jump_control(self,direction):
        self.timer.stop()
        self.play_button.setText("▶  Resume")
        position = self.slider.value() if self.canvas.playhead is not None else self.slider.minimum() if direction > 0 else self.slider.maximum()
        target = self.canvas.timeline.next_control(position,direction,self.slider.minimum(),self.slider.maximum())
        self.slider.setValue(target)
        self.seek(target)

    def play(self):
        if not self.preview_available():
            return
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText("▶  Resume")
        elif self.slider.maximum():
            if self.slider.value() == self.slider.maximum():
                self.slider.setValue(self.slider.minimum())
            self.timer.start()
            self.play_button.setText("Ⅱ  Pause")

    def tick(self):
        self.slider.setValue(min(self.slider.maximum(), self.slider.value() + 25))
        if self.slider.value() == self.slider.maximum():
            self.timer.stop()
            self.play_button.setText("▶  Preview")

    def seek(self, value):
        if not self.syncing:
            self.canvas.playhead = value
            self.canvas.update()
            start = self.slider.minimum()
            command = self.canvas.timeline.commands[value-1][1].command if value > start else "ready"
            self.counter.setText(f"{value-start:,} / {self.slider.maximum()-start:,} · {command}")

    def reset_playback(self):
        self.timer.stop()
        if hasattr(self, "canvas"):
            self.canvas.inspection_ids = None
            self.thread_run.blockSignals(True)
            self.thread_run.setCurrentIndex(0)
            self.thread_run.blockSignals(False)
            self.canvas.playhead = None
            self.canvas.update()
            self.play_button.setText("▶  Preview")
            self.slider.blockSignals(True)
            self.slider.setRange(0,sum(len(b.stitches) for b in self.blocks))
            self.slider.setValue(self.slider.maximum())
            self.slider.blockSignals(False)
            self.counter.setText(f"{sum(s.command == 'stitch' for b in self.blocks for s in b.stitches):,} stitches")

    def error(self, text):
        QMessageBox.warning(self, "Morale", text)

    def confirm_discard(self):
        focused = QApplication.focusWidget()
        if focused and self.isAncestorOf(focused):
            focused.clearFocus()
        if self.project.dumps() == self.saved:
            return True
        answer = QMessageBox.question(self, "Save your design?", "This design has unsaved changes.", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def replace_project(self, project, path=None, *, recovered=False):
        decode_reference(project.reference)
        self.project = project
        self.file_path = path
        self.saved = "" if recovered else project.dumps()
        self.history.clear()
        self.future.clear()
        self.selected_id = ""
        self.canvas.set_mode("select")
        self.mode_actions["select"].setChecked(True)
        self.refresh()
        self.canvas.fit()
        self.checkpoint()

    def apply_svg_artwork(self, path):
        result = import_svg(path)
        combined = deepcopy(self.project)
        combined.objects.extend(result.objects)
        Project.loads(combined.dumps())
        generate(combined)
        self._selected_id = result.objects[0].id
        self.selected_ids = {obj.id for obj in result.objects}
        self.commit(lambda: setattr(self.project, "objects", combined.objects))
        self.set_mode("select")
        return result

    def import_svg_artwork(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import SVG artwork", "", "SVG artwork (*.svg)")
        if not path:
            return
        try:
            result = self.apply_svg_artwork(path)
            self.statusBar().showMessage(f"Imported {len(result.objects)} editable SVG objects at their physical size, centered in the hoop.")
            if result.notices:
                QMessageBox.information(self, "SVG import notes", "\n\n".join(result.notices))
        except (OSError, ValueError) as exc:
            self.error(str(exc))

    def apply_catalog_threads(self,entries,nearest=False,metric="rgb"):
        objects=self.selected_objects()
        if not objects:
            raise ValueError("Select objects to assign catalog threads.")
        if not entries:
            raise ValueError("Choose at least one catalog thread.")
        selected={obj.id for obj in objects}
        combined=deepcopy(self.project)
        for obj in combined.objects:
            if obj.id in selected:
                entry=nearest_thread(obj.color,entries,metric) if nearest else entries[0]
                obj.color=entry.color
                obj.thread=dict(entry.metadata)
        Project.loads(combined.dumps())
        generate(combined)
        if combined.dumps()!=self.project.dumps():
            self.commit(lambda:setattr(self.project,"objects",combined.objects))

    def thread_catalog_dialog(self):
        objects=self.selected_objects()
        if not objects:
            self.statusBar().showMessage("Select objects to assign or match thread colors.")
            return
        dialog=CatalogDialog(objects[0].color,len(objects),self,getattr(self,"thread_catalog",None),metric=getattr(self,"thread_match_metric","oklab"),colors=[obj.color for obj in objects])
        try:
            accepted=dialog.exec()==dialog.DialogCode.Accepted
            self.thread_catalog=(dialog.catalog_name,dialog.catalog)
            self.thread_match_metric=dialog.metric_choice.currentData()
            if accepted:
                self.apply_catalog_threads(dialog.candidates if dialog.mode=='nearest' else [dialog.entry],dialog.mode=='nearest',dialog.metric_choice.currentData())
        except ValueError as exc:
            self.error(str(exc))
        finally:
            dialog.deleteLater()

    def capture_custom_motif(self):
        obj=self.selected_object()
        if not obj:
            self.statusBar().showMessage("Select one editable outline to capture.")
            return
        try:
            self.captured_motif=capture_motif(obj)
            self.statusBar().showMessage("Captured outline. Select guide objects, then choose Apply captured / loaded motif.")
        except ValueError as exc:
            self.error(str(exc))

    def apply_custom_motif(self):
        packet=getattr(self,'captured_motif',None)
        objects=self.selected_objects()
        if not packet or not objects:
            self.statusBar().showMessage("Capture or load a motif, then select its guide objects.")
            return
        try:
            validate_packet(packet)
            if any(o.kind in {'stitches','satin'} for o in objects):
                raise ValueError("Motif guides must be editable paths or closed shapes.")
            combined=deepcopy(self.project)
            ids={o.id for o in objects}
            for obj in combined.objects:
                if obj.id in ids:
                    obj.custom_motif_paths=deepcopy(packet['paths'])
                    obj.custom_motif_name=packet['name']
                    obj.motif_pattern='custom'
                    if obj.stitch_type!='pattern':
                        obj.stitch_type='motif'
            Project.loads(combined.dumps())
            generate(combined)
            if combined.dumps()!=self.project.dumps():
                self.commit(lambda:setattr(self.project,'objects',combined.objects))
        except ValueError as exc:
            self.error(str(exc))

    def load_custom_motif(self):
        path,_=QFileDialog.getOpenFileName(self,'Load custom motif','','Morale motif (*.mmotif)')
        if path:
            try:
                self.captured_motif=load_motif(path)
                self.statusBar().showMessage("Loaded motif. Select guides and choose Apply captured / loaded motif.")
            except (OSError,ValueError) as exc:
                self.error(str(exc))

    def save_custom_motif(self,selected=False):
        packet=None if selected else getattr(self,'captured_motif',None)
        obj=self.selected_object()
        if selected and obj and obj.custom_motif_paths:
            packet={'format':'morale-motif','version':1,'name':obj.custom_motif_name,'paths':obj.custom_motif_paths}
        if packet is None:
            self.statusBar().showMessage("Select a guide containing a custom motif." if selected else "Capture or load a motif first.")
            return
        name,_=QFileDialog.getSaveFileName(self,'Save custom motif','custom.mmotif','Morale motif (*.mmotif)')
        if name:
            path=Path(name)
            if path.suffix.lower()!='.mmotif':
                path=path.with_suffix('.mmotif')
                if not self.confirm_replacement(path):
                    return
            try:
                save_motif(packet,path)
            except (OSError,ValueError) as exc:
                self.error(str(exc))

    def apply_raster_trace(self,project):
        combined=deepcopy(self.project)
        objects=deepcopy(project.objects)
        if not objects:
            raise ValueError("The trace contains no objects to add.")
        for obj in objects:
            obj.id=uuid.uuid4().hex
        combined.objects.extend(objects)
        if project.reference:
            decode_reference(project.reference)
            combined.reference=deepcopy(project.reference)
        Project.loads(combined.dumps())
        generate(combined)
        self._selected_id=objects[0].id
        self.selected_ids={obj.id for obj in objects}
        def apply():
            self.project.objects=combined.objects
            self.project.reference=combined.reference
        self.commit(apply)
        self.set_mode('select')

    def digitize_raster(self):
        path,_=QFileDialog.getOpenFileName(self,'Digitize artwork','','Artwork (*.svg *.png *.jpg *.jpeg *.bmp *.webp)')
        if path:
            dialog=TraceDialog(path,self)
            try:
                if dialog.exec()==dialog.DialogCode.Accepted and dialog.project is not None:
                    self.apply_raster_trace(dialog.project)
            except ValueError as exc:
                self.error(str(exc))
            finally:
                dialog.runner.cancel()
                dialog.deleteLater()

    def compare_machine_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Compare machine file with current design","",file_filters())
        if path:
            try:
                dialog=ComparisonDialog(self.project,path,self)
                try:
                    dialog.exec()
                finally:
                    dialog.deleteLater()
            except (OSError,ValueError) as exc:
                self.error(str(exc))

    def placement_template(self):
        if not self.preview_available():
            return
        dialog = TemplateDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export placement template", "placement.pdf", "PDF document (*.pdf)")
        if not path:
            return
        if not Path(path).suffix:
            path += ".pdf"
        try:
            plan = export_template(self.project,path,dialog.paper.currentText(),dialog.stitches.isChecked())
            self.statusBar().showMessage(f"Exported {plan.rows*plan.columns} placement pages. Print at Actual size and verify the 50 mm ruler.")
        except (OSError,ValueError) as exc:
            self.error(str(exc))

    def new(self):
        if self.confirm_discard():
            self.replace_project(Project())

    def load_demo(self):
        if self.confirm_discard():
            self.replace_project(demo_project())

    def load_satin_sample(self):
        if self.confirm_discard():
            self.replace_project(satin_sample())

    def open(self):
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open design", "", "Morale project (*.morale);;" + file_filters())
        if path:
            self.open_path(path)

    def browse_designs(self):
        dialog=LibraryDialog(self,getattr(self,"library_folder",str(self.file_path.parent) if self.file_path else None))
        try:
            accepted=dialog.exec()==dialog.DialogCode.Accepted
            self.library_folder=dialog.folder
            if accepted and dialog.selected_path and self.confirm_discard():
                self.open_path(dialog.selected_path)
        finally:
            dialog.runner.cancel()
            dialog.deleteLater()

    def open_path(self,path):
        try:
            if Path(path).suffix.lower() == ".morale":
                if Path(path).stat().st_size > 50_000_000:
                    raise ValueError("Project files are limited to 50 MB.")
                project = Project.loads(Path(path).read_text(encoding="utf-8"))
                self.replace_project(project, Path(path))
            else:
                result = import_machine(path)
                self.replace_project(result.project)
                self.saved = ""
                self.update_title()
                QMessageBox.information(self, "Design imported", "\n\n".join(result.notes))
        except (ValueError, OSError) as exc:
            self.error(f"Could not open this project.\n{exc}")

    def import_design(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import machine design", "", file_filters())
        if not path:
            return
        try:
            result = import_machine(path)
            if len(self.project.objects) + len(result.project.objects) > 500:
                raise ValueError("Combined design would exceed 500 objects.")
            combined = deepcopy(self.project)
            combined.objects.extend(result.project.objects)
            generate(combined)  # Check the combined command budget before mutation.
            self.selected_id = result.project.objects[0].id
            self.commit(lambda: self.project.objects.extend(result.project.objects))
            QMessageBox.information(self, "Design imported", "\n\n".join(result.notes))
        except (ValueError, OSError) as exc:
            self.error(f"Could not import this design.\n{exc}")

    def batch_convert(self):
        self.reset_playback()
        BatchDialog(self).exec()

    def add_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import reference image", "", "Raster images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            try:
                self.set_reference(import_reference(path, self.project.hoop_width, self.project.hoop_height))
            except (ValueError, OSError) as exc:
                self.error(str(exc))

    def set_reference(self, reference):
        candidate = deepcopy(self.project)
        candidate.reference = reference
        Project.loads(candidate.dumps())
        decode_reference(reference)
        self.commit(lambda: setattr(self.project, "reference", deepcopy(reference)))

    def edit_reference(self):
        if not self.project.reference:
            self.statusBar().showMessage("Import a reference image first.")
            return
        dialog = ReferenceDialog(self.project.reference, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.set_reference(dialog.result_reference())

    def compatibility(self):
        QMessageBox.information(self, "Format compatibility", f"Readers available: {len(IMPORT_FORMATS)}\n" + ", ".join(sorted(IMPORT_FORMATS)) + f"\n\nMachine writers: {len(EXPORT_FORMATS)}\n" + ", ".join(sorted(EXPORT_FORMATS)) + "\n\nReader availability is not physical machine certification. Synthetic round-trip tests cover supported writers; externally produced files are still needed to validate reader-only formats.\n\nImported designs preserve stitches, jumps, trims, stops and color changes. Needle events are converted to color blocks with a notice. Unsupported specialist commands are rejected. Proprietary editable formats such as EMB and ART are not supported.")

    def save(self, save_as=False):
        path = self.file_path
        if not path or save_as:
            name, _ = QFileDialog.getSaveFileName(self, "Save editable project", str(path or "design.morale"), "Morale project (*.morale)")
            if not name:
                return False
            path = Path(name)
            if path.suffix.lower() != ".morale":
                path = path.with_suffix(".morale")
                if not self.confirm_replacement(path):
                    return False
        try:
            self.project.save(path)
            self.file_path = path
            self.saved = self.project.dumps()
            self.checkpoint()
            self.update_title()
            self.statusBar().showMessage(f"Project saved · {path}")
            return True
        except (OSError, ValueError) as exc:
            self.error(f"Could not save your project.\n{exc}")
            return False

    def export(self):
        if not self.preview_available():
            return
        issues = [self.generation_error] if self.generation_error else preflight(self.project, self.blocks)
        if issues:
            self.error("\n".join(issues))
            return
        name, selected_filter = QFileDialog.getSaveFileName(self, "Export machine stitches", "design.pes", file_filters(export=True))
        if not name:
            return
        if not self.preview_available():
            return
        path = Path(name)
        extension = selected_filter.split("*.")[-1].split(")")[0]
        if path.suffix.lower() != f".{extension}":
            path = path.with_suffix(f".{extension}")
            if not self.confirm_replacement(path):
                return
        try:
            result=export_machine(self.project, path, self.blocks, pes_version=1 if "PES v1" in selected_filter else 6)
            self.statusBar().showMessage(f"Exported {path.name} · {result['prepared_stitches']:,} stitches prepared · {result['subdivision_added_stitches']:,} positions added")
            notes = [export_summary(result),*export_notes(path.suffix.lower(), 1 if "PES v1" in selected_filter else 6)]
            QMessageBox.information(self, "Stitches exported", f"Saved {path.name}.\n\n" + "\n\n".join(notes) + "\n\nTest on scrap fabric. Keep your editable .morale project.")
        except Exception as exc:
            self.error(f"Could not export the machine file.\n{exc}")

    def confirm_replacement(self, path):
        # A suffix correction can change the target after the native dialog's
        # overwrite check. Confirm that actual destination if it already exists.
        return not path.exists() or QMessageBox.question(
            self, "Replace existing file?", f"{path.name} already exists. Replace it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def thread_chart(self):
        if not self.preview_available():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export thread sequence", "threads.csv", "Thread chart (*.csv)")
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    write_chart(self.project, self.blocks, f)
                self.statusBar().showMessage(f"Thread chart saved · {path}")
            except OSError as exc:
                self.error(str(exc))

    def help(self):
        QMessageBox.information(self, "Make your first design", "Choose a shape tool and drag in the hoop. For polygon/path and satin rails, click points and press Enter. Escape cancels. Scroll zooms; middle-drag pans.\n\nEdit → Add lettering creates editable system-font outlines with holes. Edit lettering changes text/font/height/spacing. Saved contours remain usable without the font. Choose straight, curved, or three-letter monogram layout. Purpose-digitized embroidery fonts remain in development.\n\nSelect an object to set size, thread, stitches, and finishing. Edit path / satin points changes coordinates; Edit individual stitches permits command editing. Applying stitch edits converts that object to manual stitches; Undo restores geometry.\n\nPreview, save a .morale project, and export a machine format. File also offers machine import, batch conversion, CSV charts and samplers. View provides units, custom fields and rulers.\n\nFile → Import SVG artwork creates editable fills and running outlines. Pull compensation in object properties extends fill and satin stitches per side. Advanced routing remains in development. Physical sew-out validation is still required.")

    def closeEvent(self, event):
        if self.confirm_discard():
            self._closing = True
            self.preview_revision += 1
            self.timer.stop()
            self.preview_debounce.stop()
            if self.generation_runner:
                self.generation_runner.cancel()
            self.recovery_timer.stop()
            self.recovery_idle.stop()
            if self.recovery:
                try:
                    self.recovery.close()
                except OSError:
                    pass  # A stale recovery is preferable to losing project data.
            event.accept()
        else:
            event.ignore()

    def checkpoint(self):
        if not self.recovery:
            return
        try:
            current = self.project.dumps()
            if current == self.saved:
                self.recovery.clear()
                self.recovery_last = None
            elif current != self.recovery_last:
                self.recovery.write(self.project, self.file_path)
                self.recovery_last = current
            self.recovery_error = ""
        except (OSError, ValueError) as exc:
            self.recovery_error = str(exc)
            self.statusBar().showMessage(f"Recovery snapshot could not be saved: {exc}")

    def restore_recovery(self, path):
        if not self.recovery:
            raise ValueError("Recovery storage is unavailable.")
        project = self.recovery.load(path)
        decode_reference(project.reference)
        # Secure the recovered copy before consuming its source. Recovered work
        # always saves to a newly chosen path, never silently over the old file.
        self.recovery.write(project)
        self.recovery_last = project.dumps()
        self.replace_project(project, recovered=True)
        if self.recovery_error:
            raise OSError(self.recovery_error)
        self.recovery.discard(path)
        self.update_title()

    def recover_session(self, quiet=False):
        if not self.recovery:
            if not quiet:
                self.error("Recovery storage is unavailable. " + self.recovery_error)
            return
        try:
            entries = self.recovery.available()
        except OSError as exc:
            self.recovery_error = str(exc)
            self.statusBar().showMessage(f"Recovery copies could not be read: {exc}")
            return
        if not entries:
            if not quiet:
                self.statusBar().showMessage("No interrupted sessions found.")
            return
        choices = [f"{i + 1}. {entry['name']} — {entry['updated']}" + (" (damaged)" if entry["error"] else "") for i, entry in enumerate(entries)]
        choice, accepted = QInputDialog.getItem(self, "Recover interrupted session", "Choose a recovery copy. Cancel keeps all copies for later.", choices, 0, False)
        if not accepted:
            return
        entry = entries[choices.index(choice)]
        action = QMessageBox.question(self, "Recovery copy", "Restore this design as an unsaved project? Choose No to discard this recovery copy, or Cancel to keep it.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        try:
            if action == QMessageBox.StandardButton.Yes and self.confirm_discard():
                self.restore_recovery(entry["path"])
            elif action == QMessageBox.StandardButton.No:
                self.recovery.discard(entry["path"])
        except (OSError, ValueError) as exc:
            self.error(str(exc))


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--library-search-worker':
        from .library_search import worker_main
        sys.exit(worker_main(sys.argv[2:]))
    if len(sys.argv)>1 and sys.argv[1]=='--self-test':
        from .self_test import worker_main
        sys.exit(worker_main(sys.argv[2:]))
    if len(sys.argv)>1 and sys.argv[1]=='--generation-worker':
        from .generation import worker_main
        sys.exit(worker_main(sys.argv[2:]))
    if len(sys.argv)>1 and sys.argv[1]=='--hoop-worker':
        from .hoop_bundle import worker_main
        sys.exit(worker_main(sys.argv[2:]))
    if len(sys.argv)>1 and sys.argv[1]=='--trace-worker':
        from .raster_trace import worker_main
        sys.exit(worker_main(sys.argv[2:]))
    if len(sys.argv)>1 and sys.argv[1]=='--preview-worker':
        from .preview_worker import worker_main
        sys.exit(worker_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--batch-worker":
        from .batch import worker_main
        sys.exit(worker_main(sys.argv[2:]))
    app = QApplication(sys.argv)
    app.setApplicationName("Morale")
    app.setOrganizationName("Morale")
    app.setStyle("Fusion")
    window = MainWindow(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "recovery", background_generation=True)
    window.show()
    QTimer.singleShot(0, lambda: window.recover_session(quiet=True))
    sys.exit(app.exec())
