# encoding: utf-8
from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import Glyphs, GSPath, GSNode, distance, OFFCURVE, CURVE
from GlyphsApp.plugins import FilterWithDialog
from Foundation import NSPoint, NSMutableArray
from AppKit import NSControlStateValueOn, NSControlStateValueOff, NSObject
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from pendot import doDotter, doStroker, KEY, PARAMS


# class TabviewDelegate(NSObject):
#     def tabView_didSelectTabViewItem_(self, tabview, item):
#         print("I selected ", item)
#         pass


class PendotDesigner(FilterWithDialog):
    # Definitions of IBOutlets

    # The NSView object from the User Interface. Keep this here!
    dialog = objc.IBOutlet()

    dotSizeField = objc.IBOutlet()
    dotSpacingField = objc.IBOutlet()
    preventOverlapsButton = objc.IBOutlet()
    splitPathsButton = objc.IBOutlet()
    tabField = objc.IBOutlet()

    strokerWidth = objc.IBOutlet()
    strokerHeight = objc.IBOutlet()
    strokerAngle = objc.IBOutlet()
    strokerHeightLock = objc.IBOutlet()
    startCapPopup = objc.IBOutlet()
    endCapPopup = objc.IBOutlet()
    joinTypePopup = objc.IBOutlet()
    removeInternal = objc.IBOutlet()
    removeExternal = objc.IBOutlet()
    segmentWise = objc.IBOutlet()


    @objc.python_method
    def settings(self):
        self.menuName = "Pendot Designer"
        self.actionButtonLabel = 'Done'  # We don't "apply" anything
        # Load dialog from .nib (without .extension)
        self.loadNib("IBdialog", __file__)

    @objc.python_method
    def get_param(self, name):
        # Set default value
        if KEY not in Glyphs.font.userData:
            Glyphs.font.userData[KEY] = dict(PARAMS)
        if name not in Glyphs.font.userData[KEY]:  # If we added a param
            Glyphs.font.userData[KEY][name] = PARAMS[name]
        return Glyphs.font.userData[KEY][name]

    @objc.python_method
    def set_param(self, name, value):
        self.get_param(name)  # Establish defaults
        Glyphs.font.userData[KEY][name] = value

    # On dialog show
    @objc.python_method
    def start(self):
        # Set delegate
        # self.delegate = TabviewDelegate.alloc().init()
        # self.tabField.setDelegate_(self.delegate)

        # Set value of text field
        self.dotSizeField.setStringValue_(self.get_param("dotSize"))
        self.dotSpacingField.setStringValue_(self.get_param("dotSpacing"))
        self.preventOverlapsButton.setState_(self.get_param("preventOverlaps"))
        self.splitPathsButton.setState_(self.get_param("splitPaths"))
        self.strokerWidth.setStringValue_(self.get_param("strokerWidth"))
        self.strokerHeight.setStringValue_(self.get_param("strokerHeight"))
        self.strokerAngle.setStringValue_(self.get_param("strokerAngle"))
        self.strokerHeightLock.setState_(self.get_param("strokerHeightLock"))
        CAPS = ["Round", "Square", "Circle"]
        JOINS = ["Round", "Bevel", "Miter", "Circle"]
        sc = self.get_param("startCap")
        ec = self.get_param("endCap")
        jt = self.get_param("joinType")
        if sc in CAPS:
            self.startCapPopup.selectItemAtIndex_(CAPS.index(sc))
        if ec in CAPS:
            print("Selecting end cap "+str(CAPS.index(ec)))
            self.endCapPopup.selectItemAtIndex_(CAPS.index(ec))
        if jt in JOINS:
            self.joinTypePopup.selectItemAtIndex_(JOINS.index(jt))
        self.removeExternal.setState_(self.get_param("removeExternal"))
        self.removeInternal.setState_(self.get_param("removeInternal"))
        self.segmentWise.setState_(self.get_param("segmentWise"))

        # Set focus to text field
        self.dotSizeField.becomeFirstResponder()

        for param in PARAMS.keys():
            print(param, self.get_param(param))

    # Action triggered by UI
    @objc.IBAction
    def setParams_(self, sender):
        # Store value coming in from dialog
        if self.tabField.selectedTabViewItem().label() == "Stroker":
            self.set_param("strokerWidth", self.strokerWidth.floatValue())
            if self.strokerHeightLock.state() == NSControlStateValueOn:
                self.set_param("strokerHeightLock", True)
                self.set_param("strokerHeight", self.strokerWidth.floatValue())
                self.strokerHeight.setEnabled_(False)
                self.strokerHeight.setStringValue_(self.get_param("strokerHeight"))
            else:
                self.set_param("strokerHeightLock", False)
                self.strokerHeight.setEnabled_(True)
                self.set_param("strokerHeight", self.strokerHeight.floatValue())
            self.set_param("strokerAngle", self.strokerAngle.floatValue())
            self.set_param("startCap", self.startCapPopup.titleOfSelectedItem())
            print("Storing start cap -> ", self.startCapPopup.titleOfSelectedItem())
            self.set_param("endCap", self.endCapPopup.titleOfSelectedItem())
            print("Storing end cap -> ", self.endCapPopup.titleOfSelectedItem())
            self.set_param("joinType", self.joinTypePopup.titleOfSelectedItem())
            print("Storing join type -> ", self.joinTypePopup.titleOfSelectedItem())
            self.set_param("removeExternal", self.removeExternal.state() == NSControlStateValueOn)
            self.set_param("removeInternal", self.removeInternal.state() == NSControlStateValueOn)
            self.set_param("segmentWise", self.segmentWise.state() == NSControlStateValueOn)
        else:
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
            if param in customParameters and customParameters[param] is not None:
                params[param] = customParameters[param]
            else:
                params[param] = self.get_param(param)

        layer.decomposeComponents()
        if self.tabField.selectedTabViewItem().label() == "Stroker":
            doStroker(layer, params)
        else:
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
