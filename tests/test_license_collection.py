import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

spec=importlib.util.spec_from_file_location('morale_license_collection',Path(__file__).parents[1]/'packaging/collect_licenses.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_license_collection_retains_exact_text_version_and_gaps(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();(source/'LICENSE').write_bytes(b'Example license\r\n')
    (source/'code.py').write_text('not a license')
    monkeypatch.setattr(module,'PACKAGES',('available','empty','missing'))
    def distribution(name):
        if name=='missing':raise module.PackageNotFoundError(name)
        return SimpleNamespace(version='1.2.3',files=['LICENSE','code.py'] if name=='available' else [],locate_file=lambda p:source/p)
    monkeypatch.setattr(module,'distribution',distribution)
    root=tmp_path/'licenses';report=module.collect(root,prefix=tmp_path/'no-conda')
    assert report==json.loads((root/'manifest.json').read_text())
    assert not report['release_compliance_verified']
    first,empty,missing=report['packages']
    assert first['version']=='1.2.3' and first['status']=='texts_collected' and len(first['files'])==1
    copied=root/first['files'][0]['path'];assert copied.read_bytes()==b'Example license\r\n'
    assert first['files'][0]['sha256']==hashlib.sha256(copied.read_bytes()).hexdigest()
    assert empty['status']=='license_text_missing' and missing['status']=='metadata_unavailable'
    with pytest.raises(FileExistsError):module.collect(root)



def test_conda_cache_licenses_keep_version_and_provenance(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'PACKAGES',())
    prefix=tmp_path/'env';metadata=prefix/'conda-meta';metadata.mkdir(parents=True)
    cache=tmp_path/'cache';licenses=cache/'info/licenses/LICENSES';licenses.mkdir(parents=True)
    (licenses/'LGPL.txt').write_bytes(b'upstream license text')
    (metadata/'qt.json').write_text(json.dumps({'name':'qt6-main','version':'6.11.2','build':'example',
        'license':'LGPL-3.0-only','link':{'source':str(cache)}}))
    (metadata/'python.json').write_text(json.dumps({'name':'python','version':'3.12','link':{'source':str(tmp_path/'missing')}}))
    root=tmp_path/'out';report=module.collect(root,prefix)
    records={r['package']:r for r in report['packages']}
    qt=records['qt6-main']
    assert qt['version']=='6.11.2' and qt['provenance']=='conda-package-cache'
    assert qt['declared_license']=='LGPL-3.0-only' and qt['status']=='texts_collected'
    assert (root/qt['files'][0]['path']).read_bytes()==b'upstream license text'
    assert records['python']['status']=='license_text_missing'


@pytest.mark.parametrize('damage',[None,'license','font','dependency','escape','omitted_package','omitted_file','changed_version','missing_manifest'])
def test_bundle_notice_integrity_detects_missing_or_changed_files(tmp_path,damage):
    spec=importlib.util.spec_from_file_location('check_notices',Path(__file__).parents[1]/'packaging/check_notices.py')
    check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
    source=tmp_path/'source';bundle=tmp_path/'bundle'
    for root in (source,bundle):
        root.mkdir();(root/'LICENSE').write_text('GPL text');(root/'THIRD_PARTY_NOTICES.md').write_text('notices')
        fonts=root/'morale/fonts/example';fonts.mkdir(parents=True);(fonts/'LICENSE').write_text('font license')
    collected=bundle/'dependency-licenses';collected.mkdir();(collected/'LICENSE').write_bytes(b'dependency')
    item={'path':'LICENSE','sha256':hashlib.sha256(b'dependency').hexdigest()}
    if damage=='escape':item['path']='../LICENSE'
    (collected/'manifest.json').write_text(json.dumps({'packages':[{'package':'example','status':'texts_collected','files':[item]}]}))
    expected=source/'build/dependency-licenses';expected.mkdir(parents=True)
    (expected/'manifest.json').write_bytes((collected/'manifest.json').read_bytes())
    manifest=json.loads((collected/'manifest.json').read_text())
    if damage=='omitted_package':manifest['packages']=[]
    if damage=='omitted_file':manifest['packages'][0]['files']=[]
    if damage=='changed_version':manifest['packages'][0]['version']='different'
    (collected/'manifest.json').write_text(json.dumps(manifest))
    if damage=='missing_manifest':(collected/'manifest.json').unlink()
    if damage=='license':(bundle/'LICENSE').write_text('changed')
    if damage=='font':(bundle/'morale/fonts/example/LICENSE').unlink()
    if damage=='dependency':(collected/'LICENSE').write_text('changed')
    if damage:
        with pytest.raises((ValueError,OSError)):check.verify(bundle,source)
    else:
        report=check.verify(bundle,source)
        assert report['collected_license_files']==report['font_license_files']==1
        assert not report['release_compliance_verified']
