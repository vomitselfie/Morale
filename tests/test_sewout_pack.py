import json
import pytest
from PySide6.QtWidgets import QApplication
from morale.sewout_pack import build_pack
from morale.formats import import_machine
from morale.model import Project
from morale.engine import generate


@pytest.fixture(scope='module')
def pack(tmp_path_factory):
    QApplication.instance() or QApplication([])
    root=tmp_path_factory.mktemp('sewout')/'pack'
    return root,build_pack(root)


def test_every_cell_splits_and_overlapped_cells_overlap_every_join(pack):
    _,report=pack
    assert len(report['cells'])==9 and not report['physical_sewouts'] and not report['machine_validated']
    for cell in report['cells']:
        assert cell['pieces']>=2 and cell['joins']>=1,cell
        assert cell['overlapped_joins']==(cell['joins'] if cell['join_overlap_mm'] else 0),cell
        assert 'satin' in cell['stitch_types'] and 'running' not in cell['stitch_types'],cell
    assert {c['join_overlap_mm'] for c in report['cells'] if c['shape']=='Y'}=={0,.3,.6}


def test_design_fits_a_100mm_hoop_with_margin(pack):
    root,report=pack
    left,top,right,bottom=report['sewn_bounds_mm']
    assert -47<=left and right<=47 and -47<=top and bottom<=47
    project=Project.loads((root/'branch-sewout.morale').read_text())
    assert len({o.color for o in project.objects})==1 and project.hoop_width==project.hoop_height==100


@pytest.mark.parametrize('name',['branch-sewout.pes','branch-sewout-v1.pes','branch-sewout.exp','branch-sewout.dst'])
def test_machine_files_reopen_with_matching_stitch_counts(pack,name):
    root,report=pack
    decoded=[s for b in generate(import_machine(root/name).project) for s in b.stitches if s.command=='stitch']
    # Writers can add needle positions for long spans or ties; nothing may be lost.
    assert report['stitches']<=len(decoded)<=report['stitches']*1.05


def test_pack_includes_instructions_and_refuses_existing_folder(pack):
    root,_=pack
    for name in ('README.txt','placement.pdf','thread-chart.csv','report.json'):assert (root/name).stat().st_size>0
    readme=(root/'README.txt').read_text()
    assert 'has not been sewn before' in readme and 'A1' in readme and 'C3' in readme
    assert json.loads((root/'report.json').read_text())['design']=='Branch join sew-out'
    with pytest.raises(FileExistsError):build_pack(root)
