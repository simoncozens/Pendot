# MenuTitle: Pendot Designer
__doc__ = """
Pendot Designer
"""

import functools
import sys
import traceback
from pathlib import Path
import re

import AppKit
import vanilla
from GlyphsApp import Glyphs, GSApplication, GSFontMaster, GSLayer

sys.path.append(str(Path(__file__).parent.parent / "Plugins" / "Dotter"))

from pendot.constants import KEY, PREVIEW_MASTER_NAME, QUICK_PREVIEW_LAYER_NAME
from pendot.effect.dotter import Dotter
from pendot.effect.guidelines import Guidelines
from pendot.effect.stroker import Stroker
from pendot.effect.startdot import StartDot
from pendot import create_effects, transform_layer

GSSteppingTextField = objc.lookUpClass("GSSteppingTextField")


# Parameters for pendot are stored per instance.
# Each instance has a default custom parameter entry for each parameter; for example,
# instance.customParameters["co.uk.corvelsoftware.Dotter.dotSize"] stores the
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
# instance.customParameters["co.uk.corvelsoftware.Dotter.guidelines"]. This is a list
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
    def __init__(self, owner, effect, name, basepos, postChange=None):
        super().__init__(basepos)
        label = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).title()
        param_param = effect.params[name]
        default = param_param["default"]
        self.typecast = param_param.get("type", type(default))
        if self.typecast is bool:
            widgetclass = vanilla.CheckBox
            widgetargs = {"title": ""}
        elif self.typecast is int or self.typecast is float:
            self.typecast = safe_int
            widgetclass = SteppingTextBox
            widgetargs = {}
        elif self.typecast is str:
            widgetclass = vanilla.PopUpButton
            widgetargs = {"items": self.get_popup_items(effect, name)}
        else:
            Message(f"Unknown type for {name} (type={self.typecast})")

        self.owner = owner
        self.target = name
        self.effect = effect
        self.postChange = postChange
        self.label = vanilla.TextBox((0, 0, 200, 24), label)
        if "help" in param_param:
            self.label.setToolTip(param_param["help"])
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
        if sender.get():
            # There is now an override
            self.overridewidget.enable(True)
            if not self.overridewidget.get():
                if isinstance(self.overridewidget, vanilla.PopUpButton):
                    self.overridewidget.setItem(self.defaultwidget.getItem())
                else:
                    self.overridewidget.set(self.typecast(self.defaultwidget.get()))
            layer.userData[layer_instance_override] = self.typecast(
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
        if isinstance(self.defaultwidget, vanilla.PopUpButton):
            instance.customParameters[thisKey] = self.typecast(sender.getItem())
        else:
            instance.customParameters[thisKey] = self.typecast(sender.get())
        if self.postChange:
            self.postChange(self)

    def updateOverride(self, sender):
        layer_instance_override = (
            KEY + "." + self.owner.selectedInstanceName + "." + self.target
        )
        layer = Glyphs.font.selectedLayers[0]
        if isinstance(self.overridewidget, vanilla.PopUpButton):
            layer.userData[layer_instance_override] = self.typecast(sender.getItem())
        else:
            layer.userData[layer_instance_override] = self.typecast(sender.get())
        if self.postChange:
            self.postChange(self)

    def loadValues(self):
        instance = self.owner.selectedInstance
        thisKey = KEY + "." + self.target
        if not instance:
            return

        if not instance.customParameters or thisKey not in instance.customParameters:
            instance.customParameters[thisKey] = self.effect.params[self.target][
                "default"
            ]
        if instance.customParameters[thisKey]:
            if isinstance(self.defaultwidget, vanilla.PopUpButton):
                self.defaultwidget.setItem(instance.customParameters[thisKey])
            else:
                try:
                    self.defaultwidget.set(instance.customParameters[thisKey])
                except Exception as e:
                    print(
                        f"Error setting default value {instance.customParameters[thisKey]} for {thisKey}: {e}"
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

    def get_popup_items(self, effect, name):
        if "choices" in effect.params[name]:
            return effect.params[name]["choices"]
        # Here is where we hard-code the stuff we can't automatically compute
        if name == "counterSource":
            return ["<Default>"] + [l.name for l in Glyphs.font.masters]
        else:
            return ["oops " + name]


# On with the show.


class PendotDesigner:
    def __init__(self):
        self.idempotence = False
        font = Glyphs.font
        self.w = vanilla.Window((600, 600), "Pendot Designer")
        self.w.instanceSelector = LabelledComponent(
            "Instance",
            vanilla.PopUpButton(
                "auto", [i.name for i in font.instances], callback=self.reload_values
            ),
        )
        self.w.instanceSummary = vanilla.TextBox("auto", "")
        self.widget_reloaders = []
        instance = self.selectedInstance or Glyphs.font.instances[0]
        self.effects = [
            Dotter(font, instance),
            Stroker(font, instance),
            StartDot(font, instance),
            Guidelines(font, instance),
        ]

        self.w.tabs = vanilla.Tabs(
            "auto",
            [obj.display_name for obj in self.effects],
            callback=self.create_layer_preview,
        )

        self.migrate()

        for effect, tab in zip(self.effects, self.w.tabs):

            tab.enabledtoggle = vanilla.CheckBox(
                (10, 0, -10, 24),
                "Enabled ",
                callback=self.toggle_effect_enabled,
            )
            if effect.__class__.__name__ != "Guidelines":
                tab.glyphoverridelabel = vanilla.TextBox((350, 30, 250, 24), "")
                basepos = (10, 60, -10, 30)
                for name in effect.params.keys():
                    component = OverridableComponent(
                        self,
                        effect,
                        name,
                        basepos,
                        postChange=self.create_layer_preview,
                    )
                    setattr(tab, name, component)
                    self.widget_reloaders.append(component.loadValues)
                    basepos = (10, basepos[1] + 30, -10, 30)
            else:
                # The guidelines tab is just, as it were, built different
                metrics = Glyphs.font.masters[0].metrics
                # Georg keeps changing the type of this object.
                if callable(metrics):
                    metrics = metrics()
                columnDescriptions = [
                    {
                        "identifier": "height",
                        "title": "Height",
                        "editable": True,
                        "cellClass": vanilla.ComboBoxList2Cell,
                        "cellClassArguments": {"items": [m.name for m in metrics]},
                    },
                    {
                        "identifier": "thickness",
                        "title": "Thickness",
                        # "cellClass": SteppingTextBoxList2Cell,
                        "editable": True,
                    },
                ]

                self.guidelines_tab.list = vanilla.List2(
                    "auto",
                    items=[],
                    columnDescriptions=columnDescriptions,
                    editCallback=self.edit_guidelines,
                    deleteCallback=self.remove_guideline,
                )
                self.guidelines_tab.addButton = vanilla.Button(
                    "auto", "+", callback=self.add_guideline
                )
                self.guidelines_tab.addAutoPosSizeRules(
                    ["H:|-[list]-|", "H:[addButton]-|", "V:|-[list]-[addButton]-|"]
                )

        self.on_layer_change()
        self.w.createPreviewButton = vanilla.Button(
            "auto", "Create preview master", callback=self.createPreviewMaster
        )
        rules = [
            "H:|-[instanceSelector]-|",
            "H:|-[instanceSummary]-|",
            "H:|-[tabs]-|",
            "H:|-[createPreviewButton]-|",
            "V:|-20-[instanceSelector]-20-[instanceSummary]-20-[tabs]-20-[createPreviewButton]-|",
        ]
        metrics = {}
        self.w.addAutoPosSizeRules(rules, metrics)
        self.w.bind("close", self.finish)
        self.w.open()
        Glyphs.addCallback(self.on_layer_change, "GSUpdateInterface")
        # Glyphs.addCallback(self.create_layer_preview, "GSUpdateInterface")
        self.create_layer_preview()

    ## Utility methods
    def _is_valid_source(self, layer):
        if not layer or not layer.name:
            return False
        if layer.name.endswith(" dotted"):
            return False
        if layer.name == PREVIEW_MASTER_NAME:
            return False
        return True

    def enabled_effects(self, gsinstance):
        return gsinstance.customParameters[KEY + ".effects"] or []

    @property
    def selectedInstanceName(self):
        return str(self.w.instanceSelector.widget.getItem())

    @property
    def selectedInstance(self):
        for instance in Glyphs.font.instances:
            if instance.name == self.selectedInstanceName:
                return instance
        return None

    def ensure_quick_preview_layer_exists(self, glyph, layer):
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
        return destination_layer

    def ensure_full_preview_layer_exists(self, glyph, layer):
        preview_master = self.ensure_preview_master_exists()
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
        return preview_layer

    def ensure_preview_master_exists(self):
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
        return preview_master

    ## Guideline-related methods
    @property
    def guidelines_tab(self):
        guidelines = [
            ix
            for ix, effect in enumerate(self.effects)
            if effect.__class__.__name__ == "Guidelines"
        ]
        if guidelines:
            return self.w.tabs[guidelines[0]]

    def remove_guideline(self, sender=None):
        selectedIndexes = self.guidelines_tab.list.getSelectedIndexes()
        if not len(selectedIndexes):
            return
        selectedIndex = selectedIndexes[0]
        instance = self.selectedInstance or Glyphs.font.instances[0]
        if not instance.customParameters[KEY + ".guidelines"]:
            instance.customParameters[KEY + ".guidelines"] = []
        items = instance.customParameters[KEY + ".guidelines"]
        del items[selectedIndex]
        self.reload_guidelines()

    def add_guideline(self, sender=None):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        if not instance.customParameters[KEY + ".guidelines"]:
            instance.customParameters[KEY + ".guidelines"] = []
        items = instance.customParameters[KEY + ".guidelines"]
        items.append({"height": "0", "thickness": 10})
        self.reload_guidelines()

    def edit_guidelines(self, sender):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        instance.customParameters[KEY + ".guidelines"] = [
            {"height": item["height"], "thickness": item["thickness"]}
            for item in self.guidelines_tab.list.get()
        ]
        self.create_layer_preview()

    def reload_guidelines(self):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        items = instance.customParameters[KEY + ".guidelines"]
        if items:
            # Make a deep mutable copy of this
            self.guidelines_tab.list.set(
                [
                    {"height": item["height"], "thickness": item["thickness"]}
                    for item in items
                ]
            )
        self.create_layer_preview()

    ## Other methods
    def toggle_effect_enabled(self, sender=None):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        instance.customParameters[KEY + ".effects"] = [
            e.__class__.__name__
            for e, tab in zip(self.effects, self.w.tabs)
            if tab.enabledtoggle.get()
        ]
        self.create_layer_preview()

    def finish(self, sender=None):
        Glyphs.removeCallback(self.on_layer_change)
        Glyphs.removeCallback(self.create_layer_preview)
        if Glyphs.font:
            # Make quick preview layer invisible
            for layer in Glyphs.font.selectedLayers:
                glyph = layer.parent
                if glyph.layers[QUICK_PREVIEW_LAYER_NAME]:
                    glyph.layers[QUICK_PREVIEW_LAYER_NAME].visible = False
        del self.w

    def on_layer_change(self, sender=None):
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
            for effect, tab in zip(self.effects, self.w.tabs):
                # Skip for Guidelines
                if effect.__class__.__name__ == "Guidelines":
                    continue
                tab.glyphoverridelabel.set(
                    "Override glyph /" + layers[0].parent.name + "?"
                )
        self.reload_values()
        self.create_layer_preview()

    def reload_values(self, sender=None):
        instance = self.selectedInstance or Glyphs.font.instances[0]
        for reloader in self.widget_reloaders:
            reloader()
        # Reload the "enabled" checkboxes
        for effect, tab in zip(self.effects, self.w.tabs):
            tab.enabledtoggle.set(
                effect.__class__.__name__ in self.enabled_effects(instance)
            )
        self.reload_guidelines()

    def create_layer_preview(self, sender=None):
        instance = self.selectedInstance
        if not instance:
            return
        if not Glyphs.font:
            return

        if self.idempotence:
            return
        self.idempotence = True

        # Get a description of the effects
        effects = create_effects(Glyphs.font, instance, preview=True)
        self.w.instanceSummary.set(
            ", ".join(effect.description() for effect in effects)
        )

        for layer in Glyphs.font.selectedLayers:
            if (
                layer.name == QUICK_PREVIEW_LAYER_NAME
                or layer.name == PREVIEW_MASTER_NAME
            ):
                continue
            glyph = layer.parent
            destination_layer = self.ensure_quick_preview_layer_exists(glyph, layer)
            # Do dotting and redrawing if we are in the edit view
            if Glyphs.font.parent.windowController().activeEditViewController():
                destination_layer.visible = True
                if not glyph.undoManager():
                    continue
                glyph.undoManager().disableUndoRegistration()
                try:
                    destination_layer.shapes = transform_layer(layer, effects)
                    Glyphs.redraw()
                except Exception as e:
                    print(traceback.format_exc())
                    print(e)
                    print("Error in layer", layer)
                glyph.undoManager().enableUndoRegistration()
        self.idempotence = False

    def createPreviewMaster(self, sender=None):
        instance = self.selectedInstance or Glyphs.font.instances[0]

        effects = create_effects(Glyphs.font, instance, preview=False)

        for glyph in Glyphs.font.glyphs:
            glyph.undoManager().disableUndoRegistration()
            layer = glyph.layers[0]  # Really?
            preview_layer = self.ensure_full_preview_layer_exists(glyph, layer)
            preview_layer.shapes = transform_layer(layer, effects)
            glyph.undoManager().enableUndoRegistration()
        for effect in effects:
            effect.postprocess_font()
        Glyphs.redraw()

    def migrate(self):
        # Migrate any old userData parameters to custom parameters
        for instance in Glyphs.font.instances:
            to_delete = []
            if instance.userData:
                for ix, key in enumerate(instance.userData.keys()):
                    if key.startswith(KEY + "."):
                        instance.customParameters[key] = instance.userData[key]
                        to_delete.append(key)
            for key in reversed(to_delete):
                del instance.userData[key]


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
