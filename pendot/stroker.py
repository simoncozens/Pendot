from dataclasses import dataclass
from typing import Optional

try:
    from GlyphsApp import GSNode, GSPath, OFFCURVE, LINE, CURVE
except:
    from glyphsLib.classes import GSNode, GSPath, OFFCURVE, LINE, CURVE

from ufostroker.ufostroker import constant_width_stroke as cws_rust

type_map = {
    "": OFFCURVE,
    "curve": CURVE,
    "line": LINE
}

@dataclass
class Point:
    x: float
    y: float
    type: Optional[str] # move,line,curve,None

    @classmethod
    def fromGSPoint(cls, pt, ix=None):
        typ = pt.type
        if typ == OFFCURVE:
            typ = None
        if ix is not None and ix == 0:
            typ = 'move'
        return cls(pt.position.x, pt.position.y, typ)


def doStroker(layer, params: dict):
    if not layer.paths:
        return
    list_of_list_of_nodes = []
    for path in layer.paths:
        list_of_list_of_nodes.append([
            Point.fromGSPoint(p, ix) for ix, p in enumerate(path.nodes)
        ])

    result = cws_rust(list_of_list_of_nodes, **params)
    layer.shapes = []
    for res_path in result:
        path = GSPath()
        path.closed = True
        for x,y,typ in res_path:
            path.nodes.append(GSNode((x,y), type_map[typ]))
        layer.shapes.append(path)


