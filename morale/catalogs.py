"""File-based thread catalogs and explicit RGB-distance matching."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import csv
import io
import re

from .threads import THREAD_FIELDS


@dataclass
class ThreadEntry:
    color: str
    metadata: dict


def builtin_catalog(name):
    if name=='PEC fixed palette':
        from pyembroidery.EmbThreadPec import get_thread_set
    elif name=='JEF fixed palette':
        from pyembroidery.EmbThreadJef import get_thread_set
    else:
        raise ValueError('Unknown built-in thread palette.')
    return [ThreadEntry(t.hex_color(),{key:str(getattr(t,key)) for key in THREAD_FIELDS if getattr(t,key,None) is not None})
            for t in get_thread_set() if t is not None]


def read_catalog(path):
    path=Path(path)
    if path.stat().st_size>2_000_000:
        raise ValueError('Thread catalogs are limited to 2 MB.')
    try:
        reader=csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig')))
        if not reader.fieldnames:
            raise ValueError('A catalog needs a header and thread rows.')
        headers={name:name.strip().lower().replace(' ','_') for name in reader.fieldnames}
        if len(set(headers.values()))!=len(reader.fieldnames):
            raise ValueError('Catalog column names must be unique.')
        colors=[name for name,key in headers.items() if key in {'color','thread_rgb'}]
        if len(colors)!=1:
            raise ValueError('Provide one color or Thread RGB column containing #RRGGBB values.')
        entries=[]
        seen=set()
        for index,row in enumerate(reader,2):
            if index>10_001:
                raise ValueError('Catalogs support at most 10,000 rows.')
            if None in row:
                raise ValueError(f'Row {index} has more values than column names.')
            if not any(value and value.strip() for value in row.values()):
                continue
            color=(row.get(colors[0]) or '').strip().lower()
            if not re.fullmatch(r'#[0-9a-f]{6}',color):
                raise ValueError(f'Row {index} needs a #RRGGBB color.')
            metadata={key:(row.get(name) or '').strip() for name,key in headers.items() if key in THREAD_FIELDS}
            metadata={key:value for key,value in metadata.items() if value}
            if any(len(value)>1024 for value in metadata.values()):
                raise ValueError(f'Row {index} has a metadata field longer than 1,024 characters.')
            identity=color,tuple(sorted(metadata.items()))
            if identity not in seen:
                entries.append(ThreadEntry(color,metadata))
                seen.add(identity)
        if not entries:
            raise ValueError('Catalog has no thread rows.')
        return entries
    except (UnicodeError,csv.Error) as exc:
        raise ValueError(f'Could not read the UTF-8 CSV catalog: {exc}') from exc


@lru_cache(maxsize=20000)
def rgb(color):
    if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):
        raise ValueError('A thread color must use #RRGGBB.')
    return tuple(int(color[i:i+2],16) for i in (1,3,5))


def distance_squared(a,b):
    return sum((x-y)**2 for x,y in zip(rgb(a),rgb(b)))


def nearest_thread(color,entries):
    if not entries:
        raise ValueError('Choose a catalog containing threads.')
    return min(entries,key=lambda entry:distance_squared(color,entry.color))
