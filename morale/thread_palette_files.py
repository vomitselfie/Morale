"""Bounded INF and EDR palette decoding; these files contain no stitches."""
import struct
from pathlib import Path


def read_palette(path):
    from .catalogs import ThreadEntry
    path=Path(path)
    with path.open('rb') as stream:data=stream.read(2_000_001)
    if len(data)>2_000_000:raise ValueError('Thread palettes are limited to 2 MB.')
    entries=[]
    if path.suffix.lower()=='.edr':
        if not data or len(data)%4 or len(data)//4>10_000:raise ValueError('EDR requires 1–10,000 complete four-byte color records.')
        for i in range(0,len(data),4):entries.append(ThreadEntry('#'+data[i:i+3].hex(),{}))
    elif path.suffix.lower()=='.inf':
        if len(data)<16:raise ValueError('Incomplete INF palette header.')
        _,_,remaining,count=struct.unpack_from('>4I',data)
        if remaining!=len(data)-12 or not 1<=count<=10_000:raise ValueError('Invalid INF palette size or color count.')
        offset=16
        for _ in range(count):
            if offset+2>len(data):raise ValueError('Incomplete INF color record.')
            size=struct.unpack_from('>H',data,offset)[0];end=offset+size
            if size<11 or end>len(data):raise ValueError('Invalid INF color record length.')
            strings=data[offset+9:end].split(b'\0')
            if len(strings)!=3 or strings[-1]:raise ValueError('INF color names must have two terminated fields.')
            try:description,chart=(value.decode('utf-8') for value in strings[:2])
            except UnicodeError as exc:raise ValueError('INF color names must be valid UTF-8.') from exc
            if max(len(description),len(chart))>1024:raise ValueError('INF color metadata exceeds 1,024 characters.')
            metadata={key:value for key,value in (('description',description),('chart',chart)) if value}
            entries.append(ThreadEntry('#'+data[offset+4:offset+7].hex(),metadata));offset=end
        if offset!=len(data):raise ValueError('Unexpected data after INF color records.')
    else:raise ValueError('Choose an INF or EDR palette.')
    return entries


def write_palette(path,entries):
    """Export the supplied order; INF retains description/chart, EDR only RGB."""
    import os
    import tempfile
    from .catalogs import rgb
    path=Path(path);extension=path.suffix.lower()
    if extension not in {'.inf','.edr'}:raise ValueError('Choose an INF or EDR palette destination.')
    if not 1<=len(entries)<=10_000:raise ValueError('Palettes require 1–10,000 colors.')
    body=bytearray()
    for index,entry in enumerate(entries):
        color=bytes(rgb(entry.color))
        if extension=='.edr':body.extend(color+b'\0')
        else:
            strings=[]
            for key in ('description','chart'):
                value=entry.metadata.get(key,'')
                if not isinstance(value,str) or len(value)>1024 or '\0' in value:
                    raise ValueError('INF names must be text up to 1,024 characters without embedded nulls.')
                try:strings.append(value.encode('utf-8')+b'\0')
                except UnicodeError as exc:raise ValueError('INF names must be valid Unicode.') from exc
            payload=b''.join(strings)
            body.extend(struct.pack('>HH',9+len(payload),index)+color+struct.pack('>H',index+1)+payload)
        if len(body)+16>2_000_000:raise ValueError('Thread palettes are limited to 2 MB.')
    data=struct.pack('>4I',1,8,len(body)+4,len(entries))+body if extension=='.inf' else body
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);stream.write(data)
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return {'colors':len(entries),'format':extension,'metadata_fields':['description','chart'] if extension=='.inf' else []}
