"""Resolve embedded SVG CSS rules to inline declarations before geometry import."""
import cssselect2
import tinycss2
from tinycss2.color4 import parse_color


def normalize_color(value):
    """Translate modern sRGB CSS paints for the geometry parser."""
    token=tinycss2.parse_one_component_value(value,skip_comments=True)
    if token.type!='function' and value.lower()!='rebeccapurple':return value
    if token.type=='function' and token.lower_name=='url':return value
    try:color=parse_color(token)
    except (ValueError,TypeError,IndexError):color=None
    if color is None or isinstance(color,str):
        raise ValueError('Unsupported SVG CSS color expression.')
    try:color=color.to('srgb')
    except NotImplementedError as exc:
        raise ValueError('SVG CSS color space must be converted to sRGB before import.') from exc
    channels=[round(max(0,min(1,v))*255) for v in color.coordinates]
    return f'rgba({channels[0]},{channels[1]},{channels[2]},{color.alpha})'


def apply_styles(root):
    nodes=list(root.iter())
    if len(nodes)>10_000:raise ValueError('SVG exceeds 10,000 XML elements.')
    styles=[];pending=[(root,0)]
    while pending:
        node,depth=pending.pop()
        if depth>64:raise ValueError('SVG style nesting exceeds 64 levels.')
        kind=node.tag.split('}')[-1]
        if kind in {'metadata','title','desc'}:continue
        if kind=='style':styles.append(node)
        pending.extend((child,depth+1) for child in reversed(list(node)))
    color_properties={'color','fill','stroke','stop-color','flood-color','lighting-color'}
    presentation_properties=color_properties | {'opacity','fill-opacity','stroke-opacity','stop-opacity',
        'stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','stroke-dasharray','stroke-dashoffset',
        'fill-rule','clip-rule','clip-path','mask','display','visibility','paint-order','color-interpolation'}
    def normalize_attributes():
        for node in nodes:
            for key in color_properties & node.attrib.keys():
                node.set(key,normalize_color(node.get(key)))
    from .svg_variables import has_variable
    if not styles and not any(node.get('style') or any(has_variable(node.get(key)) for key in presentation_properties & node.attrib.keys()) for node in nodes):
        normalize_attributes()
        return
    def declarations(content):
        result=[]
        # Remove comments inside values as well as between declarations. The
        # downstream geometry parser consumes normalized CSS, not CSS tokens.
        if isinstance(content,str):
            content=tinycss2.parse_component_value_list(content,skip_comments=True)
        else:
            content=tinycss2.parse_component_value_list(tinycss2.serialize(content),skip_comments=True)
        for declaration in tinycss2.parse_declaration_list(content,skip_comments=True,skip_whitespace=True):
            if declaration.type!='declaration':raise ValueError('Unsupported or malformed SVG CSS declaration.')
            value=tinycss2.serialize(declaration.value).strip()
            if not value and not declaration.name.startswith('--'):continue
            key=declaration.name if declaration.name.startswith('--') else declaration.lower_name
            result.append((key,value,declaration.important))
        return result
    matcher=cssselect2.Matcher();count=0
    for style in styles:
        if style.get('type','text/css')!='text/css':raise ValueError('Unsupported SVG stylesheet type.')
        if style.get('media','all') not in {'all','screen',''}:raise ValueError('SVG stylesheet media queries are not supported.')
        for rule in tinycss2.parse_stylesheet(style.text or '',skip_comments=True,skip_whitespace=True):
            if rule.type!='qualified-rule':raise ValueError('SVG CSS at-rules and external stylesheets are not supported.')
            try:selectors=cssselect2.compile_selector_list(rule.prelude,namespaces={'svg':'http://www.w3.org/2000/svg'})
            except cssselect2.SelectorError as exc:raise ValueError('Unsupported SVG CSS selector.') from exc
            values=declarations(rule.content)
            for selector in selectors:
                if selector.pseudo_element is not None:raise ValueError('SVG CSS pseudo-elements are not supported.')
                count+=1
                if count>1000 or count*len(nodes)>2_000_000:raise ValueError('SVG stylesheet exceeds the selector matching limit.')
                matcher.add_selector(selector,values)
    # Reusable elements resolve custom properties in each instance's context.
    # Until instance-style resolution is implemented, do not bake definition-side
    # values into clones and silently lose their per-use overrides.
    references={node.get('href') or node.get('{http://www.w3.org/1999/xlink}href') for node in nodes if node.tag.split('}')[-1]=='use'}
    referenced_nodes=set()
    for node in nodes:
        if node.get('id') and '#'+node.get('id') in references:referenced_nodes.update(node.iter())
    from .svg_variables import resolve_variables
    updates=[];attribute_updates=[];environments={};expanded_size=0
    for wrapped in cssselect2.ElementWrapper.from_xml_root(root).iter_subtree():
        node=wrapped.etree_element;chosen={}
        for specificity,order,pseudo,values in matcher.match(wrapped):
            for index,(key,value,important) in enumerate(values):
                priority=(important,0,specificity,order,index)
                if key not in chosen or priority>=chosen[key][0]:chosen[key]=(priority,value)
        for index,(key,value,important) in enumerate(declarations(node.get('style',''))):
            priority=(important,1,(0,0,0),0,index)
            if key not in chosen or priority>=chosen[key][0]:chosen[key]=(priority,value)
        paints={key:node.get(key) for key in presentation_properties & node.attrib.keys()}
        if node in referenced_nodes and any(has_variable(value) for value in [*(value for _,value in chosen.values()),*paints.values()]):
            raise ValueError('SVG CSS variables in reusable elements require instance-style resolution; expand the instances before import.')
        inherited=environments.get(wrapped.parent.etree_element,{}) if wrapped.parent is not None else {}
        environment,substitute=resolve_variables(inherited,{key:value for key,(_,value) in chosen.items() if key.startswith('--')})
        environments[node]=environment
        for key,paint in paints.items():
            paint=substitute(chosen[key][1] if key in chosen else paint)
            if not paint:raise ValueError('SVG CSS paint resolved to an empty value.')
            if key in color_properties:paint=normalize_color(paint)
            expanded_size+=len(paint)
            attribute_updates.append((node,key,paint))
        output=[]
        for key,(_,value) in chosen.items():
            if key.startswith('--'):continue
            value=substitute(value)
            if not value:raise ValueError('SVG CSS property resolved to an empty value.')
            if key in color_properties:value=normalize_color(value)
            output.append(f'{key}:{value}')
        value=';'.join(output)
        expanded_size+=len(value)+sum(len(v or '') for v in environment.values())
        if expanded_size>2_000_000:raise ValueError('SVG CSS expanded styles exceed 2 MB.')
        if chosen:updates.append((node,value))
    for node,value in updates:node.set('style',value)
    for node,key,value in attribute_updates:node.set(key,value)
    for parent in nodes:
        for child in list(parent):
            if child in styles:parent.remove(child)
