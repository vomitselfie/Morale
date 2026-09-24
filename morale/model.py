"""Editable, millimeter-based project data. No GUI or format-library dependency."""
from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
import re
import uuid
from .reference import validate_reference

PALETTE = ["#447568", "#7d9c69", "#d68b79", "#e9b75e", "#77668b", "#547e9d", "#333c39", "#eee7d7"]


@dataclass
class DesignObject:
    name: str = "Petal"
    kind: str = "ellipse"
    x: float = 0
    y: float = 0
    width: float = 20
    height: float = 30
    rotation: float = 0
    color: str = PALETTE[0]
    stitch_type: str = "fill"
    spacing: float = 0.45
    stitch_length: float = 2.5
    angle: float = 45
    underlay: bool = True
    visible: bool = True
    points: list = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    stitch_data: list = field(default_factory=list)
    color_break: bool = False
    tie_in: bool = False
    tie_off: bool = False
    trim_after: bool = False
    satin_max: float = 6
    connect_fill: bool = False
    route_fill: bool = False
    thread: dict = field(default_factory=dict)
    contours: list = field(default_factory=list)
    lettering: dict = field(default_factory=dict)
    flip_x: bool = False
    flip_y: bool = False
    stop_after: bool = False
    stage_note: str = ""
    group_id: str = ""
    handles: list = field(default_factory=list)
    pull_compensation: float = 0
    underlay_style: str = "auto"
    underlay_inset: float = 0
    underlay_spacing: float = 2
    minimum_stitch: float = 0
    jump_trim: float = 0
    motif_pattern: str = "diamond"
    motif_width: float = 4
    motif_height: float = 3
    motif_spacing: float = 5
    custom_motif_paths: list = field(default_factory=list)
    custom_motif_name: str = ""
    motif_reflected: bool = False
    density_gradient: bool = False
    gradient_end_spacing: float = 1.5
    gradient_reverse: bool = False
    motif_row_spacing: float = 5
    pattern_flip_x: bool = False
    pattern_flip_y: bool = False

    def outline(self):
        if self.handles:
            from .bezier import flatten_cubics
            return flatten_cubics(self.control_points(), self.kind == "polygon")
        if self.kind == "ellipse":
            points = [(math.cos(i * math.tau / 96) / 2, math.sin(i * math.tau / 96) / 2) for i in range(96)]
        elif self.kind in {"rectangle", "stitches", "compound"}:
            points = [(-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)]
        elif self.kind == "leaf":
            points = [(math.sin(i * math.pi / 32) * .5, -.5 + i / 32) for i in range(33)]
            points += [(-math.sin(i * math.pi / 32) * .5, -.5 + i / 32) for i in range(32, -1, -1)]
        elif self.kind == "satin":
            points = self.points[::2] + list(reversed(self.points[1::2]))
        else:
            points = self.points
        return self.transform(points)

    def rings(self):
        return [self.transform(ring) for ring in self.contours] if self.kind == "compound" else [self.outline()]

    def control_points(self):
        if not self.handles:
            return self.transform(self.points)
        return self.transform([p for anchor, handles in zip(self.points, self.handles) for p in (handles[0], anchor, handles[1])])

    def transform(self, points):
        a = math.radians(self.rotation)
        c, s = math.cos(a), math.sin(a)
        sx, sy = (-1 if self.flip_x else 1), (-1 if self.flip_y else 1)
        return [(self.x + px * sx * self.width * c - py * sy * self.height * s,
                 self.y + px * sx * self.width * s + py * sy * self.height * c) for px, py in points]


def validate_columns(columns, number):
    """Planned satin-lettering pieces in the object's normalized frame."""
    if not isinstance(columns, list) or not 1 <= len(columns) <= 2000:
        raise ValueError("Satin lettering needs 1–2,000 planned pieces.")
    total = 0
    for piece in columns:
        if not isinstance(piece, dict) or len(piece) != 1 or next(iter(piece)) not in {"rails", "fill", "run"}:
            raise ValueError("Invalid satin lettering piece.")
        kind, value = next(iter(piece.items()))
        paths = value if kind == "fill" else [value]
        if not isinstance(paths, list) or not paths:
            raise ValueError("Invalid satin lettering piece.")
        for path in paths:
            minimum = 3 if kind == "fill" else 4 if kind == "rails" else 2
            if not isinstance(path, list) or len(path) < minimum or kind == "rails" and len(path) % 2:
                raise ValueError("Invalid satin lettering outline or rails.")
            total += len(path)
            for point in path:
                if not isinstance(point, list) or len(point) != 2:
                    raise ValueError("Invalid satin lettering coordinate.")
                # Join overlaps can reach just past the glyph bounds.
                for v in point:
                    number(v, -1, 1)
    if total > 100_000:
        raise ValueError("Satin lettering exceeds 100,000 planned points.")


def drop_lettering(obj):
    """Turn lettering into plain outlines; planned satin columns go with it."""
    obj.lettering = {}
    if obj.kind == "compound" and obj.stitch_type == "satin":
        obj.stitch_type = "fill"


@dataclass
class Project:
    name: str = "Untitled design"
    hoop_width: float = 100
    hoop_height: float = 100
    objects: list[DesignObject] = field(default_factory=list)
    reference: dict = field(default_factory=dict)

    def dumps(self):
        return json.dumps({"format": "morale", "version": 2, **asdict(self)}, indent=2, allow_nan=False)

    @classmethod
    def loads(cls, text):
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("format") != "morale" or type(data.get("version")) is not int or data.get("version") not in {1, 2}:
            raise ValueError("This is not a supported Morale project (versions 1–2).")
        def number(value, low, high):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"Expected a number between {low} and {high}.")
            return value
        name = data.get("name")
        if not isinstance(name, str) or len(name) > 200:
            raise ValueError("Invalid project name.")
        project = cls(name, number(data.get("hoop_width"), 20, 500), number(data.get("hoop_height"), 20, 500))
        validate_reference(data.get("reference", {}))
        project.reference = dict(data.get("reference", {}))
        objects = data.get("objects")
        if not isinstance(objects, list) or len(objects) > 500:
            raise ValueError("A project may contain at most 500 objects.")
        ids = set()
        command_count = 0
        for raw in objects:
            if not isinstance(raw, dict):
                raise ValueError("Invalid design object.")
            try:
                obj = DesignObject(**raw)
            except TypeError as exc:
                raise ValueError("Unsupported object properties.") from exc
            if not isinstance(obj.kind, str) or not isinstance(obj.stitch_type, str) or obj.kind not in {"ellipse", "rectangle", "leaf", "polygon", "path", "stitches", "satin", "compound"} or obj.stitch_type not in {"running", "triple", "fill", "contour", "motif", "pattern", "manual", "satin"}:
                raise ValueError("Unsupported object or stitch type.")
            if not isinstance(obj.id, str) or obj.id in ids or len(obj.id) > 100:
                raise ValueError("Invalid or duplicate object ID.")
            if not isinstance(obj.group_id, str) or len(obj.group_id) > 100:
                raise ValueError("Invalid object group.")
            ids.add(obj.id)
            if not isinstance(obj.name, str) or len(obj.name) > 200:
                raise ValueError("Invalid object name.")
            if not isinstance(obj.stage_note, str) or len(obj.stage_note) > 500:
                raise ValueError("Invalid stage instruction.")
            if not isinstance(obj.color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", obj.color):
                raise ValueError("Invalid thread color.")
            if not isinstance(obj.thread, dict) or any(key not in {"brand", "catalog_number", "description", "weight", "chart", "details"} or not isinstance(value, str) or len(value) > 1024 for key, value in obj.thread.items()):
                raise ValueError("Invalid thread metadata.")
            if not isinstance(obj.contours, list) or len(obj.contours) > 256:
                raise ValueError("Compound shapes allow at most 256 contours.")
            vertices = 0
            for ring in obj.contours:
                if not isinstance(ring, list) or len(ring) < 3:
                    raise ValueError("Each contour needs at least three points.")
                vertices += len(ring)
                if vertices > 20_000:
                    raise ValueError("Compound shape exceeds 20,000 points.")
                for point in ring:
                    if not isinstance(point, (list, tuple)) or len(point) != 2:
                        raise ValueError("Invalid contour point.")
                    for value in point:
                        number(value, -.500000001, .500000001)
            if (obj.kind == "compound") != bool(obj.contours):
                raise ValueError("Compound objects require contours; other objects cannot contain them.")
            if not isinstance(obj.lettering, dict):
                raise ValueError("Invalid lettering properties.")
            if obj.lettering:
                if obj.kind != "compound" or not {"text", "family", "height", "spacing"} <= set(obj.lettering) or set(obj.lettering) - {"text", "family", "height", "spacing", "layout", "curve", "layout_height", "baseline", "columns"}:
                    raise ValueError("Unsupported lettering properties.")
                if not isinstance(obj.lettering["text"], str) or not 1 <= len(obj.lettering["text"]) <= 80 or not isinstance(obj.lettering["family"], str) or len(obj.lettering["family"]) > 200:
                    raise ValueError("Invalid lettering text or font.")
                number(obj.lettering["height"], 1, 100)
                number(obj.lettering["spacing"], 50, 200)
                if obj.lettering.get("layout", "straight") not in ("straight", "curved", "monogram", "path"):
                    raise ValueError("Unsupported lettering layout.")
                if obj.lettering.get('layout')=='path':
                    baseline=obj.lettering.get('baseline')
                    if not isinstance(baseline,list) or not 2<=len(baseline)<=2000:raise ValueError('Path lettering requires a stored baseline.')
                    for point in baseline:
                        if not isinstance(point,list) or len(point)!=2:raise ValueError('Invalid lettering baseline point.')
                        for value in point:number(value,-10000,10000)
                    if any(a==b for a,b in zip(baseline,baseline[1:])):raise ValueError('Lettering baseline has a zero-length segment.')
                elif 'baseline' in obj.lettering:raise ValueError('Only path lettering can store a baseline.')
                number(obj.lettering.get("curve", 60), -180, 180)
                if "columns" in obj.lettering:
                    validate_columns(obj.lettering["columns"], number)
                    if obj.stitch_type != "satin":
                        raise ValueError("Only satin lettering stores planned columns.")
                number(obj.lettering.get("layout_height", obj.lettering["height"]), .1, 500)
            for key, low, high in [("x", -1000, 1000), ("y", -1000, 1000), ("width", .1, 500), ("height", .1, 500), ("rotation", -360, 360), ("angle", -360, 360), ("spacing", .2, 5), ("stitch_length", .5, 6)]:
                number(getattr(obj, key), low, high)
            if type(obj.visible) is not bool or type(obj.underlay) is not bool or type(obj.color_break) is not bool:
                raise ValueError("Invalid visibility or underlay setting.")
            for flag in (obj.tie_in, obj.tie_off, obj.trim_after, obj.connect_fill, obj.route_fill, obj.flip_x, obj.flip_y, obj.stop_after, obj.density_gradient, obj.gradient_reverse, obj.pattern_flip_x, obj.pattern_flip_y):
                if type(flag) is not bool:
                    raise ValueError("Invalid tie or trim setting.")
            number(obj.satin_max, .5, 12)
            number(obj.pull_compensation, 0, 2)
            number(obj.underlay_inset, 0, 3)
            number(obj.underlay_spacing, .5, 10)
            number(obj.minimum_stitch, 0, 1)
            number(obj.jump_trim, 0, 50)
            number(obj.gradient_end_spacing, .2, 5)
            for value in (obj.motif_width,obj.motif_height,obj.motif_spacing,obj.motif_row_spacing):
                number(value,.5,30)
            if not isinstance(obj.motif_pattern,str) or obj.motif_pattern not in {"diamond","box","cross","custom"}:
                raise ValueError("Unsupported motif pattern.")
            if type(obj.motif_reflected) is not bool or not isinstance(obj.custom_motif_name,str) or len(obj.custom_motif_name)>200 or not isinstance(obj.custom_motif_paths,list):
                raise ValueError("Invalid custom motif properties.")
            if obj.custom_motif_paths or obj.motif_pattern=='custom':
                from .motifs import validate_custom
                validate_custom(obj.custom_motif_paths)
            if not isinstance(obj.underlay_style,str) or obj.underlay_style not in {"auto", "edge", "sparse", "edge_sparse", "zigzag", "center_zigzag"}:
                raise ValueError("Unsupported underlay style.")
            if not isinstance(obj.points, list) or len(obj.points) > 2000:
                raise ValueError("Too many path points.")
            for point in obj.points:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise ValueError("Invalid path point.")
                for v in point:
                    number(v, -.5, .5)
            if obj.kind in {"polygon", "path"} and len(obj.points) < (2 if obj.kind == "path" else 3):
                raise ValueError("Not enough path points.")
            if not isinstance(obj.handles, list) or (obj.handles and (obj.kind not in {"path", "polygon"} or len(obj.handles) != len(obj.points))):
                raise ValueError("Bezier handles must match path or polygon anchors.")
            for pair in obj.handles:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError("Each Bezier anchor needs incoming and outgoing handles.")
                for point in pair:
                    if not isinstance(point, (list, tuple)) or len(point) != 2:
                        raise ValueError("Invalid Bezier handle coordinate.")
                    for v in point:
                        number(v, -.500000001, .500000001)
            if obj.kind == "path" and obj.stitch_type not in {"running", "triple", "motif"}:
                raise ValueError("Open paths must use running or motif stitches.")
            satin_lettering = obj.kind == "compound" and "columns" in obj.lettering
            if (obj.kind == "satin" or satin_lettering) != (obj.stitch_type == "satin"):
                raise ValueError("Satin stitches require paired rails.")
            if obj.kind == "satin" and (len(obj.points) < 4 or len(obj.points) % 2):
                raise ValueError("Satin requires at least two complete left/right rail pairs.")
            if (obj.kind == "stitches") != (obj.stitch_type == "manual"):
                raise ValueError("Imported stitch objects must use manual stitches.")
            if not isinstance(obj.stitch_data, list):
                raise ValueError("Invalid stitch data.")
            command_count += len(obj.stitch_data)
            if command_count > 250_000:
                raise ValueError("Project exceeds the 250,000-command limit.")
            if obj.kind != "stitches" and obj.stitch_data:
                raise ValueError("Only imported objects may contain stitch data.")
            for stitch in obj.stitch_data:
                if not isinstance(stitch, (list, tuple)) or len(stitch) != 3:
                    raise ValueError("Invalid stitch record.")
                number(stitch[0], -.500000001, .500000001)
                number(stitch[1], -.500000001, .500000001)
                if not isinstance(stitch[2], str) or stitch[2] not in {"stitch", "jump", "trim", "stop"}:
                    raise ValueError("Unsupported stitch command.")
            project.objects.append(obj)
        return project

    def save(self, path):
        # Replace atomically, preserving the previous project if writing fails.
        import os
        import tempfile
        path = Path(path)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(self.dumps())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def demo_project():
    p = Project("A little wildflower", 100, 100)
    p.objects.append(DesignObject("Stem", "path", 0, 15, 10, 48, color=PALETTE[0], stitch_type="running", points=[[-.5, .5], [0, .1], [.1, -.2], [.5, -.5]]))
    p.objects.extend([
        DesignObject("Left leaf", "leaf", -10, 16, 15, 29, -48, PALETTE[0]),
        DesignObject("Right leaf", "leaf", 9, 7, 13, 25, 48, PALETTE[1]),
    ])
    for i in range(6):
        a = i * math.tau / 6
        p.objects.append(DesignObject(f"Petal {i + 1}", "ellipse", math.sin(a) * 12, -18 + math.cos(a) * 12, 13, 23, -i * 60, PALETTE[2], angle=i * 30))
    p.objects.append(DesignObject("Golden center", "ellipse", 0, -18, 13, 13, color=PALETTE[3], angle=0))
    return p


def satin_sample():
    return Project("Satin and running sampler", objects=[
        DesignObject("Variable-width satin", "satin", -24, 0, 10, 45, color=PALETTE[4],
                     stitch_type="satin", points=[[-.25, -.5], [.25, -.5], [-.5, 0], [.5, 0], [-.25, .5], [.25, .5]],
                     tie_in=True, tie_off=True, trim_after=True, satin_max=6),
        DesignObject("Connected tatami", "ellipse", 12, -14, 26, 26, color=PALETTE[0],
                     underlay=False, connect_fill=True, tie_in=True, tie_off=True, trim_after=True),
        DesignObject("Triple running path", "path", 12, 20, 28, 12, color=PALETTE[2],
                     stitch_type="triple", points=[[-.5, -.5], [-.25, .5], [.25, -.5], [.5, .5]],
                     tie_in=True, tie_off=True, trim_after=True),
    ])
