"""Bounded filename and explicit native-project note searches."""
import json
import os
from pathlib import Path
import sys

from .formats import IMPORT_FORMATS


def find_designs(root,query,limit=5000,entry_limit=200_000,metadata_byte_limit=64_000_000):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('Choose an existing design folder.')
    if any(type(v) is not int or v<1 for v in (limit,entry_limit,metadata_byte_limit)):
        raise ValueError('Search limits must be positive integers.')
    if not isinstance(query,str) or len(query)>200:raise ValueError('Use up to 200 characters to search filenames and relative paths; leave blank to list all designs.')
    needle=query.strip().casefold();pending=[root];matches=[];visited=errors=0;complete=True
    notes_search=needle.startswith('notes:');metadata_bytes=0;stop_reason=None
    if notes_search:
        needle=needle[6:].strip()
        if not needle:raise ValueError('Enter text after notes: to search saved design notes.')
    extensions=set(IMPORT_FORMATS)|{'.morale'}
    while pending and complete:
        folder=pending.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    visited+=1
                    if visited>entry_limit:complete=False;stop_reason='entry_limit';break
                    if entry.name.startswith('.') or entry.is_symlink():continue
                    try:
                        if entry.is_dir(follow_symlinks=False):pending.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in extensions:
                            relative=str(Path(entry.path).relative_to(root))
                            matched=needle in relative.casefold()
                            if notes_search:
                                if Path(entry.name).suffix.lower()!='.morale':continue
                                if entry.stat(follow_symlinks=False).st_size>20_000_000:errors+=1;continue
                                remaining=metadata_byte_limit-metadata_bytes
                                if remaining<=0:complete=False;stop_reason='metadata_byte_limit';break
                                with open(entry.path,'rb') as stream:data=stream.read(min(remaining,20_000_000)+1)
                                metadata_bytes+=len(data)
                                if metadata_bytes>metadata_byte_limit:complete=False;stop_reason='metadata_byte_limit';break
                                if len(data)>20_000_000:errors+=1;continue
                                try:
                                    document=json.loads(data)
                                    notes=document.get('notes','') if isinstance(document,dict) else None
                                    if not isinstance(notes,str) or len(notes)>10000:raise ValueError('Invalid notes.')
                                    matched=needle in notes.casefold()
                                except (ValueError,RecursionError):errors+=1;continue
                            if matched:
                                matches.append(relative)
                                if len(matches)>=limit:complete=False;stop_reason='result_limit';break
                    except OSError:errors+=1
        except OSError:errors+=1
    return {'root':str(root),'query':query,'matches':sorted(matches,key=str.casefold),'complete':complete,
            'entries_examined':min(visited,entry_limit),'unreadable_entries':errors,'result_limit':limit,
            'notes_search':notes_search,'metadata_bytes_read':metadata_bytes,'stop_reason':stop_reason}


def worker_main(args):
    if len(args)!=3:return 2
    root,output,query=args;destination=Path(output)
    try:
        result=find_designs(root,query)
        (destination/'search.json').write_text(json.dumps(result),encoding='utf-8');return 0
    except Exception as exc:
        (destination/'search.error.json').write_text(json.dumps({'error':str(exc)}),encoding='utf-8');return 1


if __name__=='__main__':sys.exit(worker_main(sys.argv[1:]))
