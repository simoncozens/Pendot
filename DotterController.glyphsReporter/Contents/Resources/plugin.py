from __future__ import division, print_function, unicode_literals
import objc
from AppKit import NSMenuItem
from GlyphsApp import Glyphs, GSNode, ONSTATE, OFFSTATE, MIXEDSTATE, OFFCURVE
from GlyphsApp.plugins import ReporterPlugin
from GlyphsApp.drawingTools import stroke, oval, fill, strokeWidth

KEY = "co.uk.corvelsoftware.Dotter"

def is_start_end(node):
    return node.index == 0 or node.index == len(node.parent.nodes) - 1


class DotterController(ReporterPlugin):
    @objc.python_method
    def settings(self):
        self.menuName = "Dotter Controller"

    @objc.python_method
    def conditionalContextMenus(self):
        states = []
        selectedNodes = self.selectedNodes()
        if not selectedNodes:
            return []

        menuname = "Force dot here"

        action = self.toggleForced_
        if all(is_start_end(n) for n in selectedNodes):
            action = None

        for node in selectedNodes:
            if self.getForced(node=node):
                states.append(ONSTATE)
            else:
                states.append(OFFSTATE)
        finalstate = OFFSTATE
        if all(state == ONSTATE for state in states):
            finalstate = ONSTATE
        elif states and not all(state == OFFSTATE for state in states):
            finalstate = MIXEDSTATE
        return [
            {"name": menuname, "action": action, "state": finalstate}
        ]


    @objc.python_method
    def getForced(self, sender=None, node=None):
        if KEY in node.userData:
            our_dict = node.userData[KEY]
            if our_dict.get("locally_forced", False):
                return "locally_forced"
            if our_dict.get("forced", False):
                return "forced"
        # First nodes and last nodes are always forced
        if is_start_end(node):
            return "startend"
        return None

    @objc.python_method
    def setForced(self, sender=None, node=None, value=None):
        if KEY not in node.userData:
            node.userData[KEY] = {}
        node.userData[KEY]["forced"] = value

    def selectedNodes(self, sender=None):
        if not Glyphs.font.selectedLayers:
            return []
        layer = Glyphs.font.selectedLayers[0]
        selectedNodes = list(filter(lambda x: isinstance(x, GSNode) and x.type != OFFCURVE, layer.selection))
        return selectedNodes

    @objc.python_method
    def background(self, layer):
        if not Glyphs.font.selectedLayers:
            return []
        layer = Glyphs.font.selectedLayers[0]
        fill(None)
        handSizeInPoints = 5 + Glyphs.handleSize * 5.0  # (= 5.0 or 7.5 or 10.0)
        scaleCorrectedHandleSize = handSizeInPoints / Glyphs.font.currentTab.scale
        strokeWidth(scaleCorrectedHandleSize / 5.0)
        for path in layer.paths:
            if path.closed:
                continue
            for node in path.nodes:
                if not node.parent:
                    print("Dead node %s in %s" % (node, path))
                    continue
                forcetype = self.getForced(node=node)
                if forcetype == "forced":
                    stroke(0.8, 0.2, 0.2, 1.0)
                elif forcetype == "locally_forced":
                    stroke(204/255, 134/255, 14/255, 1.0)
                elif forcetype == "startend":
                    stroke(5/255, 166/255, 93/255, 1.0)
                else:
                    continue
                oval(
                    node.position.x - scaleCorrectedHandleSize * 0.5,
                    node.position.y - scaleCorrectedHandleSize * 0.5,
                    scaleCorrectedHandleSize,
                    scaleCorrectedHandleSize,
                )

    def toggleForced_(self, sender=None):
        for node in self.selectedNodes():
            if is_start_end(node):
                continue
            self.setForced(node=node, value=not self.getForced(node=node))

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
