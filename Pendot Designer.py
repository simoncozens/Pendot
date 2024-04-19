# MenuTitle: Pendot Designer
__doc__ = """
Pendot Designer
"""

import vanilla
from pathlib import Path
from GlyphsApp import Glyphs, GSLayer, GSFontMaster, GSApplication
import sys
import AppKit

sys.path.append(str(Path(__file__).parent.parent / "Plugins" / "Dotter"))

from pendot import (
    PARAMS,
    doStroker,
    KEY,
    doDotter,
    addComponentGlyph,
    add_guidelines_to_layer,
)
from pendot.constants import (
    PREVIEW_MASTER_NAME,
    QUICK_PREVIEW_LAYER_NAME,
)
import traceback


GSSteppingTextField = objc.lookUpClass("GSSteppingTextField")


# Parameters for pendot are stored per instance.
# Each instance has a default userdata entry for each parameter; for example,
# instance.userData["co.uk.corvelsoftware.Dotter.dotSize"] stores the
# dot size for this instance. However, each layer may provide an instance-specific
# override, allowing you to have, for example, different dot sizes for the letter
# B. This is stored in the layer.userData dictionary, but the key includes the
# instance name; for example:
# font.glyphs["B"].layers[0].userData["co.uk.corvelsoftware.Dotter.Regular.dotSize"]
#
# See pendot/dotter.py and pendot/stroker.py for the list of parameters, but
# it will be something like:
#     # Dotter parameters
#     "dotSize": 15,
#     "dotSpacing": 15,
#     "preventOverlaps": True,
#     "splitPaths": False,
#     "contourSource": "<Default>",
#     # Stroker parameters
#     "strokerWidth": 50,
#     "strokerHeight": 50,
#     "strokerAngle": 0,
#     "strokerHeightLock": True,
#     "startCap": "round",
#     "endCap": "round",
#     "joinType": "round",
#     "removeExternal": False,
#     "removeInternal": False,
#     "segmentWise": False

# Guidelines parameters are stored in the instance as
# instance.userData["co.uk.corvelsoftware.Dotter.guidelines"]. This is a list
# of tuples, each of which is a pair of (height, thickness). The height is
# either a number of font units, or one of the names of the Glyphs metrics.


def safe_int(s):
    try:
        return int(s)
    except Exception:
        return 0


# Vanilla backports
class SteppingTextBox(vanilla.EditText):
    nsTextFieldClass = GSSteppingTextField

    def _setCallback(self, callback):
        super(SteppingTextBox, self)._setCallback(callback)
        if callback is not None and self._continuous:
            self._nsObject.setContinuous_(True)
            self._nsObject.setAction_(self._target.action_)
            self._nsObject.setTarget_(self._target)

    # This is in git vanilla, but not in any release yet

    def enable(self, onOff):
        self._nsObject.setEditable_(onOff)
        self._nsObject.setSelectable_(onOff)
        if onOff:
            alpha = 1.0
        else:
            alpha = 0.2
        self._nsObject.setAlphaValue_(alpha)


class ComboBoxList2Cell(vanilla.ComboBox):
    def __init__(self, items=[], completes=True, editable=False, callback=None):
        super().__init__(
            posSize="auto",
            items=items,
            completes=completes,
            continuous=False,
            sizeStyle="small",
            callback=callback,
        )
        self.enable(editable)


class SteppingTextBoxList2Cell(SteppingTextBox):
    def __init__(self, **kwargs):
        # Force it to be editable
        if "editable" in kwargs:
            del kwargs["editable"]
        super().__init__(
            **kwargs,
            posSize="auto",
            sizeStyle="small",
            readOnly=False,
        )
        self.enable(True)


class LabelledComponent(vanilla.Group):
    defaultMetrics = {"leftpad": 10, "toppad": 10, "bottompad": 10, "widgetwidth": 200}

    def __init__(self, label, widget, **metrics):
        metrics = {**self.defaultMetrics, **metrics}
        super().__init__("auto")
        self.label = vanilla.TextBox("auto", label)
        self.widget = widget
        rules = [
            "H:|-leftpad-[label]-[widget(>=20,<=widgetwidth)]-10-|",
            "V:|-toppad-[label]-bottompad-|",
            "V:|-toppad-[widget]-bottompad-|",
        ]
        self.addAutoPosSizeRules(rules, metrics)


class OverridableComponent(vanilla.Group):
    def __init__(
        self, owner, target, possize, label, widgetclass, widgetargs, postChange=None
    ):
        super().__init__(possize)
        self.owner = owner
        self.target = target
        self.postChange = postChange
        self.label = vanilla.TextBox((0, 0, 200, 24), label)
        self.defaultwidget = widgetclass(
            (200, 0, 100, 24), callback=self.updateDefault, **widgetargs
        )
        self.override = vanilla.CheckBox(
            (350, 0, 20, 24), None, callback=self.toggleOverride
        )
        self.overridewidget = widgetclass(
            (380, 0, 100, 24), callback=self.updateOverride, **widgetargs
        )
        self.overridewidget.enable(False)
        self.loadValues()

    def toggleOverride(self, sender):
        layer_instance_override = (
            KEY + "." + self.owner.selectedInstanceName + "." + self.target
        )
        layer = Glyphs.font.selectedLayers[0]
        typecast = type(PARAMS[self.target])
        if sender.get():
            # There is now an override
            self.overridewidget.enable(True)
            if not self.overridewidget.get():
                self.overridewidget.set(typecast(self.defaultwidget.get()))
            layer.userData[layer_instance_override] = typecast(
                self.overridewidget.get()
            )
        else:
            # Override removed
            self.overridewidget.enable(False)
            if layer_instance_override in layer.userData:
                del layer.userData[layer_instance_override]
        if self.postChange:
            self.postChange()

    def updateDefault(self, sender):
        instance = self.owner.selectedInstance
        thisKey = KEY + "." + self.target
        typecast = type(PARAMS[self.target])
        if typecast == int:
            typecast = safe_int
        if isinstance(self.defaultwidget, vanilla.PopUpButton):
            instance.userData[thisKey] = typecast(sender.getItem())
        else:
            instance.userData[thisKey] = typecast(sender.get())
        if self.postChange:
            self.postChange(self)

    def updateOverride(self, sender):
        layer_instance_override = (
            KEY + "." + self.owner.selectedInstanceName + "." + self.target
        )
        layer = Glyphs.font.selectedLayers[0]
        typecast = type(PARAMS[self.target])
        if typecast == int:
            typecast = safe_int
        if isinstance(self.overridewidget, vanilla.PopUpButton):
            layer.userData[layer_instance_override] = typecast(sender.getItem())
        else:
            layer.userData[layer_instance_override] = typecast(sender.get())
        if self.postChange:
            self.postChange(self)

    def loadValues(self):
        instance = self.owner.selectedInstance
        thisKey = KEY + "." + self.target
        if not instance.userData or thisKey not in instance.userData:
            instance.userData[thisKey] = PARAMS[self.target]
        if instance.userData[thisKey]:
            if isinstance(self.defaultwidget, vanilla.PopUpButton):
                self.defaultwidget.setItem(instance.userData[thisKey])
            else:
                try:
                    self.defaultwidget.set(instance.userData[thisKey])
                except Exception as e:
                    print(
                        f"Error setting default value {instance.userData[thisKey]} for {thisKey}: {e}"
                    )
        # Check if there is an override for this selected layer
        layer_instance_override = KEY + "." + instance.name + "." + self.target
        layers = Glyphs.font.selectedLayers
        if not layers:
            return
        if layer_instance_override in layers[0].userData:
            self.override.set(True)
            self.overridewidget.enable(True)
            if isinstance(self.defaultwidget, vanilla.PopUpButton):
                self.overridewidget.setItem(layers[0].userData[layer_instance_override])
            else:
                self.overridewidget.set(layers[0].userData[layer_instance_override])


# On with the show.


class PendotDesigner:
    def __init__(self):
        self.idempotence = False
        font = Glyphs.font
        self.w = vanilla.Window((600, 600), "Pendot Designer")
        self.w.instanceSelector = LabelledComponent(
            "Instance",
            # vanilla.PopUpButton("auto", instancenames)
            vanilla.PopUpButton(
                "auto", [i.name for i in font.instances], callback=self.reloadValues
            ),
        )
        self.widget_reloaders = []
        self.w.tabs = vanilla.Tabs(
            "auto",
            ["Dotter", "Stroker", "Guidelines"],
            callback=self.createLayerPreview,
        )
        dotterTab, strokerTab, guidelineTab = self.w.tabs

        # Set up dotter tab
        def setuptab(tab, controls):
            tab.glyphoverridelabel = vanilla.TextBox((350, 0, 250, 24), "")
            basepos = (10, 30, -10, 30)
            for name, title, widget, args in controls:
                component = OverridableComponent(
                    self,
                    name,
                    basepos,
                    title,
                    widget,
                    args,
                    postChange=self.createLayerPreview,
                )
                setattr(tab, name, component)
                self.widget_reloaders.append(component.loadValues)
                basepos = (10, basepos[1] + 30, -10, 30)

        setuptab(
            dotterTab,
            [
                ("contourSource", "Contour Source", vanilla.PopUpButton, {"items": []}),
                ("dotSize", "Dot Size", SteppingTextBox, {}),
                ("dotSpacing", "Dot Spacing", SteppingTextBox, {}),
                (
                    "preventOverlaps",
                    "Prevent Overlaps",
                    vanilla.CheckBox,
                    {"title": ""},
                ),
                ("splitPaths", "Split paths at nodes", vanilla.CheckBox, {"title": ""}),
            ],
        )
        # Set up Stroker tab
        setuptab(
            strokerTab,
            [
                ("strokerWidth", "Stroke Width", SteppingTextBox, {}),
                ("strokerHeight", "Stroke Height", SteppingTextBox, {}),
                ("strokerAngle", "Stroke Angle", SteppingTextBox, {}),
                (
                    "startCap",
                    "StartCap",
                    vanilla.PopUpButton,
                    {"items": ["Round", "Circle", "Square"]},
                ),
                (
                    "endCap",
                    "EndCap",
                    vanilla.PopUpButton,
                    {"items": ["Round", "Circle", "Square"]},
                ),
                (
                    "joinType",
                    "Join Type",
                    vanilla.PopUpButton,
                    {"items": ["Round", "Bevel", "Mitre", "Circle"]},
                ),
                ("removeExternal", "Remove External", vanilla.CheckBox, {"title": ""}),
                ("removeInternal", "Remove Internal", vanilla.CheckBox, {"title": ""}),
                ("segmentWise", "Stroke Each Segment", vanilla.CheckBox, {"title": ""}),
            ],
        )

        # Set up Guidelines tab
        columnDescriptions = [
            {
                "identifier": "height",
                "title": "Height",
                "editable": True,
                "cellClass": vanilla.ComboBoxList2Cell,
                "cellClassArguments": {
                    "items": [m.name for m in Glyphs.font.masters[0].metrics()]
                },
            },
            {
                "identifier": "thickness",
                "title": "Thickness",
                # "cellClass": SteppingTextBoxList2Cell,
                "editable": True,
            },
        ]

        guidelineTab.list = vanilla.List2(
            "auto",
            items=[],
            columnDescriptions=columnDescriptions,
            editCallback=self.editGuidelines,
            deleteCallback=self.removeGuideline,
        )
        guidelineTab.addButton = vanilla.Button("auto", "+", callback=self.addGuideline)
        guidelineTab.addAutoPosSizeRules(
            ["H:|-[list]-|", "H:[addButton]-|", "V:|-[list]-[addButton]-|"]
        )

        self.onLayerChange()
        self.w.createPreviewButton = vanilla.Button(
            "auto", "Create preview master", callback=self.createPreviewMaster
        )
        rules = [
            "H:|-[instanceSelector]-|",
            "H:|-[tabs]-|",
            "H:|-[createPreviewButton]-|",
            "V:|-20-[instanceSelector]-20-[tabs]-20-[createPreviewButton]-|",
        ]
        metrics = {}
        self.w.addAutoPosSizeRules(rules, metrics)
        self.w.bind("close", self.finish)
        self.w.open()
        Glyphs.addCallback(self.onLayerChange, "GSUpdateInterface")
        # Glyphs.addCallback(self.createLayerPreview, "GSUpdateInterface")
        self.createLayerPreview()

    def removeGuideline(self, sender=None):
        selectedIndexes = self.w.tabs[2].list.getSelectedIndexes()
        if not len(selectedIndexes):
            return
        selectedIndex = selectedIndexes[0]
        instance = self.selectedInstance or Glyphs.font.instances[0]
        items = instance.userData[KEY + ".guidelines"]
        del items[selectedIndex]
        self.reloadGuidelines()

    def addGuideline(self, sender=None):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        items = instance.userData[KEY + ".guidelines"]
        items.append({"height": "0", "thickness": 10})
        self.reloadGuidelines()

    def finish(self, sender=None):
        Glyphs.removeCallback(self.onLayerChange)
        Glyphs.removeCallback(self.createLayerPreview)
        # Make quick preview layer invisible
        for layer in Glyphs.font.selectedLayers:
            glyph = layer.parent
            # Find or create a quick preview layer
            if glyph.layers[QUICK_PREVIEW_LAYER_NAME]:
                glyph.layers[QUICK_PREVIEW_LAYER_NAME].visible = False
        del self.w

    def _is_valid_source(self, layer):
        if layer.name.endswith(" dotted"):
            return False
        if layer.name == PREVIEW_MASTER_NAME:
            return False
        return True

    def onLayerChange(self, sender=None):
        font = Glyphs.font
        layers = font.selectedLayers
        if not layers:
            return
        alternate_layers = ["<Default>"]
        if layers[0]:
            alternate_layers.extend(
                [l.name for l in layers[0].parent.layers if self._is_valid_source(l)]
            )
            self.w.tabs[0].contourSource.defaultwidget.setItems(alternate_layers)
            self.w.tabs[0].contourSource.overridewidget.setItems(alternate_layers)
            for tab in (self.w.tabs[0], self.w.tabs[1]):
                tab.glyphoverridelabel.set(
                    "Override glyph /" + layers[0].parent.name + "?"
                )
        self.reloadValues()
        self.createLayerPreview()

    def editGuidelines(self, sender):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        instance.userData[KEY + ".guidelines"] = [
            {"height": item["height"], "thickness": item["thickness"]}
            for item in self.w.tabs[2].list.get()
        ]
        self.createLayerPreview()

    def reloadValues(self, sender=None):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        if KEY + ".mode" in instance.userData:
            if instance.userData[KEY + ".mode"] == "dotter":
                self.w.tabs.set(0)
            elif instance.userData[KEY + ".mode"] == "stroker":
                self.w.tabs.set(1)
        for reloader in self.widget_reloaders:
            reloader()
        self.reloadGuidelines()

    def reloadGuidelines(self):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        if (
            not instance.userData
            or KEY + ".guidelines" not in instance.userData
            or not instance.userData[KEY + ".guidelines"]
        ):
            instance.userData[KEY + ".guidelines"] = [
                {"height": "Descender", "thickness": 10},
                {"height": "x-Height", "thickness": 10},
                {"height": "Cap Height", "thickness": 10},
                {"height": "Ascender", "thickness": 10},
            ]
        items = instance.userData[KEY + ".guidelines"]
        # Make a deep mutable copy of this
        self.w.tabs[2].list.set(
            [
                {"height": item["height"], "thickness": item["thickness"]}
                for item in items
            ]
        )
        self.createLayerPreview()

    @property
    def mode(self):
        tabIndex = self.w.tabs.get()
        if tabIndex == 0:
            return "dotter"
        elif tabIndex == 1:
            return "stroker"
        else:
            return "guides"

    def createLayerPreview(self, sender=None):
        # Store the current mode inside the instance object
        instance = self.selectedInstance
        if not instance:
            return
        instance.userData[KEY + ".mode"] = self.mode

        if self.idempotence:
            return
        self.idempotence = True

        for layer in Glyphs.font.selectedLayers:
            if (
                layer.name == QUICK_PREVIEW_LAYER_NAME
                or layer.name == PREVIEW_MASTER_NAME
            ):
                continue  # No recursion!
            glyph = layer.parent
            # Find or create a quick preview layer
            if glyph.layers[QUICK_PREVIEW_LAYER_NAME]:
                destination_layer = glyph.layers[QUICK_PREVIEW_LAYER_NAME]
            else:
                destination_layer = GSLayer()
                destination_layer.name = QUICK_PREVIEW_LAYER_NAME
                destination_layer.width = layer.width
                destination_layer.parent = layer.parent
                destination_layer.associatedMasterId = layer.associatedMasterId
                glyph.layers.append(destination_layer)
            # Do dotting and redrawing if we are in the edit view
            if Glyphs.font.parent.windowController().activeEditViewController():
                destination_layer.visible = True
                glyph.undoManager().disableUndoRegistration()
                try:
                    if self.mode == "dotter":
                        destination_layer.shapes = doDotter(
                            layer, instance, component=False
                        )
                    elif self.mode == "stroker":
                        destination_layer.shapes = doStroker(layer, instance)
                    else:
                        destination_layer.shapes = layer.copyDecomposedLayer().shapes
                        add_guidelines_to_layer(destination_layer, instance)
                    Glyphs.redraw()
                except Exception as e:
                    print(traceback.format_exc())
                    print(e)
                    print("Error in layer", layer)
                glyph.undoManager().enableUndoRegistration()
        self.idempotence = False

    @property
    def selectedInstanceName(self):
        return str(self.w.instanceSelector.widget.getItem())

    @property
    def selectedInstance(self):
        for instance in Glyphs.font.instances:
            if instance.name == self.selectedInstanceName:
                return instance
        return None

    def createPreviewMaster(self, sender=None):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        preview_master = None
        for master in Glyphs.font.masters:
            if master.name == PREVIEW_MASTER_NAME:
                preview_master = master
                break
        if not preview_master:
            preview_master = GSFontMaster()
            Glyphs.font.masters.append(preview_master)
            preview_master.name = PREVIEW_MASTER_NAME
            preview_master.ascender = master.ascender
            preview_master.capHeight = master.capHeight
            preview_master.descender = master.descender
            preview_master.xHeight = master.xHeight

        del Glyphs.font.glyphs["_dot"]
        addComponentGlyph(Glyphs.font, instance)

        for glyph in Glyphs.font.glyphs:
            if glyph.name == "_dot":
                continue
            glyph.undoManager().disableUndoRegistration()
            layer = glyph.layers[0]  # Really?
            # Find target layer
            preview_layer = None
            for l in glyph.layers:
                if l.associatedMasterId == preview_master.id:
                    preview_layer = l
                    break
            if not preview_layer:
                preview_layer = GSLayer()
                preview_layer.name = layer.name
                preview_layer.associatedMasterId = preview_master.id
                glyph.layers.append(preview_layer)
            preview_layer.width = layer.width
            if self.mode == "dotter":
                preview_layer.shapes = doDotter(layer, instance, component=True)
            else:
                preview_layer.shapes = doStroker(layer, instance)
            glyph.undoManager().enableUndoRegistration()
        Glyphs.redraw()


if Glyphs.font:
    if not hasattr(GSApplication, "_pendotdesigner"):
        setattr(GSApplication, "_pendotdesigner", PendotDesigner())
    if (
        not hasattr(GSApplication._pendotdesigner, "w")
        or not GSApplication._pendotdesigner.w
    ):
        GSApplication._pendotdesigner.__init__()
    GSApplication._pendotdesigner.w.open()
else:
    print("Open a font first")
