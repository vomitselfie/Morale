import pytest
from PySide6.QtWidgets import QApplication
from morale.svg_render import render_svg_artwork


@pytest.fixture(scope='module',autouse=True)
def application():
    return QApplication.instance() or QApplication([])


GRADIENT='<linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient>'


def test_gradient_clip_preserves_original_color_coordinates():
    image,_=render_svg_artwork(f'''<svg width="100" height="100"><defs>{GRADIENT}
      <clipPath id="c"><rect width="20" height="20"/></clipPath></defs>
      <rect width="80" height="80" fill="url(#g)" clip-path="url(#c)"/></svg>''',resolution=100)
    assert image.pixelColor(10,10).getRgb()==(222,0,33,255)
    assert image.pixelColor(50,50).alpha()==0


def test_gradient_inherited_by_transformed_group_and_solid_marker_collision():
    image,_=render_svg_artwork(f'''<svg width="100" height="100"><defs>{GRADIENT}</defs>
      <g fill="url(#g)" transform="translate(10,10)"><rect width="80" height="30"/></g>
      <rect y="60" width="100" height="30" fill="#000001"/></svg>''',resolution=100)
    assert image.pixelColor(20,20).red()>215
    assert image.pixelColor(80,20).blue()>215
    assert image.pixelColor(20,70).getRgb()==(0,0,1,255)


def test_gradient_stroke_paint_order_and_center_hole():
    image,_=render_svg_artwork(f'''<svg width="100" height="100"><defs>{GRADIENT}</defs>
      <rect x="10" y="10" width="80" height="80" fill="none" stroke="url(#g)" stroke-width="10"/>
      </svg>''',resolution=100)
    assert image.pixelColor(10,50).red()>245
    assert image.pixelColor(90,50).blue()>245
    assert image.pixelColor(50,50).alpha()==0


def test_inherited_radial_gradient_inside_symbol_viewport():
    image,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <radialGradient id="base"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></radialGradient>
      <radialGradient id="g" href="#base"/>
      <symbol id="s" viewBox="0 0 10 10"><rect width="10" height="10" fill="url(#g)"/></symbol>
      </defs><use href="#s" x="10" y="10" width="80" height="80"/></svg>''',resolution=100)
    assert image.pixelColor(50,50).red()>245
    assert image.pixelColor(89,50).blue()>245
    assert image.pixelColor(5,5).alpha()==0


@pytest.mark.parametrize('body',[
    '<rect fill="url(https://example.com/a.svg#g)"/>',
    '<rect fill="url(#missing)"/>',
    '<image href="file:///tmp/image.png"/>',
    '<script/>',
])
def test_unsupported_artwork_fails_before_painting(body):
    with pytest.raises(ValueError):render_svg_artwork('<svg width="100" height="100">'+body+'</svg>')


def test_gradient_render_to_editable_embroidery_regions(tmp_path):
    from morale.svg_render import trace_svg_artwork
    from morale.engine import generate
    from morale.model import Project
    source=tmp_path/'gradient.svg'
    text=f'''<svg width="100" height="100"><defs>{GRADIENT}
      <clipPath id="c"><rect width="40" height="80"/></clipPath></defs>
      <rect width="80" height="80" fill="url(#g)" clip-path="url(#c)"/></svg>'''
    source.write_text(text)
    project,image,stats=trace_svg_artwork(source,width=100,colors=3,resolution=64,ignore_white=False)
    assert source.read_text()==text
    assert project.objects and len(project.objects)>=2
    assert project.name=='gradient'
    assert stats['source_kind']=='rendered_svg'
    assert image.pixelColor(50,30).alpha()==0
    for obj in project.objects:
        for ring in obj.rings():
            assert all(-50.1<=x<=-9 and -50.1<=y<=31 for x,y in ring)
    assert generate(project)==generate(Project.loads(project.dumps()))
    assert generate(project)


def test_gradient_worker_produces_reviewable_preview_and_checks_source(tmp_path):
    import hashlib
    import json
    from morale.raster_trace import worker_main
    from morale.model import Project
    source=tmp_path/'gradient.svg'
    source.write_text(f'<svg width="100" height="100"><defs>{GRADIENT}</defs><rect width="80" height="80" fill="url(#g)"/></svg>')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    output=tmp_path/'preview';output.mkdir()
    settings={'render_svg':True,'width':80,'colors':3,'resolution':64,'ignore_white':False,
              'stitch_mode':'fill','keep_reference':True,'expected_source_digest':digest}
    assert worker_main([str(source),str(output),json.dumps(settings)])==0
    info=json.loads((output/'preview.json').read_text())
    assert info['source_digest']==digest
    assert info['trace_stats']['source_kind']=='rendered_svg'
    assert set(info['aligned_previews'])=={'source','vectors','stitches'}
    project=Project.loads(info['project'])
    assert len(project.objects)>=2 and project.reference
    assert all(obj.stitch_type=='fill' for obj in project.objects)
    source.write_text(source.read_text().replace('width="80"','width="70"'))
    stale=tmp_path/'stale';stale.mkdir()
    assert worker_main([str(source),str(stale),json.dumps(settings)])==1
    assert 'changed before tracing' in json.loads((stale/'preview.error.json').read_text())['error']


def test_native_gradient_conversion_controls_worker_and_undo(tmp_path):
    import time
    from PySide6.QtTest import QTest
    from morale.trace_dialog import TraceDialog
    from morale.app import MainWindow
    source=tmp_path/'gradient.svg'
    source.write_text(f'<svg width="100" height="100"><defs>{GRADIENT}</defs><rect width="80" height="80" fill="url(#g)"/></svg>')
    dialog=TraceDialog(str(source));window=MainWindow()
    try:
        assert not dialog.method.isEnabled() and dialog.colors.isHidden()
        dialog.render_svg.setChecked(True)
        assert dialog.method.isEnabled() and not dialog.colors.isHidden()
        assert dialog.expand_strokes.isHidden()
        dialog.resolution.setCurrentIndex(dialog.resolution.findData(64))
        dialog.colors.setValue(3)
        dialog.generate();deadline=time.monotonic()+15
        while dialog.project is None and time.monotonic()<deadline:QTest.qWait(10)
        assert dialog.project is not None,dialog.status.text()
        assert dialog.runner.options['render_svg'] is True
        before=window.project.dumps()
        window.apply_raster_trace(dialog.project)
        assert window.project.reference
        window.undo();assert window.project.dumps()==before
        dialog.render_svg.setChecked(False)
        assert not dialog.method.isEnabled() and dialog.colors.isHidden()
        assert not dialog.expand_strokes.isHidden()
        assert dialog.project is None
    finally:
        dialog.close();window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
def test_gradient_worker_machine_export_geometry(tmp_path,extension):
    import json
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine,import_machine
    from morale.export_verify import verify_export
    source=tmp_path/'gradient.svg'
    source.write_text(f'''<svg width="100" height="100"><defs>{GRADIENT}
      <clipPath id="c"><rect width="40" height="80"/></clipPath></defs>
      <rect width="80" height="80" fill="url(#g)" clip-path="url(#c)"/></svg>''')
    output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(source),str(output),json.dumps(dict(render_svg=True,width=100,colors=3,
        resolution=64,method='smooth',ignore_white=False,stitch_mode='fill'))])==0
    project=Project.loads(json.loads((output/'preview.json').read_text())['project'])
    blocks=generate(project)
    assert len(project.objects)>=2
    path=tmp_path/f'gradient.{extension}';export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result
    decoded=generate(import_machine(path).project)
    stitches=[s for block in decoded for s in block.stitches if s.command=='stitch']
    assert stitches and all(-50.3<=s.x<=-8 and -50.3<=s.y<=31 for s in stitches)


def test_gradient_current_color_comes_from_definition_ancestors():
    image,_=render_svg_artwork('''<svg width="100" height="100" color="green">
      <defs style="color:red"><linearGradient id="g"><stop stop-color="currentColor"/>
      <stop offset="1" stop-color="blue"/></linearGradient></defs>
      <rect width="100" height="100" fill="url(#g)" color="yellow"/></svg>''',resolution=100)
    assert image.pixelColor(10,50).red()>220
    assert image.pixelColor(10,50).green()==0


def test_template_stops_use_consuming_gradient_color_context():
    image,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <linearGradient id="base" color="red"><stop stop-color="currentColor"/><stop offset="1" stop-color="blue"/></linearGradient>
      <g color="lime"><linearGradient id="g" href="#base"/></g></defs>
      <rect width="100" height="100" fill="url(#g)"/></svg>''',resolution=100)
    assert image.pixelColor(10,50).green()>220
    assert image.pixelColor(10,50).red()==0


@pytest.mark.parametrize('offset',['.5','.4'])
def test_hard_gradient_transition_preserves_first_and_last_coincident_colors(offset):
    image,_=render_svg_artwork(f'''<svg width="100" height="100"><defs>
      <linearGradient id="g"><stop stop-color="red"/><stop offset=".5" stop-color="red"/>
      <stop offset="{offset}" stop-color="lime"/><stop offset=".5" stop-color="blue"/>
      <stop offset="1" stop-color="blue"/></linearGradient></defs>
      <rect width="100" height="100" fill="url(#g)"/></svg>''',resolution=100)
    for x in (0,10,40,48):assert image.pixelColor(x,50).getRgb()==(255,0,0,255)
    for x in (51,60,90,99):assert image.pixelColor(x,50).getRgb()==(0,0,255,255)


def test_hard_gradient_start_uses_last_coincident_stop():
    image,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <linearGradient id="g"><stop stop-color="red"/><stop stop-color="blue"/>
      <stop offset="1" stop-color="blue"/></linearGradient></defs>
      <rect width="100" height="100" fill="url(#g)"/></svg>''',resolution=100)
    assert all(image.pixelColor(x,50).getRgb()==(0,0,255,255) for x in range(100))


def test_transparent_gradient_stop_preserves_rgb_during_interpolation():
    image,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <linearGradient id="g"><stop stop-color="red" stop-opacity="0"/>
      <stop offset="1" stop-color="blue"/></linearGradient></defs>
      <rect width="100" height="100" fill="url(#g)"/></svg>''',resolution=100)
    red,green,blue,alpha=image.pixelColor(50,50).getRgb()
    assert 124<=red<=130 and green==0 and 125<=blue<=132 and 126<=alpha<=132


@pytest.mark.parametrize('attrs',['','r="0"','fr="50%"','fx="200%"'])
def test_single_stop_radial_gradient_is_solid_paint(attrs):
    image,_=render_svg_artwork(f'''<svg width="100" height="100"><defs>
      <radialGradient id="g" {attrs}><stop stop-color="red"/></radialGradient></defs>
      <rect x="10" y="10" width="80" height="80" fill="url(#g)"/></svg>''',resolution=100)
    for point in ((15,15),(50,50),(85,85)):
        assert image.pixelColor(*point).getRgb()==(255,0,0,255)
    assert image.pixelColor(5,5).alpha()==0


@pytest.mark.parametrize('gradient',[False,True])
def test_partial_fill_opacity_blends_over_underlying_artwork(gradient):
    definition='<defs><linearGradient id="g"><stop stop-color="red"/></linearGradient></defs>' if gradient else ''
    fill='url(#g)' if gradient else 'red'
    image,_=render_svg_artwork(f'''<svg width="100" height="100">{definition}
      <rect width="100" height="100" fill="blue"/>
      <rect width="50" height="100" fill="{fill}" fill-opacity="50%"/></svg>''',resolution=100)
    r,g,b,a=image.pixelColor(25,50).getRgb()
    assert 125<=r<=129 and g==0 and 126<=b<=130 and a==255
    assert image.pixelColor(75,50).getRgb()==(0,0,255,255)


def test_gradient_stroke_opacity_combines_with_stop_opacity():
    image,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <linearGradient id="g"><stop stop-color="red" stop-opacity=".5"/></linearGradient></defs>
      <rect x="20" y="20" width="60" height="60" fill="none" stroke="url(#g)" stroke-width="10" stroke-opacity=".5"/>
      </svg>''',resolution=100)
    r,g,b,a=image.pixelColor(20,50).getRgb()
    assert r==255 and g==0 and b==0 and 61<=a<=65
    assert image.pixelColor(50,50).alpha()==0


def test_group_opacity_applies_once_to_overlapping_children():
    image,_=render_svg_artwork('''<svg width="100" height="100"><rect width="100" height="100" fill="blue"/>
      <g opacity=".5"><rect width="60" height="100" fill="red"/>
      <rect x="30" width="60" height="100" fill="red"/></g></svg>''',resolution=100)
    assert image.pixelColor(10,50)==image.pixelColor(40,50)==image.pixelColor(80,50)
    r,g,b,a=image.pixelColor(40,50).getRgb()
    assert 125<=r<=129 and g==0 and 126<=b<=130 and a==255


def test_object_opacity_composites_fill_and_stroke_together():
    image,_=render_svg_artwork('''<svg width="100" height="100">
      <rect x="20" y="20" width="60" height="60" fill="red" stroke="blue" stroke-width="20" opacity=".5"/>
      </svg>''',resolution=100)
    assert image.pixelColor(25,50).alpha()==image.pixelColor(50,50).alpha()
    assert 125<=image.pixelColor(25,50).alpha()<=129
    assert image.pixelColor(25,50).blue()==255


def test_nested_group_opacity_multiplies_after_compositing():
    image,_=render_svg_artwork('''<svg width="100" height="100"><g opacity=".5"><g opacity=".5">
      <rect width="100" height="100" fill="red" opacity="1"/></g></g></svg>''',resolution=100)
    assert 61<=image.pixelColor(50,50).alpha()<=65


@pytest.mark.parametrize('extension',['pes','exp'])
def test_group_compositing_worker_and_machine_exports(tmp_path,extension):
    import json
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    source=tmp_path/'translucent.svg'
    source.write_text('''<svg width="100" height="100"><rect width="100" height="100" fill="blue"/>
      <g opacity=".5"><rect width="60" height="100" fill="red"/>
      <rect x="30" width="60" height="100" fill="red"/></g></svg>''')
    original=source.read_bytes();output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(source),str(output),json.dumps(dict(render_svg=True,width=80,colors=2,
        resolution=64,method='smooth',ignore_white=False,stitch_mode='fill'))])==0
    info=json.loads((output/'preview.json').read_text());project=Project.loads(info['project'])
    assert len(project.objects)==2
    from PySide6.QtGui import QColor
    colors=[QColor(obj.color) for obj in project.objects]
    # Palette reduction averages antialiased edge pixels into the blue region.
    assert any(c.blue()>235 and c.red()<20 for c in colors)
    assert any(120<=c.red()<=135 and 120<=c.blue()<=135 and c.green()<5 for c in colors)
    blocks=generate(project)
    assert blocks==generate(Project.loads(project.dumps()))
    path=tmp_path/f'translucent.{extension}';export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['verified'],result
    assert result['complete_path_comparison']
    assert source.read_bytes()==original


def test_linear_light_gradient_midpoint_and_transparent_alpha():
    image,_=render_svg_artwork('''<svg width="100" height="100"><defs color-interpolation="linearRGB">
      <linearGradient id="g"><stop stop-color="red" stop-opacity="0"/><stop offset="1" stop-color="blue"/></linearGradient></defs>
      <rect width="100" height="100" fill="url(#g)"/></svg>''',resolution=100)
    r,g,b,a=image.pixelColor(50,50).getRgb()
    assert 183<=r<=191 and g==0 and 184<=b<=193 and 126<=a<=132


def test_linear_light_black_white_ramp_matches_transfer_function():
    image,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <linearGradient id="g" color-interpolation="linearRGB"><stop stop-color="black"/><stop offset="1" stop-color="white"/></linearGradient></defs>
      <rect width="100" height="100" fill="url(#g)"/></svg>''',resolution=100)
    for x in range(2,98):
        linear=(x+.5)/100
        expected=round(255*(12.92*linear if linear<=.0031308 else 1.055*linear**(1/2.4)-.055))
        r,g,b,a=image.pixelColor(x,50).getRgb()
        assert abs(r-expected)<=2 and r==g==b and a==255


def test_reused_gradient_resolves_once_but_keeps_per_shape_bounds(monkeypatch):
    import morale.svg_render as renderer
    original=renderer.resolve_gradient;calls=[]
    def resolve(root,ident):
        calls.append(ident);return original(root,ident)
    monkeypatch.setattr(renderer,'resolve_gradient',resolve)
    image,_=renderer.render_svg_artwork(f'''<svg width="100" height="100"><defs>{GRADIENT}</defs>
      <rect width="40" height="40" fill="url(#g)"/>
      <rect x="50" width="20" height="40" fill="url(#g)"/>
      <rect x="80" width="20" height="40" fill="url(#g)"/>
      </svg>''',resolution=100)
    assert calls==['g']
    assert image.pixelColor(2,20).red()>230
    assert image.pixelColor(51,20).red()>230
    assert image.pixelColor(81,20).red()>230
    assert image.pixelColor(38,20).blue()>230
    assert image.pixelColor(68,20).blue()>230
    assert image.pixelColor(98,20).blue()>230
