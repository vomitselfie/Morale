"""Isolated stitch generation with bounded result decoding and stale-job rejection."""
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import tempfile
from PySide6.QtCore import QObject,QProcess,QProcessEnvironment,QTimer,Signal
from .engine import Block,Stitch,generate
from .model import Project


def decode_blocks(data,expected):
    if not isinstance(data,list) or len(data)!=len(expected): raise ValueError('Preview returned the wrong object set.')
    blocks=[]; count=0
    for item,metadata in zip(data,expected):
        if not isinstance(item,dict) or any(item.get(key)!=value for key,value in metadata.items()):
            raise ValueError('Preview metadata does not match the requested design.')
        rows=item.get('stitches')
        if not isinstance(rows,list): raise ValueError('Invalid preview commands.')
        count+=len(rows)
        if count>250_000: raise ValueError('Preview exceeds 250,000 commands.')
        stitches=[]
        for row in rows:
            if not isinstance(row,list) or len(row)!=3 or not isinstance(row[2],str) or row[2] not in {'stitch','jump','trim','stop'} or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>10000 for v in row[:2]):
                raise ValueError('Invalid preview command data.')
            stitches.append(Stitch(*row))
        blocks.append(Block(metadata['object_id'],metadata['color'],stitches,metadata['color_break'],metadata['thread']))
    return blocks


def worker_main(args):
    if len(args)!=2: return 2
    source,output=map(Path,args)
    try:
        if source.stat().st_size>50_000_000: raise ValueError('Project exceeds the 50 MB preview worker limit.')
        project=Project.loads(source.read_text(encoding='utf-8'))
        blocks=generate(project)
        data=[{'object_id':b.object_id,'color':b.color,'color_break':b.color_break,'thread':b.thread,'stitches':[[s.x,s.y,s.command] for s in b.stitches]} for b in blocks]
        (output/'blocks.json').write_text(json.dumps(data,allow_nan=False),encoding='utf-8')
        return 0
    except Exception as exc:
        (output/'error.json').write_text(json.dumps({'error':str(exc)[:8192]}),encoding='utf-8'); return 1


class GenerationRunner(QObject):
    ready=Signal(int,object)
    failed=Signal(int,str)

    def __init__(self,parent=None,timeout_ms=60_000):
        super().__init__(parent)
        self.process=QProcess(self); self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.finished.connect(self.finished); self.process.errorOccurred.connect(self.process_error)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(timeout_ms); self.timer.timeout.connect(self.timeout)
        self.revision=None; self.directory=None; self.expected=[]; self.log=b''

    def command(self,source,output):
        return (sys.executable,['--generation-worker',source,output]) if getattr(sys,'frozen',False) else (sys.executable,['-m','morale.generation','--worker',source,output])

    def request(self,project,revision):
        self.cancel()
        source=project.dumps()
        if len(source.encode('utf-8'))>50_000_000: raise ValueError('Project exceeds the 50 MB preview worker limit.')
        self.directory=tempfile.TemporaryDirectory(prefix='morale-generation-'); root=Path(self.directory.name)
        (root/'input.morale').write_text(source,encoding='utf-8')
        self.expected=[{'object_id':o.id,'color':o.color,'color_break':o.color_break,'thread':deepcopy(o.thread)} for o in project.objects if o.visible]
        self.revision=revision; self.log=b''
        environment=QProcessEnvironment.systemEnvironment(); environment.insert('QT_QPA_PLATFORM','offscreen'); self.process.setProcessEnvironment(environment)
        program,args=self.command(str(root/'input.morale'),str(root))
        self.process.start(program,args)
        if self.revision is not None: self.timer.start()

    def read_output(self): self.log=(self.log+bytes(self.process.readAllStandardOutput()))[-8192:]

    def clean(self):
        if self.directory: self.directory.cleanup(); self.directory=None

    def cancel(self):
        self.revision=None; self.timer.stop()
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.process.kill(); self.process.waitForFinished(1000)
        self.clean()

    def finished(self,code,status):
        self.timer.stop()
        if self.revision is None: return
        revision=self.revision; self.revision=None
        try:
            self.read_output(); root=Path(self.directory.name)
            if code!=0:
                path=root/'error.json'
                message=json.loads(path.read_text(encoding='utf-8')).get('error','Preview failed.') if path.exists() and path.stat().st_size<=65536 else self.log.decode('utf-8',errors='replace') or 'Preview process failed.'
                raise ValueError(message)
            path=root/'blocks.json'
            if path.stat().st_size>64_000_000: raise ValueError('Preview result exceeds 64 MB.')
            blocks=decode_blocks(json.loads(path.read_text(encoding='utf-8')),self.expected)
        except (OSError,ValueError,TypeError,RecursionError) as exc:
            self.clean(); self.failed.emit(revision,str(exc)); return
        self.clean(); self.ready.emit(revision,blocks)

    def process_error(self,error):
        if error==QProcess.ProcessError.FailedToStart and self.revision is not None:
            revision=self.revision; message=self.process.errorString(); self.cancel(); self.failed.emit(revision,message)

    def timeout(self):
        revision=self.revision; self.cancel()
        if revision is not None: self.failed.emit(revision,'Stitch calculation timed out. Simplify the design or change stitch settings, then recalculate.')


if __name__=='__main__':
    sys.exit(worker_main(sys.argv[2:]) if len(sys.argv)>1 and sys.argv[1]=='--worker' else 2)
