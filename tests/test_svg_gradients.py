import xml.etree.ElementTree as ET
import pytest
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QPainterPath,QTransform
from morale.svg_gradients import linear_brush


def paint(attrs='',clip=False):
    node=ET.fromstring(f'<linearGradient {attrs}><stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient>')
    image=QImage(100,40,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image)
    if clip:painter.setClipRect(QRectF(0,0,20,40))
    painter.fillRect(QRectF(0,0,100,40),linear_brush(node,QRectF(0,0,100,40),(100,40)))
    painter.end();return image


def test_gradient_paints_through_geometry_clip_without_rescaling_colors():
    full=paint();clipped=paint(clip=True)
    assert clipped.pixelColor(50,20).alpha()==0
    assert clipped.pixelColor(10,20)==full.pixelColor(10,20)
    assert full.pixelColor(10,20).red()>full.pixelColor(10,20).blue()
    assert full.pixelColor(90,20).blue()>full.pixelColor(90,20).red()


def test_user_space_percentages_match_object_bounds():
    first=paint('gradientUnits="userSpaceOnUse" x2="100%"');second=paint()
    for x in range(100):
        assert max(abs(a-b) for a,b in zip(first.pixelColor(x,20).getRgb(),second.pixelColor(x,20).getRgb()))<=1


def test_gradient_transform_reverses_colors():
    image=paint('gradientTransform="translate(1,0) scale(-1,1)"')
    assert image.pixelColor(10,20).blue()>image.pixelColor(10,20).red()


@pytest.mark.parametrize('value',['nan','inf','bad'])
def test_invalid_gradient_coordinates_rejected(value):
    node=ET.fromstring(f'<linearGradient x1="{value}"/>')
    with pytest.raises(ValueError):linear_brush(node,QRectF(0,0,10,10),(100,100))


def test_gradient_templates_resolve_chains_without_mutating_source():
    from morale.svg_gradients import resolve_gradient
    root=ET.fromstring('''<svg><defs>
      <linearGradient id="base" x2="80%" spreadMethod="reflect">
        <stop stop-color="red"/><stop offset="1" stop-color="blue"/>
      </linearGradient>
      <linearGradient id="middle" href="#base" y2="25%"/>
      <linearGradient id="front" href="#middle" x2="100%"><title>Color</title></linearGradient>
    </defs></svg>''')
    before=ET.tostring(root)
    node=resolve_gradient(root,'front')
    assert node.get('x2')=='100%'
    assert node.get('y2')=='25%'
    assert node.get('spreadMethod')=='reflect'
    assert [stop.get('stop-color') for stop in node]==['red','blue']
    assert 'href' not in node.attrib
    linear_brush(node,QRectF(0,0,100,40),(100,40))
    node[0].set('stop-color','green')
    assert ET.tostring(root)==before


def test_own_stops_replace_template_stops_and_template_style_does_not_leak():
    from morale.svg_gradients import resolve_gradient
    root=ET.fromstring('''<svg>
      <linearGradient id="base" style="color:red" x2="70%"><stop stop-color="blue"/></linearGradient>
      <linearGradient id="front" href="#base" color="green"><stop stop-color="currentColor"/></linearGradient>
    </svg>''')
    node=resolve_gradient(root,'front')
    assert len(node)==1 and 'color:red' not in node.get('style','')
    assert linear_brush(node,QRectF(0,0,100,40),(100,40)).color().name()=='#008000'


def test_cross_kind_gradient_template_inherits_only_common_attributes():
    from morale.svg_gradients import resolve_gradient
    root=ET.fromstring('''<svg xmlns:xlink="http://www.w3.org/1999/xlink">
      <radialGradient id="base" cx="20%" gradientUnits="userSpaceOnUse"><stop stop-color="red"/></radialGradient>
      <linearGradient id="front" xlink:href="#base"/>
    </svg>''')
    node=resolve_gradient(root,'front')
    assert node.get('gradientUnits')=='userSpaceOnUse'
    assert node.get('cx') is None and len(node)==1
    assert not any('href' in key for key in node.attrib)


@pytest.mark.parametrize('content,message',[
    ('<linearGradient id="a" href="#a"/>','circular'),
    ('<linearGradient id="a" href="#b"/><linearGradient id="b" href="#a"/>','circular'),
    ('<linearGradient id="a" href="#missing"/>','existing local'),
    ('<linearGradient id="a" href="file.svg#b"/>','local references'),
    ('<linearGradient id="a" href="#b"/><rect id="b"/>','name a gradient'),
    ('<linearGradient id="a"/><linearGradient id="a"/>','duplicate'),
    ('<linearGradient id="a"><animate/></linearGradient>','Unsupported'),
])
def test_invalid_gradient_templates_rejected(content,message):
    from morale.svg_gradients import resolve_gradient
    with pytest.raises(ValueError,match=message):resolve_gradient(ET.fromstring('<svg>'+content+'</svg>'),'a')


def test_gradient_template_depth_bounded():
    from morale.svg_gradients import resolve_gradient
    root=ET.fromstring('<svg>'+''.join(f'<linearGradient id="g{i}" href="#g{i+1}"/>' for i in range(65))+'<linearGradient id="g65"/></svg>')
    with pytest.raises(ValueError,match='64 levels'):resolve_gradient(root,'g0')


def test_inherited_gradient_renders_same_as_explicit_gradient_under_world_transform():
    from morale.svg_gradients import resolve_gradient
    root=ET.fromstring('''<svg>
      <linearGradient id="base" gradientTransform="translate(1,0) scale(-1,1)">
        <stop stop-color="red"/><stop offset="1" stop-color="blue"/>
      </linearGradient><linearGradient id="front" href="#base"/>
    </svg>''')
    explicit=ET.fromstring('''<linearGradient gradientTransform="translate(1,0) scale(-1,1)">
      <stop stop-color="red"/><stop offset="1" stop-color="blue"/>
    </linearGradient>''')
    bounds=QRectF(0,0,30,20)
    world=QTransform().translate(20,10).scale(2,1)
    images=[]
    for node in (resolve_gradient(root,'front'),explicit):
        image=QImage(100,40,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image)
        painter.setClipRect(QRectF(20,10,30,20))
        painter.fillRect(world.mapRect(bounds),linear_brush(node,bounds,(100,40),world))
        painter.end();images.append(image)
    assert images[0]==images[1]
    assert images[0].pixelColor(25,20).blue()>220
    assert images[0].pixelColor(55,20).alpha()==0


def radial_image(attrs='',clip=False):
    from morale.svg_gradients import gradient_brush
    node=ET.fromstring(f'<radialGradient {attrs}><stop stop-color="red"/><stop offset="1" stop-color="blue"/></radialGradient>')
    image=QImage(100,40,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
    brush=gradient_brush(node,QRectF(0,0,100,40),(100,40))
    painter=QPainter(image)
    if clip:painter.setClipRect(QRectF(0,0,60,40))
    painter.fillRect(QRectF(0,0,100,40),brush)
    painter.end();return image


def test_radial_object_bounds_make_elliptical_rings():
    image=radial_image()
    assert image.pixelColor(50,20).red()>240
    assert image.pixelColor(99,20).blue()>245
    assert image.pixelColor(50,39).blue()>240
    assert abs(image.pixelColor(75,20).red()-image.pixelColor(50,30).red())<8


def test_radial_clipping_does_not_move_highlight():
    full=radial_image('fx="25%"');clipped=radial_image('fx="25%"',True)
    assert full.pixelColor(25,20).red()>240
    assert clipped.pixelColor(25,20)==full.pixelColor(25,20)
    assert clipped.pixelColor(75,20).alpha()==0


def test_radial_percentage_radius_uses_normalized_viewport_diagonal():
    import math
    percentage=radial_image('gradientUnits="userSpaceOnUse" r="50%"')
    absolute=radial_image(f'gradientUnits="userSpaceOnUse" r="{math.hypot(100,40)/math.sqrt(2)/2}"')
    assert percentage==absolute


def test_radial_focal_circle_and_identical_circles():
    image=radial_image('fr="25%"')
    assert image.pixelColor(60,20).red()==255
    assert image.pixelColor(99,20).blue()>240
    empty=radial_image('fr="50%"')
    assert all(empty.pixelColor(x,20).alpha()==0 for x in range(100))


@pytest.mark.parametrize('attrs',['r="-1"','fr="-1"','cx="nan"','fy="inf"'])
def test_invalid_radial_geometry_rejected(attrs):
    with pytest.raises(ValueError):radial_image(attrs)


@pytest.mark.parametrize('stops',['','<stop stop-color="red"/>','<stop stop-color="red"/><stop offset="1" stop-color="blue"/>'])
def test_zero_area_gradient_bounds_never_become_solid_paint(stops):
    from morale.svg_gradients import gradient_brush
    node=ET.fromstring('<linearGradient>'+stops+'</linearGradient>')
    assert gradient_brush(node,QRectF(0,0,0,10),(100,100)).color().alpha()==0


@pytest.mark.parametrize('stops',['','<stop stop-color="red"/>'])
def test_invalid_spread_rejected_even_without_color_interpolation(stops):
    from morale.svg_gradients import gradient_brush
    node=ET.fromstring('<linearGradient spreadMethod="invalid">'+stops+'</linearGradient>')
    with pytest.raises(ValueError,match='spread'):gradient_brush(node,QRectF(0,0,10,10),(100,100))


def test_singular_gradient_transform_does_not_fall_back_to_identity():
    from morale.svg_gradients import gradient_brush
    node=ET.fromstring('<linearGradient gradientTransform="scale(0)"><stop stop-color="red"/></linearGradient>')
    assert gradient_brush(node,QRectF(0,0,10,10),(100,100)).color().alpha()==0


def test_nonfinite_world_transform_rejected():
    from morale.svg_gradients import gradient_brush
    node=ET.fromstring('<linearGradient><stop stop-color="red"/></linearGradient>')
    with pytest.raises(ValueError,match='world transform'):
        gradient_brush(node,QRectF(0,0,10,10),(100,100),QTransform(1,0,0,1,float('nan'),0))


def test_validated_svg_paint_sink_preserves_gradient_bounds_after_clipping():
    from morale.svg_import import checked_xml
    from morale.svg_clipping import geometry
    from morale.svg_gradients import gradient_brush
    source='''<svg width="100" height="40"><defs><clipPath id="c"><rect width="20" height="30"/></clipPath></defs>
      <g transform="translate(10,5)" clip-path="url(#c)"><rect width="80" height="30" fill="red"/></g></svg>'''
    gradient=ET.fromstring('<linearGradient><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient>')
    paints=[]
    checked_xml(source,paint_sink=lambda *args:paints.append(args))
    assert len(paints)==1
    visible,element,paint_name,viewport=paints[0]
    assert paint_name=='fill'
    assert visible.boundingRect()==QRectF(10,5,20,30)
    m=element.transform;world=QTransform(m.a,m.b,m.c,m.d,m.e,m.f)
    inverse,valid=world.inverted();assert valid
    original=inverse.map(geometry(element)).boundingRect()
    assert original==QRectF(0,0,80,30)
    brush=gradient_brush(gradient,original,viewport,world)
    image=QImage(100,40,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image);painter.fillPath(visible,brush);painter.end()
    assert image.pixelColor(20,20).red()>215
    assert image.pixelColor(40,20).alpha()==0


def test_paint_sink_keeps_paint_order_and_expands_unclipped_strokes():
    from morale.svg_import import checked_xml
    paints=[]
    checked_xml('<svg width="100" height="100"><rect x="10" y="10" width="20" height="20" fill="red" stroke="blue" stroke-width="4" paint-order="stroke fill"/></svg>',
                paint_sink=lambda *args:paints.append(args))
    assert [item[2] for item in paints]==['stroke','fill']
    assert paints[0][0].boundingRect()==QRectF(8,8,24,24)
    assert paints[1][0].boundingRect()==QRectF(10,10,20,20)


def test_paint_sink_survives_symbol_expansion_and_skips_hidden_artwork():
    from morale.svg_import import checked_xml
    paints=[]
    checked_xml('''<svg width="100" height="100"><defs><symbol id="s" viewBox="0 0 10 10"><rect width="10" height="10"/></symbol></defs>
      <use href="#s" width="20" height="20"/>
      <rect width="100" height="100" display="none"/></svg>''',paint_sink=lambda *args:paints.append(args))
    assert len(paints)==1
    assert paints[0][0].boundingRect()==QRectF(0,0,20,20)
    assert paints[0][3]==(10,10)


@pytest.mark.parametrize('length',['96px','25.4mm','2.54cm','1in','72pt','6pc','101.6Q'])
def test_absolute_linear_gradient_units_match_pixels(length):
    expected=paint('gradientUnits="userSpaceOnUse" x2="96"')
    actual=paint(f'gradientUnits="userSpaceOnUse" x2="{length}"')
    assert actual==expected


def test_absolute_radial_gradient_units_match_pixels():
    assert radial_image('gradientUnits="userSpaceOnUse" cx="12.7mm" cy="15pt" r=".25in"')==radial_image('gradientUnits="userSpaceOnUse" cx="48" cy="20" r="24"')
