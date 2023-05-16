from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import Glyphs, GSNode, ONSTATE, OFFSTATE, MIXEDSTATE, OFFCURVE
from GlyphsApp.plugins import ReporterPlugin
from GlyphsApp.drawingTools import stroke, oval, fill, strokeWidth

KEY = "co.uk.corvelsoftware.Dotter"


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
            {"name": "Force dot here", "action": self.toggleForced_, "state": finalstate}
        ]

    @objc.python_method
    def getForced(self, sender=None, node=None):
        # First nodes and last nodes are always forced
        if node.index == 0 or node.index == len(node.parent.nodes) - 1:
            return True
        return KEY in node.userData and node.userData[KEY]["forced"]

    @objc.python_method
    def setForced(self, sender=None, node=None, value=None):
        if KEY not in node.userData:
            node.userData[KEY] = {}
        node.userData[KEY]["forced"] = value

    def selectedNodes(self, sender=None):
        if not Glyphs.font.selectedLayers:
            return []
        layer = Glyphs.font.selectedLayers[0]
        selectedNodes = filter(lambda x: isinstance(x, GSNode) and x.type != OFFCURVE, layer.selection)
        return selectedNodes

    @objc.python_method
    def background(self, layer):
        if not Glyphs.font.selectedLayers:
            return []
        layer = Glyphs.font.selectedLayers[0]
        fill(None)
        stroke(0.8, 0.2, 0.2, 1.0)
        handSizeInPoints = 5 + Glyphs.handleSize * 5.0  # (= 5.0 or 7.5 or 10.0)
        scaleCorrectedHandleSize = handSizeInPoints / Glyphs.font.currentTab.scale
        strokeWidth(scaleCorrectedHandleSize / 5.0)
        for path in layer.paths:
            if path.closed:
                continue
            for node in path.nodes:
                if not self.getForced(node=node):
                    continue
                oval(
                    node.position.x - scaleCorrectedHandleSize * 0.5,
                    node.position.y - scaleCorrectedHandleSize * 0.5,
                    scaleCorrectedHandleSize,
                    scaleCorrectedHandleSize,
                )

    def toggleForced_(self, sender=None):
        for node in self.selectedNodes():
            self.setForced(node=node, value=not self.getForced(node=node))

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
