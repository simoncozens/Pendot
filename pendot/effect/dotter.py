from typing import List, NamedTuple

import kurbopy
from pendot.constants import KEY
from pendot.effect import Effect
from pendot.glyphsbridge import (
    CURVE,
    LINE,
    OFFCURVE,
    GSComponent,
    GSGlyph,
    GSLayer,
    GSNode,
    GSPath,
    GSShape,
    Message,
)
from pendot.utils import (
    Segment,
    TuplePoint,
    TupleSegment,
    decomposedPaths,
    distance,
    kurbo_bounds_intersect,
    path_to_kurbo,
    seg_to_tuples,
    seg_to_kurbo,
    makeCircle,
)

try:
    from fontTools.misc.bezierTools import (
        Intersection,
        linePointAtT,
        segmentSegmentIntersections,
        splitCubicAtT,
    )
    from fontTools.varLib.models import piecewiseLinearMap
except ImportError:
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


def findIntersections(seg1: Segment, seg2: Segment) -> List["Intersection"]:
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
    segs = [seg_to_kurbo(seg) for seg in path.segments]
    if not segs or not segs[0]:
        return

    pathstart = segs[0].start()
    pathend = segs[-1].end()

    LIMIT = 100
    plen = sum([seg.arclen(0.1) for seg in segs])
    if plen == 0:
        return
    lengthSoFar = 0
    x_lut = {
        0: pathstart.x,
        1: pathend.x,
    }
    y_lut = {
        0: pathstart.y,
        1: pathend.y,
    }
    distance_lut = {
        0: 0,
        1: plen,
    }

    for seg in segs:
        seglen = seg.arclen(0.1)
        for t in range(1, LIMIT):
            local_t = t / LIMIT
            left = seg.subsegment((0, local_t))
            lengthHere = lengthSoFar + left.arclen(0.1)
            global_t = lengthHere / plen
            leftend = left.end()
            x_lut[global_t] = leftend.x
            y_lut[global_t] = leftend.y
            distance_lut[global_t] = lengthHere
        lengthSoFar += seglen

    inverted_distance_lut = {v: k for k, v in distance_lut.items()}

    dotsize = params["dotSize"]
    orig_preferred_step = dotsize + params["dotSpacing"]
    # print(f"Path length is {plen}")
    # print(f"Original preferred step is {orig_preferred_step}")
    dotcount = plen / orig_preferred_step
    preferred_step = orig_preferred_step
    # print(f"We have {dotcount} dots")
    residue = (int(dotcount) - dotcount) * orig_preferred_step
    # print(f"We have {residue} units left over")
    # Adjust preferred step to fit residue
    adjustment = residue / int(max(dotcount, 1))
    if abs(adjustment / params["dotSpacing"]) <= (params["flexPercent"] / 100):
        preferred_step = orig_preferred_step - adjustment
    # else:
    #     print("Could not adjust dot spacing to form an even number of dots")
    # print(f"New preferred step is {preferred_step}")
    # print(f"This yields {plen / preferred_step} dots")

    centers.append(Center(pos=[x_lut[0], y_lut[0]], forced=True))
    centers.append(Center(pos=[x_lut[1], y_lut[1]], forced=True))

    start = preferred_step  # Ignore first point
    while start < plen:
        this_t = piecewiseLinearMap(start, inverted_distance_lut)
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
    best = None
    new_left_right: tuple[TupleSegment, TupleSegment] = None
    nearest_seg = None
    insertion_point_index = None
    kpt = kurbopy.Point(pt[0], pt[1])
    index = 0
    for ix, seg in enumerate(path.segments):
        kseg = seg_to_kurbo(seg)
        nearest = kseg.nearest(kpt, 0.1)
        if best is None or nearest.get_distance_sq() < best.get_distance_sq():
            best = nearest
            nearest_seg = ix
            best_t = nearest.get_t()
            left, right = kseg.subsegment((0, best_t)), kseg.subsegment((best_t, 1))
            if isinstance(left, kurbopy.CubicBez):
                new_left_right = [
                    (p.x, p.y)
                    for p in [
                        left.p0,
                        left.p1,
                        left.p2,
                        left.p3,
                        right.p1,
                        right.p2,
                        right.p3,
                    ]
                ]
            else:
                new_left_right = [
                    (left.start().x, left.start().y),
                    pt,
                    (right.end().x, right.end().y),
                ]
            insertion_point_index = index
        index += len(seg) - 1
    if nearest_seg is None:
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
    if len(paths) == 1:
        return
    for ix, p1 in enumerate(paths):
        p1_kurbo = path_to_kurbo(p1)
        p1_bounds = p1_kurbo.bounding_box()
        # Compiling the list of segments is expensive (and their bounds)
        # is expensive, do it in advance
        segs1 = p1.segments
        s1_bboxes = [seg_to_kurbo(s).bounding_box() for s in segs1]
        for p2 in list(paths)[ix + 1 :]:  # list() needed for GlyphsApp
            # Stupid case of two identical paths
            if str(p1.nodes) == str(p2.nodes):
                continue
            p2_kurbo = path_to_kurbo(p2)
            if not kurbo_bounds_intersect(p1_bounds, p2_kurbo.bounding_box()):
                continue
            for s1, bbox1 in zip(segs1, s1_bboxes):
                for s2 in p2.segments:
                    if not kurbo_bounds_intersect(
                        bbox1, seg_to_kurbo(s2).bounding_box()
                    ):
                        continue
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
        "dotSize": {
            "default": 15,
            "help": "Size of dots",
        },
        "dotSpacing": {
            "default": 15,
            "help": "Preferred space between dots",
        },
        "flexPercent": {
            "default": 25,
            "help": "Percentage amount by which spacing may be adjusted to fit an even number of dots",
        },
        "preventOverlaps": {
            "default": True,
            "help": "Prevent dots from overlapping",
        },
        "splitPaths": {
            "default": False,
            "help": "Split paths at intersections before dotting",
        },
        "contourSource": {
            "default": "<Default>",
            "help": "Layer to use as source for contours",
        },
    }

    @property
    def display_params(self):
        return ["dotSize", "dotSpacing"]

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        if layer.parent.name == "_dot":
            return layer.shapes
        self._resolved_params = {
            p: self.parameter(p, layer) for p in self.params.keys()
        }
        contour_source = self._resolved_params["contourSource"]
        if contour_source != "<Default>" and layer.parent.layers[contour_source]:
            sourcelayer = layer.parent.layers[contour_source]
        else:
            sourcelayer = layer
        centers = []
        paths = decomposedPaths(sourcelayer)
        if self._resolved_params["splitPaths"]:
            splitPathsAtIntersections(paths)
        for path in paths:
            for subpath in splitAtForcedNode(path):
                findCenters(subpath, self._resolved_params, centers, layer.parent.name)
        new_paths = self.centers_to_paths(centers)

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
        size = self._resolved_params["dotSize"]
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

    def centers_to_paths(self, centers: list[Center]):
        dotsize = self._resolved_params["dotSize"]
        if self._resolved_params["preventOverlaps"]:
            newcenters = []
            # Sort, to put forced points first
            for c in sorted(centers, key=lambda pt: pt.forced, reverse=True):
                # This could probably be improved...
                ok = True
                for nc in newcenters:
                    if distance(c.pos, nc) < dotsize:
                        ok = False
                        break
                if ok:
                    newcenters.append(c.pos)
        else:
            newcenters = [c.pos for c in centers]

        # If we are in Glyphsapp, then we want to draw a dot
        if self.preview or not self.instance:
            return [makeCircle(c, dotsize / 2) for c in newcenters]
        component_size = self.instance.customParameters[KEY + ".dotSize"]
        components = []
        for center in newcenters:
            comp = GSComponent("_dot", center)
            if dotsize != component_size:
                comp.scale = (
                    dotsize / component_size,
                    dotsize / component_size,
                )
            components.append(comp)
        return components
