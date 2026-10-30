import pytest
from PySide6.QtGui import QColor,QImage
from morale.svg_masks import apply_mask


def image(color):
    result=QImage(3,2,QImage.Format.Format_ARGB32);result.fill(QColor(*color));return result


@pytest.mark.parametrize('mode,alpha',[('alpha',128),('luminance',0)])
def test_opaque_black_mask_has_distinct_alpha_and_luminance_meanings(mode,alpha):
    source=image((255,0,0,128));mask=image((0,0,0,255))
    before_source=source.copy();before_mask=mask.copy()
    result=apply_mask(source,mask,mode=mode)
    assert result.pixelColor(1,1).alpha()==alpha
    assert source==before_source and mask==before_mask


def test_white_mask_multiplies_source_and_mask_alpha():
    result=apply_mask(image((255,0,0,128)),image((255,255,255,128)))
    assert result.pixelColor(0,0).getRgb()==(255,0,0,64)


@pytest.mark.parametrize('color,expected',[((255,0,0,255),54),((0,255,0,255),182),((0,0,255,255),18)])
def test_luminance_uses_all_color_channels(color,expected):
    result=apply_mask(image((255,255,255,255)),image(color))
    assert result.pixelColor(0,0).alpha()==expected


def test_linear_light_mask_differs_from_srgb_gray():
    source=image((255,0,0,255));mask=image((128,128,128,255))
    assert apply_mask(source,mask).pixelColor(0,0).alpha()==128
    assert apply_mask(source,mask,interpolation='linearRGB').pixelColor(0,0).alpha()==55


def test_mask_dimensions_must_match():
    with pytest.raises(ValueError,match='dimensions'):
        apply_mask(image((255,0,0,255)),QImage(1,1,QImage.Format.Format_ARGB32))


def test_default_mask_region_extends_original_bounds():
    import xml.etree.ElementTree as ET
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QTransform
    from morale.svg_masks import mask_geometry
    region,content=mask_geometry(ET.fromstring('<mask/>'),QRectF(10,20,40,20),(100,100),QTransform().translate(5,7))
    assert region.boundingRect()==QRectF(11,25,48,24)
    assert content==QTransform().translate(5,7)


def test_mask_content_units_are_independent_of_region_units():
    import xml.etree.ElementTree as ET
    from PySide6.QtCore import QRectF,QPointF
    from PySide6.QtGui import QTransform
    from morale.svg_masks import mask_geometry
    node=ET.fromstring('<mask maskUnits="userSpaceOnUse" maskContentUnits="objectBoundingBox" x="10%" y="20%" width="50%" height="50%"/>')
    region,content=mask_geometry(node,QRectF(10,20,40,20),(200,100),QTransform().translate(5,7))
    assert region.boundingRect()==QRectF(25,27,100,50)
    assert content.map(QPointF(.5,.5))==QPointF(35,37)


@pytest.mark.parametrize('width',['0','0%'])
def test_zero_mask_region_displays_nothing(width):
    import xml.etree.ElementTree as ET
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QTransform
    from morale.svg_masks import mask_geometry
    region,_=mask_geometry(ET.fromstring(f'<mask width="{width}"/>'),QRectF(0,0,10,10),(100,100),QTransform())
    assert region.isEmpty()


def test_mask_children_render_with_bounding_box_percentages_and_region_crop():
    import xml.etree.ElementTree as ET
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QTransform
    from morale.svg_masks import render_mask
    node=ET.fromstring('<mask maskContentUnits="objectBoundingBox" x="0" y="0" width="50%" height="100%"><rect width="100%" height="100%" fill="white"/></mask>')
    mask,mode,interpolation=render_mask(node,QRectF(10,20,80,60),(100,100),QTransform(),(100,100),resolution=100)
    assert mode=='luminance' and interpolation=='sRGB'
    assert mask.pixelColor(20,30).getRgb()==(255,255,255,255)
    assert mask.pixelColor(60,30).alpha()==0
    assert mask.pixelColor(5,5).alpha()==0


def test_gradient_mask_render_and_composite_preserve_alignment():
    import xml.etree.ElementTree as ET
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QTransform
    from morale.svg_masks import render_mask
    gradient=ET.fromstring('<linearGradient id="fade"><stop stop-color="black"/><stop offset="1" stop-color="white"/></linearGradient>')
    node=ET.fromstring('<mask maskUnits="userSpaceOnUse" x="0" y="0" width="100" height="100"><rect width="100" height="100" fill="url(#fade)"/></mask>')
    mask,mode,interpolation=render_mask(node,QRectF(0,0,100,100),(100,100),QTransform(),(100,100),resolution=100,definitions=[gradient])
    source=QImage(100,100,QImage.Format.Format_ARGB32);source.fill(QColor('red'))
    result=apply_mask(source,mask,mode=mode,interpolation=interpolation)
    assert 24<=result.pixelColor(10,50).alpha()<=29
    assert 229<=result.pixelColor(90,50).alpha()<=233
    assert result.pixelColor(50,50).red()==255


def test_document_mask_composites_group_once():
    from morale.svg_render import render_svg_artwork
    result,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <mask id="m" maskContentUnits="objectBoundingBox"><rect width=".5" height="1" fill="white"/></mask></defs>
      <g mask="url(#m)"><rect x="10" y="10" width="80" height="80" fill="red"/>
      <rect x="30" y="30" width="40" height="40" fill="blue"/></g></svg>''',resolution=100)
    assert result.pixelColor(20,20).getRgb()==(255,0,0,255)
    assert result.pixelColor(40,40).getRgb()==(0,0,255,255)
    assert result.pixelColor(60,40).alpha()==0


def test_document_nested_mask_and_opacity():
    from morale.svg_render import render_svg_artwork
    result,_=render_svg_artwork('''<svg width="100" height="100"><defs>
      <mask id="outer" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white" mask="url(#inner)"/></mask>
      <mask id="inner" maskContentUnits="objectBoundingBox"><rect width=".5" height="1" fill="white"/></mask></defs>
      <rect width="100" height="100" fill="red" mask="url(#outer)" opacity=".5"/></svg>''',resolution=100)
    assert 125<=result.pixelColor(20,20).alpha()<=129
    assert result.pixelColor(80,20).alpha()==0


def test_document_circular_mask_rejected():
    from morale.svg_render import render_svg_artwork
    with pytest.raises(ValueError,match='cycle'):
        render_svg_artwork('''<svg width="100" height="100"><defs><mask id="m"><rect width="100" height="100" mask="url(#m)"/></mask></defs><rect width="100" height="100" mask="url(#m)"/></svg>''',resolution=100)


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
def test_mask_worker_exports_preserve_visible_bounds(tmp_path,extension):
    import json
    from PySide6.QtWidgets import QApplication
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine,import_machine
    from morale.export_verify import verify_export
    application=QApplication.instance() or QApplication([])
    source=tmp_path/'masked.svg'
    source.write_text('''<svg width="100" height="100"><defs>
      <mask id="m" maskContentUnits="objectBoundingBox"><rect width=".5" height="1" fill="white"/></mask></defs>
      <rect x="10" y="10" width="80" height="80" fill="red" mask="url(#m)"/></svg>''')
    original=source.read_bytes();output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(source),str(output),json.dumps(dict(render_svg=True,width=100,colors=2,
        resolution=128,method='smooth',ignore_white=False,stitch_mode='fill'))])==0
    project=Project.loads(json.loads((output/'preview.json').read_text())['project'])
    assert len(project.objects)==1
    assert project.objects[0].width==pytest.approx(40,abs=.5)
    blocks=generate(project)
    assert blocks==generate(Project.loads(project.dumps()))
    path=tmp_path/f'masked.{extension}';export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison'] and result['bounds_delta_mm']<=.3
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result
    decoded=generate(import_machine(path).project)
    sewn=[s for block in decoded for s in block.stitches if s.command=='stitch']
    assert sewn and all(-40.5<=s.x<=.5 and -40.5<=s.y<=40.5 for s in sewn)
    assert source.read_bytes()==original


def test_mask_internal_ids_and_nested_definitions_stay_local():
    from morale.svg_render import render_svg_artwork
    result,_=render_svg_artwork('''<svg width="100" height="100"><defs><defs>
      <mask id="m" maskContentUnits="objectBoundingBox"><defs>
        <linearGradient id="g"><stop stop-color="white"/><stop offset="1" stop-color="white"/></linearGradient>
        <rect id="half" width=".5" height="1" fill="url(#g)"/></defs>
        <use href="#half"/></mask></defs></defs>
      <rect width="100" height="100" fill="red" mask="url(#m)"/></svg>''',resolution=100)
    assert result.pixelColor(20,20).getRgb()==(255,0,0,255)
    assert result.pixelColor(80,20).alpha()==0


def test_mask_inherits_definition_fill_not_referencing_shape_fill():
    from morale.svg_render import render_svg_artwork
    result,_=render_svg_artwork('''<svg width="100" height="100"><defs fill="white">
      <mask id="m"><rect width="100" height="100"/></mask></defs>
      <rect width="100" height="100" fill="red" mask="url(#m)"/></svg>''',resolution=100)
    assert result.pixelColor(50,50).getRgb()==(255,0,0,255)


def test_mask_gradient_resource_retains_root_color_context():
    from morale.svg_render import render_svg_artwork
    result,_=render_svg_artwork('''<svg width="100" height="100" color="white"><defs>
      <linearGradient id="g"><stop stop-color="currentColor"/></linearGradient>
      <mask id="m"><rect width="100" height="100" fill="url(#g)"/></mask></defs>
      <rect width="100" height="100" fill="red" color="black" mask="url(#m)"/></svg>''',resolution=100)
    assert result.pixelColor(50,50).getRgb()==(255,0,0,255)


def test_mask_and_gradient_resources_outside_defs_are_available():
    from morale.svg_render import render_svg_artwork
    result,_=render_svg_artwork('''<svg width="100" height="100" color="white">
      <linearGradient id="g"><stop stop-color="currentColor"/></linearGradient>
      <mask id="inner" maskContentUnits="objectBoundingBox"><rect width=".5" height="1" fill="white"/></mask>
      <mask id="outer"><rect width="100" height="100" fill="url(#g)" mask="url(#inner)"/></mask>
      <rect width="100" height="100" fill="red" mask="url(#outer)"/></svg>''',resolution=100)
    assert result.pixelColor(20,20).getRgb()==(255,0,0,255)
    assert result.pixelColor(80,20).alpha()==0
