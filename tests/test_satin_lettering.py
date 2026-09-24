import math
import random
import pytest
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.lettering import make_lettering,LetteringDialog
from morale.satin_lettering import components,cut_holes,normalize,_area,plan_columns


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def square(size,x=0,y=0):
    h=size/2;return [(x-h,y-h),(x+h,y-h),(x+h,y+h),(x-h,y+h)]


def test_components_group_holes_and_islands_left_to_right():
    rings=[square(10,20),square(4,20),square(20),square(10),square(4)]
    groups=components(rings)
    # Two outlines on the left (outer square, and the island in its hole) plus one on the right.
    assert [len(g) for g in groups]==[2,1,2]
    assert groups[2][0]==rings[0] and groups[2][1]==rings[1]


def test_cutting_a_hole_gives_two_hole_free_pieces_with_the_same_area():
    outer,hole=square(12),square(6)
    pieces=cut_holes([outer,hole])
    assert pieces and len(pieces)==2 and all(_area(p)>0 for p in pieces)
    assert sum(_area(p) for p in pieces)==pytest.approx(144-36)


def test_two_holes_are_opened_one_after_another():
    outer=[(-12,-6),(12,-6),(12,6),(-12,6)]
    pieces=cut_holes([outer,square(4,-6),square(4,6)])
    assert pieces and len(pieces)>=3
    assert sum(_area(p) for p in pieces)==pytest.approx(24*12-2*16)


def test_normalize_inverts_transform():
    rng=random.Random(3)
    for _ in range(20):
        obj=DesignObject(x=rng.uniform(-40,40),y=rng.uniform(-40,40),width=rng.uniform(2,60),height=rng.uniform(2,60),
                         rotation=rng.uniform(-180,180),flip_x=rng.random()<.5,flip_y=rng.random()<.5)
        points=[(rng.uniform(-.5,.5),rng.uniform(-.5,.5)) for _ in range(5)]
        back=normalize(obj,obj.transform(points))
        assert all(math.dist(a,b)<1e-9 for a,b in zip(points,back))


def test_satin_lettering_plans_valid_columns_that_stay_inside_the_letters():
    obj=make_lettering('Mix',QFont().family(),20,stitch_type='satin')
    columns=obj.lettering['columns']
    assert obj.stitch_type=='satin' and obj.underlay and any('rails' in piece for piece in columns)
    project=Project(objects=[obj]);restored=Project.loads(project.dumps())
    assert restored.objects[0].lettering['columns']==columns
    stitches=[s for b in generate(restored) for s in b.stitches if s.command=='stitch']
    xs=[x for ring in obj.rings() for x,_ in ring];ys=[y for ring in obj.rings() for _,y in ring]
    assert stitches and all(min(xs)-.5<=s.x<=max(xs)+.5 and min(ys)-.5<=s.y<=max(ys)+.5 for s in stitches)


def test_most_strokes_of_a_sans_alphabet_become_satin():
    # Font lookup needs the application, so the check cannot be a skip marker.
    if 'DejaVu Sans' not in QFontDatabase.families():pytest.skip('Needs DejaVu Sans for stable glyph shapes')
    obj=make_lettering('abcdefghijklmnopqrstuvwxyz',"DejaVu Sans",15,stitch_type='satin')
    kinds=[next(iter(piece)) for piece in obj.lettering['columns']]
    assert kinds.count('rails')>=0.8*len(kinds)
    # Bowl letters with holes are opened rather than left as fill.
    b=make_lettering('b',"DejaVu Sans",15,stitch_type='satin')
    assert all('rails' in piece for piece in b.lettering['columns'])


def test_editing_satin_lettering_replans_and_moving_keeps_columns():
    obj=make_lettering('Hi',QFont().family(),15,stitch_type='satin')
    edited=make_lettering('Hit',obj.lettering['family'],15,previous=obj)
    assert edited.stitch_type=='satin' and len(edited.lettering['columns'])>len(obj.lettering['columns'])
    # Columns live in the object's frame, so moving it moves every stitch.
    moved=Project.loads(Project(objects=[edited]).dumps()).objects[0];moved.x+=30;moved.y-=12
    before=[s for b in generate(Project(objects=[edited])) for s in b.stitches]
    after=[s for b in generate(Project(objects=[moved])) for s in b.stitches]
    assert len(before)==len(after) and all(b.x-a.x==pytest.approx(30) and b.y-a.y==pytest.approx(-12) for a,b in zip(before,after))


def test_fill_lettering_drops_columns_and_invalid_columns_are_rejected():
    obj=make_lettering('Hi',QFont().family(),15,stitch_type='satin')
    fill=make_lettering('Hi',obj.lettering['family'],15,previous=obj,stitch_type='fill')
    assert fill.stitch_type=='fill' and 'columns' not in fill.lettering
    bad=make_lettering('Hi',QFont().family(),15,stitch_type='satin');bad.lettering['columns']=[{'rails':[[0,0],[1,1],[2,2]]}]
    with pytest.raises(ValueError):Project.loads(Project(objects=[bad]).dumps())
    stale=make_lettering('Hi',QFont().family(),15,stitch_type='satin');stale.stitch_type='fill'
    with pytest.raises(ValueError):Project.loads(Project(objects=[stale]).dumps())
    with pytest.raises(ValueError):make_lettering('Hi',QFont().family(),15,stitch_type='contour')


def test_uneven_scaling_turns_satin_lettering_into_fill_outlines():
    from morale.arrange import transform_selection
    obj=make_lettering('Hi',QFont().family(),15,stitch_type='satin')
    [stretched]=transform_selection([obj],1.5,scale_y=1.)
    assert stretched.stitch_type=='fill' and stretched.lettering=={}
    Project.loads(Project(objects=[stretched]).dumps());generate(Project(objects=[stretched]))
    # Uniform scaling keeps the planned columns.
    [scaled]=transform_selection([obj],1.5)
    assert scaled.stitch_type=='satin' and scaled.lettering['columns']==obj.lettering['columns']


def test_dialog_defaults_to_satin_and_properties_switch_with_undo(monkeypatch):
    from morale.app import MainWindow
    dialog=LetteringDialog()
    assert dialog.stitches.currentData()=='satin';dialog.close()
    window=MainWindow()
    try:
        window.apply_lettering(make_lettering('Hi',QFont().family(),15,stitch_type='fill'))
        obj=window.selected_object();before=window.project.dumps()
        window.update_property('stitch_type','satin')
        assert window.selected_object().stitch_type=='satin' and window.selected_object().lettering['columns']
        window.update_property('stitch_type','fill')
        assert window.selected_object().stitch_type=='fill' and 'columns' not in window.selected_object().lettering
        window.undo();window.undo()
        assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('extension',['pes','exp','dst'])
def test_satin_lettering_exports(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project=Project(objects=[make_lettering('Ok',QFont().family(),15,stitch_type='satin')])
    path=tmp_path/f'text.{extension}';export_machine(project,path)
    assert [s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
