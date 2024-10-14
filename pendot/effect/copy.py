from typing import List

from pendot.constants import KEY
from pendot.effect import Effect
from pendot.glyphsbridge import GSLayer, GSShape


class Copy(Effect):
    params = {}

    @property
    def display_name(self):
        return "Copy paths"

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        if layer.parent.userData.get(KEY + ".disableCopy"):
            return []
        return shapes
