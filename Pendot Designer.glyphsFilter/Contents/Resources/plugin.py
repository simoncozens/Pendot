# encoding: utf-8
from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import Glyphs, GSPath, GSNode, distance, OFFCURVE, CURVE
from GlyphsApp.plugins import FilterWithDialog
from Foundation import NSPoint, NSMutableArray
from AppKit import NSControlStateValueOn, NSControlStateValueOff
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from pendot.dotter import doDotter, KEY, PARAMS


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

    @objc.python_method
    def get_param(self, name):
        # Set default value
        if KEY not in Glyphs.font.userData:
            Glyphs.font.userData[KEY] = dict(PARAMS)
        return Glyphs.font.userData[KEY][name]

    @objc.python_method
    def set_param(self, name, value):
        self.get_param(name)  # Establish defaults
        Glyphs.font.userData[KEY][name] = value

    # On dialog show
    @objc.python_method
    def start(self):
        # Set value of text field
        self.dotSizeField.setStringValue_(self.get_param("dotSize"))
        self.dotSpacingField.setStringValue_(self.get_param("dotSpacing"))
        self.preventOverlapsButton.setState_(self.get_param("preventOverlaps"))
        self.splitPathsButton.setState_(self.get_param("splitPaths"))

        # Set focus to text field
        self.dotSizeField.becomeFirstResponder()

    # Action triggered by UI
    @objc.IBAction
    def setParams_(self, sender):
        # Store value coming in from dialog
        self.set_param("dotSize", self.dotSizeField.floatValue())
        self.set_param("dotSpacing", self.dotSpacingField.floatValue())
        self.set_param("preventOverlaps", self.preventOverlapsButton.state() == NSControlStateValueOn)
        self.set_param("splitPaths", self.splitPathsButton.state() == NSControlStateValueOn)

        # Trigger redraw
        self.update()

    # Actual filter
    @objc.python_method
    def filter(self, layer, inEditView, customParameters):
        params = {}
        for param in PARAMS.keys():
            if param in customParameters:
                params[param] = customParameters[param]
            else:
                params[param] = float(self.get_param(param))

        layer.decomposeComponents()
        doDotter(layer, params)
        layer.cleanUpPaths()

    @objc.python_method
    def generateCustomParameter(self):
        params = [self.__class__.__name__]
        for param in PARAMS.keys():
            params.append(
                "%s: %s"
                % (
                    param,
                    self.get_param(param),
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
