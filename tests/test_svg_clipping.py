import pytest
from PySide6.QtWidgets import QApplication
from morale.svg_import import import_svg_text
from morale.vector_artwork import vector_artwork

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def artwork(body,clip='<rect width="20" height="20"/>',units='userSpaceOnUse'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><defs><clipPath id="c" clipPathUnits="{units}">{clip}</clipPath></defs>{body}</svg>'

def bounds(obj):
    points=[p for ring in obj.rings() for p in ring]
    return [min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]

def test_transformed_group_clip_preserves_visible_geometry(tmp_path):
    text=artwork('<g transform="translate(10,5)" clip-path="url(#c)"><rect width="40" height="40" fill="red"/></g>')
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([(10-50)*25.4/96,(5-50)*25.4/96,(30-50)*25.4/96,(25-50)*25.4/96])
    source=tmp_path/'clipped.svg';source.write_text(text)
    project,image,info=vector_artwork(source,width=100)
    assert project.objects[0].width==pytest.approx(20)
    assert any('clipping' in note for note in info['notes'])
    assert image.pixelColor(5,5).alpha()==0

@pytest.mark.parametrize('reference',['clip-path="url(#c)"','style="clip-path:url(#c)"'])
def test_clip_on_shape_and_evenodd_hole(reference):
    text=artwork(f'<rect width="60" height="60" {reference}/>',
                 '<path clip-rule="evenodd" d="M0 0H40V40H0Z M10 10H30V30H10Z"/>')
    obj=import_svg_text(text).objects[0]
    assert obj.width==pytest.approx(40*25.4/96)
    assert len(obj.contours)==2


def test_multiple_clip_children_are_unioned_not_xored():
    text=artwork('<rect width="60" height="60" clip-path="url(#c)"/>',
                 '<rect width="20" height="20"/><rect x="10" width="20" height="20"/>')
    obj=import_svg_text(text).objects[0]
    assert obj.width==pytest.approx(30*25.4/96)
    assert len(obj.contours)==1

@pytest.mark.parametrize('body,clip,units,message',[
 ('<rect width="40" height="40" clip-path="url(#missing)"/>','<rect width="20" height="20"/>','userSpaceOnUse','existing local'),
])
def test_unimplemented_clip_semantics_are_explicit(body,clip,units,message):
    with pytest.raises(ValueError,match=message):import_svg_text(artwork(body,clip,units))


def test_nested_group_clips_intersect_in_world_coordinates():
    text=artwork('<g clip-path="url(#c)"><g transform="translate(10,0)" clip-path="url(#c)"><rect width="40" height="40"/></g></g>')
    obj=import_svg_text(text).objects[0]
    assert obj.width==pytest.approx(10*25.4/96)
    assert obj.height==pytest.approx(20*25.4/96)


def test_viewbox_and_clip_transform_preserve_physical_size():
    text=artwork('<rect width="60" height="60" clip-path="url(#c)"/>','<rect transform="translate(5,10)" width="20" height="30"/>')
    text=text.replace('width="100" height="100"','width="100mm" height="100mm" viewBox="0 0 100 100"',1)
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-45,-40,-25,-10])


def test_clip_geometry_ignores_fill_paint_and_opacity():
    text=artwork('<rect width="60" height="60" clip-path="url(#c)"/>','<rect fill="none" opacity="0" width="20" height="20"/>')
    assert import_svg_text(text).objects[0].width==pytest.approx(20*25.4/96)


def test_unclipped_sibling_retains_stroke_transform_and_color():
    text=artwork('<rect width="60" height="60" clip-path="url(#c)"/><path transform="translate(30,5)" d="M0 0L20 0" fill="none" stroke="blue"/>')
    objects=import_svg_text(text,center_artwork=False).objects
    assert len(objects)==2
    assert objects[1].stitch_type=='running' and objects[1].color=='#0000ff'
    assert objects[1].width==pytest.approx(20*25.4/96)


def test_clipped_group_retains_use_instances():
    text='<svg width="100" height="100"><defs><clipPath id="c"><rect width="20" height="20"/></clipPath><rect id="r" width="40" height="40"/></defs><g clip-path="url(#c)"><use href="#r" x="10"/></g><use href="#r" x="50"/></svg>'
    objects=import_svg_text(text,center_artwork=False).objects
    assert len(objects)==2
    assert objects[0].width==pytest.approx(10*25.4/96)
    assert objects[1].width==pytest.approx(40*25.4/96)


@pytest.mark.parametrize('stroke',[False,True])
def test_clipped_artwork_worker_generates_only_visible_sewing(tmp_path,stroke):
    import json
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    source=tmp_path/'clipped.svg'
    shape='<path d="M-10 10H40" fill="none" stroke="red" stroke-width="20"/>' if stroke else '<rect width="40" height="40" fill="red"/>'
    source.write_text(artwork('<g transform="translate(10,5)" clip-path="url(#c)">'+shape+'</g>'))
    destination=tmp_path/'preview';destination.mkdir()
    assert worker_main([str(source),str(destination),json.dumps({'width':100,'stitch_mode':'fill'})])==0
    info=json.loads((destination/'preview.json').read_text())
    project=Project.loads(info['project'])
    assert len(project.objects)==1
    assert project.objects[0].width==pytest.approx(20)
    obj=project.objects[0]
    stitches=[s for b in generate(project) for s in b.stitches if s.command=='stitch']
    assert stitches
    assert all(obj.x-10-.01<=s.x<=obj.x+10+.01 and obj.y-10-.01<=s.y<=obj.y+10+.01 for s in stitches)


@pytest.mark.parametrize('cap',['butt','round','square'])
def test_clipped_stroke_is_visible_border_not_centerline(cap):
    text=artwork(f'<path d="M-10 10H40" fill="none" stroke="blue" stroke-width="6" stroke-linecap="{cap}" clip-path="url(#c)"/>')
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert obj.kind=='compound' and obj.stitch_type=='fill'
    assert obj.color=='#0000ff'
    assert bounds(obj)==pytest.approx([-50*25.4/96,-43*25.4/96,-30*25.4/96,-37*25.4/96])


@pytest.mark.parametrize('order,colors',[('normal',['#ff0000','#0000ff']),('stroke fill',['#0000ff','#ff0000'])])
def test_clipped_fill_and_border_retain_paint_order(order,colors):
    text=artwork(f'<rect x="5" y="5" width="30" height="30" fill="red" stroke="blue" stroke-width="4" paint-order="{order}" clip-path="url(#c)"/>')
    assert [o.color for o in import_svg_text(text).objects]==colors


def test_clipped_dash_expansion_preserves_gaps(tmp_path):
    source=tmp_path/'dash.svg'
    source.write_text(artwork('<path d="M0 10H40" fill="none" stroke="blue" stroke-width="4" stroke-dasharray="5 5" clip-path="url(#c)"/>'))
    project,image,info=vector_artwork(source,width=100,expand_strokes=True)
    assert len(project.objects)==1
    assert len(project.objects[0].contours)==2
    assert project.objects[0].width==pytest.approx(15)


@pytest.mark.parametrize('effect,height',[('none',8),('non-scaling-stroke',4)])
def test_clipped_stroke_transform_and_vector_effect(effect,height):
    text=artwork(f'<g transform="scale(2)" clip-path="url(#c)"><path d="M-10 10H40" fill="none" stroke="blue" stroke-width="4" vector-effect="{effect}"/></g>')
    obj=import_svg_text(text).objects[0]
    assert obj.width==pytest.approx(40*25.4/96)
    assert obj.height==pytest.approx(height*25.4/96)


@pytest.mark.parametrize('width',['.5','50%'])
def test_bounding_box_clip_scales_to_shape(width):
    text=artwork('<rect x="10" y="20" width="60" height="40" clip-path="url(#c)"/>',
                 f'<rect width="{width}" height="1"/>',units='objectBoundingBox')
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-40*25.4/96,-30*25.4/96,-10*25.4/96,10*25.4/96])


def test_group_bounding_box_includes_child_transforms_before_clipping():
    text=artwork('<g transform="translate(10,5) scale(2)" clip-path="url(#c)"><rect width="10" height="10"/><rect transform="translate(20,0)" width="10" height="10"/></g>',
                 '<rect width=".5" height="1"/>',units='objectBoundingBox')
    objects=import_svg_text(text,center_artwork=False).objects
    assert len(objects)==1
    assert bounds(objects[0])==pytest.approx([-40*25.4/96,-45*25.4/96,-20*25.4/96,-25*25.4/96])


def test_zero_height_geometry_ignores_bounding_box_clip():
    text=artwork('<path d="M10 20H70" fill="none" stroke="blue" stroke-width="4" clip-path="url(#c)"/>',
                 '<rect width=".5" height="1"/>',units='objectBoundingBox')
    objects=import_svg_text(text).objects
    assert len(objects)==1 and objects[0].stitch_type=='running'
    assert objects[0].width==pytest.approx(60*25.4/96)


def test_bounding_box_clip_reused_by_different_shapes():
    text=artwork('<rect width="20" height="20" clip-path="url(#c)"/><rect x="40" width="40" height="20" clip-path="url(#c)"/>',
                 '<rect width=".5" height="1"/>',units='objectBoundingBox')
    objects=import_svg_text(text,center_artwork=False).objects
    assert [o.width for o in objects]==pytest.approx([10*25.4/96,20*25.4/96])


def test_rotated_bounding_box_clip_uses_local_axes():
    text=artwork('<rect width="60" height="20" transform="translate(50,10) rotate(90)" clip-path="url(#c)"/>',
                 '<rect width=".5" height="1"/>',units='objectBoundingBox')
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-20*25.4/96,-40*25.4/96,0,-10*25.4/96])


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
def test_clipped_fill_hole_and_border_survive_machine_export(tmp_path,extension):
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    source=tmp_path/'hole-and-border.svg'
    source.write_text(artwork('<g clip-path="url(#c)"><rect x="20" y="20" width="60" height="60" fill="red"/><path d="M20 50H80" fill="none" stroke="blue" stroke-width="8"/></g>',
        '<path clip-rule="evenodd" d="M30 30H70V70H30Z M40 40H60V60H40Z"/>'))
    project,image,info=vector_artwork(source,width=100)
    assert [obj.color for obj in project.objects]==['#ff0000','#0000ff']
    assert len(project.objects[0].contours)==2
    assert len(project.objects[1].contours)==2
    blocks=generate(project)
    assert generate(Project.loads(project.dumps()))==blocks
    for block in blocks:
        previous=None
        for stitch in block.stitches:
            if stitch.command=='stitch':
                assert -20.01<=stitch.x<=20.01 and -20.01<=stitch.y<=20.01
                if previous is not None:
                    # Check the entire sewn segment against the open rectangular
                    # cutout by clipping its parameter interval on both axes.
                    lower,upper=0.,1.
                    for a,b in ((previous.x,stitch.x),(previous.y,stitch.y)):
                        if abs(b-a)<1e-12:
                            if not -9.99<a<9.99:upper=-1
                        else:
                            first,last=sorted(((-9.99-a)/(b-a),(9.99-a)/(b-a)))
                            lower=max(lower,first);upper=min(upper,last)
                    assert lower>=upper
            previous=stitch
    path=tmp_path/f'clipped.{extension}'
    export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result


def test_clipped_border_preview_has_no_false_line_across_hole(tmp_path):
    source=tmp_path/'border.svg'
    source.write_text(artwork('<path d="M20 50H80" fill="none" stroke="blue" stroke-width="8" clip-path="url(#c)"/>',
        '<path clip-rule="evenodd" d="M30 30H70V70H30Z M40 40H60V60H40Z"/>'))
    project,image,info=vector_artwork(source,width=100,resolution=512)
    # Every pixel well inside the cutout must be transparent, including where
    # the clipped border's top and bottom edges used to touch the cutout contour.
    assert all(image.pixelColor(x,y).alpha()==0 for x in range(220,290) for y in range(220,290))
    assert image.pixelColor(175,256).alpha()==255
    assert image.pixelColor(335,256).alpha()==255
    assert len(project.objects[0].contours)==2


@pytest.mark.parametrize('href',['href','xlink:href'])
def test_clip_use_references_shape_with_position_and_transform(href):
    text=f'<svg xmlns:xlink="http://www.w3.org/1999/xlink" width="100" height="100"><defs><rect id="r" width="10" height="10"/><clipPath id="c"><use {href}="#r" x="5" y="10" transform="scale(2)"/></clipPath></defs><rect width="80" height="80" clip-path="url(#c)"/></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-40*25.4/96,-30*25.4/96,-20*25.4/96,-10*25.4/96])


def test_clip_use_ignores_referenced_opacity_without_reviving_painted_shape():
    text='<svg width="100" height="100"><defs><rect id="r" width="20" height="20" fill="blue" opacity="0"/><clipPath id="c"><use href="#r"/></clipPath></defs><rect width="40" height="40" fill="red" clip-path="url(#c)"/><use href="#r" x="60"/></svg>'
    objects=import_svg_text(text).objects
    assert len(objects)==1 and objects[0].width==pytest.approx(20*25.4/96)


def test_clip_use_does_not_ignore_clip_on_referenced_shape():
    text='<svg width="100" height="100"><defs><rect id="r" width="20" height="20" clip-path="url(#c)"/><clipPath id="c"><use href="#r"/></clipPath></defs><rect width="40" height="40" clip-path="url(#c)"/></svg>'
    with pytest.raises(ValueError,match='circular clip'):import_svg_text(text)


@pytest.mark.parametrize('visibility',['display="none"','visibility="hidden"','style="display:none"'])
def test_clip_reference_respects_explicit_hidden_geometry(visibility):
    text=f'<svg width="100" height="100"><defs><rect id="r" width="20" height="20" {visibility}/><clipPath id="c"><use href="#r"/></clipPath></defs><rect width="40" height="40" fill="red" clip-path="url(#c)"/><rect x="60" width="10" height="10" fill="blue"/></svg>'
    objects=import_svg_text(text).objects
    assert len(objects)==1 and objects[0].color=='#0000ff'


def test_zero_opacity_group_cannot_revive_child_when_clips_exist():
    text=artwork('<rect width="40" height="40" fill="red" clip-path="url(#c)"/><g opacity="0"><rect x="50" width="20" height="20" fill="blue" opacity="1"/></g>')
    objects=import_svg_text(text).objects
    assert len(objects)==1 and objects[0].color=='#ff0000'


@pytest.mark.parametrize('assisted',[False,True])
def test_native_clipped_import_preview_undo_redo_and_reopen(tmp_path,assisted):
    import time
    from PySide6.QtTest import QTest
    from morale.app import MainWindow
    from morale.trace_dialog import TraceDialog
    from morale.model import Project,DesignObject
    from morale.engine import generate
    source=tmp_path/'native-clipped.svg'
    source.write_text(artwork('<rect width="60" height="60" fill="red" clip-path="url(#c)"/>',
        '<path clip-rule="evenodd" d="M0 0H40V40H0Z M10 10H30V30H10Z"/>'))
    original=source.read_bytes();window=MainWindow();dialog=None
    try:
        window.replace_project(Project(objects=[DesignObject(x=30,y=30,width=5,height=5)]))
        before=window.project.dumps()
        if assisted:
            dialog=TraceDialog(str(source));dialog.generate();deadline=time.monotonic()+10
            while dialog.project is None and time.monotonic()<deadline:QTest.qWait(10)
            assert dialog.project is not None,dialog.status.text()
            assert any('clipping' in note for note in dialog.quality['artwork_notes'])
            assert len(dialog.project.objects)==1 and len(dialog.project.objects[0].contours)==2
            dialog.accept()
            window.apply_raster_trace(dialog.project)
        else:window.apply_svg_artwork(source)
        assert len(window.project.objects)==2
        assert len(window.project.objects[-1].contours)==2
        after=window.project.dumps();blocks=generate(window.project)
        assert generate(Project.loads(after))==blocks
        window.undo();assert window.project.dumps()==before
        window.redo();assert window.project.dumps()==after
        assert generate(window.project)==blocks
        assert source.read_bytes()==original
    finally:
        if dialog is not None:dialog.close()
        window.saved=window.project.dumps();window.close()


def test_overlapping_normalized_curved_clips_keep_physical_precision():
    import math
    text=artwork('<rect width="100" height="100" clip-path="url(#c)"/>',
        '<circle cx=".4" cy=".5" r=".4"/><circle cx=".6" cy=".5" r=".4"/>',units='objectBoundingBox')
    text=text.replace('width="100" height="100"','width="100mm" height="100mm" viewBox="0 0 100 100"',1)
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert len(obj.contours)==1
    ring=obj.rings()[0]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        x,y=(a[0]+b[0])/2,(a[1]+b[1])/2
        error=abs(min(math.hypot(x+10,y)-40,math.hypot(x-10,y)-40))
        assert error<.02


@pytest.mark.parametrize('location',['definition','shape'])
def test_nested_clip_references_intersect_instead_of_union(location):
    outer='clip-path="url(#half)"' if location=='definition' else ''
    inner='clip-path="url(#half)"' if location=='shape' else ''
    text=f'<svg width="100" height="100"><defs><clipPath id="half"><rect width="10" height="40"/></clipPath><clipPath id="outer" {outer}><rect width="40" height="20" {inner}/></clipPath></defs><rect width="60" height="60" clip-path="url(#outer)"/></svg>'
    obj=import_svg_text(text).objects[0]
    assert (obj.width,obj.height)==pytest.approx((10*25.4/96,20*25.4/96))


def test_nested_clip_on_referenced_shape_is_applied():
    text='<svg width="100" height="100"><defs><clipPath id="half" clipPathUnits="objectBoundingBox"><rect width=".5" height="1"/></clipPath><rect id="r" width="40" height="20" clip-path="url(#half)"/><clipPath id="outer"><use href="#r" x="10"/></clipPath></defs><rect width="60" height="60" clip-path="url(#outer)"/></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-40*25.4/96,-50*25.4/96,-20*25.4/96,-30*25.4/96])


def test_indirect_clip_cycles_fail_cleanly():
    text='<svg width="100" height="100"><defs><clipPath id="a" clip-path="url(#b)"><rect width="20" height="20"/></clipPath><clipPath id="b" clip-path="url(#a)"><rect width="20" height="20"/></clipPath></defs><rect width="40" height="40" clip-path="url(#a)"/></svg>'
    with pytest.raises(ValueError,match='circular clip'):import_svg_text(text)


def test_clip_reference_depth_is_bounded():
    definitions=[]
    for index in range(65):
        reference=f' clip-path="url(#c{index+1})"' if index<64 else ''
        definitions.append(f'<clipPath id="c{index}"{reference}><rect width="20" height="20"/></clipPath>')
    text='<svg width="100" height="100"><defs>'+''.join(definitions)+'</defs><rect width="40" height="40" clip-path="url(#c0)"/></svg>'
    with pytest.raises(ValueError,match='nesting exceeds 64'):import_svg_text(text)


@pytest.mark.parametrize('warm_cache',[False,True])
def test_nested_user_space_curves_keep_precision_inside_normalized_clip(warm_cache):
    import math
    text='<svg width="100mm" height="100mm" viewBox="0 0 100 100"><defs><clipPath id="curves"><circle cx=".4" cy=".5" r=".4"/><circle cx=".6" cy=".5" r=".4"/></clipPath><clipPath id="outer" clipPathUnits="objectBoundingBox"><rect width="1" height="1" clip-path="url(#curves)"/></clipPath></defs><rect width="100" height="100" clip-path="url(#outer)"/></svg>'
    if warm_cache:text=text.replace('</defs>','</defs><rect width="1" height="1" clip-path="url(#curves)"/>')
    obj=import_svg_text(text,center_artwork=False).objects[-1]
    ring=obj.rings()[0]
    assert len(obj.contours)==1
    for a,b in zip(ring,ring[1:]+ring[:1]):
        x,y=(a[0]+b[0])/2,(a[1]+b[1])/2
        assert abs(min(math.hypot(x+10,y)-40,math.hypot(x-10,y)-40))<.02


@pytest.mark.parametrize('viewbox',[False,True])
def test_user_space_clip_percentages_follow_viewport(viewbox):
    text=artwork('<rect width="100" height="100" clip-path="url(#c)"/>',
                 '<rect x="25%" y="10%" width="50%" height="40%"/>')
    if viewbox:text=text.replace('width="100" height="100"','width="200" height="200" viewBox="0 0 100 100"',1)
    obj=import_svg_text(text,center_artwork=False).objects[0]
    factor=2 if viewbox else 1
    assert bounds(obj)==pytest.approx([v*factor*25.4/96 for v in [-25,-40,25,0]])


def test_percentage_circle_radius_uses_normalized_viewport_diagonal():
    import math
    text='<svg width="200" height="100"><defs><clipPath id="c"><circle cx="50%" cy="50%" r="10%"/></clipPath></defs><rect width="200" height="100" clip-path="url(#c)"/></svg>'
    obj=import_svg_text(text).objects[0]
    diameter=math.hypot(200,100)/math.sqrt(2)*.2*25.4/96
    assert obj.width==pytest.approx(diameter,abs=.001)
    assert obj.height==pytest.approx(diameter,abs=.001)


def test_user_space_percentage_clip_with_nested_viewport():
    text=artwork('<svg width="50" height="50"><rect width="40" height="40" clip-path="url(#c)"/></svg>',
                 '<rect width="50%" height="50%"/>')
    obj=import_svg_text(text).objects[0]
    assert (obj.width,obj.height)==pytest.approx((25*25.4/96,25*25.4/96))


@pytest.mark.parametrize('shape',['rectangle','circle','ellipse'])
def test_percentage_clip_worker_matches_absolute_artwork(tmp_path,shape):
    import json,math
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    radius=math.hypot(200,100)/math.sqrt(2)*.1
    pairs={
        'rectangle':('<rect x="25%" y="10%" width="50%" height="40%"/>','<rect x="50" y="10" width="100" height="40"/>'),
        'circle':('<circle cx="50%" cy="50%" r="10%"/>',f'<circle cx="100" cy="50" r="{radius}"/>'),
        'ellipse':('<ellipse cx="50%" cy="50%" rx="20%" ry="30%"/>','<ellipse cx="100" cy="50" rx="40" ry="30"/>'),
    }
    results=[]
    for index,clip in enumerate(pairs[shape]):
        source=tmp_path/f'source{index}.svg'
        source.write_text('<svg width="400" height="200" viewBox="0 0 200 100"><defs><clipPath id="c">'+clip+'</clipPath></defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/></svg>')
        before=source.read_bytes();output=tmp_path/f'worker{index}';output.mkdir()
        assert worker_main([str(source),str(output),json.dumps({'width':80,'stitch_mode':'fill'})])==0
        assert source.read_bytes()==before
        info=json.loads((output/'preview.json').read_text())
        project=Project.loads(info['project'])
        assert len(project.objects)==1
        blocks=generate(project)
        results.append(([(b.color,b.stitches) for b in blocks],info['raster_png'],info['trace_svg']))
    assert results[0]==results[1]



def test_percentage_clip_cache_distinguishes_nested_viewports():
    text='<svg width="200" height="100"><defs><clipPath id="c"><rect width="50%" height="100%"/></clipPath></defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/><svg x="100" width="80" height="40" viewBox="0 0 40 20"><rect width="40" height="20" fill="blue" clip-path="url(#c)"/></svg></svg>'
    objects=import_svg_text(text,center_artwork=False).objects
    assert len(objects)==2
    assert objects[0].width==pytest.approx(100*25.4/96)
    assert objects[1].width==pytest.approx(40*25.4/96)
    assert objects[1].height==pytest.approx(40*25.4/96)
    assert bounds(objects[1])==pytest.approx([0,-50*25.4/96,40*25.4/96,-10*25.4/96])


@pytest.mark.parametrize('viewbox',['',' viewBox="0 0 40 20"'])
def test_clip_on_nested_svg_matches_clip_on_its_content_group(viewbox):
    prefix='<svg width="200" height="100"><defs><clipPath id="c"><rect width="50%" height="100%"/></clipPath></defs>'
    child='<rect width="80" height="40" fill="red"/>'
    direct=prefix+f'<svg x="60" y="10" width="80" height="40"{viewbox} clip-path="url(#c)">'+child+'</svg></svg>'
    grouped=prefix+f'<svg x="60" y="10" width="80" height="40"{viewbox}><g clip-path="url(#c)">'+child+'</g></svg></svg>'
    expected=import_svg_text(grouped,center_artwork=False).objects
    actual=import_svg_text(direct,center_artwork=False).objects
    assert len(actual)==len(expected)==1
    assert bounds(actual[0])==pytest.approx(bounds(expected[0]))
    assert bounds(actual[0])==pytest.approx([-40*25.4/96,-40*25.4/96,0,0])


@pytest.mark.parametrize('overflow',['overflow="hidden"','style="overflow:hidden"','overflow="scroll"'])
def test_explicit_viewport_crop_trims_artwork_to_page(overflow):
    text=f'<svg width="100" height="80" {overflow}><rect x="-20" y="-10" width="140" height="100"/></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-50*25.4/96,-40*25.4/96,50*25.4/96,40*25.4/96])


@pytest.mark.parametrize('viewbox',['',' viewBox="0 0 40 20"'])
def test_nested_viewport_crop_includes_position_and_scaling(viewbox):
    text=f'<svg width="200" height="100"><svg x="60" y="10" width="80" height="40"{viewbox} overflow="hidden"><rect x="-100" y="-100" width="300" height="300"/></svg></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-40*25.4/96,-40*25.4/96,40*25.4/96,0])


def test_slice_viewbox_crops_overflow_but_explicit_visible_preserves_it():
    template='<svg width="100" height="50" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" %s><rect width="100" height="100"/></svg>'
    cropped=import_svg_text(template%'').objects[0]
    visible=import_svg_text(template%'overflow="visible"').objects[0]
    assert cropped.height==pytest.approx(50*25.4/96)
    assert visible.height==pytest.approx(100*25.4/96)


def test_viewport_crop_and_explicit_clip_intersect(tmp_path):
    source=tmp_path/'cropped.svg'
    source.write_text('<svg width="100" height="80" overflow="hidden"><defs><clipPath id="c"><rect x="50" y="20" width="80" height="80"/></clipPath></defs><rect x="-20" y="-20" width="160" height="140" fill="red" clip-path="url(#c)"/></svg>')
    project,image,info=vector_artwork(source,width=100)
    assert len(project.objects)==1
    assert bounds(project.objects[0])==pytest.approx([0,-20,50,40])
    assert image.pixelColor(100,100).alpha()==0
    assert image.pixelColor(400,200).alpha()==255


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
def test_cropped_border_worker_and_machine_export(tmp_path,extension):
    import json
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine,import_machine
    from morale.export_verify import verify_export
    source=tmp_path/'cropped-border.svg'
    source.write_text('<svg width="80" height="40" overflow="hidden"><path d="M-20 20H100" fill="none" stroke="blue" stroke-width="8" stroke-linecap="round"/></svg>')
    output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(source),str(output),json.dumps({'width':80,'stitch_mode':'fill'})])==0
    info=json.loads((output/'preview.json').read_text())
    project=Project.loads(info['project'])
    assert len(project.objects)==1
    assert (project.objects[0].width,project.objects[0].height)==pytest.approx((80,8))
    blocks=generate(project)
    destination=tmp_path/f'cropped-border.{extension}'
    export_machine(project,destination,blocks)
    result=verify_export(blocks,destination)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result
    decoded=generate(import_machine(destination).project)
    stitches=[s for b in decoded for s in b.stitches if s.command=='stitch']
    assert stitches
    assert all(-40.1<=s.x<=40.1 and -4.1<=s.y<=4.1 for s in stitches)


@pytest.mark.parametrize('viewbox',['',' viewBox="0 0 40 20"'])
def test_nested_svg_defaults_to_cropped_viewport(viewbox):
    text=f'<svg width="200" height="100"><svg x="60" y="10" width="80" height="40"{viewbox}><rect x="-100" y="-100" width="300" height="300"/></svg></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-40*25.4/96,-40*25.4/96,40*25.4/96,0])


@pytest.mark.parametrize('overflow',['overflow="visible"','style="overflow:visible"'])
def test_explicit_visible_overrides_nested_svg_default(overflow):
    text=f'<svg width="100" height="100"><svg x="20" y="20" width="40" height="40" {overflow}><rect x="-10" y="-10" width="60" height="60"/></svg></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-40*25.4/96,-40*25.4/96,20*25.4/96,20*25.4/96])


def test_nested_default_position_does_not_inherit_parent_offset():
    text='<svg width="100" height="100"><svg x="20" y="10" width="60" height="60"><svg width="20" height="20"><rect width="40" height="40"/></svg></svg></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert bounds(obj)==pytest.approx([-30*25.4/96,-40*25.4/96,-10*25.4/96,-20*25.4/96])
