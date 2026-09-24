import pytest
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.trace_threads import match_trace_threads
from morale.trace_quality import conversion_quality,quality_text


def test_custom_chart_matches_colors_and_preserves_geometry(tmp_path):
    path=tmp_path/'my-threads.csv'
    path.write_text('color,brand,catalog_number,description\n#ee0011,Hobby,12,Cherry\n#0011ee,Hobby,35,Blue\n')
    source=Project(objects=[DesignObject(color=c,x=i*25) for i,c in enumerate(('#ff0000','#0000ff','#f00000'))])
    before=source.dumps();result,matches=match_trace_threads(source,str(path))
    assert source.dumps()==before
    assert [o.color for o in result.objects]==['#ee0011','#0011ee','#ee0011']
    assert result.objects[0].thread=={'brand':'Hobby','catalog_number':'12','description':'Cherry'}
    assert [b.stitches for b in generate(source)]==[b.stitches for b in generate(result)]
    assert [o.id for o in source.objects]==[o.id for o in result.objects]
    assert Project.loads(result.dumps()).objects==result.objects
    report=conversion_quality(result);report['thread_matches']=matches
    assert '#ff0000 → #ee0011' in quality_text(report) and 'Hobby 12 Cherry' in quality_text(report)


@pytest.mark.parametrize('catalog',['PEC fixed palette','JEF fixed palette'])
def test_builtin_matching_uses_only_chart_entries(catalog):
    from morale.catalogs import builtin_catalog
    source=Project(objects=[DesignObject(color='#b85164'),DesignObject(color='#089e6a')])
    result,matches=match_trace_threads(source,catalog)
    colors={e.color.lower() for e in builtin_catalog(catalog)}
    assert all(o.color in colors and o.thread for o in result.objects)
    assert len(matches)==2


def test_keep_artwork_colors_is_lossless():
    source=Project(objects=[DesignObject()]);result,matches=match_trace_threads(source,'')
    assert result==source and result is not source and matches==[]


def test_bad_chart_is_rejected(tmp_path):
    path=tmp_path/'bad.csv';path.write_text('color\ninvalid\n')
    with pytest.raises(ValueError,match='RRGGBB'): match_trace_threads(Project(),str(path))


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_matched_design_exports_without_changing_sewn_bounds(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    result,_=match_trace_threads(Project(objects=[DesignObject(kind='rectangle',width=10,height=10)]),'PEC fixed palette')
    path=tmp_path/f'thread.{extension}';export_machine(result,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(abs(s.x)<=5.1 and abs(s.y)<=5.1 for s in sewn)
