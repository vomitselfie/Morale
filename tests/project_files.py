"""Older project file layouts, for tests of loading and migration."""
from dataclasses import asdict


def flat_document(project, version=2):
    """``project`` as a version 1–2 document: object properties not grouped."""
    return {"format": "morale", "version": version, **asdict(project)}
