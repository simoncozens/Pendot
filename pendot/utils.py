import math
from typing import Optional, Union
import copy
from fontTools.misc.transform import Identity, Transform


from pendot.glyphsbridge import (
    GSPath,
    GSNode,
    GSLayer,
    OFFCURVE,
    CURVE,
    GSLINE,
    Message,
)

try:
    from fontTools.misc.bezierTools import (
        approximateCubicArcLength,
        calcCubicArcLength,
    )
except ImportError:
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


def seg_to_kurbo(seg: Segment) -> TupleSegment:
    import kurbopy

    if type(seg).__name__ == "GSPathSegment":
        seg = seg.segmentStruct()[0][0 : seg.countOfPoints()]
    seg = [kurbopy.Point(pt.x, pt.y) for pt in seg]
    if len(seg) == 4:
        return kurbopy.CubicBez(*seg)
    else:
        return kurbopy.Line(*seg)


def path_to_kurbo(path: GSPath):
    import kurbopy

    bezpath = kurbopy.BezPath()

    for ix, seg in enumerate(path.segments):
        if type(seg).__name__ == "GSPathSegment":
            seg = seg.segmentStruct()[0][0 : seg.countOfPoints()]
        if ix == 0:
            bezpath.move_to(kurbopy.Point(seg[0].x, seg[0].y))
        if len(seg) == 4:
            bezpath.curve_to(
                kurbopy.Point(seg[1].x, seg[1].y),
                kurbopy.Point(seg[2].x, seg[2].y),
                kurbopy.Point(seg[3].x, seg[3].y),
            )
        else:
            bezpath.line_to(kurbopy.Point(seg[1].x, seg[1].y))
    if path.closed:
        bezpath.close_path()
    return bezpath


def kurbo_bounds_intersect(b1: "Rect", b2: "Rect") -> bool:
    return b1.intersect(b2).size().max_side() > 0


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
            path.closed = shape.closed
            path.applyTransform(ctm)
            outpaths.append(path)
        else:
            their_ctm = Transform(*shape.transform).transform(ctm)
            outpaths.extend(decomposedPaths(shape.layer, their_ctm))
    return outpaths


def append_cubicseg(path, points):
    path.nodes.append(GSNode(points[0], OFFCURVE))
    path.nodes.append(GSNode(points[1], OFFCURVE))
    path.nodes.append(GSNode(points[2], CURVE))


def makeCircle(center: TuplePoint, radius: float):
    centerx, centery = center
    path = GSPath()
    # We are using eight 45 degree circle segments, for accuracy at
    # small sizes

    # Work out the numbers for a unit circle, then scale and
    # move them.
    a_circle = [
        [(1, 0.265216), (0.894643, 0.51957), (0.7071, 0.7071)],
        [(0.51957, 0.894643), (0.265216, 1), (0, 1)],
        [(-0.265216, 1), (-0.51957, 0.894643), (-0.7071, 0.7071)],
        [(-0.894643, 0.51957), (-1, 0.265216), (-1, 0)],
        [(-1, -0.265216), (-0.894643, -0.51957), (-0.7071, -0.7071)],
        [(-0.51957, -0.894643), (-0.265216, -1), (0, -1)],
        [(0.265216, -1), (0.51957, -0.894643), (0.7071, -0.7071)],
        [(0.894643, -0.51957), (1, -0.265216), (1, 0)],
    ]
    for segment in a_circle:
        append_cubicseg(
            path, [(x * radius + centerx, y * radius + centery) for (x, y) in segment]
        )
    path.closed = True
    for ix, node in enumerate(path.nodes):
        if (ix + 1) % 3:
            node.smooth = True
    return path


# from https://github.com/mekkablue/Glyphs-Scripts/blob/a4421210dd17305e3205b7ca998cab579b778bf6/Paths/Fill%20Up%20with%20Rectangles.py
def makeRect(myBottomLeft, myTopRight):
    myRect = GSPath()
    myCoordinates = [
        [myBottomLeft[0], myBottomLeft[1]],
        [myTopRight[0], myBottomLeft[1]],
        [myTopRight[0], myTopRight[1]],
        [myBottomLeft[0], myTopRight[1]],
    ]

    for thisPoint in myCoordinates:
        newNode = GSNode((thisPoint[0], thisPoint[1]), GSLINE)
        myRect.nodes.append(newNode)

    myRect.closed = True
    return myRect
