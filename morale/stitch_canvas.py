"""Canvas interaction for individual generated or manual needle positions."""
import math
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QColor,QPen,QPolygonF,QPainterPath


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

    def selected_stitch_indices(self):
        selected=self.selected_stitch()
        if not selected:return set()
        block,index=selected
        indices=self.stitch_multi[1] if self.stitch_multi and self.stitch_multi[0]==block.object_id else {index}
        return {i for i in indices if 0<=i<len(block.stitches) and block.stitches[i].command in {'stitch','jump'}}

    def move_stitch_selection(self,object_id,index,target):
        indices=self.selected_stitch_indices()
        if len(indices)>1:
            stitch=self.stitch_block().stitches[index]
            self.stitches_moved.emit(object_id,sorted(indices),target.x()-stitch.x,target.y()-stitch.y)
        else:self.stitch_moved.emit(object_id,index,target.x(),target.y())

    def select_all_stitches(self):
        block=self.stitch_block()
        if block is None or self.playhead is not None or self.stitch_drag is not None or self.stitch_marquee is not None:return
        indices={i for i,s in enumerate(block.stitches) if s.command in {'stitch','jump'}}
        self.stitch_multi=(block.object_id,indices)
        self.stitch_selection=(block.object_id,min(indices)) if indices else None
        self.announce_stitch();self.update()

    def pick_stitch(self,point,modifiers=Qt.KeyboardModifier.NoModifier):
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
        indices=self.selected_stitch_indices()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            indices.symmetric_difference_update({index})
            self.stitch_multi=(block.object_id,indices)
            self.stitch_selection=(block.object_id,index if index in indices else min(indices)) if indices else None
            self.stitch_drag=None;self.press=None;self.announce_stitch();self.update();return True
        if modifiers & Qt.KeyboardModifier.ShiftModifier and previous>=0:
            indices.update(i for i in range(min(previous,index),max(previous,index)+1) if block.stitches[i].command in {'stitch','jump'})
        elif index not in indices:indices={index}
        self.stitch_multi=(block.object_id,indices)
        self.stitch_selection=(block.object_id,index)
        stitch=block.stitches[index]
        self.stitch_drag=(block.object_id,index,QPointF(stitch.x,stitch.y))
        self.press=point
        self.announce_stitch()
        return True

    def announce_stitch(self):
        selected=self.selected_stitch()
        if selected:
            block,index=selected; stitch=block.stitches[index]
            self.message.emit(f'{len(self.selected_stitch_indices())} needle positions selected · Command {index+1}: {stitch.command} at {stitch.x:.3f}, {stitch.y:.3f} mm · Ctrl-click toggles, Shift-click selects a range · arrows move · Escape cancels dragging. Moving converts generated objects to manual stitches.')

    def stitch_key(self,event):
        selected=self.selected_stitch()
        block=self.stitch_block()
        if self.playhead is not None or block is None or self.stitch_marquee is not None: return False
        key=event.key()
        if key==Qt.Key.Key_Delete and self.stitch_drag is None:
            indices=self.selected_stitch_indices()
            if indices:self.stitches_deleted.emit(block.object_id,sorted(indices))
            return True
        if key in {Qt.Key.Key_BracketLeft,Qt.Key.Key_BracketRight}:
            indices=[i for i,s in enumerate(block.stitches) if s.command in {'stitch','jump'}]
            if not indices: return True
            if selected:
                position=indices.index(selected[1])+(-1 if key==Qt.Key.Key_BracketLeft else 1)
                index=indices[max(0,min(len(indices)-1,position))]
            else: index=indices[-1] if key==Qt.Key.Key_BracketLeft else indices[0]
            chosen=self.selected_stitch_indices() if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else set()
            chosen.add(index);self.stitch_multi=(block.object_id,chosen)
            self.stitch_selection=(block.object_id,index)
            self.stitch_drag=None; self.press=None
            self.announce_stitch(); self.update(); return True
        directions={Qt.Key.Key_Left:(-1,0),Qt.Key.Key_Right:(1,0),Qt.Key.Key_Up:(0,-1),Qt.Key.Key_Down:(0,1)}
        if selected and key in directions and self.stitch_drag is None:
            _,index=selected; stitch=block.stitches[index]
            step=self.grid_step() if self.snap_grid else 1. if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else .1
            dx,dy=directions[key]
            target=self.snapped(QPointF(stitch.x+dx*step,stitch.y+dy*step))
            self.move_stitch_selection(block.object_id,index,target)
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
        indices=self.selected_stitch_indices()
        if len(indices)>1:
            delta=target-QPointF(stitch.x,stitch.y)
            if self.stitch_drag:
                paths={'stitch':QPainterPath(),'jump':QPainterPath()};previous=None;prior_index=None
                for i,s in enumerate(block.stitches):
                    if s.command not in paths:continue
                    position=QPointF(s.x,s.y)+(delta if i in indices else QPointF())
                    if previous is not None and (i in indices or prior_index in indices):
                        paths[s.command].moveTo(previous);paths[s.command].lineTo(position)
                    previous=position;prior_index=i
                for command,path in paths.items():
                    painter.setPen(QPen(QColor('#2360c5'),2/self.scale,Qt.PenStyle.DashLine if command=='jump' else Qt.PenStyle.SolidLine));painter.drawPath(path)
            painter.setBrush(QColor('white'));painter.setPen(QPen(QColor('#c34c39'),2/self.scale))
            visible=sorted(indices)
            for i in visible[::max(1,math.ceil(len(visible)/20000))]:
                s=block.stitches[i];painter.drawEllipse(QPointF(s.x,s.y)+delta,5/self.scale,5/self.scale)
            return
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
