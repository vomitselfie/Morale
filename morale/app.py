"""Morale's native Qt desktop application."""
import math
from pathlib import Path
import sys
import uuid
from PySide6.QtCore import Qt, QTimer, QStandardPaths, QObject, QEvent
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QListWidgetItem, QLineEdit, QMessageBox, QColorDialog,
    QInputDialog)
from .model import Project, DesignObject, PALETTE, demo_project
from .generation import GenerationRunner
from .measurements import HoopDialog as SewingFieldDialog, factor, dimension, validate_hoop
from .threads import THREAD_FIELDS, thread_key, usage
from .reference import decode_reference
from .recovery import RecoveryStore
from .engine import generate, preflight
from .window_ui import STYLE, WindowLayoutMixin
from .window_files import FileWorkflowsMixin
from .window_artwork import ArtworkMixin
from .window_editing import EditingMixin

class MainWindow(WindowLayoutMixin, FileWorkflowsMixin, ArtworkMixin, EditingMixin, QMainWindow):
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
        # Opening and importing decode files in a worker in the desktop app.
        self.open_runner = None
        self.opening = None
        self.open_progress = None
        if background_generation:
            from .open_worker import make_runner
            self.open_runner = make_runner(self)
            self.open_runner.ready.connect(self.opened)
            self.open_runner.failed.connect(self.open_failed)
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
                # Lettering offers planned satin columns alongside fill and running.
                enabled = mode in ({"manual"} if obj.kind == "stitches" else {"satin"} if obj.kind == "satin" else {"running", "triple", "motif"} if obj.kind == "path" else {"satin", "fill", "running", "triple"} if obj.lettering else {"fill", "contour", "running", "triple", "motif", "pattern"})
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
            if key == "stitch_type" and obj.lettering:
                self.change_lettering_stitches(obj, value)
                return
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
        dialog = SewingFieldDialog(self.project.hoop_width, self.project.hoop_height, self.unit, self)
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

    def help(self):
        QMessageBox.information(self, "Make your first design", "Choose a shape tool and drag in the hoop. For polygon/path and satin rails, click points and press Enter. Escape cancels. Scroll zooms; middle-drag pans.\n\nEdit → Add lettering creates editable system-font lettering, sewn as satin columns by default. Edit lettering changes text/font/height/spacing. Saved contours remain usable without the font. Choose straight, curved, or three-letter monogram layout. Purpose-digitized embroidery fonts remain in development.\n\nSelect an object to set size, thread, stitches, and finishing. Edit path / satin points changes coordinates; Edit individual stitches permits command editing. Applying stitch edits converts that object to manual stitches; Undo restores geometry.\n\nPreview, save a .morale project, and export a machine format. File also offers machine import, batch conversion, CSV charts and samplers. View provides units, custom fields and rulers.\n\nFile → Import SVG artwork creates editable fills and running outlines. Pull compensation in object properties extends fill and satin stitches per side. Advanced routing remains in development. Physical sew-out validation is still required.")

    def closeEvent(self, event):
        if self.confirm_discard():
            self._closing = True
            self.preview_revision += 1
            self.timer.stop()
            self.preview_debounce.stop()
            if self.generation_runner:
                self.generation_runner.cancel()
            if self.open_runner:
                self.cancel_opening()
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
    if len(sys.argv)>1 and sys.argv[1]=='--open-worker':
        from .open_worker import worker_main
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
    opener = FileOpenFilter(window)
    app.installEventFilter(opener)
    path = startup_file(sys.argv)
    if path:
        # A file opened from the desktop takes priority; recovery stays in the File menu.
        QTimer.singleShot(0, lambda: window.open_path(path))
    else:
        QTimer.singleShot(0, lambda: window.recover_session(quiet=True))
    sys.exit(app.exec())


def startup_file(argv):
    """The design passed by a file association or command line, if any."""
    for argument in argv[1:]:
        if not argument.startswith("-") and Path(argument).is_file():
            return argument
    return None


class FileOpenFilter(QObject):
    """Open designs that macOS delivers as file-open events (Finder, Dock)."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.FileOpen and event.file():
            if self.window.confirm_discard():
                self.window.open_path(event.file())
            return True
        return super().eventFilter(watched, event)
