import json
import tempfile
from pathlib import Path
import pytest
from PySide6.QtCore import QProcess
from PySide6.QtGui import QImage
from morale.library import read_preview_result,PreviewRunner


def output(root):
    info={'name':'Preview','stitches':5,'colors':1,'width':10.,'height':5.,'size':42,'mtime_ns':123,'notes':[]}
    (root/'preview.json').write_text(json.dumps(info))
    image=QImage(16,16,QImage.Format.Format_RGB32);image.fill(0);image.save(str(root/'preview.png'))
    return info

def test_valid_result_retains_trace_extension_fields(tmp_path):
    info=output(tmp_path);info['project']='extra';info['density_png']='extra'
    (tmp_path/'preview.json').write_text(json.dumps(info))
    result,image=read_preview_result(tmp_path)
    assert result==info and not image.isNull()

@pytest.mark.parametrize('key,value',[('name',None),('name','x'*201),('stitches',True),('stitches',250001),('colors',-1),('width',float('nan')),('height',float('inf')),('width',10**400),('width',True),('size',-1),('mtime_ns','123'),('notes','text'),('notes',[None])])
def test_invalid_metadata_rejected(tmp_path,key,value):
    info=output(tmp_path);info[key]=value;(tmp_path/'preview.json').write_text(json.dumps(info))
    with pytest.raises(ValueError):read_preview_result(tmp_path)

@pytest.mark.parametrize('data',['[]','null','{invalid'])
def test_invalid_document_rejected(tmp_path,data):
    output(tmp_path);(tmp_path/'preview.json').write_text(data)
    with pytest.raises(ValueError):read_preview_result(tmp_path)

def test_excessive_json_nesting_is_a_normal_preview_error(tmp_path):
    output(tmp_path);(tmp_path/'preview.json').write_text('['*2000+'0'+']'*2000)
    with pytest.raises(ValueError):read_preview_result(tmp_path)

@pytest.mark.parametrize('filename,size',[('preview.json',64_000_001),('preview.png',8_000_001)])
def test_oversized_files_rejected_before_parsing(tmp_path,filename,size):
    output(tmp_path)
    with (tmp_path/filename).open('wb') as stream:stream.truncate(size)
    with pytest.raises(ValueError,match='exceeds'):read_preview_result(tmp_path)

def test_large_or_corrupt_image_rejected(tmp_path):
    output(tmp_path)
    image=QImage(2049,2,QImage.Format.Format_RGB32);image.fill(0);image.save(str(tmp_path/'preview.png'))
    with pytest.raises(ValueError,match='2048'):read_preview_result(tmp_path)
    (tmp_path/'preview.png').write_bytes(b'not an image')
    with pytest.raises(ValueError):read_preview_result(tmp_path)

def test_invalid_result_emits_failure_and_cleans_temporary_directory(tmp_path):
    runner=PreviewRunner();runner.path=str(tmp_path/'source.morale')
    runner.directory=tempfile.TemporaryDirectory();root=Path(runner.directory.name)
    info=output(root);info.pop('width');(root/'preview.json').write_text(json.dumps(info))
    failed=[];ready=[];runner.failed.connect(lambda *args:failed.append(args));runner.ready.connect(lambda *args:ready.append(args))
    runner.finished(0,QProcess.ExitStatus.NormalExit)
    assert len(failed)==1 and not ready and not root.exists() and runner.path is None
