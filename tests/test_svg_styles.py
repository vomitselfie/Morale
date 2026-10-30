import xml.etree.ElementTree as ET
import pytest
from morale.svg_styles import apply_styles
from morale.svg_gradients import properties
from morale.svg_render import render_svg_artwork


@pytest.fixture(scope='module',autouse=True)
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_css_specificity_inline_and_important():
    root=ET.fromstring('''<svg><style>rect {fill:red} .paint {fill:blue} #target {fill:green} .paint {stroke:black !important}</style>
      <rect id="target" class="paint" style="fill:yellow;stroke:red"/></svg>''')
    apply_styles(root);attrs=properties(root.find('rect'))
    assert attrs['fill']=='yellow' and attrs['stroke']=='black'
    assert root.find('style') is None


def test_descendant_and_attribute_selectors_render_gradient_stops():
    image,_=render_svg_artwork('''<svg width="100" height="100"><style>
      defs stop {stop-color:red} stop[offset="1"] {stop-color:blue}
      .art > rect {fill:url(#g)}
      </style><defs><linearGradient id="g"><stop/><stop offset="1"/></linearGradient></defs>
      <g class="art"><rect width="100" height="100"/></g></svg>''',resolution=100)
    assert image.pixelColor(10,50).red()>220
    assert image.pixelColor(90,50).blue()>220


def test_stylesheet_mask_and_group_opacity():
    image,_=render_svg_artwork('''<svg width="100" height="100"><style>
      .mask {fill:white} #art {fill:red;mask:url(#m);opacity:.5}
      </style><defs><mask id="m" maskContentUnits="objectBoundingBox"><rect class="mask" width=".5" height="1"/></mask></defs>
      <rect id="art" width="100" height="100"/></svg>''',resolution=100)
    assert image.pixelColor(20,20).red()==255
    assert 125<=image.pixelColor(20,20).alpha()<=129
    assert image.pixelColor(80,20).alpha()==0


@pytest.mark.parametrize('css',['@import "external.css";','@media print {rect {fill:red}}','rect::before {fill:red}','rect {fill:var(--color)}'])
def test_unsupported_css_fails_explicitly(css):
    root=ET.fromstring('<svg><style>'+css+'</style><rect/></svg>')
    with pytest.raises(ValueError):apply_styles(root)


def test_embedded_stylesheet_direct_vector_import():
    from morale.svg_import import import_svg_text
    imported=import_svg_text('''<svg width="100" height="100"><style>
      .paint {fill:blue} #chosen {fill:red}
      </style><rect id="chosen" class="paint" width="20" height="20"/></svg>''')
    assert len(imported.objects)==1 and imported.objects[0].color=='#ff0000'


@pytest.mark.parametrize('style',[
    'fill:red ! important;fill:blue',
    'fill:red ! /* priority */ IMPORTANT;fill:blue',
    'fill:/* palette; note */red',
])
def test_inline_css_syntax_preserves_color_in_both_import_modes(style):
    from morale.svg_import import import_svg_text
    source=f'<svg width="100" height="100"><rect width="100" height="100" style="{style}"/></svg>'
    image,_=render_svg_artwork(source,resolution=100)
    assert image.pixelColor(50,50).name()=='#ff0000'
    imported=import_svg_text(source)
    assert len(imported.objects)==1 and imported.objects[0].color=='#ff0000'


def test_embedded_css_value_comments_preserve_color():
    image,_=render_svg_artwork('''<svg width="100" height="100"><style>
      rect {fill:/* selected; color */red ! /* priority */ important}
      </style><rect width="100" height="100" fill="blue"/></svg>''',resolution=100)
    assert image.pixelColor(50,50).name()=='#ff0000'


def test_styled_symbol_instances_worker_and_all_machine_writers(tmp_path):
    import json
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    source=tmp_path/'styled-instances.svg'
    source.write_text('''<svg width="100" height="50"><style>
      .red {color:red} .blue {color:blue}
      .face {fill:currentColor;clip-path:url(#cut)}
      </style><defs><symbol id="s" viewBox="0 0 10 10">
      <defs><clipPath id="cut"><rect width="5" height="10"/></clipPath></defs>
      <rect class="face" width="10" height="10"/>
      </symbol></defs><use class="red" href="#s" width="40" height="40"/>
      <use class="blue" href="#s" x="60" width="40" height="40"/></svg>''')
    original=source.read_bytes()
    image,_=render_svg_artwork(source.read_text(),resolution=100)
    assert image.pixelColor(10,20).name()=='#ff0000'
    assert image.pixelColor(70,20).name()=='#0000ff'
    assert image.pixelColor(30,20).alpha()==image.pixelColor(90,20).alpha()==0
    output=tmp_path/'worker';output.mkdir()
    options=dict(render_svg=True,width=100,colors=2,resolution=256,
                 method='smooth',ignore_white=False,stitch_mode='fill')
    assert worker_main([str(source),str(output),json.dumps(options)])==0
    assert source.read_bytes()==original
    info=json.loads((output/'preview.json').read_text())
    project=Project.loads(info['project'])
    assert len(project.objects)==2
    objects=sorted(project.objects,key=lambda obj:obj.x)
    # Raster antialiasing can shift the reduced palette by a channel level.
    from PySide6.QtGui import QColor
    for obj,expected in zip(objects,((255,0,0),(0,0,255))):
        actual=QColor(obj.color).getRgb()[:3]
        assert all(abs(a-b)<=2 for a,b in zip(actual,expected))
    assert [obj.width for obj in objects]==pytest.approx([20,20],abs=.5)
    assert objects[1].x-objects[0].x==pytest.approx(60,abs=.5)
    blocks=generate(project)
    assert generate(Project.loads(project.dumps()))==blocks
    for extension in ('pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'):
        target=tmp_path/f'styled-instances.{extension}'
        export_machine(project,target,blocks)
        result=verify_export(blocks,target)
        assert result['complete_path_comparison'],extension
        assert result['bounds_delta_mm']<=.3,extension
        assert all(problem.startswith('Trim commands increased:')
                   for problem in result['problems']),(extension,result)


@pytest.mark.parametrize('paint,expected',[
    ('rgb(255 0 0)',(255,0,0,255)),
    ('rgb(100% 0% 0% / 50%)',(255,0,0,128)),
    ('hsl(120 100% 50%)',(0,255,0,255)),
    ('hwb(240 0% 0%)',(0,0,255,255)),
    ('color(srgb 1 0 0)',(255,0,0,255)),
    ('rebeccapurple',(102,51,153,255)),
])
@pytest.mark.parametrize('location',['attribute','inline','stylesheet'])
def test_modern_css_colors_render_with_alpha(paint,expected,location):
    rule=f'<style>rect {{fill:{paint}}}</style>' if location=='stylesheet' else ''
    attribute=f'fill="{paint}"' if location=='attribute' else f'style="fill:{paint}"' if location=='inline' else ''
    image,_=render_svg_artwork(f'<svg width="100" height="100">{rule}<rect width="100" height="100" {attribute}/></svg>',resolution=100)
    assert image.pixelColor(50,50).getRgb()==expected


@pytest.mark.parametrize('paint',['color(display-p3 1 0 0)','oklch(.5 .2 30)','color()'])
def test_unsupported_color_spaces_do_not_silently_become_black(paint):
    with pytest.raises(ValueError,match='color'):
        render_svg_artwork(f'<svg width="100" height="100"><rect width="100" height="100" fill="{paint}"/></svg>')


def test_modern_color_attribute_selector_matches_original_value():
    image,_=render_svg_artwork('''<svg width="100" height="100"><style>
      rect[fill="rgb(255 0 0)"] {fill:rgb(0 0 255)}
      </style><rect width="100" height="100" fill="rgb(255 0 0)"/></svg>''',resolution=100)
    assert image.pixelColor(50,50).name()=='#0000ff'


def test_modern_colors_direct_vector_import():
    from morale.svg_import import import_svg_text
    imported=import_svg_text('<svg width="100" height="100"><rect width="20" height="20" fill="hsl(120 100% 50%)"/></svg>')
    assert imported.objects[0].color=='#00ff00'


def test_css_variables_cascade_case_and_inherited_computed_alias():
    root=ET.fromstring('''<svg style="--Paint:red;--paint:blue;--alias:var(--Paint)"><style>
      rect {fill:var(--alias);stroke:var(--paint)} .chosen {--Paint:green !important}
      </style><g style="--Paint:yellow"><rect class="chosen" style="--paint:black"/></g></svg>''')
    apply_styles(root);attrs=properties(root.find('g/rect'))
    assert attrs['fill']=='red' and attrs['stroke']=='black'
    assert '--' not in root.get('style','')


def test_css_variables_nested_fallbacks_and_color_functions_render_and_import():
    from morale.svg_import import import_svg_text
    source='''<svg width="100" height="100" style="--r:255;--fallback:rgb(var(--r),0,0)">
      <rect width="100" height="100" style="fill:var(--missing,var(--fallback,blue))"/></svg>'''
    image,_=render_svg_artwork(source,resolution=100)
    assert image.pixelColor(50,50).name()=='#ff0000'
    assert import_svg_text(source).objects[0].color=='#ff0000'


@pytest.mark.parametrize('style',['--a:var(--a);fill:var(--a)','--a:var(--b);--b:var(--a);fill:var(--a)',
                                  'fill:var(red)','--a:revert;fill:var(--a)'])
def test_unsupported_variable_cases_fail_explicitly(style):
    root=ET.fromstring(f'<svg><rect style="{style}"/></svg>')
    with pytest.raises(ValueError):apply_styles(root)


def test_variable_expansion_bounded():
    definitions=['--v0:red']+[f'--v{i}:var(--v{i-1}) var(--v{i-1})' for i in range(1,20)]
    root=ET.fromstring('<svg style="'+';'.join(definitions)+'"><rect style="fill:var(--v19)"/></svg>')
    with pytest.raises(ValueError,match='16 KB'):apply_styles(root)


def test_custom_property_important_beats_inline_and_initial_uses_fallback():
    root=ET.fromstring('''<svg style="--paint:red"><style>rect {--paint:blue !important}</style>
      <rect style="--paint:green;fill:var(--paint)"/><circle style="--paint:initial;fill:var(--paint,yellow)"/></svg>''')
    apply_styles(root)
    assert properties(root.find('rect'))['fill']=='blue'
    assert properties(root.find('circle'))['fill']=='yellow'


@pytest.mark.parametrize('rendered',[False,True])
def test_variable_palette_worker_to_editable_objects_and_machine_files(tmp_path,rendered):
    import json
    from PySide6.QtGui import QColor
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    source=tmp_path/'variable-palette.svg'
    source.write_text('''<svg width="100" height="50" style="--paint:rgb(255,0,0);--edge:blue">
      <style>.art {fill:var(--paint);stroke:var(--missing,none)}</style>
      <path class="art" fill-rule="evenodd" d="M5 5H35V35H5Z M15 15H25V25H15Z"/>
      <g style="--paint:var(--edge)"><rect class="art" x="65" y="5" width="30" height="30"/></g>
      </svg>''')
    original=source.read_bytes();output=tmp_path/'converted';output.mkdir()
    options=dict(render_svg=rendered,width=100,colors=2,resolution=256,
                 method='smooth',ignore_white=False,stitch_mode='fill')
    assert worker_main([str(source),str(output),json.dumps(options)])==0
    assert source.read_bytes()==original
    project=Project.loads(json.loads((output/'preview.json').read_text())['project'])
    objects=sorted(project.objects,key=lambda obj:obj.x)
    assert len(objects)==2 and len(objects[0].rings())==2
    for obj,expected in zip(objects,((255,0,0),(0,0,255))):
        assert all(abs(a-b)<=(12 if rendered else 0) for a,b in zip(QColor(obj.color).getRgb()[:3],expected))
    if rendered:
        literal=tmp_path/'literal.svg'
        literal.write_text('<svg width="100" height="50"><path fill="red" fill-rule="evenodd" d="M5 5H35V35H5Z M15 15H25V25H15Z"/><rect fill="blue" x="65" y="5" width="30" height="30"/></svg>')
        reference=tmp_path/'reference';reference.mkdir()
        assert worker_main([str(literal),str(reference),json.dumps(options)])==0
        reference_project=Project.loads(json.loads((reference/'preview.json').read_text())['project'])
        reference_objects=sorted(reference_project.objects,key=lambda obj:obj.x)
        assert [obj.color for obj in objects]==[obj.color for obj in reference_objects]
        assert [obj.rings() for obj in objects]==[obj.rings() for obj in reference_objects]
    assert [obj.width for obj in objects]==pytest.approx([30,30],abs=.6)
    blocks=generate(project)
    assert blocks==generate(Project.loads(project.dumps()))
    for extension in ('pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'):
        target=tmp_path/f'variables.{extension}';export_machine(project,target,blocks)
        result=verify_export(blocks,target)
        assert result['complete_path_comparison'] and result['bounds_delta_mm']<=.3,result
        assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result


@pytest.mark.parametrize('tag',['symbol','g'])
def test_instance_dependent_variables_fail_instead_of_baking_wrong_color(tag):
    source=f'<svg style="--paint:red"><defs><{tag} id="s"><rect style="fill:var(--paint)"/></{tag}></defs><use href="#s" style="--paint:blue"/></svg>'
    with pytest.raises(ValueError,match='instance-style'):apply_styles(ET.fromstring(source))


@pytest.mark.parametrize('paint',['var(--paint)','var(--missing,red)',r'v\61 r(--paint)'])
def test_presentation_attribute_variables_render_and_import(paint):
    from morale.svg_import import import_svg_text
    source=f'<svg width="20" height="20" style="--paint:red"><rect fill="{paint}" width="20" height="20"/></svg>'
    image,_=render_svg_artwork(source,resolution=64)
    assert image.pixelColor(30,30).name()=='#ff0000'
    assert import_svg_text(source).objects[0].color=='#ff0000'


def test_attribute_fallback_without_any_styles():
    root=ET.fromstring('<svg><rect fill="var(--missing,blue)"/></svg>')
    apply_styles(root);assert root.find('rect').get('fill')=='blue'


def test_style_overrides_unresolved_presentation_paint():
    root=ET.fromstring('<svg><rect fill="var(--missing)" style="fill:red"/></svg>')
    apply_styles(root);assert properties(root.find('rect'))['fill']=='red'


def test_presentation_variables_do_not_change_selector_matching():
    root=ET.fromstring('''<svg style="--paint:red"><style>rect[fill="var(--paint)"] {stroke:blue}</style><rect fill="var(--paint)"/></svg>''')
    apply_styles(root);attrs=properties(root.find('rect'))
    assert attrs['fill']=='red' and attrs['stroke']=='blue'


def test_empty_custom_property_does_not_silently_inherit_parent_color():
    root=ET.fromstring('<svg style="--paint:red"><rect style="--paint:;fill:var(--paint,blue)"/></svg>')
    with pytest.raises(ValueError,match='empty value'):apply_styles(root)


def test_reusable_presentation_variable_is_rejected():
    root=ET.fromstring('<svg style="--paint:red"><defs><g id="s"><rect fill="var(--paint)"/></g></defs><use href="#s" style="--paint:blue"/></svg>')
    with pytest.raises(ValueError,match='instance-style'):apply_styles(root)


def test_variable_opacity_attributes_render_like_literal_values():
    source='''<svg width="100" height="100" style="--alpha:.5;--stop:.4">
      <defs><linearGradient id="g"><stop stop-color="red" stop-opacity="var(--stop)"/>
      <stop offset="1" stop-color="red" stop-opacity="var(--stop)"/></linearGradient></defs>
      <g opacity="var(--alpha)"><rect width="100" height="100" fill="url(#g)" fill-opacity="var(--missing,.5)"/></g></svg>'''
    literal=source.replace('var(--stop)','.4').replace('var(--alpha)','.5').replace('var(--missing,.5)','.5')
    image,_=render_svg_artwork(source,resolution=100)
    reference,_=render_svg_artwork(literal,resolution=100)
    assert image==reference
    assert 24<=image.pixelColor(50,50).alpha()<=27


def test_variable_stroke_width_caps_and_dashes_preserve_expanded_geometry(tmp_path):
    from morale.vector_artwork import vector_artwork
    source='''<svg width="40" height="40" style="--width:2;--cap:round;--dash:4 4">
      <path d="M4 20H36" fill="none" stroke="red" stroke-width="var(--width)"
       stroke-linecap="var(--cap)" stroke-dasharray="var(--dash)"/></svg>'''
    literal=source.replace('var(--width)','2').replace('var(--cap)','round').replace('var(--dash)','4 4')
    projects=[]
    for name,text in [('variables',source),('literal',literal)]:
        path=tmp_path/f'{name}.svg';path.write_text(text)
        project,_,_=vector_artwork(path,width=40,expand_strokes=True);projects.append(project)
    assert projects[0].objects
    assert [obj.rings() for obj in projects[0].objects]==[obj.rings() for obj in projects[1].objects]
    assert all(obj.height==pytest.approx(2) for obj in projects[0].objects)


def test_opacity_fallback_without_styles():
    image,_=render_svg_artwork('<svg width="20" height="20"><rect width="20" height="20" fill="red" opacity="var(--missing,.5)"/></svg>',resolution=64)
    assert 126<=image.pixelColor(30,30).alpha()<=129


def test_missing_dependency_activates_consuming_paint_fallback():
    from morale.svg_import import import_svg_text
    source='''<svg width="20" height="20" style="--base:var(--missing);--paint:var(--base)">
      <rect width="20" height="20" fill="var(--paint,red)"/></svg>'''
    image,_=render_svg_artwork(source,resolution=64)
    assert image.pixelColor(30,30).name()=='#ff0000'
    assert import_svg_text(source).objects[0].color=='#ff0000'


def test_inherited_invalid_alias_is_not_recomputed_from_child_definition():
    root=ET.fromstring('''<svg style="--alias:var(--missing)">
      <rect style="--missing:red;fill:var(--alias,blue)"/></svg>''')
    apply_styles(root);assert properties(root.find('rect'))['fill']=='blue'


def test_unused_missing_dependency_does_not_block_valid_artwork():
    root=ET.fromstring('<svg style="--unused:var(--missing)"><rect fill="red"/></svg>')
    apply_styles(root);assert root.find('rect').get('fill')=='red'


def test_invalid_dependency_without_consuming_fallback_still_fails():
    root=ET.fromstring('<svg style="--paint:var(--missing)"><rect fill="var(--paint)"/></svg>')
    with pytest.raises(ValueError,match='Unresolved'):apply_styles(root)
