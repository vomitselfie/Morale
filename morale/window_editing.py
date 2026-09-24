"""Point, stitch, outline and arrangement edits plus the clipboard."""
from copy import deepcopy
import math
import uuid
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox
from .model import Project
from .nodes import PointDialog, ContourDialog
from .routing import route_object
from .routing_dialog import RoutingDialog
from .stitch_edit import StitchDialog, manual_object
from .arrange import arrange_selection, transform_selection, bounds
from .transform_dialog import TransformDialog
from .geometry import combine_outlines, replace_contours
from .bezier import enable_handles, edit_controls
from .clipboard import MIME_TYPE, encode_objects, decode_objects
from .engine import generate


class EditingMixin:
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
