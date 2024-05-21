import math
from typing import Optional, Union
import copy
from fontTools.misc.transform import Identity, Transform


try:
    from GlyphsApp import (
        GSPath,
        GSNode,
        GSLayer,
        Message,
    )
except ImportError:
    from glyphsLib.classes import (
        GSPath,
        GSLayer,
        GSNode,
    )
    import sys

    def Message(message):
        print(message)
        sys.exit(1)


try:
    from fontTools.misc.bezierTools import (
        Intersection,
        segmentSegmentIntersections,
        approximateCubicArcLength,
        calcCubicArcLength,
        linePointAtT,
        splitCubicAtT,
    )
except:
    Message("You need to install the fontTools library to run dotter")


Segment = Union["GSPathSegment", list[GSNode]]
TuplePoint = tuple[float, float]
TupleSegment = list[TuplePoint]


def distance(a: TuplePoint, b: TuplePoint) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


# All the curve-handling code here has to work both in Glyphs and glyphsLib.
# Here are some utility functions to bridge the gap
def seg_to_tuples(seg: Segment) -> TupleSegment:
    if type(seg).__name__ == "GSPathSegment":
        seg = seg.segmentStruct()[0][0 : seg.countOfPoints()]
    return [(pt.x, pt.y) for pt in seg]


def arclength(seg: Union[Segment, TupleSegment], approx=False) -> float:
    # For GSSegments, we could just return seg.length() here, but we want to
    # ensure that the same algorithm is used in both Glyphs and
    # glyphsLib for visual consistency.

    if not isinstance(seg[0], tuple):
        seg = seg_to_tuples(seg)
    if len(seg) == 2:
        return distance(seg[0], seg[1])
    if approx:
        return approximateCubicArcLength(*seg)
    return calcCubicArcLength(*seg)


def pathLength(path: GSPath) -> float:
    return sum(arclength(seg) for seg in path.segments)


def decomposedPaths(layer: GSLayer, ctm: Optional[Transform] = None) -> list[GSPath]:
    if hasattr(layer, "copyDecomposedLayer"):
        return layer.copyDecomposedLayer().paths
    if ctm is None:
        ctm = Identity
    outpaths = []
    for shape in layer.shapes:
        if isinstance(shape, GSPath):
            path = GSPath()
            for node in shape.nodes:
                copied = node.clone()
                copied._userData = copy.deepcopy(node._userData)
                path.nodes.append(copied)
            path.applyTransform(ctm)
            outpaths.append(path)
        else:
            their_ctm = Transform(*shape.transform).transform(ctm)
            outpaths.extend(decomposedPaths(shape.layer, their_ctm))
    return outpaths
