import struct
import pytest
from morale.catalogs import read_catalog
from morale.trace_threads import match_trace_threads
from morale.model import Project,DesignObject


def inf(records):
    body=b''
    for i,(rgb,description,chart) in enumerate(records):
        strings=description.encode()+b'\0'+chart.encode()+b'\0'
        body+=struct.pack('>HH',9+len(strings),i)+bytes(rgb)+struct.pack('>H',i+1)+strings
    return struct.pack('>4I',1,8,len(body)+4,len(records))+body


def test_inf_unicode_chart_and_matching(tmp_path):
    path=tmp_path/'threads.INF';path.write_bytes(inf([((255,0,0),'Rougé','Chart α'),((0,0,255),'Blue','Chart')]))
    entries=read_catalog(path)
    assert [e.color for e in entries]==['#ff0000','#0000ff']
    assert entries[0].metadata=={'description':'Rougé','chart':'Chart α'}
    source=Project(objects=[DesignObject(color='#f10000')]);before=source.dumps()
    result,report=match_trace_threads(source,str(path))
    assert source.dumps()==before and result.objects[0].color=='#ff0000'
    assert result.objects[0].thread['chart']=='Chart α' and report[0]['catalog']==path.name


def test_edr_retains_order_and_duplicates(tmp_path):
    path=tmp_path/'threads.edr';path.write_bytes(bytes([255,0,0,0,0,0,255,0,255,0,0,0]))
    assert [e.color for e in read_catalog(path)]==['#ff0000','#0000ff','#ff0000']


@pytest.mark.parametrize('data',[b'',b'\x01',b'12345',b'0000'*10001])
def test_invalid_edr_rejected(tmp_path,data):
    path=tmp_path/'bad.edr';path.write_bytes(data)
    with pytest.raises(ValueError):read_catalog(path)


@pytest.mark.parametrize('mutation',['truncate','extra','count','length','utf8'])
def test_invalid_inf_rejected(tmp_path,mutation):
    data=bytearray(inf([((1,2,3),'Red','Chart')]))
    if mutation=='truncate':data=data[:-1]
    if mutation=='extra':data+=b'X'
    if mutation=='count':data[12:16]=struct.pack('>I',10001)
    if mutation=='length':data[16:18]=b'\0\1'
    if mutation=='utf8':data[25]=255
    path=tmp_path/'bad.inf';path.write_bytes(data)
    with pytest.raises(ValueError):read_catalog(path)


def test_matches_installed_inf_writer_for_ascii(tmp_path):
    import pyembroidery as emb
    path=tmp_path/'palette.inf';pattern=emb.EmbPattern()
    thread=emb.EmbThread();thread.set_color(0x12,0x34,0x56);thread.description='Sample';thread.chart='Chart';pattern.add_thread(thread)
    emb.write(pattern,str(path))
    assert read_catalog(path)[0].color=='#123456'
    assert read_catalog(path)[0].metadata=={'description':'Sample','chart':'Chart'}


@pytest.mark.parametrize('extension',['inf','edr'])
def test_native_palette_import_selection_and_chart_display(tmp_path,monkeypatch,extension):
    from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
    from PySide6.QtCore import Qt
    from morale.catalog_dialog import CatalogDialog
    app=QApplication.instance() or QApplication([])
    path=tmp_path/f'threads.{extension}'
    path.write_bytes(inf([((255,0,0),'Rougé','Chart α')]) if extension=='inf' else bytes([255,0,0,0]))
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:(str(path),''))
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:pytest.fail(str(args)))
    dialog=CatalogDialog('#ff0000',1)
    try:
        dialog.load_csv()
        assert dialog.model.rowCount()==1 and dialog.model.columnCount()==6
        assert dialog.model.headerData(4,Qt.Orientation.Horizontal)=='Chart'
        assert dialog.model.data(dialog.model.index(0,4),Qt.ItemDataRole.DisplayRole)==('Chart α' if extension=='inf' else '')
        if extension=='inf':dialog.search.setText('Chart α');assert dialog.model.rowCount()==1
        dialog.assign()
        assert dialog.entry.color=='#ff0000'
        if extension=='inf':assert dialog.entry.metadata['chart']=='Chart α'
    finally:dialog.reject()


@pytest.mark.parametrize('extension',['inf','edr'])
def test_palette_export_order_duplicates_and_unicode(tmp_path,extension):
    from morale.catalogs import ThreadEntry
    from morale.thread_palette_files import write_palette
    entries=[ThreadEntry('#ff0000',{'description':'Rougé','chart':'Chart α','brand':'Not encoded'}),ThreadEntry('#0000ff',{}),ThreadEntry('#ff0000',{})]
    path=tmp_path/f'palette.{extension}';result=write_palette(path,entries);restored=read_catalog(path)
    assert [e.color for e in restored]==[e.color for e in entries]
    assert result['colors']==3
    assert restored[0].metadata==({'description':'Rougé','chart':'Chart α'} if extension=='inf' else {})
    if extension=='inf':
        import pyembroidery as emb
        decoded=emb.read(str(path))
        assert len(decoded.threadlist)==3 and decoded.threadlist[0].description=='Rougé'
        assert decoded.threadlist[0].chart=='Chart α'


def test_invalid_export_preserves_destination(tmp_path):
    from morale.catalogs import ThreadEntry
    from morale.thread_palette_files import write_palette
    path=tmp_path/'palette.inf';path.write_bytes(b'original')
    with pytest.raises(ValueError):write_palette(path,[ThreadEntry('#ff0000',{'description':'bad\0name'})])
    assert path.read_bytes()==b'original'
    with pytest.raises(ValueError):write_palette(tmp_path/'source.pes',[ThreadEntry('#ff0000',{})])
    assert not (tmp_path/'source.pes').exists()


def test_native_export_uses_filtered_display_order(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
    from morale.catalog_dialog import CatalogDialog
    app=QApplication.instance() or QApplication([])
    path=tmp_path/'selected.edr';messages=[]
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(path),'EDR (*.edr)'))
    monkeypatch.setattr(QMessageBox,'information',lambda *args:messages.append(args[-1]))
    dialog=CatalogDialog('#0000ff',1)
    try:
        dialog.search.setText('blue');expected=[entry.color for _,entry in dialog.model.rows]
        dialog.export_palette()
        assert [entry.color for entry in read_catalog(path)]==expected
        assert messages and 'metadata omitted' in messages[-1]
    finally:dialog.reject()
