import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from morale.engine import generate
from morale.export_verify import verify_export, verification_text
from morale.formats import export_machine
from morale.model import demo_project


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('extension', ['pes', 'dst', 'exp', 'jef', 'xxx'])
def test_demo_export_verification_reports_added_controls(tmp_path, extension):
    project = demo_project(); blocks = generate(project)
    path = tmp_path / f'design.{extension}'
    export_machine(project, path, blocks)
    result = verify_export(blocks, path)
    assert result['decoded_stitches'] >= result['source_stitches']
    if extension == 'dst':
        assert not result['verified']
        assert any('Trim commands increased' in p for p in result['problems'])
    else:
        assert result['verified'] and not result['problems']


def test_vp3_preserves_geometry_but_reports_added_trims(tmp_path):
    project = demo_project(); blocks = generate(project)
    path = tmp_path / 'design.vp3'
    export_machine(project, path, blocks)
    result = verify_export(blocks, path)
    assert result['bounds_delta_mm'] < .1
    assert not result['verified'] and all('Trim commands increased' in p for p in result['problems'])


def test_a_damaged_file_is_flagged(tmp_path, monkeypatch):
    project = demo_project(); blocks = generate(project)
    path = tmp_path / 'design.dst'
    export_machine(project, path, blocks)
    import morale.export_verify as module
    original = module.import_machine
    def shifted(p):
        result = original(p)
        for obj in result.project.objects:
            obj.x += 2
        return result
    monkeypatch.setattr(module, 'import_machine', shifted)
    result = verify_export(blocks, path)
    assert not result['verified'] and any('edge moved' in p for p in result['problems'])


@pytest.mark.parametrize('extension,title', [('jef', 'Stitches exported'), ('pes', 'Stitches exported'), ('dst', 'Check the exported file')])
def test_window_export_reports_verification(tmp_path, monkeypatch, extension, title):
    from morale.app import MainWindow
    shown = []
    monkeypatch.setattr(QMessageBox, 'information', lambda *a: shown.append(('info', a[1], a[2])))
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: shown.append(('warning', a[1], a[2])))
    label = {'pes': 'PES', 'dst': 'DST','jef':'JEF'}[extension]
    if extension == 'dst':
        # Simulate a writer fault: the reopened file is shifted by 2 mm.
        import morale.export_verify as module
        original = module.import_machine
        def shifted(p):
            result = original(p)
            for obj in result.project.objects:
                obj.x += 2
            return result
        monkeypatch.setattr(module, 'import_machine', shifted)
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(tmp_path / f'design.{extension}'), f'{label} (*.{extension})'))
    window = MainWindow()
    try:
        window.export()
        assert shown and shown[-1][1] == title
        assert ('Export verified' if extension in {'jef','pes'} else 'Export check found differences') in shown[-1][2]
    finally:
        window.saved = window.project.dumps(); window.close()


@pytest.mark.parametrize('fault',['incomplete','empty'])
def test_incomplete_path_comparison_cannot_verify_export(tmp_path,monkeypatch,fault):
    import morale.export_verify as module
    project=demo_project();blocks=generate(project);path=tmp_path/'partial.pes'
    export_machine(project,path,blocks)
    original=module.compare_commands
    def partial(source,decoded):
        report=original(source,decoded)
        metric=report['sewn_geometry']['decoded_outside_source']
        if fault=='incomplete':metric['complete']=False
        else:metric['samples']=0
        return report
    monkeypatch.setattr(module,'compare_commands',partial)
    result=verify_export(blocks,path)
    assert not result['verified']
    assert any('could not be established' in p for p in result['problems'])
    assert 'Export verified' not in verification_text(result,path.name)


def test_success_text_limits_its_claim(tmp_path):
    project=demo_project();blocks=generate(project);path=tmp_path/'sample.jef'
    export_machine(project,path,blocks)
    text=verification_text(verify_export(blocks,path),path.name)
    assert 'sampled geometry and count checks' in text
    assert 'do not verify stitch order, thread identity or physical machine behavior' in text
    assert 'matches the design' not in text


@pytest.mark.parametrize('command',['stop','trim'])
def test_lost_control_is_flagged_even_when_sewn_geometry_matches(monkeypatch,command):
    from types import SimpleNamespace
    from morale.engine import Block,Stitch
    import morale.export_verify as module
    source=[Block('test','#ff0000',[Stitch(0,0,'jump'),Stitch(1,0),Stitch(1,0,command),Stitch(2,0)])]
    decoded=[Block('test','#ff0000',[s for s in source[0].stitches if s.command!=command])]
    monkeypatch.setattr(module,'import_machine',lambda _:SimpleNamespace(project=None))
    monkeypatch.setattr(module,'generate',lambda _:decoded)
    result=verify_export(source,'unused.pes')
    assert not result['verified'] and result['bounds_delta_mm']==0
    assert result['source_stitches']==result['decoded_stitches']
    assert result['controls'][command]=={'source':1,'decoded':0}
    assert any(f'{command.title()} commands decreased' in p for p in result['problems'])


@pytest.mark.parametrize('extension',['pes','pec','u01','tbf','jef','vp3','xxx','exp','dst'])
def test_real_writer_control_round_trip_requires_review_for_pause_normalization(tmp_path,extension):
    from morale.model import Project,DesignObject
    project=Project(objects=[
        DesignObject(kind='path',stitch_type='running',width=10,height=2,
                     points=[[-.5,0],[.5,0]],trim_after=True,stop_after=True),
        DesignObject(kind='path',stitch_type='running',y=10,width=10,height=2,
                     points=[[-.5,0],[.5,0]])])
    blocks=generate(project);path=tmp_path/f'controls.{extension}'
    export_machine(project,path,blocks);result=verify_export(blocks,path)
    assert result['controls']['trim']['source']==1
    assert result['controls']['trim']['decoded']>=1
    if extension in {'vp3','xxx','exp','dst'}:
        # Current normalization is disclosed, not exempted from verification.
        assert result['controls']['stop']=={'source':1,'decoded':0}
        assert not result['verified']
        assert any('operator pauses as thread changes' in p for p in result['problems'])
    else:
        assert result['controls']['stop']=={'source':1,'decoded':1}
        assert result['verified']


@pytest.mark.parametrize('command',['stop','trim'])
def test_moved_control_with_equal_counts_and_geometry_is_flagged(monkeypatch,command):
    from types import SimpleNamespace
    from morale.engine import Block,Stitch
    import morale.export_verify as module
    source=[Block('test','#ff0000',[Stitch(0,0,'jump'),Stitch(1,0),Stitch(99,99,command),Stitch(3,0)])]
    decoded=[Block('test','#ff0000',[Stitch(0,0,'jump'),Stitch(1,0),Stitch(3,0),Stitch(99,99,command)])]
    monkeypatch.setattr(module,'import_machine',lambda _:SimpleNamespace(project=None))
    monkeypatch.setattr(module,'generate',lambda _:decoded)
    result=verify_export(source,'unused.pes')
    assert result['controls'][command]=={'source':1,'decoded':1}
    assert not result['verified'] and result['bounds_delta_mm']==0
    assert any(f'{command.title()} locations differ by up to 2.00 mm' in p for p in result['problems'])


def test_control_locations_follow_motion_across_blocks():
    from morale.engine import Block,Stitch
    from morale.export_verify import control_positions
    blocks=[Block('a','#ff0000',[Stitch(4,5,'jump')]),
            Block('b','#ff0000',[Stitch(99,99,'trim'),Stitch(0,0,'stop')])]
    assert control_positions(blocks)=={'trim':[(4,5)],'stop':[(4,5)]}


@pytest.mark.parametrize('command',['stop','trim'])
def test_added_controls_require_review_without_geometry_change(monkeypatch,command):
    from types import SimpleNamespace
    from morale.engine import Block,Stitch
    import morale.export_verify as module
    source=[Block('test','#ff0000',[Stitch(0,0,'jump'),Stitch(1,0),Stitch(2,0)])]
    decoded=[Block('test','#ff0000',[*source[0].stitches,Stitch(2,0,command)])]
    monkeypatch.setattr(module,'import_machine',lambda _:SimpleNamespace(project=None))
    monkeypatch.setattr(module,'generate',lambda _:decoded)
    result=verify_export(source,'unused.pes')
    assert result['controls'][command]=={'source':0,'decoded':1}
    assert not result['verified'] and result['bounds_delta_mm']==0
    assert any(f'{command.title()} commands increased' in p for p in result['problems'])


def test_dst_reader_interpretation_is_disclosed(tmp_path):
    project=demo_project();blocks=generate(project);path=tmp_path/'inferred.dst'
    export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert any('infers trims' in note for note in result['reader_notes'])
    assert 'not dedicated trim commands' in verification_text(result,path.name)


def test_same_location_controls_cannot_silently_swap_order(monkeypatch):
    from types import SimpleNamespace
    from morale.engine import Block,Stitch
    import morale.export_verify as module
    prefix=[Stitch(0,0,'jump'),Stitch(1,0)]
    source=[Block('test','#ff0000',[*prefix,Stitch(1,0,'stop'),Stitch(1,0,'trim'),Stitch(2,0)])]
    decoded=[Block('test','#ff0000',[*prefix,Stitch(1,0,'trim'),Stitch(1,0,'stop'),Stitch(2,0)])]
    monkeypatch.setattr(module,'import_machine',lambda _:SimpleNamespace(project=None))
    monkeypatch.setattr(module,'generate',lambda _:decoded)
    result=verify_export(source,'unused.pes')
    assert not result['verified'] and result['control_order_matches'] is False
    assert result['problems']==['Stop/trim order differs despite matching counts. Review the operator pause and cutting sequence before sewing.']


@pytest.mark.parametrize('extension',['pes','exp','dst','jef','pec','u01','xxx','vp3'])
def test_trim_after_color_change_preservation_and_remaining_loss(tmp_path,extension):
    from morale.model import Project,DesignObject
    first=DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#ff0000',
        stitch_data=[[0,0,'jump'],[.2,0,'stitch']])
    second=DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#0000ff',
        stitch_data=[[.2,0,'jump'],[.2,0,'trim'],[.3,0,'jump'],[.4,0,'stitch']])
    project=Project(objects=[first,second]);before=project.dumps();blocks=generate(project)
    path=tmp_path/f'boundary.{extension}';export_machine(project,path,blocks)
    report=verify_export(blocks,path)
    assert project.dumps()==before
    if extension=='vp3':
        from morale.formats import import_machine
        commands=[s.command for s in generate(import_machine(path).project)[1].stitches]
        assert commands.index('trim')<commands.index('stitch')
        assert report['controls']['trim']=={'source':1,'decoded':2}
        assert all('Trim commands increased' in p for p in report['problems'])
        return
    if extension in {'pes','pec','exp','dst','jef','u01','xxx'}:
        from morale.formats import import_machine
        reopened=generate(import_machine(path).project)
        commands=[s.command for s in reopened[1].stitches]
        assert commands.index('trim')<commands.index('stitch')
        assert report['decoded_stitches']==report['source_stitches']
        assert report['verified'] and not report['problems']
        return
    assert not report['verified'] and report['complete_path_comparison']
    assert any('Trim commands decreased: 1' in p for p in report['problems'])
    assert any('1 source trims occur after thread changes' in p for p in report['problems'])


def test_tbf_stationary_jumps_do_not_become_unrequested_cuts(tmp_path):
    from morale.model import Project,DesignObject
    from morale.formats import import_machine
    obj=DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,
        stitch_data=[[0,0,'jump'],[.1,0,'stitch'],[.1,0,'jump'],[.2,0,'stitch']])
    project=Project(objects=[obj]);blocks=generate(project)
    path=tmp_path/'stationary.tbf';export_machine(project,path,blocks)
    reopened=generate(import_machine(path).project)
    assert not any(s.command=='trim' for b in reopened for s in b.stitches)
    report=verify_export(blocks,path)
    assert report['verified'] and report['source_stitches']==report['decoded_stitches']


def test_tbf_boundary_trim_reordering_is_not_hidden_by_matching_counts(tmp_path):
    from morale.model import Project,DesignObject
    first=DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#ff0000',
        stitch_data=[[0,0,'jump'],[.2,0,'stitch']])
    second=DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#0000ff',
        stitch_data=[[.2,0,'jump'],[.2,0,'trim'],[.3,0,'jump'],[.4,0,'stitch']])
    project=Project(objects=[first,second]);blocks=generate(project)
    path=tmp_path/'order.tbf';export_machine(project,path,blocks)
    report=verify_export(blocks,path)
    assert report['controls']['trim']=={'source':1,'decoded':1}
    assert report['control_order_matches'] is True
    assert report['thread_control_order_matches'] is False and not report['verified']
    assert any('relative to thread changes' in p for p in report['problems'])


def test_success_text_reports_control_order_only_when_checked(tmp_path):
    project=demo_project();blocks=generate(project);path=tmp_path/'review.pes'
    export_machine(project,path,blocks);report=verify_export(blocks,path)
    assert report['verified'] and report['thread_control_order_matches'] is True
    assert 'Stop/trim sequence relative to thread changes: unchanged' in verification_text(report,path.name)
    del report['thread_control_order_matches']
    assert 'Stop/trim sequence relative to thread changes: unchanged' not in verification_text(report,path.name)
    assert 'physical machine behavior' in verification_text(report,path.name)


@pytest.mark.parametrize('intermediate',['pes','pec'])
def test_pes_stationary_jumps_do_not_multiply_trims_in_jef(tmp_path,intermediate):
    from morale.model import Project,DesignObject
    from morale.formats import import_machine
    first=DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#ff0000',
        stitch_data=[[0,0,'jump'],[.2,0,'stitch']])
    second=DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#0000ff',
        stitch_data=[[.2,0,'jump'],[.2,0,'trim'],[.3,0,'jump'],[.4,0,'stitch']])
    project=Project(objects=[first,second]);original=generate(project)
    path=tmp_path/f'intermediate.{intermediate}';export_machine(project,path,original)
    converted=import_machine(path).project;before=converted.dumps()
    output=tmp_path/'final.jef';export_machine(converted,output)
    report=verify_export(original,output)
    assert report['verified'] and report['thread_control_order_matches'] is True
    assert report['controls']['trim']=={'source':1,'decoded':1}
    assert converted.dumps()==before
