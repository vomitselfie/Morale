"""Check collected notice integrity, without treating collection as license compliance."""
import hashlib
import json
from pathlib import Path


def verify(data_root,source_root):
    data_root,source_root=Path(data_root),Path(source_root)
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    for filename in ('LICENSE','THIRD_PARTY_NOTICES.md'):
        if digest(data_root/filename)!=digest(source_root/filename):
            raise ValueError(f'Bundled {filename} differs from the build source.')
    root=data_root/'dependency-licenses'
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    expected=json.loads((source_root/'build/dependency-licenses/manifest.json').read_text(encoding='utf-8'))
    if manifest!=expected:
        raise ValueError('Bundled license manifest differs from the collected build manifest.')
    count=0;gaps=[]
    for package in manifest['packages']:
        if package['status']!='texts_collected':gaps.append(package['package'])
        for item in package['files']:
            path=(root/item['path']).resolve()
            if not path.is_relative_to(root.resolve()):raise ValueError('License manifest path escapes its directory.')
            if digest(path)!=item['sha256']:raise ValueError(f'Bundled license hash mismatch: {item["path"]}')
            count+=1
    fonts=0
    for source in sorted((source_root/'morale/fonts').glob('*/LICENSE')):
        relative=source.relative_to(source_root)
        if digest(data_root/relative)!=digest(source):raise ValueError(f'Bundled font license differs: {relative}')
        fonts+=1
    return {'collected_license_files':count,'font_license_files':fonts,
            'metadata_gaps':gaps,'release_compliance_verified':False}
