import math
try:
    from GlyphsApp import GSPath, GSNode, OFFCURVE, CURVE
except:
    from glyphsLib.classes import GSPath, GSNode, OFFCURVE, CURVE

KEY = "co.uk.corvelsoftware.Dotter"
PARAMS = {
 "dotSize": 15,
 "dotSpacing": 15,
 "preventOverlaps": True,
 "splitPaths": False
}
MAGIC_NUMBER = 0.593667

def distance(a, b):
    return math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2)

def set_locally_forced(node):
    if KEY not in node.userData:
        node.userData[KEY] = {}
    node.userData[KEY]["locally_forced"] = True

def clear_locally_forced(node):
    # print("Clearing force from ", node)
    if KEY in node.userData:
        del node.userData[KEY]["locally_forced"]
        if not node.userData[KEY]:
            del node.userData[KEY]
    # print(node.userData)

def is_start_end(node):
    return node.index == 0 or node.index == len(node.parent.nodes) - 1

def isForced(node):
    # if is_start_end(node):
    #     return True
    return KEY in node.userData and (
        node.userData[KEY].get("forced")
        or node.userData[KEY].get("locally_forced")
    )


# This is just for display purposes; for the real thing we'll use a
# component
def makeCircle(center, radius):
    x, y = center
    path = GSPath()
    path.nodes.append(GSNode((x - radius * MAGIC_NUMBER, y - radius), OFFCURVE))
    path.nodes.append(GSNode((x - radius, y - radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode((x - radius, y), CURVE))
    path.nodes.append(GSNode((x - radius, y + radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode((x - radius * MAGIC_NUMBER, y + radius), OFFCURVE))
    path.nodes.append(GSNode((x, y + radius), CURVE))
    path.nodes.append(GSNode((x + radius * MAGIC_NUMBER, y + radius), OFFCURVE))
    path.nodes.append(GSNode((x + radius, y + radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode((x + radius, y), CURVE))
    path.nodes.append(GSNode((x + radius, y - radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode((x + radius * MAGIC_NUMBER, y - radius), OFFCURVE))
    path.nodes.append(GSNode((x, y - radius), CURVE))
    path.closed = True
    for ix, node in enumerate(path.nodes):
        if (ix+1) % 3:
            node.smooth = True
    return path


def splitAtForcedNode(path):
    # Iterator, yields GSPaths
    new_path = GSPath()
    for n in path.nodes:
        new_path.nodes.append(n)
        if isForced(n):
            yield new_path
            new_path = GSPath()
            new_path.nodes.append(GSNode(n.position, n.type))
    yield new_path


def findCenters(path, params, centers):
    segs = path.segments
    lengthSoFar = 0
    LIMIT = 1000
    lastLength = 0
    plen = path.length()
    centerSpace = params["dotSize"] + params["dotSpacing"]
    if not segs or not segs[0]:
        return
    centers.append({"pos": segs[0][0], "forced": True})
    centers.append({"pos": segs[-1].lastPoint(), "forced": True})
    # Adjust space such that end point falls at integer multiples
    # XXX We should add some "flex" in here to push it looser/tighter
    if centerSpace < plen:
        centerSpace = plen / math.ceil(plen / centerSpace)
    for pathtime, seg in enumerate(segs):
        for t in range(1, LIMIT):
            left, right = seg.splitAtTime_firstHalf_secondHalf_(t / LIMIT, None, None)
            lengthHere = lengthSoFar + left.length()
            if lengthHere > lastLength + centerSpace:
                centers.append({"pos": left.lastPoint(), "forced": False})
                lastLength = lengthHere

        lengthSoFar += seg.length()


def centersToPaths(centers, params):
    if params["preventOverlaps"]:
        newcenters = []
        # Sort, to put forced points first
        for c in sorted(centers, key=lambda pt: pt["forced"], reverse=True):
            # This could probably be improved...
            ok = True
            for nc in newcenters:
                if distance(c["pos"], nc) < params["dotSize"]:
                    ok = False
                    break
            if ok:
                newcenters.append(c["pos"])
    else:
        newcenters = [c["pos"] for c in centers]
    return [makeCircle(c, params["dotSize"]/2) for c in newcenters]


def insertPointInPathUnlessThere(path, pt):
    newpoint, pathtime = path.nearestPointOnPath_pathTime_(pt, None)
    # print("Intersection / pathtime was %s, %s, %s" % (pt, pathtime, path.nodes))
    # print("newpoint was %s" % newpoint)
    if pathtime.is_integer():
        nearest = path.nearestNodeWithPathTime_(pathtime)
        if nearest: # and not isForced(nearest) and nearest.type != OFFCURVE:
            # print("Point already, forcing: %s" % nearest)
            set_locally_forced(nearest)
    nearest = path.nearestNodeWithPathTime_(pathtime)
    if nearest and distance(nearest.position, pt) < 1.0 and nearest.type != OFFCURVE:
        return
    node = path.insertNodeWithPathTime_(pathtime)
    if not node:
        print(f"Couldn't insert node at {pt} ({pathtime}) in {path}")
        return
    # print("Inserted, forcing: %s" % node)
    set_locally_forced(node)


def splitPathsAtIntersections(paths):
    # We don't necessarily need to split the paths; we can
    # get away with adding a new node and setting it to forced.
    for p1 in paths:
        for s1 in p1.segments:
            for p2 in paths:
                if p1 == p2:
                    continue
                for s2 in p2.segments:
                    # Yes this is O(n^2). Yes I could improve it.
                    # Let's see if it's actually a problem first.
                    intersections = s1.intersectionPoints_(s2)
                    for pt in intersections:
                        # print("Intersection between %s/%s and %s/%s at %s" % (
                        #     p1,s1,p2,s2,pt)
                        # )
                        insertPointInPathUnlessThere(p1, pt)
                        insertPointInPathUnlessThere(p2, pt)

def doDotter(layer, params):

    layer.decomposeComponents()
    centers = []
    if params["splitPaths"]:
        splitPathsAtIntersections(layer.paths)
    for path in layer.paths:
        for subpath in splitAtForcedNode(path):
            findCenters(subpath, params, centers)
    new_paths = centersToPaths(centers, params)

    layer.shapes = new_paths + list(layer.components)
    for path in layer.paths:
        for node in path.nodes:
            clear_locally_forced(node)
