"""Scrollable native getting-started guidance."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QTextBrowser,QDialogButtonBox

GUIDE='''Start a design
Choose a shape tool and drag inside the hoop. For polygons, paths and paired satin rails, place points and press Enter. Escape cancels the draft. Scroll to zoom; middle-drag to pan.

Draw with the keyboard
Choose a drawing tool from the Tools menu; focus moves to the canvas. Arrows move the cursor 1 mm, Shift+arrows 10 mm and Alt+arrows 0.1 mm. With grid snapping enabled, arrows use the grid step. Home returns to the origin. Space places a point or shape corner, Backspace removes the last point, Enter finishes a path and Escape cancels. Satin points alternate between the two rails; complete each pair before finishing.

Align with guides
Drag from the left ruler to create a vertical guide, or from the top ruler for a horizontal guide. Release inside the canvas to keep it; Escape cancels. View → Layout guides edits exact millimeter positions or removes guides. Enable Snap to layout guides to align drawing points and selection edges or centers. Hiding guides disables their snapping. Guides are saved with your project and never become stitches.

Convert artwork
File offers SVG import and image digitizing. Conversion produces editable objects. Inspect the source, vector and stitch previews; adjust region stitch types, density and angles before adding the result to your design. Solid SVG geometry can be imported directly; rendered SVG conversion handles supported gradients, masks and styles. Save the editable .morale project so you can revise the conversion later.

Find and document designs
Design → Design notes stores fabric, stabilizer and adjustment notes in your project and its sewout worksheet. The library previews saved notes. Search filenames, leave the search blank to list designs, or enter notes: linen to search project notes in subfolders. Note searches skip unreadable and oversized projects; check the result counts and narrow the folder if a search limit is reached.

Add lettering
Edit → Add lettering offers system fonts and bundled purpose-digitized embroidery fonts. Choose the font's supported size range and inspect its stitches. Straight, curved and monogram layouts are available; select a drawn path for Edit → Add lettering along path. Saved stitch geometry remains usable without the original system font.

Refine stitches
Select an object to edit its size, thread, stitch type, spacing, underlay and finishing. Fabric settings provides editable experimental starting points. Circular ripple fill offers an adjustable center. Edit path / satin points changes geometry. Editing individual stitches converts the object to manual stitches; Undo restores the editable geometry.

Review and export
Use Design → Check design, then inspect sewing order and simulation. Save your .morale project and export the machine format your model accepts. Export checks compare reopened files with the generated design; they do not establish physical stitch quality. View offers display units, custom fields, rulers and snapping.

Test on fabric
File → Export standard sewout pack creates machine files, placement and evaluation PDFs, and blank machine/material records. It runs in the background and can be cancelled. Record your exact machine model, hoop, thread, fabric and stabilizer, then compare the sewn sample with its targets. For an edited design, export its sewout worksheet and machine file. Keep physical results with the test pack.
'''


class GettingStartedDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Getting started with Morale');self.resize(660,560)
        layout=QVBoxLayout(self)
        self.guide=QTextBrowser();self.guide.setAccessibleName('Getting started guide')
        self.guide.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.guide.setPlainText(GUIDE);layout.addWidget(self.guide)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject);layout.addWidget(buttons)
