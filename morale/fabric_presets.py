"""Portable, bounded fabric settings with atomic file replacement."""
import json
import os
from pathlib import Path
import tempfile
from .fabric import validate_settings


def unique_fields(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate fabric preset field.')
        result[key]=value
    return result


def load_preset(path):
    with Path(path).open('rb') as stream:data=stream.read(8193)
    if len(data)>8192:raise ValueError('Fabric presets are limited to 8 KB.')
    try:document=json.loads(data,object_pairs_hook=unique_fields)
    except (ValueError,RecursionError) as exc:raise ValueError('Could not read the fabric preset.') from exc
    if not isinstance(document,dict) or set(document)!={'format','version','settings'} or document['format']!='morale-fabric-preset' or type(document['version']) is not int or document['version']!=1:
        raise ValueError('Unsupported fabric preset format or version.')
    return validate_settings(document['settings'])


def save_preset(path,settings):
    document={'format':'morale-fabric-preset','version':1,'settings':validate_settings(settings)}
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);json.dump(document,stream,indent=2);stream.write('\n')
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
