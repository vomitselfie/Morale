"""Byte-counted text helpers for the upstream PES/PEC/VP3 binary writers.

Each adapter has its own function globals: no installed modules or process-global
writer functions are patched. PEC encoding also omits the upstream synthetic
needle point before a diagonal stitch after travel. VP3 uses actual first-block
start coordinates instead of a forced origin.
"""
from functools import lru_cache
import struct
import types
from pyembroidery import EmbPattern,PecWriter,PesWriter,Vp3Writer
from pyembroidery.EmbConstant import COMMAND_MASK,STITCH,JUMP,COLOR_CHANGE,END


def _adapter(module,replacements):
    namespace=dict(vars(module))
    for name,value in vars(module).items():
        if isinstance(value,types.FunctionType) and value.__module__==module.__name__:
            namespace[name]=types.FunctionType(value.__code__,namespace,name,value.__defaults__,value.__closure__)
    namespace.update(replacements)
    return types.SimpleNamespace(**namespace)


def _utf8(stream,text,format,limit):
    data=('' if text is None else str(text)).encode('utf-8')
    if len(data)>limit:data=data[:limit].decode('utf-8','ignore').encode('utf-8')
    stream.write(struct.pack(format,len(data)));stream.write(data)


def _pec_pattern(pattern):
    result=pattern.copy()
    result.metadata('name',str(pattern.get_metadata('name','Untitled')).encode('ascii','replace').decode('ascii')[:8])
    return result


def _pec_encode(pattern,stream):
    # Based on pyembroidery PecWriter.pec_encode (MIT). Preserve its command
    # encoding, but do not add a zero-length stitch at the preceding jump end
    # solely because the next sewn segment has both X and Y displacement.
    color_two=True;jumping=True;initial=True;x0=y0=0
    for x,y,encoded in pattern.stitches:
        command=encoded & COMMAND_MASK;dx=int(round(x-x0));dy=int(round(y-y0));x0+=dx;y0+=dy
        if command==STITCH:
            jumping=False;PecWriter.write_stitch(stream,dx,dy)
        elif command==JUMP:
            jumping=True
            (PecWriter.write_jump if initial else PecWriter.write_trimjump)(stream,dx,dy)
        elif command==COLOR_CHANGE:
            if jumping:PecWriter.write_stitch(stream,0,0);jumping=False
            stream.write(bytes((254,176,2 if color_two else 1)));color_two=not color_two
        elif command==END:
            stream.write(bytes((255,)));break
        initial=False


@lru_cache(maxsize=1)
def _pec_encoder():return _adapter(PecWriter,{'pec_encode':_pec_encode})


def _embedded_pec(pattern,stream,*args,**kwargs):
    return _pec_encoder().write_pec(_pec_pattern(pattern),stream,*args,**kwargs)


@lru_cache(maxsize=3)
def writer(extension):
    if extension=='.pes':
        return _adapter(PesWriter,{'write_pes_string_8':lambda f,s:_utf8(f,s,'B',255),
            'write_pes_string_16':lambda f,s:_utf8(f,s,'<H',65535),'write_pec':_embedded_pec})
    if extension=='.vp3':
        adapted=_adapter(Vp3Writer,{'vp3_write_string_8':lambda f,s:_utf8(f,s,'>H',65535)})
        colorblock=adapted.write_vp3_colorblock
        def positioned_colorblock(stream,first,cx,cy,stitches,thread):
            return colorblock(stream,False,int(cx),int(cy),stitches,thread)
        # Change only this adapter's private globals. The first color block
        # uses its actual start just as subsequent blocks already do.
        adapted.write.__globals__['write_vp3_colorblock']=positioned_colorblock
        adapted.write_vp3_colorblock=positioned_colorblock
        return adapted
    if extension=='.pec':
        return _adapter(PecWriter,{'write_pec':_embedded_pec})
    raise ValueError('No text adapter for this writer.')


def write(pattern,path,extension,settings=None):
    EmbPattern.write_embroidery(writer(extension),pattern,str(path),settings)
