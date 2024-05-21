from dataclasses import dataclass
from typing import Optional
from .constants import getParams

try:
    from GlyphsApp import GSNode, GSPath, OFFCURVE, LINE, CURVE
except:
    from glyphsLib.classes import GSNode, GSPath, OFFCURVE, LINE, CURVE

from .utils import decomposedPaths
from ufostroker.ufostroker import constant_width_stroke as cws_rust

STROKER_PARAMS = {
    "strokerWidth": 50,
    "strokerHeight": 50,
    "strokerAngle": 0,
    "strokerHeightLock": True,
    "startCap": "round",
    "endCap": "round",
    "joinType": "round",
    "removeExternal": False,
    "removeInternal": False,
    "segmentWise": False,
}

type_map = {"": OFFCURVE, "curve": CURVE, "line": LINE}


@dataclass
class Point:
    x: float
    y: float
    type: Optional[str]  # move,line,curve,None

    @classmethod
    def fromGSPoint(cls, pt, ix=None):
        typ = pt.type
        if typ == OFFCURVE:
            typ = None
        if ix is not None and ix == 0:
            typ = "move"
        return cls(pt.position.x, pt.position.y, typ)


def doStroker(layer, instance, cmd_line_params=None):
    params = getParams(layer, instance, STROKER_PARAMS, cmd_line_params=cmd_line_params)
    if not layer.paths:
        return
    list_of_list_of_nodes = []

    for path in decomposedPaths(layer):
        list_of_list_of_nodes.append(
            [Point.fromGSPoint(p, ix) for ix, p in enumerate(path.nodes)]
        )

    startcap = params["startCap"].lower()
    endcap = params["endCap"].lower()
    jointype = params["joinType"].lower()
    if startcap not in ["round", "square", "circle"]:
        raise ValueError("Unknown start cap type")
    if endcap not in ["round", "square", "circle"]:
        raise ValueError("Unknown end cap type")
    if jointype not in ["round", "bevel", "mitre", "circle"]:
        raise ValueError("Unknown join type")

    result = cws_rust(
        list_of_list_of_nodes,
        width=float(params["strokerWidth"]) / 2,
        height=float(params["strokerHeight"]) / 2,
        angle=float(params["strokerAngle"] or 0),
        startcap=startcap,
        endcap=endcap,
        jointype=jointype,
        remove_internal=bool(params["removeInternal"]),
        remove_external=bool(params["removeExternal"]),
        segmentwise=bool(params["segmentWise"]),
    )
    newpaths = []
    for res_path in result:
        path = GSPath()
        path.closed = True
        for x, y, typ in res_path:
            path.nodes.append(GSNode((x, y), type_map[typ]))
        newpaths.append(path)
    return newpaths
