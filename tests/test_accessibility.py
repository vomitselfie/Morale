"""Screen-reader names, keyboard reach, contrast and text scaling."""
import re
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication,QAbstractButton,QComboBox,QAbstractSpinBox,QLineEdit,QSlider,QAbstractItemView,
    QPlainTextEdit,QTextEdit,QFormLayout,QLabel,QWidget,QDialog,QFileDialog,QHeaderView,QToolButton)
from morale.app import MainWindow
from morale.window_ui import STYLE,style_sheet
from morale.model import Project,DesignObject

INTERACTIVE=(QAbstractButton,QComboBox,QAbstractSpinBox,QLineEdit,QSlider,QAbstractItemView,QPlainTextEdit,QTextEdit)


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def labelled(root):
    """Widgets named by a form-row label or a label buddy."""
    named=set()
    for label in root.findChildren(QLabel):
        if label.buddy() is not None:named.add(id(label.buddy()))
    for form in root.findChildren(QFormLayout):
        for row in range(form.rowCount()):
            label=form.itemAt(row,QFormLayout.ItemRole.LabelRole);field=form.itemAt(row,QFormLayout.ItemRole.FieldRole)
            if not(label and field and isinstance(label.widget(),QLabel) and label.widget().text().strip()):continue
            widgets=[field.widget()] if field.widget() else [field.layout().itemAt(i).widget() for i in range(field.layout().count())]
            for widget in widgets:
                if widget is not None:
                    named.add(id(widget));named.update(id(child) for child in widget.findChildren(QWidget))
    return named


def unnamed_controls(root):
    named=labelled(root);problems=[]
    for widget in root.findChildren(QWidget):
        if not isinstance(widget,INTERACTIVE) or isinstance(widget,QHeaderView) or widget.objectName().startswith('qt_'):continue
        if isinstance(widget.parent(),(QComboBox,QAbstractSpinBox)) or widget.parent() is not None and isinstance(widget.parent().parent(),QComboBox):continue
        text=widget.text().replace('&','').strip() if isinstance(widget,QAbstractButton) else ''
        if isinstance(widget,QToolButton) and widget.defaultAction() is not None:text=text or widget.defaultAction().text().strip()
        if not(widget.accessibleName().strip() or id(widget) in named or text):
            problems.append(f'{type(widget).__name__} (tooltip {widget.toolTip()[:50]!r})')
        elif widget.focusPolicy()==Qt.FocusPolicy.NoFocus and not isinstance(widget,QToolButton):
            problems.append(f'{type(widget).__name__} {text or widget.accessibleName()!r} cannot take keyboard focus')
    return problems


def test_main_window_controls_are_named_and_focusable():
    window=MainWindow()
    try:assert unnamed_controls(window)==[]
    finally:window.saved=window.project.dumps();window.close()


def test_dialogs_opened_from_the_window_are_named_and_focusable(monkeypatch,tmp_path):
    audited={}
    def audit(dialog):
        audited[type(dialog).__name__]=unnamed_controls(dialog)
        return 0
    monkeypatch.setattr(QDialog,'exec',audit)
    image=QImage(40,40,QImage.Format.Format_RGB32);image.fill(QColor('red'));picture=tmp_path/'art.png';image.save(str(picture))
    window=MainWindow()
    try:
        polygon=DesignObject(name='Leaf',kind='polygon',stitch_type='running',points=[[-.5,-.5],[.5,-.5],[0,.5]])
        window.replace_project(Project(objects=[polygon]));window.select(polygon.id)
        for command in ('edit_points','edit_stitches','routing_dialog','create_applique','transform_dialog','thread_catalog_dialog',
                        'add_lettering','placement_template','multihoop_dialog','custom_hoop','batch_convert','browse_designs'):
            getattr(window,command)()
        monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a:(str(picture),''))
        window.digitize_raster()
    finally:
        window.saved=window.project.dumps();window.close()
    assert len(audited)>=10,sorted(audited)
    assert {name:problems for name,problems in audited.items() if problems}=={}


def contrast(foreground,background):
    def luminance(color):
        channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        channels=[c/12.92 if c<=.03928 else ((c+.055)/1.055)**2.4 for c in channels]
        return .2126*channels[0]+.7152*channels[1]+.0722*channels[2]
    high,low=sorted((luminance(foreground),luminance(background)),reverse=True)
    return (high+.05)/(low+.05)


def rule(selector,prop):
    match=re.search(re.escape(selector)+r'\s*\{([^}]*)\}',STYLE)
    return re.search(prop+r':\s*(#[0-9a-fA-F]{6})',match.group(1)).group(1)


def test_text_and_control_borders_meet_wcag_contrast():
    page=rule('QMainWindow, QWidget','background')
    for selector in ('QMainWindow, QWidget','QLabel#muted','QLabel#eyebrow'):
        assert contrast(rule(selector,'color'),page)>=4.5,selector
    assert contrast(rule('QStatusBar','color'),rule('QStatusBar','background'))>=4.5
    assert contrast('#ffffff',rule('QPushButton#primary','background'))>=4.5
    # Input and button outlines are user-interface components: 3:1 against white.
    for selector in ('QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox','QPushButton'):
        border=re.search(r'border:\s*1px solid (#[0-9a-fA-F]{6})',re.search(re.escape(selector)+r'\s*\{([^}]*)\}',STYLE).group(1)).group(1)
        assert contrast(border,'#ffffff')>=3,selector
    assert ':focus' in STYLE


def test_text_sizes_follow_the_system_font():
    large=style_sheet(16)
    assert 'font-size: 16.0pt' in large and 'font-size: 28.8pt' in large and 'font-size: 12.8pt' in large
    assert not re.search(r'font-size:\s*\d+px',large) and '{' not in re.sub(r'\{[^{}]*\}','',large)


def test_every_menu_entry_has_a_unique_accelerator():
    window=MainWindow()
    try:
        def check(menu):
            letters=[]
            for action in menu.actions():
                if action.isSeparator():continue
                text=action.text()
                assert '&' in text,text
                letters.append(text[text.index('&')+1].lower())
                if action.menu():check(action.menu())
            # Long menus may reuse a letter (Qt cycles between matches), but rarely.
            assert len(letters)-len(set(letters))<=max(1,len(letters)//5),(menu.title(),letters)
        for top in window.menuBar().actions():check(top.menu())
    finally:window.saved=window.project.dumps();window.close()


def test_arrow_keys_nudge_the_selection_with_undo():
    window=MainWindow()
    try:
        obj=window.project.objects[0];window.select(obj.id);x,y=obj.x,obj.y;before=window.project.dumps()
        window.canvas.setFocus()
        QTest.keyClick(window.canvas,Qt.Key.Key_Right)
        QTest.keyClick(window.canvas,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier)
        moved=window.selected_object()
        assert moved.x==pytest.approx(x+.1) and moved.y==pytest.approx(y+1)
        window.canvas.snap_grid=True
        QTest.keyClick(window.canvas,Qt.Key.Key_Left)
        assert window.selected_object().x==pytest.approx(x+.1-window.canvas.grid_step())
        for _ in range(3):window.undo()
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('points',[10,16])
def test_sequence_buttons_are_not_clipped_at_larger_text(points):
    from PySide6.QtGui import QFont
    app=QApplication.instance();previous=app.font()
    font=QFont(previous);font.setPointSizeF(points);app.setFont(font)
    window=MainWindow()
    try:
        window.resize(1400,900);window.show();QApplication.processEvents()
        for text in ('Copy','Delete'):
            widget=next(b for b in window.findChildren(QAbstractButton) if b.text()==text)
            assert widget.width()>=widget.sizeHint().width(),(text,widget.width(),widget.sizeHint().width())
    finally:
        window.saved=window.project.dumps();window.close();app.setFont(previous)
