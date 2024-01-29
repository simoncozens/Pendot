# MenuTitle: Pendot Designer
__doc__ = """
Pendot Designer
"""

import vanilla
from pathlib import Path
from GlyphsApp import Glyphs, GSLayer
import sys

sys.path.append(str(Path(__file__).parent.parent / "Plugins" / "Dotter"))

from pendot.dotter import doDotter, KEY
from pendot import PARAMS
import traceback


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
        layers = font.selectedLayers
        self.w = vanilla.Window((600, 600), "Pendot Designer")
        self.w.instanceSelector = LabelledComponent(
            "Instance",
            # vanilla.PopUpButton("auto", instancenames)
            vanilla.PopUpButton("auto", [i.name for i in font.instances]),
        )
        self.w.tabs = vanilla.Tabs("auto", ["Dotter", "Stroker", "Guidelines"])
        dotterTab = self.w.tabs[0]
        alternate_layers = ["<Default>"]
        if layers[0]:
            alternate_layers.extend([l.name for l in layers[0].parent.layers])
        dotterTab.glyphoverridelabel = vanilla.TextBox((350, 0, 250, 24), "")
        if layers:
            dotterTab.glyphoverridelabel.set(
                "Override glyph /" + layers[0].parent.name + "?"
            )
        dotterTab.contourSource = OverridableComponent(
            self,
            "contourSource",
            (10, 30, -10, 30),
            "Contour Source",
            vanilla.PopUpButton,
            {"items": alternate_layers},
            postChange=self.filter,
        )
        dotterTab.dotSize = OverridableComponent(
            self,
            "dotSize",
            (10, 70, -10, 30),
            "Dot Size",
            SteppingTextBox,
            {},
            postChange=self.filter,
        )
        dotterTab.dotSpacing = OverridableComponent(
            self,
            "dotSpacing",
            (10, 100, -10, 30),
            "Dot Spacing",
            SteppingTextBox,
            {},
            postChange=self.filter,
        )
        dotterTab.preventOverlaps = OverridableComponent(
            self,
            "preventOverlaps",
            (10, 130, -10, 30),
            "PreventOverlaps",
            vanilla.CheckBox,
            {"title": ""},
            postChange=self.filter,
        )
        dotterTab.splitPaths = OverridableComponent(
            self,
            "splitPaths",
            (10, 160, -10, 30),
            "Split paths at nodes",
            vanilla.CheckBox,
            {"title": ""},
            postChange=self.filter,
        )
        self.w.filterButton = vanilla.Button("auto", "Filter", callback=self.filter)
        # self.w.closeButton = vanilla.Button("auto", "Close", callback=self.close)
        rules = [
            "H:|-[instanceSelector]-|",
            "H:|-[tabs]-|",
            "H:|-[filterButton]-|",
            "V:|-20-[instanceSelector]-20-[tabs]-20-[filterButton]-|",
        ]
        metrics = {}
        self.w.addAutoPosSizeRules(rules, metrics)
        self.w.open()

    def filter(self, sender=None):
        if self.idempotence:
            return
        font = Glyphs.font
        if Glyphs.font.selectedLayers:
            for instance in font.instances:
                layer = Glyphs.font.selectedLayers[0]
                if layer.layerId != layer.associatedMasterId:
                    continue
                # Find or create a "dotted" layer
                destination_layer_name = "%s dotted" % (instance.name)
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
                try:
                    self.idempotence = True
                    destination_layer.parent.beginUndo()
                    destination_layer.shapes = doDotter(layer, instance)
                    destination_layer.parent.endUndo()
                    Glyphs.redraw()
                except Exception as e:
                    print(traceback.format_exc())
                    print(e)
                    print("Error in layer", layer)
                finally:
                    self.idempotence = False

    def close(self, sender=None):
        self.w.close()
        del self.w

    @property
    def selectedInstanceName(self):
        return str(self.w.instanceSelector.widget.getItem())

    @property
    def selectedInstance(self):
        for instance in Glyphs.font.instances:
            if instance.name == self.selectedInstanceName:
                return instance
        return None


if Glyphs.font:
    PendotDesigner()
else:
    print("Open a font first")
