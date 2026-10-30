"""Bounded substitution for SVG custom properties; unsupported values fail explicitly."""
from copy import deepcopy
import tinycss2


class MissingVariable(ValueError):
    """An invalid computed custom property may activate a consuming fallback."""


def resolve_variables(inherited,local):
    resolved=dict(inherited);active=set()
    for key in local:resolved.pop(key,None)
    def variable(name,depth):
        if name in active:raise ValueError('Cyclic SVG CSS variables are not supported.')
        if name in resolved:return resolved[name]
        if name not in local:return None
        if depth>32:raise ValueError('SVG CSS variable nesting exceeds 32 levels.')
        active.add(name)
        try:
            raw=local[name]
            if raw.lower() in {'inherit','unset'}:value=inherited.get(name)
            elif raw.lower()=='initial':value=None
            elif raw.lower() in {'revert','revert-layer'}:raise ValueError('SVG CSS variable cascade rollback is not supported.')
            else:
                try:value=substitute(raw,depth+1)
                except MissingVariable:value=None
            resolved[name]=value
            return value
        finally:active.remove(name)
    def tokens(items,depth):
        if depth>32:raise ValueError('SVG CSS variable nesting exceeds 32 levels.')
        result=[];size=0
        for token in items:
            if token.type=='function' and token.lower_name=='var':
                args=token.arguments
                comma=next((i for i,t in enumerate(args) if t.type=='literal' and t.value==','),len(args))
                names=[t for t in args[:comma] if t.type!='whitespace']
                if len(names)!=1 or names[0].type!='ident' or not names[0].value.startswith('--') or names[0].value=='--':
                    raise ValueError('Malformed SVG CSS variable reference.')
                value=variable(names[0].value,depth+1)
                if value is None:
                    if comma==len(args):raise MissingVariable('Unresolved SVG CSS variable; provide a value or fallback.')
                    value=tinycss2.serialize(tokens(args[comma+1:],depth+1))
                replacement=tinycss2.parse_component_value_list(value,skip_comments=True)
            else:
                token=deepcopy(token)
                if token.type=='function':token.arguments=tokens(token.arguments,depth+1)
                elif hasattr(token,'content'):token.content=tokens(token.content,depth+1)
                replacement=[token]
            size+=len(tinycss2.serialize(replacement))
            if size>16384:raise ValueError('SVG CSS variable expansion exceeds 16 KB.')
            result.extend(replacement)
        return result
    def substitute(value,depth=0):
        return tinycss2.serialize(tokens(tinycss2.parse_component_value_list(value,skip_comments=True),depth)).strip()
    for name in local:variable(name,0)
    return resolved,substitute



def has_variable(value):
    pending=[(t,0) for t in tinycss2.parse_component_value_list(value,skip_comments=True)]
    while pending:
        token,depth=pending.pop()
        if depth>32:raise ValueError('SVG CSS variable nesting exceeds 32 levels.')
        if token.type=='function' and token.lower_name=='var':return True
        children=token.arguments if token.type=='function' else getattr(token,'content',[])
        pending.extend((child,depth+1) for child in children)
    return False
