from typing import Optional, List

from pendot.constants import KEY
from pendot.glyphsbridge import GSLayer, GSFont, GSInstance, GSShape


class Effect:
    params = {}

    def __init__(
        self,
        font: GSFont,
        instance: GSInstance,
        overrides: Optional[dict] = None,
        preview: bool = False,
    ):
        self.font = font
        self.instance = instance
        self.overrides = overrides or {}
        self.preview = preview

    def parameter(self, paramname: str, layer: Optional[GSLayer]):
        # First try inside the layer
        layer_instance_override = KEY + "." + self.instance.name + "." + paramname
        if layer and layer_instance_override in layer.userData:
            return layer.userData[layer_instance_override]
        # Then try inside the instance; but here we look in custom parameters
        elif KEY + "." + paramname in self.instance.customParameters:
            return self.instance.customParameters[KEY + "." + paramname]
        # Then try command line parameters
        elif self.overrides and paramname in self.overrides:
            return self.overrides[paramname]
        else:  # Take the default
            return self.params[paramname]

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        pass

    def postprocess_font(self):
        pass

    @property
    def display_params(self):
        return self.params.keys()

    def description(self):
        params = [f"{k}={self.parameter(k,None)}" for k in self.display_params]
        return self.__class__.__name__ + "(" + ("; ".join(params)) + ")"
