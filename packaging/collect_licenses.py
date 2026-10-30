"""Collect installed distribution license texts; report gaps without claiming release compliance."""
import argparse
import hashlib
from importlib.metadata import distribution,PackageNotFoundError
import json
import sys
from pathlib import Path

PACKAGES=('PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','pyembroidery',
          'svgelements','vtracer','tinycss2','cssselect2','webencodings','pyinstaller')


def collect(output,prefix=None):
    root=Path(output);root.mkdir(parents=True,exist_ok=False)
    records=[]
    for name in PACKAGES:
        try:dist=distribution(name)
        except PackageNotFoundError:
            records.append({'package':name,'status':'metadata_unavailable','files':[]})
            continue
        record={'package':name,'version':dist.version,'status':'license_text_missing','files':[]}
        for entry in sorted(dist.files or [],key=str):
            basename=Path(str(entry)).name.lower()
            if not basename.startswith(('license','licence','copying','copyright','notice')):continue
            source=Path(dist.locate_file(entry))
            if not source.is_file():continue
            data=source.read_bytes()
            if len(data)>5_000_000:raise ValueError(f'License text is unexpectedly large: {name}/{basename}')
            target=root/name/f'{len(record["files"])+1:02d}-{source.name}'
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(data)
            record['files'].append({'source':str(entry),'path':str(target.relative_to(root)),
                                    'sha256':hashlib.sha256(data).hexdigest()})
        if record['files']:record['status']='texts_collected'
        records.append(record)
    # Conda retains upstream license files in the package cache even when the
    # installed wheel-style metadata does not enumerate them.
    environment=Path(prefix or sys.prefix)
    for metadata in sorted((environment/'conda-meta').glob('*.json')):
        data=json.loads(metadata.read_text(encoding='utf-8'))
        name=data.get('name')
        if name not in {'python','qt6-main','pyside6'}:continue
        record={'package':name,'version':data.get('version'),'build':data.get('build'),
                'provenance':'conda-package-cache','declared_license':data.get('license'),
                'status':'license_text_missing','files':[]}
        cache=data.get('link',{}).get('source')
        if cache:
            license_root=Path(cache)/'info'/'licenses'
            for source in sorted(license_root.rglob('*')):
                if not source.is_file():continue
                relative=source.relative_to(license_root)
                content=source.read_bytes()
                if len(content)>5_000_000:raise ValueError(f'License text is unexpectedly large: {name}/{relative}')
                target=root/('conda-'+name)/relative;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(content)
                record['files'].append({'source':str(Path('info/licenses')/relative),
                    'path':str(target.relative_to(root)),'sha256':hashlib.sha256(content).hexdigest()})
        if record['files']:record['status']='texts_collected'
        records.append(record)
    manifest={'release_compliance_verified':False,'packages':records,
        'limitations':['Installed distribution metadata may omit license texts.',
                      'Python, Qt modules, native libraries and source/relinking requirements require separate review.',
                      'Font licenses are shipped beside bundled font files.']}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();manifest=collect(args.output)
    for record in manifest['packages']:print(f'{record["package"]}: {record["status"]}')


if __name__=='__main__':main()
