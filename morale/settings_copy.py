"""Copy one object's stitch settings onto others.

Each object keeps its shape, thread, name, lettering and where its fill
starts and ends. The stitch type comes along when the receiving shape can use
it; otherwise only the settings are applied.
"""
from copy import deepcopy

from .model import Project, SETTING_GROUPS

COPIED_GROUPS = ("stitch", "fill", "satin", "underlay", "motif", "ripple", "decorative", "finishing")
# Positions on one particular outline.
NOT_COPIED = {"fill_start", "fill_end"}


def copy_settings(obj):
    return {key: deepcopy(getattr(obj, key)) for group in COPIED_GROUPS
            for key in SETTING_GROUPS[group] if key not in NOT_COPIED}


def _valid(obj):
    try:
        Project.loads(Project(objects=[obj]).dumps())
    except ValueError:
        return False
    return True


def paste_settings(project, ids, settings):
    """``project`` with ``settings`` applied to the objects in ``ids``.

    Returns (project, changed objects, objects that kept their stitch type).
    """
    result = deepcopy(project)
    changed, kept_type = 0, 0
    for index, target in enumerate(result.objects):
        if target.id not in ids:
            continue
        candidate = deepcopy(target)
        for key, value in settings.items():
            setattr(candidate, key, deepcopy(value))
        if not _valid(candidate):
            candidate.stitch_type = target.stitch_type
            kept_type += candidate.stitch_type != settings["stitch_type"]
            if not _valid(candidate):
                continue
        if candidate != target:
            result.objects[index] = candidate
            changed += 1
    return result, changed, kept_type
