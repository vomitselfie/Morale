import csv,json,shutil,subprocess,zipfile
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import DesignObject,Project
from morale.stitch_edit import manual_object
from morale.engine import generate
from morale.hoop_bundle import build_bundle,save_archive


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def source():return Project(objects=[manual_object(DesignObject(),[[-50,0,'jump'],[50,0,'stitch']])])


@pytest.mark.parametrize('registration',[False,True])
def test_per_placement_export_counts_match_native_tiles_and_archive(tmp_path,registration):
    project=source();before=project.dumps();root=tmp_path/'bundle'
    manifest=build_bundle(project,root,dict(width=40,height=40,margin=5,registration=registration,extension='.dst'))
    assert project.dumps()==before and any(t['export_preparation']['subdivision_added_stitches']>0 for t in manifest['tiles'])
    with (root/'placements.csv').open(newline='') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==len(manifest['tiles'])
    for tile,row in zip(manifest['tiles'],rows):
        native=Project.loads((root/tile['project']).read_text());count=sum(s.command=='stitch' for b in generate(native) for s in b.stitches)
        preparation=tile['export_preparation']
        assert count==tile['stitches']==preparation['source_stitches']==int(row['Native stitches'])
        assert int(row['Prepared stitches'])==count+int(row['Added needle positions'])==preparation['prepared_stitches']
        assert row['Machine file']==tile['machine'] and (root/row['Machine file']).exists()
    target=tmp_path/'placements.zip';save_archive(root,target)
    with zipfile.ZipFile(target) as archive:
        assert 'placements.csv' in archive.namelist()
        assert json.loads(archive.read('plan.json'))['tiles'][0]['export_preparation']==manifest['tiles'][0]['export_preparation']
    if shutil.which('pdftotext'):
        text=subprocess.check_output(['pdftotext',str(root/'placement.pdf'),'-'],text=True)
        assert 'prepared (+' in text and 'counts include alignment marks' in text


def test_native_only_bundle_keeps_machine_counts_empty(tmp_path):
    manifest=build_bundle(source(),tmp_path,dict(width=40,height=40,margin=5,registration=False))
    assert all(tile['export_preparation'] is None for tile in manifest['tiles'])
    with (tmp_path/'placements.csv').open(newline='') as stream:rows=list(csv.DictReader(stream))
    assert rows and all(row['Prepared stitches']==row['Added needle positions']==row['Machine file']=='' for row in rows)
