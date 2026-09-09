"""Indexed preview commands, control events and consecutive thread runs."""
from bisect import bisect_right, bisect_left
from itertools import islice
from .threads import thread_key


class Timeline:
    def __init__(self, blocks):
        self.commands = []
        self.events = []
        self.runs = []
        previous = (0.,0.)
        previous_id = ""
        prior_key = None
        for block in blocks:
            if not block.stitches:
                continue
            key = thread_key(block)
            start = len(self.commands)
            if not self.runs or key != prior_key or block.color_break:
                self.runs.append({"start":start,"end":start,"color":block.color,"thread":dict(block.thread),"ids":set()})
                if start:
                    self.events.append((start+1,"thread",previous,previous,block.object_id,previous_id))
            self.runs[-1]["ids"].add(block.object_id)
            for stitch in block.stitches:
                self.commands.append((block.object_id,stitch))
                position = (stitch.x,stitch.y)
                if stitch.command in {"jump","trim","stop"}:
                    self.events.append((len(self.commands),stitch.command,previous,position,block.object_id,previous_id))
                if stitch.command in {"jump","stitch"}:
                    previous,previous_id = position,block.object_id
            self.runs[-1]["end"] = len(self.commands)
            prior_key = key
        self.events.sort(key=lambda event:event[0])
        self.indices = [event[0] for event in self.events]
        self.controls = sorted({event[0] for event in self.events if event[1] != "jump"})

    def visible_events(self, playhead=None, ids=None):
        end = len(self.events) if playhead is None else bisect_right(self.indices,playhead)
        return (event for event in islice(self.events,end) if ids is None or event[4] in ids)

    def next_control(self, position, direction, low=0, high=None):
        high = len(self.commands) if high is None else high
        index = bisect_right(self.controls,position) if direction > 0 else bisect_left(self.controls,position)-1
        if 0 <= index < len(self.controls) and low <= self.controls[index] <= high:
            return self.controls[index]
        return high if direction > 0 else low
