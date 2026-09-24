"""Menus, toolbars and panels of the main window."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QFormLayout,
    QDoubleSpinBox, QComboBox, QCheckBox, QLineEdit, QMessageBox, QSplitter, QSlider,
    QToolBar, QScrollArea, QFrame)
from .canvas import Canvas
from .model import PALETTE
from .measurements import factor, dimension


STYLE = """
QMainWindow, QWidget { background: #f7f8f4; color: #293e35; font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: {base}pt; }
QToolBar { background: #ffffff; border: 0; border-bottom: 1px solid #dde4dc; padding: 8px; spacing: 7px; }
QToolButton { padding: 8px 12px; border-radius: 5px; }
QToolButton:hover, QPushButton:hover { background: #e1ebe3; }
QToolButton:checked { background: #dceadf; color: #23543d; }
QPushButton { border: 1px solid #7a8b7e; border-radius: 5px; padding: 7px 10px; background: #ffffff; }
QPushButton#primary { background: #315e49; color: white; border: 0; padding: 9px 15px; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox { background: white; border: 1px solid #7a8b7e; border-radius: 4px; padding: 5px; min-height: 20px; }
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #315e49; padding: 4px; }
QPushButton:focus { border: 2px solid #315e49; padding: 6px 9px; }
QPushButton#primary:focus { border: 2px solid #1c3a2c; padding: 7px 13px; }
QToolButton:focus { border: 2px solid #315e49; padding: 6px 10px; }
QListWidget { background: transparent; border: 0; outline: 0; }
QListWidget:focus { border: 2px solid #315e49; border-radius: 5px; }
QListWidget::item { padding: 10px 5px; margin: 2px 0; border-radius: 5px; }
QListWidget::item:selected { background: #dce9dd; color: #234f3a; }
QLabel#eyebrow { color: #56665a; font-size: {small}pt; font-weight: 600; letter-spacing: 2px; }
QLabel#heading { font-size: {heading}pt; font-weight: 600; }
QLabel#muted { color: #56665a; }
QStatusBar { background: #ecf0e8; color: #46594c; }
QSlider::groove:horizontal { height: 5px; background: #a9b8ab; border-radius: 2px; }
QSlider::handle:horizontal { width: 13px; margin: -4px 0; background: #37664d; border-radius: 6px; }
QSplitter::handle { background: #dce3d9; width: 1px; }
QCheckBox { spacing: 7px; }
QWidget:disabled { color: #88968c; }
"""


def style_sheet(base_points):
    """The window style in points relative to the system font, so text follows the
    operating system's text-size setting instead of fixed pixels."""
    base = max(8., min(32., base_points))
    sizes = {"base": base, "small": max(7.5, base * .8), "heading": base * 1.8}
    text = STYLE
    for key, value in sizes.items():
        text = text.replace("{" + key + "}", f"{value:.1f}")
    return text


def add_mnemonics(menu):
    """Give every entry of a menu (and its submenus) a unique keyboard accelerator."""
    used = {a.text()[a.text().index("&") + 1].lower() for a in menu.actions() if "&" in a.text() and a.text().index("&") + 1 < len(a.text())}
    for action in menu.actions():
        text = action.text()
        if action.menu() is not None:
            add_mnemonics(action.menu())
        if action.isSeparator() or not text or "&" in text:
            continue
        candidates = [i for i, character in enumerate(text) if character.isalnum()]
        # Prefer an unused letter; long menus reuse one, and Qt cycles between matches.
        index = next((i for i in candidates if text[i].lower() not in used), candidates[0] if candidates else None)
        if index is not None:
            used.add(text[index].lower())
            action.setText(text[:index] + "&" + text[index:])


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


class WindowLayoutMixin:
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
