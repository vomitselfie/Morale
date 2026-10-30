"""Expand local symbol instances into viewports before SVG geometry parsing."""
from copy import deepcopy
import xml.etree.ElementTree as ET
import re


def expand_symbols(root):
    symbols={node.get('id'):node for node in root.iter() if node.tag.split('}')[-1]=='symbol' and node.get('id')}
    count=0
    occupied={node.get('id') for node in root.iter() if node.get('id')}
    serial=0
    def localize(viewport):
        nonlocal serial
        mapping={}
        for node in viewport.iter():
            ident=node.get('id')
            if not ident:continue
            while True:
                serial+=1;candidate=f'morale-symbol-{serial}'
                if candidate not in occupied:break
            occupied.add(candidate);mapping[ident]=candidate;node.set('id',candidate)
        def reference(match):
            ident=match.group(2)
            return f'url(#{mapping[ident]})' if ident in mapping else match.group(0)
        for node in viewport.iter():
            for key,value in list(node.attrib.items()):
                if key in {'href','{http://www.w3.org/1999/xlink}href'} and value.startswith('#'):
                    node.set(key,'#'+mapping.get(value[1:],value[1:]))
                elif key!='id':node.set(key,re.sub(r"url\(\s*(['\"]?)#([^\s'\"()]+)\1\s*\)",reference,value))

    def expand(parent,stack=()):
        nonlocal count
        for index,node in enumerate(list(parent)):
            count+=1
            if count>10000 or len(stack)>64:raise ValueError('SVG symbol expansion exceeds the supported limit.')
            href=node.get('href',node.get('{http://www.w3.org/1999/xlink}href',''))
            if node.tag.split('}')[-1]=='use' and href.startswith('#') and href[1:] in symbols:
                ident=href[1:]
                if ident in stack:raise ValueError('SVG contains a circular symbol reference.')
                source=symbols[ident]
                group=ET.Element('g',{key:value for key,value in node.attrib.items()
                    if key not in {'x','y','width','height','href','{http://www.w3.org/1999/xlink}href'}})
                viewport=deepcopy(source);viewport.tag='svg';viewport.attrib.pop('id',None)
                for key,default in (('x','0'),('y','0'),('width','100%'),('height','100%')):
                    viewport.set(key,node.get(key,source.get(key,default)))
                group.append(viewport);parent.remove(node);parent.insert(index,group)
                expand(group,stack+(ident,))
                localize(viewport)
            else:expand(node,stack)
    expand(root)
    # Keep children available by ID, while never painting the definition itself.
    for node in root.iter():
        if node.tag.split('}')[-1]=='symbol':node.tag='defs'
