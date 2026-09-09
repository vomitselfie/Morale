"""Split sewn segments into nonoverlapping cores of overlapping hoop fields."""
from copy import deepcopy
from dataclasses import dataclass
import math
from .model import Project,DesignObject
from .engine import generate,preflight
from .stitch_edit import manual_object


@dataclass
class HoopTile:
    row: int
    column: int
    center: tuple
    core: tuple
    project: Project
    marks: list


@dataclass
class HoopPlan:
    width: float
    height: float
    margin: float
    columns: int
    rows: int
    bounds: tuple
    tiles: list


def clip_line(a,b,box):
    """Return the retained parameter interval of a segment in a rectangle."""
    dx,dy=b[0]-a[0],b[1]-a[1]
    lo,hi=0.,1.
    for p,q in ((-dx,a[0]-box[0]),(dx,box[2]-a[0]),(-dy,a[1]-box[1]),(dy,box[3]-a[1])):
        if abs(p)<1e-14:
            if q<0: return None
        elif p<0: lo=max(lo,q/p)
        else: hi=min(hi,q/p)
        if lo>hi: return None
    return lo,hi


def split_design(project,width=100,height=100,margin=8,registration=True):
    for value in (width,height,margin):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('Hoop dimensions and margin must be finite numbers.')
    if not 20<=width<=500 or not 20<=height<=500 or not 4<=margin<=30 or min(width,height)-2*margin<10 or type(registration) is not bool:
        raise ValueError('Use 20–500 mm hoops, 4–30 mm margins, and at least a 10 mm content core.')
    project=Project.loads(project.dumps())
    blocks=generate(project)
    points=[]
    for block in blocks:
        previous=None
        for stitch in block.stitches:
            p=(stitch.x,stitch.y)
            if stitch.command=='stitch':
                if previous is None: raise ValueError('Each source object must start with a jump before sewing. Correct its commands in the stitch editor.')
                points.extend((previous,p))
            if stitch.command in {'jump','stitch'}: previous=p
    if not points: raise ValueError('The design has no sewn segments to split.')
    xs,ys=zip(*points)
    core_w,core_h=width-2*margin,height-2*margin
    columns=max(1,math.ceil((max(xs)-min(xs))/core_w-1e-12))
    rows=max(1,math.ceil((max(ys)-min(ys))/core_h-1e-12))
    if columns*rows>100: raise ValueError('Multi-hooping is limited to 100 placements. Increase hoop size or reduce the design.')
    left=(min(xs)+max(xs)-columns*core_w)/2
    top=(min(ys)+max(ys)-rows*core_h)/2
    def owner(p):
        def cell(value,origin,step,count):
            q=(value-origin)/step
            if abs(q-round(q))<1e-9: q=round(q)
            return max(0,min(count-1,math.floor(q)))
        return cell(p[1],top,core_h,rows),cell(p[0],left,core_w,columns)
    originals={obj.id:obj for obj in project.objects}
    tiles=[]
    for row in range(rows):
        for column in range(columns):
            box=(left+column*core_w,top+row*core_h,left+(column+1)*core_w,top+(row+1)*core_h)
            center=((box[0]+box[2])/2,(box[1]+box[3])/2)
            objects=[]; pending_tile_stops=0
            for block in blocks:
                commands=[]; pending_stops=[]; previous=None; active=False
                for stitch in block.stitches:
                    point=(stitch.x,stitch.y)
                    if stitch.command=='jump':
                        previous=point; active=False; continue
                    if stitch.command in {'trim','stop'}:
                        if commands:
                            commands.append([*commands[-1][:2],stitch.command])
                        elif stitch.command=='stop': pending_stops.append('stop')
                        active=False; continue
                    interval=clip_line(previous,point,box)
                    if interval is not None:
                        lo,hi=interval
                        a=tuple(x+(y-x)*lo for x,y in zip(previous,point))
                        b=tuple(x+(y-x)*hi for x,y in zip(previous,point))
                        midpoint=tuple((x+y)/2 for x,y in zip(a,b))
                        zero=math.dist(previous,point)<1e-12
                        if owner(midpoint)!=(row,column) or (hi-lo<1e-12 and not zero): interval=None
                    if interval is not None:
                        start=(a[0]-center[0],a[1]-center[1]); end=(b[0]-center[0],b[1]-center[1])
                        if not active or not commands or math.dist(commands[-1][:2],start)>1e-8:
                            if commands and commands[-1][2] not in {'trim','stop'}:
                                commands.append([*commands[-1][:2],'trim'])
                            commands.append([*start,'jump'])
                            for command in pending_stops: commands.append([*start,command])
                            pending_stops=[]
                        commands.append([*end,'stitch'])
                        active=hi>=1-1e-12
                    else: active=False
                    previous=point
                if any(command[2]=='stitch' for command in commands):
                    if pending_tile_stops:
                        commands[1:1]=[[*commands[0][:2],'stop'] for _ in range(pending_tile_stops)]
                        pending_tile_stops=0
                    source=originals[block.object_id]
                    candidate=manual_object(source,commands)
                    candidate.group_id=''
                    objects.append(candidate)
                else:
                    pending_tile_stops+=sum(s.command=='stop' for s in block.stitches)
            if objects:
                if pending_tile_stops:
                    last=objects[-1].stitch_data[-1][:2]
                    objects[-1].stitch_data.extend([[*last,'stop'] for _ in range(pending_tile_stops)])
                tile_project=Project(name=f'{project.name[:170]} · hoop {row+1}-{column+1}',hoop_width=width,hoop_height=height,objects=objects)
                tiles.append(HoopTile(row,column,center,box,tile_project,[]))
    active={(tile.row,tile.column):tile for tile in tiles}
    if registration:
        for tile in tiles:
            row,column=tile.row,tile.column; cx,cy=tile.center
            for dr,dc in ((0,1),(1,0)):
                neighbor=active.get((row+dr,column+dc))
                if neighbor is None: continue
                if dc:
                    seam=tile.core[2]
                    positions=[(seam,cy-core_h/2-margin/2),(seam,cy+core_h/2+margin/2)]
                else:
                    seam=tile.core[3]
                    positions=[(cx-core_w/2-margin/2,seam),(cx+core_w/2+margin/2,seam)]
                for index,position in enumerate(positions):
                    mark={'id':f'{row+1}-{column+1}_to_{row+dr+1}-{column+dc+1}_{index+1}','position':list(position)}
                    tile.marks.append(deepcopy(mark)); neighbor.marks.append(deepcopy(mark))
        for tile in tiles:
            if tile.marks:
                commands=[]
                for mark in tile.marks:
                    x,y=mark['position'][0]-tile.center[0],mark['position'][1]-tile.center[1]
                    commands.extend([[x-1,y,'jump'],[x+1,y,'stitch'],[x+1,y,'trim'],[x,y-1,'jump'],[x,y+1,'stitch'],[x,y+1,'trim']])
                commands.append([*commands[-1][:2],'stop'])
                source=DesignObject(name='Removable alignment crosses',color='#c13d35',stage_note='Position the hoop using paired marks and the placement map before sewing. Sew crosses with removable thread, then pause to verify alignment before continuing with the design thread. Remove alignment stitching after assembly.')
                tile.project.objects[0].color_break=True
                tile.project.objects.insert(0,manual_object(source,commands))
    for tile in tiles:
        Project.loads(tile.project.dumps())
        issues=preflight(tile.project,generate(tile.project))
        if issues: raise ValueError('A split tile failed hoop checks: '+'; '.join(issues))
    return HoopPlan(width,height,margin,columns,rows,(left,top,left+columns*core_w,top+rows*core_h),tiles)
