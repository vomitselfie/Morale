"""Oklab distances for sRGB thread-chart swatches (D65, no ICC conversion).

Equations: Björn Ottosson, https://bottosson.github.io/posts/oklab/
The reference implementation is offered in the public domain.
"""
from functools import lru_cache
from .catalogs import rgb


@lru_cache(maxsize=20000)
def oklab(color):
    channels=[v/255 for v in rgb(color)]
    r,g,b=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
    l=(.4122214708*r+.5363325363*g+.0514459929*b)**(1/3)
    m=(.2119034982*r+.6806995451*g+.1073969566*b)**(1/3)
    s=(.0883024619*r+.2817188376*g+.6299787005*b)**(1/3)
    return (.2104542553*l+.7936177850*m-.0040720468*s,
            1.9779984951*l-2.4285922050*m+.4505937099*s,
            .0259040371*l+.7827717662*m-.8086757660*s)


def distance_squared(a,b):
    # Scale by 100 for a readable displayed distance. This is not CIEDE2000.
    return 10000*sum((x-y)**2 for x,y in zip(oklab(a),oklab(b)))
