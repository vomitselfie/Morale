"""Bounded filename-only folder search; design decoding stays in preview workers."""
import json
import os
from pathlib import Path
import sys

from .formats import IMPORT_FORMATS


def find_designs(root,query,limit=5000,entry_limit=200_000):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('Choose an existing design folder.')
    if not isinstance(query,str) or not query.strip() or len(query)>200:raise ValueError('Enter 1–200 characters to search filenames and relative paths.')
    needle=query.strip().casefold();pending=[root];matches=[];visited=errors=0;complete=True
    extensions=set(IMPORT_FORMATS)|{'.morale'}
    while pending and complete:
        folder=pending.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    visited+=1
                    if visited>entry_limit:complete=False;break
                    if entry.name.startswith('.') or entry.is_symlink():continue
                    try:
                        if entry.is_dir(follow_symlinks=False):pending.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in extensions:
                            relative=str(Path(entry.path).relative_to(root))
                            if needle in relative.casefold():
                                matches.append(relative)
                                if len(matches)>=limit:complete=False;break
                    except OSError:errors+=1
        except OSError:errors+=1
    return {'root':str(root),'query':query,'matches':sorted(matches,key=str.casefold),'complete':complete,
            'entries_examined':min(visited,entry_limit),'unreadable_entries':errors,'result_limit':limit}


def worker_main(args):
    if len(args)!=3:return 2
    root,output,query=args;destination=Path(output)
    try:
        result=find_designs(root,query)
        (destination/'search.json').write_text(json.dumps(result),encoding='utf-8');return 0
    except Exception as exc:
        (destination/'search.error.json').write_text(json.dumps({'error':str(exc)}),encoding='utf-8');return 1


if __name__=='__main__':sys.exit(worker_main(sys.argv[1:]))
