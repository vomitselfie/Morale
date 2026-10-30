"""Structured generated stitches between design objects and machine blocks.

``Stitch`` lists are the machine-oriented form and stay what format writers
receive. Before lowering, each object's stitches are kept as ``GeneratedRun``
passes that remember what they are (underlay or top) and whether they may be
sewn backwards, so planning can orient passes without guessing from flat
commands. Lowering concatenates the runs; cleanup and finishing follow as before.
"""
from dataclasses import dataclass, field, replace
import math


@dataclass
class GeneratedRun:
    """One continuous pass: a jump to its first needle position, then motion.

    Runs hold only stitch and jump commands; trims, stops and ties are added when
    the object is lowered.
    """
    stitches: list
    kind: str  # "underlay" or "top"
    reversible: bool = False

    @property
    def entry(self):
        first = self.stitches[0]
        return first.x, first.y

    @property
    def exit(self):
        last = self.stitches[-1]
        return last.x, last.y

    def reversed(self):
        """The same pass sewn backwards: each segment keeps how it is sewn."""
        if not self.reversible:
            raise ValueError("This pass cannot be sewn in reverse.")
        from .engine import Stitch
        points = self.stitches
        if any(s.command not in {"stitch", "jump"} for s in points):
            raise ValueError("Only stitch and jump commands can be reversed.")
        # Arriving at points[i-1] uses the command that arrived at points[i].
        result = [Stitch(points[-1].x, points[-1].y, "jump")]
        result += [Stitch(points[i - 1].x, points[i - 1].y, points[i].command) for i in range(len(points) - 1, 0, -1)]
        return replace(self, stitches=result)


@dataclass
class GeneratedObject:
    object_id: str
    runs: list = field(default_factory=list)

    @property
    def entry(self):
        return self.runs[0].entry if self.runs else None

    @property
    def exit(self):
        return self.runs[-1].exit if self.runs else None

    def stitches(self):
        return [s for run in self.runs for s in run.stitches]


def plan_column(underlay, top, center=None):
    """Orient underlay passes so a column starts and ends where its top pass does.

    Passes alternate direction, starting from the top's entry end. When they
    would finish at the far end, a running return along the centerline brings the needle
    back, so the top pass starts without a jump. The top keeps its direction,
    which the user may have chosen deliberately.
    """
    if not underlay:
        return [top]
    planned, position = [], top.entry
    for run in underlay:
        if run.reversible and math.dist(run.exit, position) < math.dist(run.entry, position):
            run = run.reversed()
        planned.append(run)
        position = run.exit
    # Satin starts on a rail while center passes end mid-column, so compare ends
    # of the column rather than requiring the needle to land on the top's entry.
    if center is not None and math.dist(position, top.exit) < math.dist(position, top.entry):
        back = center if math.dist(center.entry, position) <= math.dist(center.exit, position) else center.reversed()
        planned.append(replace(back, kind="underlay"))
    return planned + [top]
