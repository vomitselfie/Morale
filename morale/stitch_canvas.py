"""Canvas interaction for individual generated or manual needle positions."""
import math
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QColor,QPen,QPolygonF


class StitchCanvasMixin:
    def stitch_block(self):
        if len(self.selected_ids)!=1:
            return None
        object_id=next(iter(self.selected_ids))
        if self.inspection_ids is not None and object_id not in self.inspection_ids:
            return None
        return next((block for block in self.blocks if block.object_id==object_id),None)

    def selected_stitch(self):
        block=self.stitch_block()
        if block and self.stitch_selection and self.stitch_selection[0]==block.object_id:
            index=self.stitch_selection[1]
            if 0<=index<len(block.stitches) and block.stitches[index].command in {'stitch','jump'}:
                return block,index
        return None

    def pick_stitch(self,point):
        block=self.stitch_block()
        if block is None:
            self.message.emit('Select one visible object, then choose Stitch points.')
            return
        radius=8/self.scale
        hits=[(math.hypot(s.x-point.x(),s.y-point.y())*self.scale,i) for i,s in enumerate(block.stitches) if s.command in {'stitch','jump'} and abs(s.x-point.x())<=radius and abs(s.y-point.y())<=radius]
        if not hits: return
        nearest=min(distance for distance,_ in hits)
        if nearest>8: return
        ties=[i for distance,i in hits if distance<=nearest+.5]
        previous=self.stitch_selection[1] if self.stitch_selection and self.stitch_selection[0]==block.object_id else -1
        index=ties[(ties.index(previous)+1)%len(ties)] if previous in ties else ties[0]
        self.stitch_selection=(block.object_id,index)
        stitch=block.stitches[index]
        self.stitch_drag=(block.object_id,index,QPointF(stitch.x,stitch.y))
        self.press=point
        self.announce_stitch()

    def announce_stitch(self):
        selected=self.selected_stitch()
        if selected:
            block,index=selected; stitch=block.stitches[index]
            self.message.emit(f'Command {index+1}: {stitch.command} at {stitch.x:.3f}, {stitch.y:.3f} mm · [ / ] selects adjacent needle positions · arrows move · Escape cancels dragging. Moving converts generated objects to manual stitches.')

    def stitch_key(self,event):
        selected=self.selected_stitch()
        block=self.stitch_block()
        if self.playhead is not None or block is None: return False
        key=event.key()
        if key in {Qt.Key.Key_BracketLeft,Qt.Key.Key_BracketRight}:
            indices=[i for i,s in enumerate(block.stitches) if s.command in {'stitch','jump'}]
            if not indices: return True
            if selected:
                position=indices.index(selected[1])+(-1 if key==Qt.Key.Key_BracketLeft else 1)
                index=indices[max(0,min(len(indices)-1,position))]
            else: index=indices[-1] if key==Qt.Key.Key_BracketLeft else indices[0]
            self.stitch_selection=(block.object_id,index)
            self.stitch_drag=None; self.press=None
            self.announce_stitch(); self.update(); return True
        directions={Qt.Key.Key_Left:(-1,0),Qt.Key.Key_Right:(1,0),Qt.Key.Key_Up:(0,-1),Qt.Key.Key_Down:(0,1)}
        if selected and key in directions and self.stitch_drag is None:
            _,index=selected; stitch=block.stitches[index]
            step=self.grid_step() if self.snap_grid else 1. if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else .1
            dx,dy=directions[key]
            target=self.snapped(QPointF(stitch.x+dx*step,stitch.y+dy*step))
            self.stitch_moved.emit(block.object_id,index,target.x(),target.y())
            return True
        return False

    def paint_stitch_points(self,painter):
        block=self.stitch_block()
        if block is None: return
        a,b=self.world(QPointF(0,0)),self.world(QPointF(self.width(),self.height()))
        dots=[s for s in block.stitches if s.command in {'stitch','jump'} and a.x()<=s.x<=b.x() and a.y()<=s.y<=b.y()]
        painter.setPen(QPen(QColor('#426dad'),3/self.scale))
        # Rendering every overlapping point at overview zoom hides the design.
        # Hit testing and keyboard navigation still include every command.
        if dots: painter.drawPoints(QPolygonF([QPointF(s.x,s.y) for s in dots[::max(1,math.ceil(len(dots)/20000))]]))
        selected=self.selected_stitch()
        if not selected: return
        _,index=selected; stitch=block.stitches[index]
        target=self.stitch_drag[2] if self.stitch_drag else QPointF(stitch.x,stitch.y)
        if self.stitch_drag:
            end=index+1
            while end<len(block.stitches) and block.stitches[end].command not in {'stitch','jump'}: end+=1
            previous=None
            for i in range(max(0,index-1),min(len(block.stitches),end+1)):
                row=block.stitches[i]
                position=target if index<=i<end else QPointF(row.x,row.y)
                if previous is not None and row.command in {'stitch','jump'}:
                    painter.setPen(QPen(QColor('#2360c5'),2/self.scale,Qt.PenStyle.DashLine if row.command=='jump' else Qt.PenStyle.SolidLine))
                    painter.drawLine(previous,position)
                previous=position
        painter.setBrush(QColor('white')); painter.setPen(QPen(QColor('#c34c39'),2/self.scale))
        painter.drawEllipse(target,5/self.scale,5/self.scale)
