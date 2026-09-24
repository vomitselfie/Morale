"""Restore encoded VP3 color-block starts, including positions on either axis.

Layout follows the upstream pyembroidery VP3 reader. Stitch decoding stays with
that reader; this adapter does not infer jump commands absent from the file.
"""
import io
from pathlib import Path
import struct
from pyembroidery import EmbPattern,Vp3Reader


def block_positions(data):
    position=0
    def take(count):
        nonlocal position
        if count<0 or position+count>len(data):raise ValueError('Truncated VP3 block metadata.')
        result=data[position:position+count];position+=count;return result
    def number(fmt):return struct.unpack(fmt,take(struct.calcsize(fmt)))[0]
    def string():take(number('>H'))
    if take(6)!=b'%vsm%\0':raise ValueError('Invalid VP3 header.')
    string();take(7);string();take(32)
    center=(number('>i')/100,-number('>i')/100)
    take(27);string();take(24);string()
    count=number('>H')
    if count>500:raise ValueError('VP3 exceeds 500 color blocks.')
    starts=[]
    for _ in range(count):
        if take(3)!=b'\0\5\0':raise ValueError('Invalid VP3 color block.')
        length=number('>I');end=position+length
        if length<8 or end>len(data):raise ValueError('Invalid VP3 color-block length.')
        starts.append((center[0]+number('>i')/100,center[1]-number('>i')/100))
        take(end-position)
    return starts


def read_vp3(path):
    data=Path(path).read_bytes();starts=block_positions(data)
    class PositionedPattern(EmbPattern):
        def add_thread(self,thread):
            index=len(self.threadlist)
            if index>=len(starts):raise ValueError('VP3 thread/block count mismatch.')
            x,y=starts[index]
            if (self._previousX,self._previousY)!=(x,y):self.move_abs(x,y)
            super().add_thread(thread)
    result=PositionedPattern();Vp3Reader.read(io.BytesIO(data),result)
    return result
