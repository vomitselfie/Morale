import json
import pytest
from PySide6.QtWidgets import QApplication
from morale import coupons
from morale.embroidery_fonts import available_fonts
from morale.engine import generate
from morale.formats import import_machine


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def names():
    # The lettering coupon needs the bundled embroidery fonts.
    return [n for n in coupons.COUPONS if n != 'lettering' or available_fonts()]


@pytest.mark.parametrize('name', names())
def test_coupon_fits_the_field_and_keeps_clear_of_the_scale_square(name):
    project, tests, title, guidance = coupons.build_project(name)
    assert title and guidance and tests
    x0, y0 = coupons.SCALE_CORNER
    for block in generate(project):
        obj = next(o for o in project.objects if o.id == block.object_id)
        for s in block.stitches:
            if s.command != 'stitch':
                continue
            assert -50 <= s.x <= 50 and -50 <= s.y <= 50, (name, obj.name)
            if not obj.name.startswith('Scale'):
                inside = x0 - .5 <= s.x <= x0 + 10.5 and y0 - .5 <= s.y <= y0 + 10.5
                assert not inside, (name, obj.name)
    assert len({o.color for o in project.objects}) == 1


def test_coupon_folder_has_machine_files_templates_and_every_test_object(tmp_path):
    report = coupons.build_coupon('satin-width', tmp_path / 'satin-width')
    root = tmp_path / 'satin-width'
    assert not (root/'INCOMPLETE.txt').exists()
    for name in ('satin-width.pes', 'satin-width-v1.pes', 'satin-width.exp', 'satin-width.dst', 'satin-width.morale',
                 'placement.pdf', 'thread-chart.csv', 'metadata.json', 'evaluation.json', 'README.txt'):
        assert (root / name).stat().st_size > 0, name
    evaluation = json.loads((root / 'evaluation.json').read_text())
    widths = sorted({o['target']['width_mm'] for o in evaluation['objects']})
    assert widths == sorted(set(coupons.SATIN_WIDTHS)) and all(o['status'] is None for o in evaluation['objects'])
    metadata = json.loads((root / 'metadata.json').read_text())
    assert metadata['design'] == 'satin-width.morale' and {'machine', 'fabric', 'stabilizer', 'upper_thread'} <= set(metadata)
    decoded = [s for b in generate(import_machine(root / 'satin-width.pes').project) for s in b.stitches if s.command == 'stitch']
    assert len(decoded) >= report['stitches']
    with pytest.raises(FileExistsError):
        coupons.build_coupon('satin-width', root)


def test_stitch_length_coupon_uses_exact_spans():
    project, tests, _, _ = coupons.build_project('stitch-length')
    for obj, target in tests:
        stitches = [s for s in generate(__import__('morale.model', fromlist=['Project']).Project(objects=[obj]))[0].stitches if s.command == 'stitch']
        spans = [((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** .5 for a, b in zip(stitches, stitches[1:])]
        assert spans and all(abs(span - target['stitch_length_mm']) < .01 for span in spans)


def test_coupon_records_actual_export_checks_and_hashes(tmp_path):
    import hashlib
    from morale.export_verify import verify_export
    from morale.model import Project
    root=tmp_path/'verified'
    report=coupons.build_coupon('stitch-length',root)
    blocks=generate(Project.loads((root/'stitch-length.morale').read_text()))
    saved=json.loads((root/'report.json').read_text())
    assert saved==report and not report['physical_sewouts']
    assert set(report['export_verification'])==set(report['files'])
    readme=(root/'README.txt').read_text()
    for filename in report['files']:
        result=report['export_verification'][filename]
        assert result==verify_export(blocks,root/filename)
        assert result['complete_path_comparison']
        assert report['exports_sha256'][filename]==hashlib.sha256((root/filename).read_bytes()).hexdigest()
        assert all(problem in readme for problem in result['problems'])


def test_branch_coupon_uses_one_thread_run_and_pes_v1_has_no_added_stop(tmp_path):
    from morale.thread_palette_files import design_palette
    project,_,_,_=coupons.build_project('branch-joins')
    assert len(design_palette(generate(project)))==1
    report=coupons.build_coupon('branch-joins',tmp_path/'branch')
    for name in ('branch-joins.pes','branch-joins-v1.pes'):
        result=report['export_verification'][name]
        assert result['verified'],result['problems']
        assert result['thread_changes']==0
        assert result['controls']['stop']=={'source':0,'decoded':0}


@pytest.mark.parametrize('strict',[False,True])
def test_coupon_cli_reports_review_and_optional_failure(tmp_path,strict):
    import os
    import subprocess
    import sys
    root=tmp_path/'cli'
    command=[sys.executable,'-m','morale.coupons','--output',str(root),'--coupon','stitch-length']
    if strict:command.append('--require-verification')
    result=subprocess.run(command,env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),capture_output=True,text=True,timeout=60)
    assert result.returncode==(1 if strict else 0),result.stderr
    assert 'stitch-length.dst: REVIEW NEEDED' in result.stdout
    assert 'Trim commands increased' in result.stdout
    assert 'stitch-length.pes: CHECKS PASSED' in result.stdout
    assert (root/'stitch-length/stitch-length.dst').stat().st_size>0
    assert (root/'stitch-length/evaluation.json').is_file()


def test_fabric_coupon_evaluation_matches_saved_stitch_settings(tmp_path):
    from morale.model import Project
    from morale.fabric import PROFILES
    root=tmp_path/'fabric'
    report=coupons.build_coupon('fabric-profiles',root)
    project=Project.loads((root/'fabric-profiles.morale').read_text())
    evaluation=json.loads((root/'evaluation.json').read_text())
    records=evaluation['objects']
    assert len(records)==6
    assert {record['target']['profile'] for record in records}==set(PROFILES)
    by_name={obj.name:obj for obj in project.objects}
    for record in records:
        obj=by_name[record['object']];target=record['target']
        assert record['status'] is None and record['measured']=={}
        assert target['stitch_type']==obj.stitch_type
        assert target['spacing_mm']==obj.spacing
        assert target['pull_compensation_per_side_mm']==obj.pull_compensation
        assert target['underlay_style']==obj.underlay_style
        assert target['underlay_inset_mm']==obj.underlay_inset
        assert target['underlay_spacing_mm']==obj.underlay_spacing
        assert obj.width==pytest.approx(target['nominal_width_mm'])
        assert obj.height==pytest.approx(target['nominal_height_mm'])
    assert not report['physical_sewouts']
    for filename,verification in report['export_verification'].items():
        assert verification['complete_path_comparison'],filename
        assert verification['bounds_delta_mm']<=.3,filename
        if filename.endswith('.dst'):
            assert all(issue.startswith('Trim commands increased:') for issue in verification['problems'])
        else:assert not verification['problems'],(filename,verification)


def test_native_fabric_sampler_respects_discard_and_loads_editable_project(monkeypatch):
    from morale.app import MainWindow
    from morale.model import Project
    window=MainWindow()
    try:
        before=window.project.dumps()
        monkeypatch.setattr(window,'confirm_discard',lambda:False)
        window.load_fabric_sample()
        assert window.project.dumps()==before
        monkeypatch.setattr(window,'confirm_discard',lambda:True)
        window.load_fabric_sample()
        assert window.project.name=='Morale coupon: Fabric profile comparison'
        assert len(window.project.objects)==9
        assert window.project.hoop_width==window.project.hoop_height==100
        assert all(obj.kind!='stitches' for obj in window.project.objects)
        assert generate(Project.loads(window.project.dumps()))==generate(window.project)
        assert 'not isolated variables' in window.statusBar().currentMessage()
    finally:window.saved=window.project.dumps();window.close()


def test_native_coupon_picker_lists_all_designs_and_handles_cancel(monkeypatch):
    from morale.app import MainWindow
    from PySide6.QtWidgets import QInputDialog
    window=MainWindow();seen=[]
    try:
        before=window.project.dumps()
        def cancel(parent,title,label,items,*args):
            seen.extend(items);return '',False
        monkeypatch.setattr(QInputDialog,'getItem',cancel)
        window.choose_sewout_coupon()
        assert len(seen)==len(coupons.COUPONS)
        assert 'Fill density' in seen and 'Lettering' in seen
        assert window.project.dumps()==before
        monkeypatch.setattr(QInputDialog,'getItem',lambda *args:('Fill density',True))
        monkeypatch.setattr(window,'confirm_discard',lambda:True)
        window.choose_sewout_coupon()
        expected,_,_,_=coupons.build_project('fill-density')
        assert window.project.name==expected.name
        assert [obj.spacing for obj in window.project.objects]==[obj.spacing for obj in expected.objects]
        assert generate(window.project)
    finally:window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('failure',['incomplete','replace'])
def test_evaluation_pdf_failure_preserves_existing_sheet(tmp_path,monkeypatch,failure):
    path=tmp_path/'evaluation.pdf';path.write_bytes(b'original sheet')
    if failure=='incomplete':
        monkeypatch.setattr(coupons,'_render_evaluation_pdf',lambda target,*args:target.write_bytes(b'%PDF-incomplete'))
    else:
        def fail(*args):raise OSError('replacement failed')
        monkeypatch.setattr(coupons.os,'replace',fail)
    with pytest.raises(OSError):coupons.evaluation_pdf(path,'Test',[],'Guidance')
    assert path.read_bytes()==b'original sheet'
    assert list(tmp_path.iterdir())==[path]


def test_evaluation_pdf_is_complete(tmp_path):
    path=tmp_path/'evaluation.pdf'
    _,samples,title,guidance=coupons.build_project('fabric-profiles')
    coupons.evaluation_pdf(path,title,samples,guidance)
    data=path.read_bytes()
    assert data.startswith(b'%PDF-') and b'%%EOF' in data[-1024:]


def test_current_design_worksheet_uses_edits_and_omits_hidden_objects(tmp_path,monkeypatch):
    from morale.model import Project,DesignObject
    from morale.app import MainWindow
    from PySide6.QtWidgets import QFileDialog
    window=MainWindow();captured=[]
    try:
        obj=DesignObject(name='Adjusted fill',spacing=.72,pull_compensation=.31)
        window.replace_project(Project(objects=[obj,DesignObject(visible=False)]))
        before=window.project.dumps()
        monkeypatch.setattr(window,'preview_available',lambda:True)
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(tmp_path/'worksheet'),''))
        monkeypatch.setattr(coupons,'evaluation_pdf',lambda *args:captured.append(args))
        window.export_sewout_worksheet()
        path,title,rows,guidance=captured[0]
        assert str(path).endswith('worksheet.pdf') and len(rows)==1
        assert rows[0][1]['spacing_mm']==.72
        assert rows[0][1]['pull_compensation_per_side_mm']==.31
        assert rows[0][1]['object_id']==obj.id
        import hashlib
        assert hashlib.sha256(before.encode()).hexdigest() in guidance
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


def test_evaluation_page_failure_preserves_existing_sheet(tmp_path,monkeypatch):
    from PySide6.QtGui import QPdfWriter
    path=tmp_path/'sheet.pdf';path.write_bytes(b'previous worksheet')
    _,samples,title,guidance=coupons.build_project('fabric-profiles')
    monkeypatch.setattr(QPdfWriter,'newPage',lambda self:False)
    with pytest.raises(OSError,match='evaluation page'):
        coupons.evaluation_pdf(path,title,samples,guidance)
    assert path.read_bytes()==b'previous worksheet'
    assert list(tmp_path.iterdir())==[path]


def test_oversized_evaluation_heading_is_rejected_cleanly(tmp_path):
    path=tmp_path/'sheet.pdf';path.write_bytes(b'previous worksheet')
    with pytest.raises(ValueError,match='title is too long'):
        coupons.evaluation_pdf(path,'Long title '*1000,[],'Notes')
    assert path.read_bytes()==b'previous worksheet'
    assert list(tmp_path.iterdir())==[path]


def test_worksheet_records_compensated_generated_dimensions(tmp_path,monkeypatch):
    from morale.model import Project,DesignObject
    obj=DesignObject(kind='rectangle',width=20,height=10,angle=0,underlay=False,pull_compensation=.3)
    project=Project(objects=[obj]);captured=[]
    monkeypatch.setattr(coupons,'evaluation_pdf',lambda *args:captured.append(args))
    coupons.project_evaluation_pdf(project,tmp_path/'sheet.pdf')
    target=captured[0][2][0][1]
    stitches=[s for block in generate(project) for s in block.stitches if s.command=='stitch']
    assert target['width_mm']==20
    assert target['generated_width_mm']==pytest.approx(20.6)
    assert target['generated_height_mm']==pytest.approx(round(max(s.y for s in stitches)-min(s.y for s in stitches),4))
    assert target['needle_penetrations']==len(stitches)
    assert target['stitch_length_mm']==obj.stitch_length


def test_worksheet_records_variable_density_and_fill_direction(tmp_path,monkeypatch):
    from morale.model import Project,DesignObject
    obj=DesignObject(kind='rectangle',spacing=.4,angle=27,density_gradient=True,gradient_end_spacing=1.2,gradient_reverse=True)
    captured=[]
    monkeypatch.setattr(coupons,'evaluation_pdf',lambda *args:captured.append(args))
    coupons.project_evaluation_pdf(Project(objects=[obj]),tmp_path/'sheet.pdf')
    target=captured[0][2][0][1]
    assert target['spacing_mm']==.4 and target['gradient_end_spacing_mm']==1.2
    assert target['gradient_reverse'] is True and target['fill_angle_degrees']==27


def test_ripple_coupon_records_actual_settings_and_exports(tmp_path):
    project,tests,_,_=coupons.build_project('ripple-spacing')
    assert len(tests)==6
    actual={obj.id:obj for obj in project.objects}
    assert {(t['spacing_mm'],t['ripple_center_x_percent']) for _,t in tests}=={(s,x) for s in (.5,1,2) for x in (0,-60)}
    for source,target in tests:
        obj=actual[source.id]
        assert obj.spacing==target['spacing_mm'] and obj.ripple_center_x==target['ripple_center_x_percent']
        assert obj.minimum_stitch==target['minimum_stitch_mm'] and not obj.underlay
        assert len(obj.contours)==2 and obj.width==obj.height==20
    report=coupons.build_coupon('ripple-spacing',tmp_path/'ripple')
    assert not report['physical_sewouts']
    for filename,result in report['export_verification'].items():
        assert result['complete_path_comparison'] and result['bounds_delta_mm']<=.3,result
        if filename.endswith('.dst'):
            assert all(issue.startswith('Trim commands increased:') for issue in result['problems']),result
        else:assert not result['problems'],result
    evaluation=json.loads((tmp_path/'ripple/evaluation.json').read_text())
    assert len(evaluation['objects'])==6 and all(o['status'] is None for o in evaluation['objects'])


def test_native_pack_export_keeps_design_and_existing_results(tmp_path,monkeypatch):
    from morale.app import MainWindow
    from PySide6.QtWidgets import QInputDialog,QFileDialog,QMessageBox
    window=MainWindow();messages=[];errors=[]
    try:
        before=window.project.dumps();saved=window.saved
        monkeypatch.setattr(QInputDialog,'getItem',lambda *a:('Ripple spacing',True))
        monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a:str(tmp_path))
        monkeypatch.setattr(QMessageBox,'exec',lambda box:messages.append((box.informativeText(),box.detailedText())))
        monkeypatch.setattr(window,'error',errors.append)
        window.export_sewout_coupon_pack()
        assert window.project.dumps()==before and window.saved==saved
        root=tmp_path/'ripple-spacing'
        assert (root/'evaluation.pdf').is_file() and (root/'ripple-spacing.pes').is_file()
        assert messages and 'Export verified: ripple-spacing.pes' in messages[0][1]
        marker=root/'physical-results.txt';marker.write_text('keep these measurements')
        window.export_sewout_coupon_pack()
        assert len(messages)==1 and len(errors)==1
        assert marker.read_text()=='keep these measurements'
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('cancel_at',['coupon','folder'])
def test_native_pack_cancel_creates_nothing(tmp_path,monkeypatch,cancel_at):
    from morale.app import MainWindow
    from PySide6.QtWidgets import QInputDialog,QFileDialog
    window=MainWindow()
    try:
        before=window.project.dumps()
        monkeypatch.setattr(QInputDialog,'getItem',lambda *a:('Ripple spacing',cancel_at!='coupon'))
        monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a:'')
        monkeypatch.setattr(coupons,'build_coupon',lambda *a:pytest.fail('Cancelled export built a pack'))
        window.export_sewout_coupon_pack()
        assert window.project.dumps()==before and not list(tmp_path.iterdir())
    finally:window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('failure',['generation','machine','pdf'])
def test_interrupted_pack_is_explicitly_marked_incomplete(tmp_path,monkeypatch,failure):
    def fail(*args,**kwargs):raise OSError('simulated export failure')
    monkeypatch.setattr(coupons,{'generation':'generate','machine':'export_machine','pdf':'evaluation_pdf'}[failure],fail)
    root=tmp_path/'failed'
    with pytest.raises(OSError,match='simulated'):coupons.build_coupon('ripple-spacing',root)
    assert 'Do not use' in (root/'INCOMPLETE.txt').read_text()
    with pytest.raises(FileExistsError):coupons.build_coupon('ripple-spacing',root)


def test_unknown_coupon_does_not_create_directory(tmp_path):
    with pytest.raises(ValueError,match='Unknown'):coupons.build_coupon('unknown',tmp_path/'unknown')
    assert not (tmp_path/'unknown').exists()
