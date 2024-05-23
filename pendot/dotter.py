from typing import List, NamedTuple

from .constants import KEY
from .effect import Effect
from .glyphsbridge import (
    CURVE,
    LINE,
    OFFCURVE,
    GSComponent,
    GSFont,
    GSGlyph,
    GSInstance,
    GSLayer,
    GSNode,
    GSPath,
    GSShape,
    Message,
)
from .utils import (
    Segment,
    TuplePoint,
    TupleSegment,
    arclength,
    decomposedPaths,
    distance,
    pathLength,
    seg_to_tuples,
)

try:
    from fontTools.misc.bezierTools import (
        Intersection,
        linePointAtT,
        segmentSegmentIntersections,
        splitCubicAtT,
    )
    from fontTools.varLib.models import piecewiseLinearMap
except:
    Message("You need to install the fontTools library to run dotter")


class Center(NamedTuple):
    pos: TuplePoint
    forced: bool

    def distance(self, other):
        return distance(self.pos, other.pos)


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


def findIntersections(seg1: Segment, seg2: Segment) -> list[Intersection]:
    seg1 = seg_to_tuples(seg1)
    seg2 = seg_to_tuples(seg2)
    try:
        return segmentSegmentIntersections(seg1, seg2)
    except ZeroDivisionError:  # Defend against bad programmer (myself)
        return []


def splitSegment(seg: TupleSegment, t: float) -> tuple[TupleSegment, TupleSegment]:
    if len(seg) == 2:
        midpoint = linePointAtT(*seg, t)
        return [seg[0], midpoint], [midpoint, seg[1]]
    return splitCubicAtT(*seg, t)


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


def interpolate_lut(t, lut):
    lengths_map = {x[0]: x[1] for x in lut}
    xs_map = {x[0]: x[2] for x in lut}
    ys_map = {x[0]: x[3] for x in lut}
    return piecewiseLinearMap(t, lengths_map), (
        piecewiseLinearMap(t, xs_map),
        piecewiseLinearMap(t, ys_map),
    )


def findCenters(path: GSPath, params: dict, centers: list[Center], name: str):
    segs = [seg_to_tuples(seg) for seg in path.segments]
    if not segs or not segs[0]:
        return

    LIMIT = 100
    plen = pathLength(path)
    if plen == 0:
        return
    lengthSoFar = 0
    x_lut = {
        0: segs[0][0][0],
        1: segs[-1][-1][0],
    }
    y_lut = {
        0: segs[0][0][1],
        1: segs[-1][-1][1],
    }

    for seg in segs:
        seglen = arclength(seg)
        for t in range(1, LIMIT):
            local_t = t / LIMIT
            left, _right = splitSegment(seg, local_t)
            lengthHere = lengthSoFar + arclength(left, approx=True)
            global_t = lengthHere / plen
            x_lut[global_t] = left[-1][0]
            y_lut[global_t] = left[-1][1]
        lengthSoFar += seglen

    dotsize = params["dotSize"]
    orig_preferred_step = params["dotSize"] + params["dotSpacing"]
    max_flex = params["dotSize"] + params["dotSpacing"] * 1.25
    preferred_step = orig_preferred_step
    centers.append(Center(pos=segs[0][0], forced=True))
    centers.append(Center(pos=segs[-1][-1], forced=True))
    # Work out where the last-but-one dot should be
    iterations = 0
    while iterations < params["dotSpacing"]:
        num_dots = int(plen / preferred_step)
        this_t = preferred_step * num_dots / plen
        (x, y) = piecewiseLinearMap(this_t, x_lut), piecewiseLinearMap(this_t, y_lut)
        last_but_one = Center(pos=(x, y), forced=False)
        # If the last but one dot is within, let's say, 10% of a dotsize, we're
        # OK because it will be removed by the overlap prevention code. But
        # if we're between 10% dotsize and 125% of spacing, we need to re-evaluate
        lbo_distance = last_but_one.distance(centers[-1])
        if lbo_distance < 0.1 * dotsize or lbo_distance > max_flex:
            break
        # Walk up and down the path to find a better step size
        preferred_step = orig_preferred_step + (-1) ** iterations * iterations
        # print(
        #     "ITeration ",
        #     iterations,
        #     "Retrying with distance ",
        #     lbo_distance,
        #     " and preferred step ",
        #     preferred_step,
        # )
        iterations += 1
    start = preferred_step  # Ignore first point
    while start < plen:
        this_t = start / plen
        (x, y) = piecewiseLinearMap(this_t, x_lut), piecewiseLinearMap(this_t, y_lut)
        centers.append(Center(pos=(x, y), forced=False))
        start += preferred_step


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
    newnodes[insertion_point_index : insertion_point_index + middle + 1] = (
        nodes_to_insert
    )
    # Copy any forcing
    forced_positions = [x.position for x in path.nodes if isForced(x)]
    for node in newnodes:
        for pt in forced_positions:
            if distance(node.position, pt) < 0.5:
                set_locally_forced(node)
    path.nodes = newnodes
    # print("New path nodes", path.nodes)


def boundsIntersect(bounds1, bounds2):
    return (
        bounds1.origin.x <= bounds2.origin.x + bounds2.size.width
        and bounds1.origin.x + bounds1.size.width >= bounds2.origin.x
        and bounds1.origin.y <= bounds2.origin.y + bounds2.size.height
        and bounds1.origin.y + bounds1.size.height >= bounds2.origin.y
    )


def splitPathsAtIntersections(paths):
    # We don't necessarily need to split the paths; we can
    # get away with adding a new node and setting it to forced.
    for p1 in paths:
        for p2 in paths:
            if p1 == p2:
                continue
            if not boundsIntersect(p1.bounds, p2.bounds):
                continue
            for s1 in p1.segments:
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


class Dotter(Effect):
    params = {
        "dotSize": 15,
        "dotSpacing": 15,
        "preventOverlaps": True,
        "splitPaths": False,
        "contourSource": "<Default>",
    }

    @property
    def display_params(self):
        return ["dotSize", "dotSpacing"]

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        if layer.parent.name == "_dot":
            return layer.shapes
        params = {p: self.parameter(p, layer) for p in self.params.keys()}
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
                findCenters(subpath, params, centers, layer.parent.name)
        new_paths = self.centers_to_paths(centers, params)

        for path in sourcelayer.paths:
            for node in path.nodes:
                clear_locally_forced(node)
        return new_paths

    def postprocess_font(self):
        # Add the component glyph
        if self.font.glyphs["_dot"]:
            glyph = self.font.glyphs["_dot"]
        else:
            glyph = GSGlyph("_dot")
            self.font.glyphs.append(glyph)
        size = self.instance.customParameters[KEY + ".dotSize"]
        for master in self.font.masters:
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

    def centers_to_paths(self, centers: list[Center], params: dict):
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

        # If we are in Glyphsapp, then we want to draw a dot
        if self.preview:
            return [makeCircle(c, params["dotSize"] / 2) for c in newcenters]
        return [GSComponent("_dot", c) for c in newcenters]
