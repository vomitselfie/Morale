"""Editable sewing notes stored with the native project."""
from PySide6.QtWidgets import QInputDialog


def edit_notes(window):
    text,accepted=QInputDialog.getMultiLineText(window,'Design notes',
        'Fabric, stabilizer, thread and sewing adjustments (up to 10,000 characters):',window.project.notes)
    if not accepted or text==window.project.notes:return
    if len(text)>10000:
        window.error('Design notes must contain at most 10,000 characters.');return
    window.commit(lambda:setattr(window.project,'notes',text))
