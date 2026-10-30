import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('source_manifest',Path(__file__).parents[1]/'packaging/source_manifest.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def tree(tmp_path):
    for name in module.ROOT_FILES:(tmp_path/name).write_text(name)
    (tmp_path/'morale').mkdir();(tmp_path/'morale/app.py').write_text('source')
    return tmp_path


def test_fingerprint_tracks_uncommitted_code_and_ignores_user_designs_and_caches(tmp_path):
    root=tree(tmp_path);before=module.manifest(root)
    (root/'private.pes').write_text('design');cache=root/'morale/__pycache__';cache.mkdir();(cache/'app.pyc').write_bytes(b'cache')
    assert module.manifest(root)==before
    (root/'morale/new_module.py').write_text('new code')
    added=module.manifest(root);assert added['source_sha256']!=before['source_sha256']
    (root/'morale/app.py').write_text('changed')
    assert module.manifest(root)['source_sha256']!=added['source_sha256']


def test_source_symlinks_are_rejected(tmp_path):
    root=tree(tmp_path);(root/'morale/link.py').symlink_to(root/'README.md')
    with pytest.raises(ValueError,match='symbolic link'):module.manifest(root)
