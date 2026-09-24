"""Measured conversion diagnostics; these are not a physical sew-out verdict."""
import math
from .engine import generate

LONG_STITCH_MM=6

UNDERLAY_NAMES={'keep':'Use general choice / retain generated setting','off':'Disabled','auto':'Automatic',
                'edge':'Edge run','sparse':'Sparse fill','edge_sparse':'Edge run and sparse fill',
                'zigzag':'Zigzag','center_zigzag':'Center run and zigzag'}


def underlay_snapshot(obj):
    if obj.kind=='stitches' or obj.stitch_type not in {'fill','satin'}:return None
    style=obj.underlay_style
    if style=='auto':style='center' if obj.kind=='satin' else 'edge'
    return {'enabled':obj.underlay,'style':style,'inset_mm':obj.underlay_inset,
            'spacing_mm':obj.underlay_spacing,'stitch_length_mm':obj.stitch_length}


def conversion_quality(project,blocks=None):
    objects={obj.id:obj for obj in project.objects}
    previous=(0.,0.); regions=[]
    for block in generate(project) if blocks is None else blocks:
        obj=objects[block.object_id]
        short=zero=sewn=long_jumps=long_stitches=0; jump_length=sewn_length=maximum=0.
        long_locations=[]
        for command_index,stitch in enumerate(block.stitches):
            if stitch.command not in {'stitch','jump'}: continue
            point=(stitch.x,stitch.y); distance=math.dist(previous,point)
            if stitch.command=='stitch':
                sewn+=1;sewn_length+=distance;maximum=max(maximum,distance)
                if distance>LONG_STITCH_MM:
                    long_stitches+=1
                    if len(long_locations)<20:long_locations.append({'command_index':command_index,'from_mm':list(previous),'to_mm':list(point),'length_mm':distance})
                if distance<=1e-6: zero+=1
                elif distance<.5: short+=1
            else:
                jump_length+=distance
                long_jumps+=distance>5
            previous=point
        points=[p for ring in obj.rings() for p in ring]
        xs,ys=zip(*points)
        width=max(xs)-min(xs);height=max(ys)-min(ys)
        notes=[]
        if obj.route_fill and obj.stitch_type=='fill':notes.append('Fill-run routing enabled: compares up to 2,000 runs while retaining entry/exit. Larger fills keep scanline order. Review changed sewing order.')
        if min(width,height)<1: notes.append(f'Bounds {width:.2f} × {height:.2f} mm; inspect fine detail at this size.')
        if not sewn: notes.append('No sewn stitches were generated.')
        if short: notes.append(f'{short} stitches shorter than 0.5 mm; inspect density and short-stitch cleanup.')
        if zero: notes.append(f'{zero} zero-length stitches; inspect repeated penetrations and tie settings.')
        if long_stitches:notes.append(f'{long_stitches} sewn spans longer than 6 mm; longest {maximum:.2f} mm. Inspect stitch splitting and imported needle positions.')
        if long_jumps: notes.append(f'{long_jumps} jumps longer than 5 mm; inspect travel and trims.')
        regions.append({'object_id':obj.id,'name':obj.name,'stitch_type':obj.stitch_type,
            'underlay':underlay_snapshot(obj),'bounds_mm':[width,height],'stitches':sewn,'short_stitches':short,'zero_length_stitches':zero,
            'long_stitches':long_stitches,'maximum_stitch_mm':maximum,'long_stitch_locations':long_locations,'long_stitch_locations_complete':long_stitches<=20,
            'long_jumps':long_jumps,'jump_length_mm':jump_length,'sewn_length_mm':sewn_length,'notes':notes})
    return {'thresholds':{'short_stitch_mm':.5,'long_jump_mm':5,'long_stitch_mm':LONG_STITCH_MM,'small_bound_mm':1},
            'regions':regions,'review_regions':sum(bool(r['notes']) for r in regions),
            'jump_length_mm':sum(r['jump_length_mm'] for r in regions),
            'long_stitches':sum(r['long_stitches'] for r in regions),
            'maximum_stitch_mm':max((r['maximum_stitch_mm'] for r in regions),default=0.),
            'short_stitches':sum(r['short_stitches'] for r in regions),
            'zero_length_stitches':sum(r['zero_length_stitches'] for r in regions)}


def quality_text(report):
    lines=['Conversion measurements',
        'Thresholds are review aids, not fabric or machine limits. Ties can intentionally use short stitches.',
        f"Total jump travel: {report['jump_length_mm']:.1f} mm, starting at the artwork origin.",
        f"Short stitches (<0.5 mm): {report['short_stitches']}; zero-length stitches: {report['zero_length_stitches']}.",'']
    if 'maximum_stitch_mm' in report:
        lines.extend([f"Longest sewn span: {report['maximum_stitch_mm']:.2f} mm; spans above the 6 mm review threshold: {report['long_stitches']}.",''])
    if report.get('color_profile'):
        profile=report['color_profile']
        lines.append('Image colors: no usable embedded profile; assumed sRGB.' if profile['assumed'] else
                     f"Image colors: {profile['source'] or 'Embedded profile'} → sRGB before tracing and matching.")
        lines.append('')
    if report.get('stitch_settings',{}).get('requested'):
        settings=report['stitch_settings']
        lines.append(f"Custom stitch settings: {settings['changed_objects']} objects changed before travel planning.")
        for key,value in settings['requested'].items():
            if key in {'underlay','fill_underlay','satin_underlay'}:
                label=UNDERLAY_NAMES.get(value,str(value))
                if value=='keep' and key=='underlay':label='Retain generated setting'
                elif value=='keep':label='Use general underlay choice'
                lines.append(f"{key.replace('_',' ').capitalize()}: {label}")
            else:lines.append(f"{key.replace('_',' ').capitalize()}: {value} mm")
        lines.extend(['Inspect spacing, compensation and underlay against the source and density maps; settings remain editable after insertion.',''])
    if (report.get('background_removal') or {}).get('mode')=='border_white':
        lines.extend([f"Page-edge background removal: {report['background_removal']['removed_pixels']} near-white sampled pixels removed.",
                      'Enclosed white is retained for color reduction; a limited palette can still merge those details. Four-neighbor connectivity includes transparent pixels.',''])
    if report.get('palette_reduction'):

        palette=report['palette_reduction']
        if palette['metric']=='oklab':
            lines.extend([f"Raster palette: Oklab, fitted from {palette['fit_colors']} weighted color bins in {palette['iterations']} iterations.",
                          'Approximate color reduction before tracing; compare lost color detail against the source. Thread matching is a separate step.',''])
        else:lines.extend(['Raster palette: RGB reduction (comparison).',''])
    if report.get('density'):
        density=report['density']
        lines.extend([f"Needle penetrations: {density['penetrations']}; peak {density['peak_per_mm2']} per 1 mm² cell; {density['multi_object_cells']} cells contain stitches from multiple objects.",
                      'Fixed grid starts at the design origin. Includes ties, repeated points and underlay; travel commands are excluded. Cell counts depend on grid placement and do not predict fabric damage.',''])
    if report.get('thread_density'):
        density=report['thread_density']
        lines.extend([f"Sewn thread density: peak {density['peak_mm_per_mm2']:.2f} mm/mm²; mapped {density['mapped_sewn_mm']:.2f} of {density['total_sewn_mm']:.2f} mm.",
                      'Complete grid traversal.' if density['complete'] else 'Partial map: geometry budget exceeded.',
                      'Planar sewn length includes ties and underlay, excludes jumps, and does not estimate take-up through fabric or bobbin thread.',''])
    if report.get('layers'):
        from .coverage_review import layers_text
        lines.extend([*layers_text(report['layers']),''])
    if report.get('fabric'):
        from .coverage_review import fabric_guidance
        lines.extend([fabric_guidance(report,report['fabric'])[1],''])
    if report.get('artwork_notes'):
        lines.extend(['Artwork interpretation:',*report['artwork_notes'],''])
    if report.get('overlap'):
        overlap=report['overlap']
        lines.extend([f"Covered fill removed: {overlap['removed_area_mm2']:.2f} mm²; {overlap['removed_regions']} fully covered regions removed.",
                      f"Overlap allowance: {overlap['allowance_mm']:.2f} mm. Compensation and underlay can extend beyond these artwork boundaries; inspect seams before sewing.",''])
    if report.get('hole_filter',{}).get('minimum_area_mm2',0):
        holes=report['hole_filter']
        if holes.get('occupied_holes_retained'):lines.append(f"Small holes retained because another fill occupies them: {holes['occupied_holes_retained']}.")
        lines.extend([f"Holes below {holes['minimum_area_mm2']:.2f} mm²: {holes['filled_holes']} filled ({holes['added_area_mm2']:.2f} mm² added).",
                      'This adds artwork material. Compare enclosed details against the source before sewing.',''])
        for change in holes.get('changes',[]):
            label=change.get('name') or f"Source region {change['source_region']+1}"
            noun='hole' if change['filled_holes']==1 else 'holes'
            lines.append(f"{label}: {change['filled_holes']} {noun} filled; {change['added_area_mm2']:.2f} mm² added.")
        lines.append('')
    if report.get('detail_filter',{}).get('minimum_area_mm2',0):
        detail=report['detail_filter']
        lines.extend([f"Filled details below {detail['minimum_area_mm2']:.2f} mm²: {detail['removed_components']} islands omitted ({detail['removed_area_mm2']:.2f} mm² total).",
                      'This removes artwork detail. Compare against the retained reference before sewing.',''])
        for change in detail.get('changes',[]):
            label=change.get('name') or f"Source region {change['source_region']+1}"
            suffix=' Entire region omitted.' if change['removed_region'] else ''
            noun='island' if change['removed_components']==1 else 'islands'
            lines.append(f"{label}: {change['removed_components']} filled {noun} omitted; {change['removed_area_mm2']:.2f} mm² removed.{suffix}")
        lines.append('')
    if report.get('routing'):
        routing=report['routing']
        lines.extend([f"Inter-region travel from artwork origin: {routing['before_mm']:.2f} → {routing['after_mm']:.2f} mm before later finishing.",
                      f"Regions moved: {routing['moved_regions']}; sewing directions reversed: {len(routing.get('reversed_regions',[]))}."])
        if routing.get('status')=='rejected':lines.append('Original route retained: '+routing.get('reason','Candidate validation failed.'))
        elif routing.get('status')=='unchanged':lines.append('Original route retained; no shorter valid candidate was found.')
        lines.extend(['Travel measurements exclude transfers within a region. Routing is a bounded search; inspect sewing order.',''])
    if report.get('fill_angles'):
        angles=report['fill_angles']
        lines.extend([f"Fill-angle travel: {angles['before_mm']:.2f} → {angles['after_mm']:.2f} mm before later routing/finishing.",
                      'Candidate angle search completed.' if angles['complete'] else 'Partial angle search: evaluation budget reached.',
                      'Angles change fill grain; review appearance and fabric behavior. This is a bounded search, not a global optimum.'])
        lines.extend(f"Region {c['region']+1}: {c['from_degrees']:.1f}° → {c['to_degrees']:.1f}°; travel reduced by {c['travel_saved_mm']:.2f} mm." for c in angles['changes'])
        lines.append('')
    if report.get('finishing'):
        finish=report['finishing']
        lines.extend([f"Finishing: {finish['tie_in_objects']} objects with tie-in, {finish['tie_off_objects']} with tie-off, {finish['trim_objects']} with final trim.",
            f"Transfer threshold: {finish['threshold_mm']:g} mm; thread changes and stops also separate regions.",
            'Long internal jump sequences are trimmed and locked.' if finish.get('internal_trims') else
            'Object tie settings also lock internal sewn runs. Internal jumps are not automatically trimmed.',''])
    if report.get('thread_matches'):
        lines.extend(['Thread matches (screen-color estimates; compare physical thread samples):'])
        for match in report['thread_matches']:
            metadata=match['metadata']
            name=' '.join(metadata.get(key,'') for key in ('brand','catalog_number','description')).strip()
            metric='Oklab ×100' if match.get('metric')=='oklab' else 'RGB'
            lines.append(f"{match['source_color']} → {match['color']} · {name or match['catalog']} · {metric} distance {match.get('distance',match['rgb_distance']):.1f}")
        lines.append('')
    for order,region in enumerate(report['regions'],1):
        lines.append(f"Sew {order}: {region['name']} · {region['stitch_type']} · {region['stitches']} stitches")
        support=region.get('underlay')
        if support is not None:
            if not support['enabled']:lines.append('Underlay: Disabled.')
            else:
                style=support['style'];label='Center run' if style=='center' else UNDERLAY_NAMES.get(style,style)
                detail=[]
                if style!='center':detail.append(f"inset {support['inset_mm']:g} mm")
                if style in {'sparse','edge_sparse','zigzag','center_zigzag'}:detail.append(f"support spacing {support['spacing_mm']:g} mm")
                if style in {'center','edge','edge_sparse','center_zigzag'}:detail.append(f"run stitch length {support['stitch_length_mm']:g} mm")
                lines.append(f"Underlay: {label}; {', '.join(detail)}.")
        lines.extend(region['notes'] or ['No thresholds flagged. Inspect the preview and validate with a sew-out.'])
        for location in region.get('long_stitch_locations',[]):
            a,b=location['from_mm'],location['to_mm']
            lines.append(f"Long span at command {location['command_index']+1}: ({a[0]:.2f}, {a[1]:.2f}) → ({b[0]:.2f}, {b[1]:.2f}) mm; {location['length_mm']:.2f} mm.")
        if not region.get('long_stitch_locations_complete',True):lines.append('First 20 long-span locations shown for this region; totals include all spans.')
        lines.append('')
    return '\n'.join(lines)
