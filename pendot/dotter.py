import copy
import math
from typing import Optional, Union, NamedTuple
from fontTools.misc.transform import Identity, Transform
from .constants import KEY, getParams

try:
    from GlyphsApp import (
        GSFont,
        GSInstance,
        GSPath,
        GSComponent,
        GSGlyph,
        GSNode,
        GSLayer,
        OFFCURVE,
        CURVE,
        LINE,
        Message,
    )
except:
    from glyphsLib.classes import (
        GSFont,
        GSInstance,
        GSPath,
        GSLayer,
        GSComponent,
        GSGlyph,
        GSNode,
        OFFCURVE,
        CURVE,
        LINE,
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


class Center(NamedTuple):
    pos: TuplePoint
    forced: bool

    def distance(self, other):
        return distance(self.pos, other.pos)


TupleSegment = list[TuplePoint]

DOTTER_PARAMS = {
    "dotSize": 15,
    "dotSpacing": 15,
    "preventOverlaps": True,
    "splitPaths": False,
    "contourSource": "<Default>",
}


def distance(a: TuplePoint, b: TuplePoint) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def set_locally_forced(node: GSNode) -> None:
    if KEY not in node.userData:
        node.userData[KEY] = {}
    node.userData[KEY]["locally_forced"] = True


def clear_locally_forced(node: GSNode) -> None:
    # print("Clearing force from ", node)
    if KEY in node.userData and node.userData["KEY"]:
        if "locally_forced" in node.userData["KEY"]:
            del node.userData[KEY]["locally_forced"]
        if not node.userData[KEY]:
            del node.userData[KEY]
    # print(node.userData)


def is_start_end(node: GSNode) -> bool:
    return node.index == 0 or node.index == len(node.parent.nodes) - 1


def isForced(node: GSNode) -> bool:
    # if is_start_end(node):
    #     return True
    return KEY in node.userData and (
        node.userData[KEY].get("forced") or node.userData[KEY].get("locally_forced")
    )


# All the curve-handling code here has to work both in Glyphs and glyphsLib.
# Here are some utility functions to bridge the gap
def seg_to_tuples(seg: Segment) -> TupleSegment:
    if type(seg).__name__ == "GSPathSegment":
        seg = seg.segmentStruct()[0][0 : seg.countOfPoints()]
    return [(pt.x, pt.y) for pt in seg]


def findIntersections(seg1: Segment, seg2: Segment) -> list[Intersection]:
    seg1 = seg_to_tuples(seg1)
    seg2 = seg_to_tuples(seg2)
    return segmentSegmentIntersections(seg1, seg2)


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


def splitSegment(seg: TupleSegment, t: float) -> tuple[TupleSegment, TupleSegment]:
    if len(seg) == 2:
        midpoint = linePointAtT(*seg, t)
        return [seg[0], midpoint], [midpoint, seg[1]]
    return splitCubicAtT(*seg, t)


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

# This is just for display purposes; for the real thing we'll use a
# component

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
        [ (1, 0.265216), (0.894643, 0.51957), (0.7071,0.7071) ],
        [ (0.51957, 0.894643), (0.265216, 1), (0, 1) ],
        [ (-0.265216,1), (-0.51957, 0.894643), (-0.7071,0.7071) ],
        [ (-0.894643, 0.51957), (-1, 0.265216), (-1, 0) ],
        [ (-1, -0.265216), (-0.894643, -0.51957), (-0.7071, -0.7071) ],
        [ (-0.51957, -0.894643), (-0.265216, -1), (0, -1) ],
        [ (0.265216,-1), (0.51957, -0.894643), (0.7071,-0.7071) ],
        [ (0.894643, -0.51957), (1, -0.265216), (1, 0) ],
    ]
    for segment in a_circle:
        append_cubicseg(path,
            [ (x*radius + centerx, y*radius + centery) for (x,y) in segment ]
        )
    path.closed = True
    for ix, node in enumerate(path.nodes):
        if (ix + 1) % 3:
            node.smooth = True
    return path


def addComponentGlyph(font: GSFont, instance: GSInstance):
    if font.glyphs["_dot"]:
        glyph = font.glyphs["_dot"]
    else:
        glyph = GSGlyph("_dot")
        font.glyphs.append(glyph)
    size = instance.userData[KEY+".dotSize"]
    for master in font.masters:
        if glyph.layers[master.id]:
            layer = glyph.layers[master.id]
            layer.shapes = []
        else:
            layer = GSLayer()
            if hasattr(glyph, "_setupLayer"):
                glyph._setupLayer(layer, master.id)
            else:
                layer.layerId = master.id
                layer.associatedMasterId = master.id
            glyph.layers.append(layer)
        layer.paths.append(makeCircle((0, 0), size / 2))


def splitAtForcedNode(path: GSPath):
    # Iterator, yields GSPaths
    new_path = GSPath()
    new_path.closed = False
    for n in path.nodes:
        new_path.nodes.append(GSNode(n.position, n.type))
        if isForced(n):
            yield new_path
            new_path = GSPath()
            new_path.closed = False
            new_path.nodes.append(GSNode(n.position, n.type))
    yield new_path


def findCenters(path: GSPath, params: dict, centers: list[Center]):
    segs = [seg_to_tuples(seg) for seg in path.segments]
    LIMIT = 1000
    # The effective path length, i.e. the amount we have to fill
    # gets reduced by half a dot at the start and half a dot at the end
    plen = pathLength(path) - params["dotSize"]
    centerSpace = params["dotSize"] + params["dotSpacing"]
    if not segs or not segs[0]:
        return
    iterations = 0
    if centerSpace < plen:
        centerSpace = plen / math.ceil(plen / centerSpace)
    while True:
        lengthSoFar = 0
        newcenters = []
        lastLength = 0
        newcenters.append(Center(pos=segs[0][0], forced=True))
        newcenters.append(Center(pos=segs[-1][-1], forced=True))
        # Adjust space such that end point falls at integer multiples
        for pathtime, seg in enumerate(segs):
            for t in range(1, LIMIT):
                left, _right = splitSegment(seg, t / LIMIT)
                lengthHere = lengthSoFar + arclength(left, approx=True)
                if lengthHere > lastLength + centerSpace:
                    newcenters.append(Center(pos=left[-1], forced=False))
                    lastLength = lengthHere

            lengthSoFar += arclength(seg)
        if newcenters[1].distance(newcenters[-1]) > params["dotSize"]:
            centers.extend(newcenters)
            return
        # Try again...
        centerSpace += 1
        iterations += 1
        if iterations > 100:
            print("Could not find a good solution, approximating")
            centers.extend(newcenters)
            return
    print(centers)


def centersToPaths(centers: list[Center], params, component=False):
    if params["preventOverlaps"]:
        newcenters = []
        # Sort, to put forced points first
        for c in sorted(centers, key=lambda pt: pt.forced, reverse=True):
            # This could probably be improved...
            ok = True
            for nc in newcenters:
                if distance(c.pos, nc) < params["dotSize"]:
                    ok = False
                    break
            if ok:
                newcenters.append(c.pos)
    else:
        newcenters = [c.pos for c in centers]

    if component:
        # Fixme - alter the size of the component if overridden
        return [GSComponent("_dot", c) for c in newcenters]
    else:
        return [makeCircle(c, params["dotSize"] / 2) for c in newcenters]


def insertPointInPathUnlessThere(path, pt: TuplePoint):
    node: GSNode
    for node in path.nodes:
        if distance((node.position.x, node.position.y), pt) < 1.0:
            set_locally_forced(node)
            return
    # Find nearest point on nearest segment
    min_dist = 100000000
    insertion_point_index = None
    new_left_right: tuple[TupleSegment, TupleSegment] = None
    TICKS = 1000
    index = 0
    for seg in path.segments:
        seg = seg_to_tuples(seg)
        for t in range(1, TICKS):
            left, right = splitSegment(seg, t / TICKS)
            dist = distance(left[-1], pt)
            if dist < min_dist:
                min_dist = dist
                new_left_right = left + right[1:]
                insertion_point_index = index
        index += len(seg) - 1
    if insertion_point_index is None:
        raise ValueError("Point not on path...")
    # print("Old path nodes", path.nodes)
    # print("Splitting path at ", pt, " to ", new_left_right)
    # print("Insertion index was ", insertion_point_index)
    if len(new_left_right) == 3:  # We have split a line
        node_types = [LINE, LINE, LINE]
        middle = 1
    else:
        node_types = [CURVE, OFFCURVE, OFFCURVE, CURVE, OFFCURVE, OFFCURVE, CURVE]
        middle = 3
    nodes_to_insert = [GSNode(x, typ) for x, typ in zip(new_left_right, node_types)]
    set_locally_forced(nodes_to_insert[middle])
    newnodes = list(path.nodes)
    newnodes[
        insertion_point_index : insertion_point_index + middle + 1
    ] = nodes_to_insert
    path.nodes = newnodes
    # print("New path nodes", path.nodes)


def boundsIntersect(bounds1, bounds2):
    return (
        bounds1.origin.x < bounds2.origin.x + bounds2.size.width
        and bounds1.origin.x + bounds1.size.width > bounds2.origin.x
        and bounds1.origin.y < bounds2.origin.y + bounds2.size.height
        and bounds1.origin.y + bounds1.size.height > bounds2.origin.y
    )

def splitPathsAtIntersections(paths):
    # We don't necessarily need to split the paths; we can
    # get away with adding a new node and setting it to forced.
    for p1 in paths:
        for s1 in p1.segments:
            for p2 in paths:
                if p1 == p2:
                    continue
                if not boundsIntersect(p1.bounds, p2.bounds):
                    continue
                for s2 in p2.segments:
                    # Yes this is O(n^2). Yes I could improve it.
                    # Let's see if it's actually a problem first.
                    intersections = findIntersections(s1, s2)
                    for i in intersections:
                        if not (i.t1 >= 0 and i.t1 <= 1) or not (
                            i.t2 >= 0 and i.t2 <= 1
                        ):
                            continue
                        # print(
                        #     "Intersection between %s/%s and %s/%s at %s"
                        #     % (p1, s1, p2, s2, i.pt)
                        # )
                        insertPointInPathUnlessThere(p1, i.pt)
                        insertPointInPathUnlessThere(p2, i.pt)

def doDotter(layer, instance, cmd_line_params=None, component=True):
    if layer.parent.name == "_dot":
        return
    params = getParams(layer, instance, DOTTER_PARAMS, cmd_line_params=cmd_line_params)
    if (
        params["contourSource"] != "<Default>"
        and layer.parent.layers[params["contourSource"]]
    ):
        sourcelayer = layer.parent.layers[params["contourSource"]]
    else:
        sourcelayer = layer
    centers = []
    paths = decomposedPaths(sourcelayer)
    if params["splitPaths"]:
        splitPathsAtIntersections(paths)
    for path in paths:
        for subpath in splitAtForcedNode(path):
            findCenters(subpath, params, centers)
    new_paths = centersToPaths(centers, params, component=component)

    for path in sourcelayer.paths:
        for node in path.nodes:
            clear_locally_forced(node)
    return new_paths
