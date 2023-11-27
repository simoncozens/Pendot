# encoding: utf-8
from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import Glyphs, GSPath, GSNode, distance, OFFCURVE, CURVE
from GlyphsApp.plugins import FilterWithDialog
from Foundation import NSPoint, NSMutableArray
from AppKit import NSControlStateValueOn, NSControlStateValueOff
import math

KEY = "co.uk.corvelsoftware.Dotter"
PARAMS = ["dotSize", "dotSpacing", "preventOverlaps", "splitPaths"]
MAGIC_NUMBER = 0.593667

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
    path.nodes.append(GSNode(NSPoint(x - radius * MAGIC_NUMBER, y - radius), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x - radius, y - radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x - radius, y), CURVE))
    path.nodes.append(GSNode(NSPoint(x - radius, y + radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x - radius * MAGIC_NUMBER, y + radius), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x, y + radius), CURVE))
    path.nodes.append(GSNode(NSPoint(x + radius * MAGIC_NUMBER, y + radius), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x + radius, y + radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x + radius, y), CURVE))
    path.nodes.append(GSNode(NSPoint(x + radius, y - radius * MAGIC_NUMBER), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x + radius * MAGIC_NUMBER, y - radius), OFFCURVE))
    path.nodes.append(GSNode(NSPoint(x, y - radius), CURVE))
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


class PendotDesigner(FilterWithDialog):
    # Definitions of IBOutlets

    # The NSView object from the User Interface. Keep this here!
    dialog = objc.IBOutlet()

    dotSizeField = objc.IBOutlet()
    dotSpacingField = objc.IBOutlet()
    preventOverlapsButton = objc.IBOutlet()
    splitPathsButton = objc.IBOutlet()


    @objc.python_method
    def settings(self):
        self.menuName = "Pendot Designer"
        # Load dialog from .nib (without .extension)
        self.loadNib("IBdialog", __file__)

    # On dialog show
    @objc.python_method
    def start(self):
        # Set default value
        Glyphs.registerDefault(f"{KEY}.dotSize", 15.0)
        Glyphs.registerDefault(f"{KEY}.dotSpacing", 15.0)
        Glyphs.registerDefault(f"{KEY}.preventOverlaps", True)
        Glyphs.registerDefault(f"{KEY}.splitPaths", False)

        # Set value of text field
        self.dotSizeField.setStringValue_(Glyphs.defaults[f"{KEY}.dotSize"])
        self.dotSpacingField.setStringValue_(Glyphs.defaults[f"{KEY}.dotSpacing"])
        self.preventOverlapsButton.setState_(Glyphs.defaults[f"{KEY}.preventOverlaps"])
        self.splitPathsButton.setState_(Glyphs.defaults[f"{KEY}.splitPaths"])

        # Set focus to text field
        self.dotSizeField.becomeFirstResponder()

    # Action triggered by UI
    @objc.IBAction
    def setParams_(self, sender):
        # Store value coming in from dialog
        Glyphs.defaults[f"{KEY}.dotSize"] = self.dotSizeField.floatValue()
        Glyphs.defaults[f"{KEY}.dotSpacing"] = self.dotSpacingField.floatValue()
        Glyphs.defaults[f"{KEY}.preventOverlaps"] = self.preventOverlapsButton.state() == NSControlStateValueOn
        Glyphs.defaults[f"{KEY}.splitPaths"] = self.splitPathsButton.state() == NSControlStateValueOn

        # Trigger redraw
        self.update()

    # Action triggered by UI
    @objc.IBAction
    def setDotSpacing_(self, sender):
        # Store value coming in from dialog
        Glyphs.defaults[f"{KEY}.dotSpacing"] = sender.floatValue()

        # Trigger redraw
        self.update()

    # Actual filter
    @objc.python_method
    def filter(self, layer, inEditView, customParameters):
        layer.decomposeComponents()
        params = {}
        for param in PARAMS:
            if param in customParameters:
                params[param] = customParameters[param]
            else:
                params[param] = float(Glyphs.defaults[f"{KEY}.{param}"])

        centers = []
        if params["splitPaths"]:
            splitPathsAtIntersections(layer.paths)
        for path in layer.paths:
            for subpath in splitAtForcedNode(path):
                findCenters(subpath, params, centers)
        new_paths = centersToPaths(centers, params)

        layer.shapes = new_paths + list(layer.components)
        layer.cleanUpPaths()
        for path in layer.paths:
            for node in path.nodes:
                clear_locally_forced(node)

    @objc.python_method
    def generateCustomParameter(self):
        params = [self.__class__.__name__]
        for param in PARAMS:
            params.append(
                "%s: %s"
                % (
                    param,
                    Glyphs.defaults[f"{KEY}.{param}"],
                )
            )
        return "; ".join(params)

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__

    def confirmDialog_(self, sender):
        # On confirm, put shadowlayers back
        ShadowLayers = self.valueForKey_("shadowLayers")
        Layers = self.valueForKey_("layers")
        checkSelection = True
        for k in range(len(ShadowLayers)):
            ShadowLayer = ShadowLayers[k]
            Layer = Layers[k]
            Layer.setShapes_(NSMutableArray.alloc().initWithArray_copyItems_(ShadowLayer.pyobjc_instanceMethods.shapes(), True))
