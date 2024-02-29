# MenuTitle: Pendot Designer
__doc__ = """
Pendot Designer
"""

import vanilla
from pathlib import Path
from GlyphsApp import Glyphs, GSLayer, GSFontMaster, GSApplication
import sys

sys.path.append(str(Path(__file__).parent.parent / "Plugins" / "Dotter"))

from pendot import PARAMS, doStroker, KEY, doDotter, addComponentGlyph
import traceback


PREVIEW_MASTER_NAME = "Pendot Preview"
GSSteppingTextField = objc.lookUpClass("GSSteppingTextField")


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
        if isinstance(self.overridewidget, vanilla.PopUpButton):
            layer.userData[layer_instance_override] = typecast(sender.getItem())
        else:
            layer.userData[layer_instance_override] = typecast(sender.get())
        if self.postChange:
            self.postChange(self)

    def loadValues(self):
        instance = self.owner.selectedInstance
        thisKey = KEY + "." + self.target
        if thisKey not in instance.userData:
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
        self.w.tabs = vanilla.Tabs("auto", ["Dotter", "Stroker", "Guidelines"], callback=self.createLayerPreview)
        dotterTab, strokerTab, guidelineTab = self.w.tabs

        # Set up dotter tab
        def setuptab(tab, controls):
            tab.glyphoverridelabel = vanilla.TextBox((350, 0, 250, 24), "")
            basepos = (10, 30, -10, 30)
            for name, title, widget, args in controls:
                component = OverridableComponent(
                    self, name, basepos, title, widget, args, postChange=self.createLayerPreview
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
                ("startCap", "StartCap", vanilla.PopUpButton, {"items": ["Round", "Circle", "Square"]}),
                ("endCap", "EndCap", vanilla.PopUpButton, {"items": ["Round", "Circle", "Square"]}),
                ("joinType", "Join Type", vanilla.PopUpButton, {"items": ["Round", "Bevel", "Mitre", "Circle"]}),
                ("removeExternal", "Remove External", vanilla.CheckBox, {"title": ""}),
                ("removeInternal", "Remove Internal", vanilla.CheckBox, {"title": ""}),
                ("segmentWise", "Stroke Each Segment", vanilla.CheckBox, {"title": ""}),
            ],
        )

        self.onLayerChange()
        self.w.createPreviewButton = vanilla.Button(
            "auto", "Create preview master", callback=self.createPreviewMaster
        )
        # self.w.closeButton = vanilla.Button("auto", "Close", callback=self.close)
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
        Glyphs.addCallback(self.createLayerPreview, "GSUpdateInterface")
        self.createLayerPreview()

    def finish(self, sender=None):
        Glyphs.removeCallback(self.onLayerChange)
        Glyphs.removeCallback(self.createLayerPreview)
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
            alternate_layers.extend([l.name for l in layers[0].parent.layers if self._is_valid_source(l)])
            self.w.tabs[0].contourSource.defaultwidget.setItems(alternate_layers)
            self.w.tabs[0].contourSource.overridewidget.setItems(alternate_layers)
            for tab in (self.w.tabs[0], self.w.tabs[1]):
                tab.glyphoverridelabel.set(
                    "Override glyph /" + layers[0].parent.name + "?"
                )
        self.reloadValues()

    def updateDots(self, sender=None):
        if self.w.tabs.get() == 0:
            self.createLayerPreview()

    def reloadValues(self, sender=None):
        for reloader in self.widget_reloaders:
            reloader()
    
    @property
    def mode(self):
        tabIndex = self.w.tabs.get()
        if tabIndex == 0:
            return "dotter"
        elif tabIndex == 1:
            return "stroker"

    def createLayerPreview(self, sender=None):
        if self.idempotence or not Glyphs.font.selectedLayers:
            return
        self.idempotence = True
        layername = self.mode.replace("er", "ed")

        font = Glyphs.font
        for layer in Glyphs.font.selectedLayers:
            if layer.layerId != layer.associatedMasterId:
                continue
            for instance in font.instances:
                # Find or create a "dotted" layer
                destination_layer_name = instance.name + " " + layername
                if Glyphs.font.glyphs[layer.parent.name].layers[destination_layer_name]:
                    destination_layer = Glyphs.font.glyphs[layer.parent.name].layers[
                        destination_layer_name
                    ]
                else:
                    destination_layer = GSLayer()
                    destination_layer.name = destination_layer_name
                    destination_layer.width = layer.width
                    destination_layer.parent = layer.parent
                    destination_layer.associatedMasterId = layer.associatedMasterId
                    layer.parent.layers.append(destination_layer)
                destination_layer.visible = True
                # Do dotting and redrawing if we are in the edit view
                if Glyphs.font.parent.windowController().activeEditViewController():
                    try:
                        destination_layer.parent.beginUndo()
                        if layername == "dotted":
                            destination_layer.shapes = doDotter(layer, instance, component=False)
                        elif layername == "stroked":
                            destination_layer.shapes = doStroker(layer, instance)
                        destination_layer.parent.endUndo()
                        Glyphs.redraw()
                    except Exception as e:
                        print(traceback.format_exc())
                        print(e)
                        print("Error in layer", layer)
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
            print(glyph.name)
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
