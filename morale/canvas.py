"""Native Qt drawing surface with millimeter coordinates and stitch playback."""
import math
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget
from .measurements import dimension, factor
from .reference import decode_reference
from .simulation import Timeline
from .stitch_canvas import StitchCanvasMixin


class Canvas(StitchCanvasMixin, QWidget):
    selected = Signal(str)
    selection_request = Signal(str, bool)
    member_request = Signal(str)
    box_selected = Signal(object)
    moved = Signal(str, float, float)
    drawn = Signal(str, list)
    zoom_changed = Signal(int)
    message = Signal(str)
    measured = Signal(float, float, float)
    node_edited = Signal(str, object)
    stitch_moved = Signal(str, int, float, float)
    stitches_moved = Signal(str, object, float, float)
    stitches_deleted = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 380)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.project = None
        self.blocks = []
        self.paths = []
        self.selected_id = ""
        self.selected_ids = set()
        self.marquee_start = None
        self.marquee_base = set()
        self.snap_grid = False
        self.snap_objects = False
        self.snap_bounds_cache = {}
        self.grid_spacing = None
        self.mode = "select"
        self.scale = 5.0
        self.pan = QPointF()
        self.press = None
        self.snap_guides = (None,None)
        self.drag = QPointF()
        self.panning = False
        self.vertices = []
        self.cursor_point = QPointF()
        self.show_stitches = True
        self.show_grid = True
        self.reference_key = None
        self.reference_image = None
        self.show_rulers = True
        self.unit = "mm"
        self.measurement = None
        self.playhead = None
        self.node_drag = None
        self.stitch_drag = None
        self.stitch_selection = None
        self.stitch_multi = None
        self.stitch_marquee = None
        self.handle_drag_mode = "free"
        self.show_travel = False
        self.show_controls = False
        self.inspection_ids = None
        self.timeline = Timeline([])

    def set_design(self, project, blocks):
        self.snap_bounds_cache = {}
        self.snap_guides = (None,None)
        self.stitch_marquee = None
        self.node_drag = None
        self.stitch_drag = None
        key = project.reference.get("png")
        if key != self.reference_key:
            self.reference_image = decode_reference(project.reference)
            self.reference_key = key
        self.project, self.blocks = project, blocks
        self.timeline = Timeline(blocks)
        self.paths = []
        for block in blocks:
            path = QPainterPath()
            for stitch in block.stitches:
                if stitch.command == "stitch":
                    path.lineTo(stitch.x, stitch.y)
                else:
                    path.moveTo(stitch.x, stitch.y)
            self.paths.append((block.object_id, block.color, path))
        self.update()

    def fit(self):
        if self.project:
            self.scale = max(.4, min((self.width() - 100) / self.project.hoop_width, (self.height() - 100) / self.project.hoop_height))
            self.pan = QPointF()
            self.zoom_changed.emit(round(self.scale / 5 * 100))
            self.update()

    def set_mode(self, mode):
        self.stitch_marquee = None
        self.node_drag = None
        self.stitch_drag = None
        self.snap_guides = (None,None)
        self.drag = QPointF()
        self.mode = mode
        self.vertices = []
        self.press = None
        self.marquee_start = None
        self.measurement = None
        self.setCursor(Qt.CursorShape.ArrowCursor if mode == "select" else Qt.CursorShape.CrossCursor)
        self.update()

    def world(self, point):
        return (point - QPointF(self.width() / 2, self.height() / 2) - self.pan) / self.scale

    def snapped(self, point):
        if not self.snap_grid:
            return point
        step = self.grid_step()
        return QPointF(round(point.x() / step) * step, round(point.y() / step) * step)

    def grid_step(self):
        return self.grid_spacing if self.grid_spacing is not None else 6.35 if self.unit == "in" else 10.

    def drawing_point(self, point):
        world = self.world(point)
        return self.snapped(world) if self.mode in {"ellipse", "rectangle", "leaf", "polygon", "path", "satin"} else world

    def movement_delta(self, point):
        delta = point - self.press
        if self.snap_grid:
            anchor = next((obj for obj in self.project.objects if obj.id == self.selected_id), None)
            if anchor:
                center = QPointF(anchor.x, anchor.y)
                delta = self.snapped(center + delta) - center
        self.snap_guides=(None,None)
        if self.snap_objects and self.project:
            from .object_snapping import snap_bounds,object_bounds
            selection=set(self.selected_ids) or {self.selected_id}
            moving=[];targets=[]
            for obj in self.project.objects:
                if not obj.visible or self.inspection_ids is not None and obj.id not in self.inspection_ids:continue
                if obj.id not in self.snap_bounds_cache:self.snap_bounds_cache[obj.id]=object_bounds(obj)
                (moving if obj.id in selection else targets).append(self.snap_bounds_cache[obj.id])
            candidate,self.snap_guides=snap_bounds(moving,targets,point-self.press,8/self.scale)
            if self.snap_guides[0] is not None:delta.setX(candidate.x())
            if self.snap_guides[1] is not None:delta.setY(candidate.y())
        return delta

    @staticmethod
    def outline_path(obj):
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        for points in obj.rings():
            path.moveTo(*points[0])
            for point in points[1:]:
                path.lineTo(*point)
            if obj.kind != "path":
                path.closeSubpath()
        return path

    def node_object(self):
        if self.project and len(self.selected_ids) == 1:
            return next((o for o in self.project.objects if o.id in self.selected_ids and o.visible
                         and o.kind in {"path", "polygon", "satin", "compound"}), None)
        return None

    def node_rings(self, obj):
        return obj.rings() if obj.kind == "compound" else [obj.control_points()]

    def move_node_target(self, target):
        _, ri, pi, rings = self.node_drag
        obj = self.node_object()
        if obj and obj.handles:
            from .bezier import move_control
            rings[ri] = move_control(rings[ri], pi, (target.x(), target.y()), self.handle_drag_mode)
        else:
            rings[ri][pi] = (target.x(), target.y())

    def paint_nodes(self, painter):
        obj = self.node_object()
        if obj is None:
            return
        rings = self.node_drag[3] if self.node_drag else self.node_rings(obj)
        painter.setPen(QPen(QColor("#2563bb"), 1.5 / self.scale))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for ring in rings:
            if obj.handles:
                path = QPainterPath(QPointF(*ring[1]))
                count = len(ring) // 3
                for i in range(count if obj.kind == "polygon" else count - 1):
                    j = (i + 1) % count
                    path.cubicTo(QPointF(*ring[3*i + 2]), QPointF(*ring[3*j]), QPointF(*ring[3*j + 1]))
                painter.drawPath(path)
                for i in range(0, len(ring), 3):
                    painter.drawLine(QPointF(*ring[i]), QPointF(*ring[i+1]))
                    painter.drawLine(QPointF(*ring[i+1]), QPointF(*ring[i+2]))
            elif obj.kind == "satin":
                for rail in (ring[::2], ring[1::2]):
                    painter.drawPolyline(QPolygonF([QPointF(*point) for point in rail]))
                for left, right in zip(ring[::2], ring[1::2]):
                    painter.drawLine(QPointF(*left), QPointF(*right))
            else:
                polygon = QPolygonF([QPointF(*point) for point in ring])
                if obj.kind == "path":
                    painter.drawPolyline(polygon)
                else:
                    painter.drawPolygon(polygon)
        for ri, ring in enumerate(rings):
            for pi, point in enumerate(ring):
                active = self.node_drag and (ri, pi) == self.node_drag[1:3]
                painter.setBrush(QColor("#cc3d39" if active else "#ffffff"))
                radius = 2.5 if obj.handles and pi % 3 != 1 else 3.5
                painter.drawEllipse(QPointF(*point), radius / self.scale, radius / self.scale)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#e9eeeb"))
        if self.project is None:
            return
        p.translate(self.width() / 2 + self.pan.x(), self.height() / 2 + self.pan.y())
        p.scale(self.scale, self.scale)
        hw, hh = self.project.hoop_width, self.project.hoop_height
        hoop = QRectF(-hw / 2, -hh / 2, hw, hh)
        p.setPen(QPen(QColor("#c9d5ce"), 2 / self.scale))
        p.setBrush(QColor("#fdfbf5"))
        p.drawRoundedRect(hoop.adjusted(-3, -3, 3, 3), 4, 4)
        p.fillRect(hoop, QColor("#fffdf8"))
        reference = self.project.reference
        if reference and reference["visible"] and self.reference_image is not None:
            p.save()
            p.translate(reference["x"], reference["y"])
            p.rotate(reference["rotation"])
            p.setOpacity(reference["opacity"])
            p.drawImage(QRectF(-reference["width"] / 2, -reference["height"] / 2, reference["width"], reference["height"]), self.reference_image)
            p.restore()
        if self.show_grid:
            p.setPen(QPen(QColor("#ecebe2"), 1 / self.scale))
            spacing = self.grid_step() * max(1, math.ceil(4 / (self.grid_step() * self.scale)))
            for i in range(math.ceil(-hw / 2 / spacing), math.ceil(hw / 2 / spacing)):
                x = i * spacing
                p.drawLine(QPointF(x, -hh / 2), QPointF(x, hh / 2))
            for i in range(math.ceil(-hh / 2 / spacing), math.ceil(hh / 2 / spacing)):
                y = i * spacing
                p.drawLine(QPointF(-hw / 2, y), QPointF(hw / 2, y))
        p.setPen(QPen(QColor("#b8c8bf"), 1 / self.scale, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(hoop)
        p.drawLine(QPointF(-2, 0), QPointF(2, 0))
        p.drawLine(QPointF(0, -2), QPointF(0, 2))
        for obj in self.project.objects:
            if not obj.visible or obj.kind == "stitches" or self.inspection_ids is not None and obj.id not in self.inspection_ids:
                continue
            if obj.stitch_type == "motif" and (self.show_stitches or self.playhead is not None) and (obj.id not in self.selected_ids or self.playhead is not None):
                continue
            p.save()
            if obj.id in self.selected_ids:
                p.translate(self.drag)
            color = QColor(obj.color)
            color.setAlpha(22 if self.playhead is not None else (65 if self.show_stitches else 215))
            p.setBrush(color if obj.stitch_type in {"fill", "contour", "satin"} else Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#87958d"),1/self.scale,Qt.PenStyle.DotLine) if obj.stitch_type=="motif" else QPen(QColor(obj.color), .18))
            p.drawPath(self.outline_path(obj))
            p.restore()
        manual_ids = {obj.id for obj in self.project.objects if obj.kind == "stitches"}
        if self.show_stitches or self.playhead is not None or manual_ids:
            remaining = self.playhead
            for block, (obj_id, color, path) in zip(self.blocks, self.paths):
                if self.inspection_ids is not None and obj_id not in self.inspection_ids:
                    if remaining is not None:
                        remaining -= len(block.stitches)
                    continue
                if not self.show_stitches and self.playhead is None and obj_id not in manual_ids:
                    continue
                p.save()
                if obj_id in self.selected_ids:
                    p.translate(self.drag)
                p.setPen(QPen(QColor(color), .16))
                p.setBrush(Qt.BrushStyle.NoBrush)
                if remaining is None or remaining >= len(block.stitches):
                    p.drawPath(path)
                    if remaining is not None:
                        remaining -= len(block.stitches)
                else:
                    partial = QPainterPath()
                    for stitch in block.stitches[:remaining]:
                        if stitch.command == "stitch":
                            partial.lineTo(stitch.x, stitch.y)
                        else:
                            partial.moveTo(stitch.x, stitch.y)
                    p.drawPath(partial)
                    if remaining > 0:
                        needle = block.stitches[remaining - 1]
                        p.setBrush(QColor("#243f36"))
                        p.drawEllipse(QPointF(needle.x, needle.y), 3 / self.scale, 3 / self.scale)
                    p.restore()
                    break
                p.restore()
        if self.show_travel or self.show_controls:
            self.paint_command_overlays(p)
        for selected in [o for o in self.project.objects if o.id in self.selected_ids and o.visible and self.playhead is None]:
            bounds = self.outline_path(selected).boundingRect().translated(self.drag).adjusted(-1, -1, 1, 1)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#286453"), 1.3 / self.scale, Qt.PenStyle.DashLine))
            p.drawRect(bounds)
            p.setBrush(QColor("#ffffff"))
            for pt in [bounds.topLeft(), bounds.topRight(), bounds.bottomLeft(), bounds.bottomRight()]:
                p.drawRect(QRectF(pt.x() - 2.5 / self.scale, pt.y() - 2.5 / self.scale, 5 / self.scale, 5 / self.scale))
        p.setBrush(QColor(57, 110, 89, 35))
        p.setPen(QPen(QColor("#397359"), 1.5 / self.scale, Qt.PenStyle.DashLine))
        if self.marquee_start is not None:
            p.drawRect(QRectF(self.marquee_start, self.cursor_point).normalized())
        if self.stitch_marquee is not None:
            p.drawRect(QRectF(self.stitch_marquee[1],self.cursor_point).normalized())
        if self.press is not None and self.mode in {"ellipse", "rectangle", "leaf"}:
            rect = QRectF(self.press, self.cursor_point).normalized()
            if self.mode == "rectangle":
                p.drawRect(rect)
            else:
                p.drawEllipse(rect)
        if self.vertices:
            if self.mode == "satin":
                for i in range(0, len(self.vertices) - 1, 2):
                    p.drawLine(self.vertices[i], self.vertices[i + 1])
                for rail in (self.vertices[::2], self.vertices[1::2]):
                    p.drawPolyline(QPolygonF(rail))
            else:
                p.drawPolyline(QPolygonF(self.vertices + [self.cursor_point]))
            for point in self.vertices:
                p.drawEllipse(point, 2 / self.scale, 2 / self.scale)
        if self.mode == "nodes" and self.playhead is None:
            self.paint_nodes(p)
        if self.mode == "stitch_nodes" and self.playhead is None:
            self.paint_stitch_points(p)
        if self.mode=='select' and self.press is not None and self.snap_objects:
            p.setPen(QPen(QColor('#1765df'),1/self.scale,Qt.PenStyle.DashLine))
            top_left=self.world(QPointF(0,0));bottom_right=self.world(QPointF(self.width(),self.height()))
            x,y=self.snap_guides
            if x is not None:p.drawLine(QPointF(x,top_left.y()),QPointF(x,bottom_right.y()))
            if y is not None:p.drawLine(QPointF(top_left.x(),y),QPointF(bottom_right.x(),y))
        p.resetTransform()
        if self.measurement:
            start, end = self.measurement
            origin = QPointF(self.width() / 2, self.height() / 2) + self.pan
            p.setPen(QPen(QColor("#a45042"), 2, Qt.PenStyle.DashLine))
            p.drawLine(start * self.scale + origin, end * self.scale + origin)
            p.drawText(24, self.height() - 18, f"Distance: {dimension(math.hypot(end.x() - start.x(), end.y() - start.y()), self.unit)}")
        p.setPen(QColor("#637c70"))
        p.drawText(32, 48 if self.show_rulers else 26, f"{dimension(hw, self.unit)} × {dimension(hh, self.unit)} hoop · {dimension(self.grid_step(), self.unit)} grid")
        if self.show_rulers:
            self.paint_rulers(p)
        if self.show_travel or self.show_controls:
            p.setPen(QColor("#4a5660"))
            p.drawText(28,self.height()-38,"Dashed orange: jump  ·  X: trim  ·  square: stop  ·  diamond: thread change")
        if not self.project.objects and not (self.project.reference and self.project.reference["visible"]):
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Your next lovely thing starts here.\nChoose a shape and drag inside the hoop.")

    def paint_command_overlays(self, painter):
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for _,command,start,end,object_id,previous_id in self.timeline.visible_events(self.playhead,self.inspection_ids):
            a,b = QPointF(*start),QPointF(*end)
            if previous_id in self.selected_ids:
                a += self.drag
            if object_id in self.selected_ids:
                b += self.drag
            if command == "thread":
                b = a
            if command == "jump":
                if self.show_travel and (b-a).manhattanLength() > .001:
                    painter.setPen(QPen(QColor("#b7681f"),1.2/self.scale,Qt.PenStyle.DashLine))
                    painter.drawLine(a,b)
            elif self.show_controls:
                radius = 4/self.scale
                painter.setPen(QPen(QColor("#a33c47" if command == "stop" else "#6356a1"),1.6/self.scale))
                if command == "trim":
                    painter.drawLine(b+QPointF(-radius,-radius),b+QPointF(radius,radius))
                    painter.drawLine(b+QPointF(-radius,radius),b+QPointF(radius,-radius))
                elif command == "stop":
                    painter.drawRect(QRectF(b.x()-radius,b.y()-radius,2*radius,2*radius))
                else:
                    painter.drawPolygon(QPolygonF([b+QPointF(-radius,0),b+QPointF(0,-radius),b+QPointF(radius,0),b+QPointF(0,radius)]))
        painter.restore()

    def paint_rulers(self, painter):
        painter.fillRect(0, 0, self.width(), 24, QColor("#f2f5ee"))
        painter.fillRect(0, 0, 24, self.height(), QColor("#f2f5ee"))
        painter.setPen(QColor("#607869"))
        step = 12.7 if self.unit == "in" else 10.
        while step * self.scale < 45:
            step *= 2
        for axis, extent, origin in [(0, self.width(), self.width() / 2 + self.pan.x()), (1, self.height(), self.height() / 2 + self.pan.y())]:
            low, high = (24 - origin) / self.scale, (extent - origin) / self.scale
            for i in range(math.ceil(low / step), math.floor(high / step) + 1):
                value = i * step
                position = origin + value * self.scale
                text = f"{value / factor(self.unit):g}"
                if axis == 0:
                    painter.drawLine(QPointF(position, 19), QPointF(position, 24))
                    painter.drawText(QPointF(position + 2, 14), text)
                else:
                    painter.drawLine(QPointF(19, position), QPointF(24, position))
                    painter.save()
                    painter.translate(13, position - 2)
                    painter.rotate(-90)
                    painter.drawText(QPointF(), text)
                    painter.restore()

    def mousePressEvent(self, event):
        self.snap_bounds_cache = {}
        self.snap_guides = (None,None)
        self.setFocus()
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True
            self.pan_start = event.position()
            return
        if event.button() != Qt.MouseButton.LeftButton or self.playhead is not None:
            return
        point = self.drawing_point(event.position())
        self.cursor_point = point
        if self.mode == "stitch_nodes":
            modifiers=event.modifiers()
            subtract=bool(modifiers & Qt.KeyboardModifier.AltModifier)
            if subtract or not self.pick_stitch(point,modifiers):
                block=self.stitch_block()
                if block is not None:
                    base=self.selected_stitch_indices() if modifiers & (Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.ShiftModifier|Qt.KeyboardModifier.AltModifier) else set()
                    self.stitch_marquee=(block.object_id,point,base,subtract)
                    self.press=None;self.stitch_drag=None
        elif self.mode == "nodes":
            obj = self.node_object()
            if obj:
                rings = self.node_rings(obj)
                hits = [(math.hypot(x - point.x(), y - point.y()), 0 if not obj.handles or pi % 3 == 1 else 1, ri, pi)
                        for ri, ring in enumerate(rings) for pi, (x, y) in enumerate(ring)]
                distance, _, ri, pi = min(hits)
                if distance * self.scale <= 8:
                    self.node_drag = (obj.id, ri, pi, rings)
                    self.press = point
            else:
                self.message.emit("Use Select to choose one polygon, path, satin column, or compound shape, then return to Nodes.")
        elif self.mode in {"polygon", "path", "satin"}:
            self.vertices.append(point)
            if self.mode == "satin":
                self.message.emit("Click the right rail point to complete this pair" if len(self.vertices) % 2 else "Click the next left/right pair, or Enter to finish")
        elif self.mode == "select":
            hit = ""
            from PySide6.QtGui import QPainterPathStroker
            stroker = QPainterPathStroker()
            stroker.setWidth(6 / self.scale)
            for obj in reversed(self.project.objects):
                path = self.outline_path(obj)
                if obj.stitch_type == "motif":
                    path = QPainterPath(path)
                    for object_id,color,sewn in self.paths:
                        if object_id == obj.id:
                            path.addPath(sewn)
                if obj.visible and (path.contains(point) or stroker.createStroke(path).contains(point)):
                    hit = obj.id
                    break
            additive = bool(event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                self.member_request.emit(hit)
            else:
                self.selection_request.emit(hit, additive)
            self.press = point if hit and hit in self.selected_ids else None
            if not hit:
                self.marquee_start = point
                self.marquee_base = set(self.selected_ids)
        else:
            self.press = point
            if self.mode == "measure":
                self.measurement = (point, point)
        self.update()

    def mouseMoveEvent(self, event):
        if self.panning:
            self.pan += event.position() - self.pan_start
            self.pan_start = event.position()
        else:
            self.cursor_point = self.drawing_point(event.position())
            if self.stitch_drag and self.press is not None:
                if (self.cursor_point-self.press).manhattanLength()*self.scale>2:
                    self.stitch_drag=(*self.stitch_drag[:2],self.snapped(self.cursor_point))
            elif self.node_drag and self.press is not None:
                if (self.cursor_point - self.press).manhattanLength() * self.scale > 2:
                    target = self.snapped(self.cursor_point)
                    self.move_node_target(target)
            elif self.press is not None and self.mode == "select":
                self.drag = self.movement_delta(self.cursor_point)
            elif self.press is not None and self.mode == "measure":
                self.measurement = (self.press, self.cursor_point)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.stitch_marquee is not None:
            object_id,start,base,subtract=self.stitch_marquee;self.stitch_marquee=None
            block=self.stitch_block()
            if self.playhead is None and block is not None and block.object_id==object_id:
                rect=QRectF(start,self.world(event.position())).normalized()
                hits={i for i,s in enumerate(block.stitches) if s.command in {'stitch','jump'} and rect.contains(QPointF(s.x,s.y))}
                indices=base-hits if subtract else base|hits
                self.stitch_multi=(object_id,indices)
                self.stitch_selection=(object_id,min(indices)) if indices else None
                if indices:self.announce_stitch()
                else:self.message.emit('No needle positions selected.')
            self.press=None;self.update();return
        if self.stitch_drag:
            object_id,index,_=self.stitch_drag
            end=self.world(event.position())
            changed=self.playhead is None and self.press is not None and (end-self.press).manhattanLength()*self.scale>2
            self.stitch_drag=None
            self.press=None
            if changed:
                target=self.snapped(end)
                self.move_stitch_selection(object_id,index,target)
            self.update()
            return
        if self.node_drag:
            object_id, ri, pi, rings = self.node_drag
            end = self.world(event.position())
            if self.playhead is None and self.press is not None and (end - self.press).manhattanLength() * self.scale > 2:
                target = self.snapped(end)
                self.move_node_target(target)
                self.node_drag = None
                self.node_edited.emit(object_id, rings)
            self.node_drag = None
            self.press = None
            self.update()
            return
        if self.marquee_start is not None:
            end = self.world(event.position())
            rectangle = QRectF(self.marquee_start, end).normalized()
            ids = []
            for obj in self.project.objects:
                box = self.outline_path(obj).boundingRect()
                # QRectF.contains(rect) rejects zero-width/height rectangles;
                # endpoint checks also enclose vertical/horizontal running paths.
                if obj.visible and rectangle.contains(box.topLeft()) and rectangle.contains(box.bottomRight()):
                    ids.append(obj.id)
            self.marquee_start = None
            self.box_selected.emit(list(self.marquee_base) + ids)
            self.update()
            return
        if self.press is not None:
            end = self.drawing_point(event.position())
            if self.mode == "measure":
                self.measurement = (self.press, end)
                dx, dy = end.x() - self.press.x(), end.y() - self.press.y()
                self.measured.emit(dx, dy, math.hypot(dx, dy))
            elif self.mode == "select" and self.selected_id and (end - self.press).manhattanLength() > .05:
                delta = self.movement_delta(end)
                self.moved.emit(self.selected_id, delta.x(), delta.y())
            elif self.mode in {"ellipse", "rectangle", "leaf"} and abs(end.x() - self.press.x()) >= 1 and abs(end.y() - self.press.y()) >= 1:
                self.drawn.emit(self.mode, [(self.press.x(), self.press.y()), (end.x(), end.y())])
        self.press = None
        self.snap_guides = (None,None)
        self.drag = QPointF()
        self.update()

    def finish_path(self):
        if self.mode == "satin" and (len(self.vertices) < 4 or len(self.vertices) % 2):
            self.message.emit("Satin needs at least two complete left/right pairs. Click the missing point, or Escape to cancel.")
            return
        if len(self.vertices) >= (2 if self.mode == "path" else 3):
            points = [(p.x(), p.y()) for p in self.vertices]
            self.drawn.emit(self.mode, points)
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.mode in {"polygon", "path", "satin"}:
            self.finish_path()

    def keyPressEvent(self, event):
        if self.mode == "stitch_nodes" and self.stitch_key(event):
            event.accept()
        elif event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.finish_path()
        elif event.key() == Qt.Key.Key_Escape:
            self.stitch_marquee = None
            self.node_drag = None
            self.stitch_drag = None
            self.vertices = []
            self.press = None
            self.marquee_start = None
            self.snap_guides = (None,None)
            self.drag = QPointF()
            self.measurement = None
            self.update()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        before = self.world(event.position())
        self.scale = max(.4, min(40, self.scale * (1.15 if event.angleDelta().y() > 0 else 1 / 1.15)))
        self.pan = event.position() - QPointF(self.width() / 2, self.height() / 2) - before * self.scale
        self.zoom_changed.emit(round(self.scale / 5 * 100))
        self.update()
