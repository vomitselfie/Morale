import pytest
from morale import file_matrix
from morale.model import Project,DesignObject
from morale.formats import export_machine


def test_file_matrix_checks_both_generations_and_preserves_source(tmp_path,monkeypatch):
    monkeypatch.setattr(file_matrix,'EXPORT_FORMATS',{'.pes','.exp'})
    source=tmp_path/'source.pes';export_machine(Project(objects=[DesignObject(kind='rectangle',width=5,height=5)]),source)
    before=source.read_bytes();root=tmp_path/'probe';report=file_matrix.build_report(source,root)
    assert source.read_bytes()==before and not (root/'INCOMPLETE.txt').exists()
    assert report['summary']['pairs']==4 and len(report['first_exports'])==2
    assert all('against_original' in r and 'against_intermediate' in r for r in report['conversions'].values())
    with pytest.raises(FileExistsError):file_matrix.build_report(source,root)


def test_failed_intermediate_marks_every_dependent_pair(tmp_path,monkeypatch):
    monkeypatch.setattr(file_matrix,'EXPORT_FORMATS',{'.pes','.exp'})
    source=tmp_path/'source.pes';export_machine(Project(objects=[DesignObject()]),source)
    def fail(*args):raise ValueError('writer failed')
    monkeypatch.setattr(file_matrix,'export_machine',fail)
    report=file_matrix.build_report(source,tmp_path/'probe')
    assert len(report['conversions'])==4 and all('Intermediate failed' in r['error'] for r in report['conversions'].values())


def test_review_sheet_distinguishes_inherited_loss_and_execution_error(tmp_path):
    import csv
    report={'conversions':{'.pes->.exp':{'against_intermediate':{'verified':True,'problems':[]},
        'against_original':{'verified':False,'problems':['Trim moved, before change']}},
        '.pes->.jef':{'error':'=untrusted error'}}}
    path=tmp_path/'review.csv';file_matrix.write_review_csv(report,path)
    with path.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    assert rows[0]['Against intermediate']=='Passed software checks'
    assert rows[0]['Against original']=='Review required'
    assert rows[0]['Original findings']=='Trim moved, before change'
    assert rows[1]['Against original']=='Not completed'
    assert rows[1]['Execution error']=="'=untrusted error"
    assert all(row['Physical validation']=='Not verified' for row in rows)
    with pytest.raises(FileExistsError):file_matrix.write_review_csv(report,path)
