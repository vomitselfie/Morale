"""Remove near-white background connected to the sampled page boundary."""
from PySide6.QtGui import QImage


def remove_border_white(image):
    if image.isNull():raise ValueError('No image supplied for background removal.')
    result=image.convertToFormat(QImage.Format.Format_RGBA8888)
    width,height=result.width(),result.height();raw=bytearray(result.constBits())
    eligible=bytearray(width*height)
    for index in range(width*height):
        r,g,b,a=raw[index*4:index*4+4]
        alpha=a/255
        eligible[index]=a<128 or min(round(c*alpha+255*(1-alpha)) for c in (r,g,b))>=245
    reached=bytearray(width*height);stack=[]
    def seed(index):
        if eligible[index] and not reached[index]:reached[index]=1;stack.append(index)
    for x in range(width):seed(x);seed((height-1)*width+x)
    for y in range(height):seed(y*width);seed(y*width+width-1)
    removed=0
    while stack:
        index=stack.pop();x=index%width;y=index//width
        if raw[index*4+3]>=128:removed+=1
        raw[index*4+3]=0
        if x:seed(index-1)
        if x+1<width:seed(index+1)
        if y:seed(index-width)
        if y+1<height:seed(index+width)
    result=QImage(bytes(raw),width,height,width*4,QImage.Format.Format_RGBA8888).copy()
    result.setColorSpace(image.colorSpace())
    return result,{'mode':'border_white','removed_pixels':removed,'connectivity':4}
