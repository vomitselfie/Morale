import itertools
import math
import random
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.catalogs import ThreadEntry
from morale.perceptual_color import distance_squared
from morale.thread_planning import plan_threads,group_thread_runs,thread_changes,_assign
from morale.trace_threads import match_trace_threads


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def regions(colors,spacing=12,size=10):
    return Project(objects=[DesignObject(name=f'R{i}',kind='rectangle',x=i*spacing,width=size,height=size,color=c)
                            for i,c in enumerate(colors)])


def chart(tmp_path,colors):
    path=tmp_path/'chart.csv'
    path.write_text('color,brand,catalog_number,description\n'+''.join(f'{c},Test,{i:03},Thread {i}\n' for i,c in enumerate(colors)))
    return str(path)


def test_assignment_matches_brute_force():
    rng=random.Random(4)
    for _ in range(40):
        rows,columns=rng.randint(1,4),rng.randint(4,6)
        costs=[[rng.uniform(0,10) for _ in range(columns)] for _ in range(rows)]
        chosen=_assign(costs)
        assert len(set(chosen))==rows
        best=min(sum(costs[r][c] for r,c in enumerate(p)) for p in itertools.permutations(range(columns),rows))
        assert sum(costs[r][c] for r,c in enumerate(chosen))==pytest.approx(best)


def test_colliding_colors_get_distinct_threads(tmp_path):
    # Both reds are nearest to the single red thread; independent matching merges them.
    project=regions(['#cc2222','#991111','#2244cc'])
    path=chart(tmp_path,['#b81c1c','#e0662a','#2a4ac8','#1a8a3a'])
    nearest,_=match_trace_threads(project,path,'oklab')
    assert nearest.objects[0].color==nearest.objects[1].color
    planned,matches=match_trace_threads(project,path,'oklab',distinct=True)
    assert len({o.color for o in planned.objects})==3
    adjusted=[m for m in matches if m['adjusted']]
    assert len(adjusted)==1 and adjusted[0]['distance']>adjusted[0]['nearest_distance']
    assert all(m['planned'] for m in matches) and planned.objects[2].color=='#2a4ac8'
    assert project.objects[0].color=='#cc2222'


def test_without_conflicts_planning_equals_nearest(tmp_path):
    project=regions(['#cc2222','#2244cc','#22aa44'])
    path=chart(tmp_path,['#b81c1c','#e0662a','#2a4ac8','#1a8a3a'])
    nearest,_=match_trace_threads(project,path,'oklab')
    planned,matches=match_trace_threads(project,path,'oklab',distinct=True)
    assert [o.color for o in planned.objects]==[o.color for o in nearest.objects]
    assert not any(m['adjusted'] for m in matches)


def test_larger_regions_keep_their_best_thread(tmp_path):
    path=chart(tmp_path,['#b81c1c','#e0662a'])
    big_first=Project(objects=[DesignObject(kind='rectangle',width=40,height=40,color='#cc2222'),
                               DesignObject(kind='rectangle',x=50,width=2,height=2,color='#bb1f1f')])
    # 2 x 2 mm detail within merge distance? No: these reds differ enough to stay apart.
    assert math.sqrt(distance_squared('#cc2222','#bb1f1f'))>2
    planned,_=match_trace_threads(big_first,path,'oklab',distinct=True)
    assert planned.objects[0].color=='#b81c1c' and planned.objects[1].color=='#e0662a'


def test_nearly_identical_colors_may_share_a_thread(tmp_path):
    project=regions(['#cc2222','#cb2323','#2244cc'])
    assert math.sqrt(distance_squared('#cc2222','#cb2323'))<2
    planned,matches=match_trace_threads(project,chart(tmp_path,['#b81c1c','#e0662a','#2a4ac8']),'oklab',distinct=True)
    assert planned.objects[0].color==planned.objects[1].color=='#b81c1c'
    assert {tuple(m['shared_with']) for m in matches if m['source_color']!='#2244cc'}=={('#cb2323',),('#cc2222',)}


def test_small_chart_falls_back_to_nearest(tmp_path):
    project=regions(['#cc2222','#991111','#2244cc'])
    planned,matches=match_trace_threads(project,chart(tmp_path,['#b81c1c','#2a4ac8']),'oklab',distinct=True)
    assert planned.objects[0].color==planned.objects[1].color and not any(m['adjusted'] for m in matches)


def test_invalid_distinct_setting_is_rejected(tmp_path):
    with pytest.raises(ValueError):match_trace_threads(regions(['#cc2222']),'PEC fixed palette','oklab',distinct=1)


def test_grouping_joins_separate_same_thread_regions():
    project=regions(['#ff0000','#0000ff']*3)
    grouped,stats=group_thread_runs(project)
    assert (stats['before_changes'],stats['after_changes'])==(5,1) and thread_changes(grouped.objects)==1
    assert stats['order']==[0,2,4,1,3,5] and [o.name for o in grouped.objects]==['R0','R2','R4','R1','R3','R5']
    assert project.objects[1].name=='R1'


def test_grouping_never_reorders_overlapping_layers():
    # Each region overlaps its neighbour, so every pair keeps its order.
    project=regions(['#ff0000','#0000ff']*3,spacing=6)
    grouped,stats=group_thread_runs(project)
    assert stats['after_changes']==stats['before_changes']==5 and grouped.objects==project.objects


def test_grouping_moves_only_past_non_overlapping_regions():
    # R1 (blue) overlaps R0 and R4 (both red); R2 and R3 are separate.
    project=Project(objects=[DesignObject(name='R0',kind='rectangle',width=10,height=10,color='#ff0000'),
                             DesignObject(name='R1',kind='rectangle',x=6,width=10,height=10,color='#0000ff'),
                             DesignObject(name='R2',kind='rectangle',x=40,width=10,height=10,color='#ff0000'),
                             DesignObject(name='R3',kind='rectangle',x=60,width=10,height=10,color='#0000ff'),
                             DesignObject(name='R4',kind='rectangle',x=12,width=10,height=10,color='#ff0000')])
    grouped,stats=group_thread_runs(project)
    names=[o.name for o in grouped.objects]
    assert names==['R0','R2','R1','R3','R4'] and (stats['before_changes'],stats['after_changes'])==(4,2)


@pytest.mark.parametrize('field,value',[('stop_after',True),('color_break',True),('stage_note','Place fabric'),('group_id','g')])
def test_grouping_does_not_cross_barriers(field,value):
    project=regions(['#ff0000','#0000ff','#ff0000','#0000ff'])
    setattr(project.objects[1],field,value)
    grouped,_=group_thread_runs(project)
    names=[o.name for o in grouped.objects]
    assert names.index('R0')<names.index('R1')<names.index('R2') and names.index('R1')<names.index('R3')


def test_worker_sewing_order_and_presets(tmp_path):
    import json
    from morale.raster_trace import worker_main
    source=tmp_path/'art.svg'
    source.write_text('<svg width="60" height="20">'+''.join(f'<rect x="{i*10}" y="0" width="8" height="8" fill="{c}"/>'
                      for i,c in enumerate(['#cc2222','#2244cc','#991111','#2244cc']))+'</svg>')
    path=chart(tmp_path,['#b81c1c','#e0662a','#2a4ac8','#1a8a3a'])
    output=tmp_path/'out';output.mkdir()
    options={'thread_catalog':path,'distinct_threads':True,'group_colors':True,'reduce_travel':True}
    assert worker_main([str(source),str(output),json.dumps(options)])==0
    stats=json.loads((output/'preview.json').read_text())['trace_stats']
    project=Project.loads(json.loads((output/'preview.json').read_text())['project'])
    assert len({o.color for o in project.objects})==3 and stats['color_grouping']['after_changes']<stats['color_grouping']['before_changes']
    assert sorted(stats['sewing_order'])==list(range(4))
    # Every final object keeps the colour planned for its original region.
    matches={m['source_color']:m['color'] for m in stats['thread_matches']}
    original=['#cc2222','#2244cc','#991111','#2244cc']
    assert [o.color for o in project.objects]==[matches[original[i]] for i in stats['sewing_order']]
    from morale.trace_quality import quality_text
    text=quality_text(stats['quality'])
    assert 'Kept distinct: nearest thread' in text and 'Palette planned as a whole' in text
    grouping=stats['color_grouping']
    assert f"Thread grouping: {grouping['before_changes']} → {grouping['after_changes']} thread changes" in text
