"""Portable clipboard payloads retain editable objects, never executable data."""
import uuid
from .model import Project

MIME_TYPE = "application/vnd.morale.objects+json"
MAX_BYTES = 20_000_000


def encode_objects(objects):
    payload = Project(name="Clipboard objects", objects=objects).dumps().encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise ValueError("The selected objects exceed the 20 MB clipboard limit.")
    return payload


def decode_objects(payload):
    if len(payload) > MAX_BYTES:
        raise ValueError("The clipboard exceeds the 20 MB object limit.")
    try:
        project = Project.loads(bytes(payload).decode("utf-8"))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ValueError("The clipboard does not contain valid Morale objects.") from exc
    if project.reference or not project.objects:
        raise ValueError("The clipboard must contain design objects without reference images.")
    groups = {}
    for obj in project.objects:
        obj.id = uuid.uuid4().hex
        if obj.group_id:
            obj.group_id = groups.setdefault(obj.group_id, uuid.uuid4().hex)
    return project.objects
