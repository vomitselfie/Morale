import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from morale.routing import route_object,routing_rings
from morale.model import DesignObject,Project
from morale.engine import generate
from morale.bezier import enable_handles,edit_controls


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def polygon(stitch_type='running'):
    return DesignObject(kind='polygon',stitch_type=stitch_type,points=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],rotation=31,flip_x=True,underlay=False)


@pytest.mark.parametrize('stitch_type',['running','triple'])
@pytest.mark.parametrize('reverse',[False,True])
def test_closed_anchor_route_preserves_shape_and_generated_entry(stitch_type,reverse):
    source=polygon(stitch_type)
    result=route_object(source,[(0,2,reverse)])
    expected=[source.outline()[(2+(-i if reverse else i))%4] for i in range(4)]
    for p,q in zip(result.outline(),expected): assert p==pytest.approx(q)
    stitches=generate(Project(objects=[result]))[0].stitches
    assert (stitches[0].x,stitches[0].y)==pytest.approx(source.outline()[2])
    assert (stitches[-1].x,stitches[-1].y)==pytest.approx(source.outline()[2])
    assert Project.loads(Project(objects=[result]).dumps()).objects[0]==result


def test_bezier_reverse_swaps_handles_and_keeps_same_cubic_geometry():
    source=enable_handles(polygon())
    controls=source.control_points(); controls[2]=(7,9)
    source=edit_controls(source,controls)
    result=route_object(source,[(0,2,True)])
    controls=source.control_points()
    expected=[p for i in (2,1,0,3) for p in (controls[i*3+2],controls[i*3+1],controls[i*3])]
    for a,b in zip(result.control_points(),expected): assert a==pytest.approx(b)
    # Reversing twice from the same start gives the original representation.
    assert route_object(route_object(source,[(0,0,True)]),[(0,0,True)])==source


def test_open_curve_reversal_exchanges_endpoints():
    source=enable_handles(DesignObject(kind='path',stitch_type='running',points=[[-.5,-.5],[0,.4],[.5,.5]]))
    result=route_object(source,[(0,0,True)])
    assert result.outline()[0]==pytest.approx(source.outline()[-1])
    assert result.outline()[-1]==pytest.approx(source.outline()[0])
    with pytest.raises(ValueError): route_object(source,[(0,1,True)])


def test_satin_reverses_stations_and_underlay_entry():
    source=DesignObject(kind='satin',stitch_type='satin',points=[[-.5,-.5],[.5,-.5],[-.3,0],[.4,0],[-.2,.5],[.2,.5]],underlay=True)
    result=route_object(source,[(0,0,True)])
    assert result.points==source.points[4:6]+source.points[2:4]+source.points[0:2]
    first=generate(Project(objects=[result]))[0].stitches[0]
    pair=source.transform(source.points[-2:])
    assert (first.x,first.y)==pytest.approx(tuple((a+b)/2 for a,b in zip(*pair)))
    assert route_object(result,[(0,0,True)])==source


def test_compound_contour_order_and_starts_preserve_holes():
    rings=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.1,-.1],[.1,-.1],[.1,.1],[-.1,.1]]]
    source=DesignObject(kind='compound',stitch_type='running',contours=rings)
    result=route_object(source,[(1,1,True),(0,2,False)])
    assert result.contours[0]==[rings[1][i] for i in (1,0,3,2)]
    assert result.contours[1]==[rings[0][i] for i in (2,3,0,1)]
    jumps=[s for s in generate(Project(objects=[result]))[0].stitches if s.command=='jump']
    assert len(jumps)==2
    for s,ring in zip(jumps,result.rings()): assert (s.x,s.y)==pytest.approx(ring[0])


def test_primitive_noop_and_outline_conversion():
    source=DesignObject(stitch_type='running',rotation=31,flip_y=True)
    assert route_object(source,[(0,0,False)])==source
    result=route_object(source,[(0,5,True)])
    assert result.kind=='polygon' and len(result.points)==96
    for i,p in enumerate(result.outline()): assert p==pytest.approx(source.outline()[(5-i)%96])


@pytest.mark.parametrize('source',[DesignObject(),DesignObject(kind='stitches',stitch_type='manual')])
def test_unsupported_stitch_types_rejected(source):
    with pytest.raises(ValueError): routing_rings(source)


@pytest.mark.parametrize('plan',[[],[(0,4,False)],[(0,-1,False)],[(0,0,'yes')],[(1,0,False)]])
def test_invalid_route_rejected(plan):
    with pytest.raises(ValueError): route_object(polygon(),plan)


def test_native_preview_route_apply_and_undo():
    from morale.app import MainWindow
    from morale.routing_dialog import RoutingDialog
    source=polygon()
    window=MainWindow(); window.replace_project(Project(objects=[source])); window.select(source.id)
    dialog=RoutingDialog(source,window)
    try:
        before=window.project.dumps()
        dialog.start.setCurrentIndex(2); dialog.reverse.setChecked(True)
        assert dialog.candidate is not None and dialog.preview.stitches
        assert dialog.preview.stitches[0].x==pytest.approx(source.outline()[2][0])
        window.apply_routing(dialog.plan)
        assert window.project.objects[0]==dialog.candidate
        window.undo(); assert window.project.dumps()==before
        history=len(window.history)
        window.apply_routing([(0,0,False)])
        assert len(window.history)==history
    finally:
        dialog.close(); window.saved=window.project.dumps(); window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_routed_outline_export_preserves_sewn_end(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project=Project(objects=[route_object(polygon(),[(0,2,True)])])
    path=tmp_path/f'route.{extension}'; export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    expected=project.objects[0].outline()[0]
    assert (sewn[-1].x,sewn[-1].y)==pytest.approx(expected,abs=.15)


@pytest.mark.parametrize('plan',[None,[()],[(False,0,False)],[(0,0,False,1)]])
def test_malformed_route_has_clear_error(plan):
    with pytest.raises(ValueError): route_object(polygon(),plan)


def test_compound_dialog_reorders_independent_settings_and_cancel_keeps_source():
    from morale.routing_dialog import RoutingDialog
    source=DesignObject(kind='compound',stitch_type='running',contours=[polygon().points,[[-.1,-.1],[.1,-.1],[0,.1]]])
    before=Project(objects=[source]).dumps()
    dialog=RoutingDialog(source)
    try:
        dialog.contour.setCurrentIndex(1)
        dialog.start.setCurrentIndex(2)
        dialog.reverse.setChecked(True)
        dialog.move(-1)
        assert dialog.plan==[(1,2,True),(0,0,False)]
        assert dialog.start.currentIndex()==2 and dialog.reverse.isChecked()
        dialog.contour.setCurrentIndex(1)
        assert dialog.start.currentIndex()==0 and not dialog.reverse.isChecked()
        dialog.reject()
        assert Project(objects=[source]).dumps()==before
    finally:
        dialog.close()
