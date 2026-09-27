"""Morale embroidery studio."""
import os
import sys

__version__ = "0.3.0"

# Qt's headless (offscreen) platform does not look in the Windows font folder, so
# workers and tests would render blank text in PDFs and find no glyphs for
# lettering. Point it there before any Qt application starts.
if sys.platform == "win32" and os.environ.get("QT_QPA_PLATFORM") == "offscreen" and not os.environ.get("QT_QPA_FONTDIR"):
    os.environ["QT_QPA_FONTDIR"] = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
