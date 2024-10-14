from dataclasses import dataclass
from typing import List, Optional

from ufostroker.ufostroker import constant_width_stroke as cws_rust

from pendot.effect import Effect
from pendot.glyphsbridge import CURVE, LINE, OFFCURVE, GSNode, GSPath, GSLayer, GSShape

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


class Stroker(Effect):
    params = {
        "strokerWidth": {"default": 50, "help": "Width of the stroke in font units"},
        "strokerHeight": {
            "default": None,
            "type": int,
            "help": "Height of the stroke; if not set, it will be the same as the width",
        },
        "strokerAngle": {"default": 0, "help": "Angle of the stroke in degrees"},
        "startCap": {
            "default": "round",
            "choices": ["round", "square", "circle"],
            "help": "Type of start cap",
        },
        "endCap": {
            "default": "round",
            "choices": ["round", "square", "circle"],
            "help": "Type of end cap",
        },
        "joinType": {
            "default": "round",
            "choices": ["round", "bevel", "mitre", "circle"],
            "help": "Type of join",
        },
        "removeExternal": {
            "default": False,
            "help": "Remove external overlaps of the stroke",
        },
        "removeInternal": {
            "default": False,
            "help": "Remove internal overlaps of the stroke",
        },
        "segmentWise": {
            "default": False,
            "help": "Stroke each segment of the path independently (use with circular caps and joins)",
        },
    }

    @property
    def display_params(self):
        return ["strokerWidth"]

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        if not shapes:
            return []
        list_of_list_of_nodes = []

        for path in shapes:
            list_of_list_of_nodes.append(
                [Point.fromGSPoint(p, ix) for ix, p in enumerate(path.nodes)]
            )

        startcap = self.parameter("startCap", layer).lower()
        endcap = self.parameter("endCap", layer).lower()
        jointype = self.parameter("joinType", layer).lower()
        if startcap not in self.params["startCap"]["choices"]:
            raise ValueError("Unknown start cap type")
        if endcap not in self.params["endCap"]["choices"]:
            raise ValueError("Unknown end cap type")
        if jointype not in self.params["joinType"]["choices"]:
            raise ValueError("Unknown join type")

        height = self.parameter("strokerHeight", layer)
        if height is None:
            height = self.parameter("strokerWidth", layer)

        result = cws_rust(
            list_of_list_of_nodes,
            width=float(self.parameter("strokerWidth", layer)) / 2,
            height=float(height) / 2,
            angle=float(self.parameter("strokerAngle", layer) or 0),
            startcap=startcap,
            endcap=endcap,
            jointype=jointype,
            remove_internal=bool(self.parameter("removeInternal", layer)),
            remove_external=bool(self.parameter("removeExternal", layer)),
            segmentwise=bool(self.parameter("segmentWise", layer)),
        )
        newpaths = []
        for res_path in result:
            path = GSPath()
            path.closed = True
            for x, y, typ in res_path:
                path.nodes.append(GSNode((x, y), type_map[typ]))
            newpaths.append(path)
        return newpaths
