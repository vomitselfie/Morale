import json
import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from morale.model import DesignObject,Project
from morale.auto_digitize import is_closed_band,choose_stitches


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def square(left,top,right,bottom):return [[left,top],[right,top],[right,bottom],[left,bottom]]


@pytest.mark.parametrize('rings,expected',[
    ([square(-.5,-.5,.5,.5),square(-.2,-.2,.2,.2)],True),
    ([square(-.2,-.2,.2,.2),list(reversed(square(-.5,-.5,.5,.5)))],True),
    ([square(-.5,-.5,-.1,.5),square(.1,-.5,.5,.5)],False),
    ([square(-.5,-.5,.2,.2),square(-.2,-.2,.5,.5)],False),
    ([square(-.5,-.5,.5,.5),square(-.5,-.2,.2,.2)],False),
    ([square(-.5,-.5,.5,.5),square(-.5,-.5,.5,.5)],False)])
def test_band_requires_strictly_nested_contours(rings,expected):
    obj=DesignObject(kind='compound',width=20,height=20,contours=rings)
    assert is_closed_band(obj)==expected


def test_separate_islands_keep_fill_without_band_metadata():
    obj=DesignObject(kind='compound',width=20,height=20,contours=[square(-.5,-.5,-.1,.5),square(.1,-.5,.5,.5)])
    result,decisions=choose_stitches(Project(objects=[obj]))
    assert result.objects==[obj] and not decisions[0]['closed_band']


@pytest.mark.parametrize('nested,mode,has_control,enabled',[(False,'auto',False,False),(True,'fill',True,False),(True,'auto',True,True)])
def test_native_seam_control_matches_actual_planning(tmp_path,nested,mode,has_control,enabled):
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    d='M2 2H18V18H2Z M6 6H14V14H6Z' if nested else 'M2 2H8V18H2Z M12 2H18V18H12Z'
    source=tmp_path/'contours.svg';source.write_text(f'<svg width="20" height="20"><path fill="red" fill-rule="evenodd" d="{d}"/></svg>')
    output=tmp_path/'out';output.mkdir()
    assert worker_main([str(source),str(output),json.dumps({'width':20,'stitch_mode':mode})])==0
    info=json.loads((output/'preview.json').read_text());dialog=TraceDialog(str(source))
    try:
        dialog.ready(str(source),info,QImage(str(output/'preview.png')))
        assert dialog.project is not None and dialog.decisions.rowCount()==1
        control=dialog.decisions.cellWidget(0,4)
        assert (control is not None)==has_control
        if control is not None:assert control.isEnabled()==enabled
    finally:dialog.close()
