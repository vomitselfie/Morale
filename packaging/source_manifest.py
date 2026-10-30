"""Fingerprint application and build inputs without including user designs or caches."""
import hashlib
import json
from pathlib import Path

ROOT_FILES=('pyproject.toml','LICENSE','THIRD_PARTY_NOTICES.md','README.md','CHANGELOG.md','run_morale.py')
SOURCE_DIRS=('morale','packaging','scripts')


def manifest(root):
    root=Path(root);paths=[root/name for name in ROOT_FILES]
    for name in SOURCE_DIRS:
        paths.extend(path for path in (root/name).rglob('*') if path.is_file()
                     and '__pycache__' not in path.parts and path.suffix not in {'.pyc','.pyo'})
    files=[]
    for path in sorted(paths):
        if path.is_symlink():raise ValueError(f'Source input must not be a symbolic link: {path.relative_to(root)}')
        content=path.read_bytes()
        files.append({'path':path.relative_to(root).as_posix(),'bytes':len(content),
                      'sha256':hashlib.sha256(content).hexdigest()})
    canonical=json.dumps(files,sort_keys=True,separators=(',',':')).encode('utf-8')
    return {'format':'morale-build-source','version':1,'source_sha256':hashlib.sha256(canonical).hexdigest(),
            'files':files,'scope':'Application code/assets/fonts, build scripts and top-level package documents. Not a source archive.'}


def write(root,destination):
    result=manifest(root)
    Path(destination).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
