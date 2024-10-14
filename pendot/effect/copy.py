from typing import List

from pendot.effect import Effect
from pendot.glyphsbridge import GSLayer, GSShape


class Copy(Effect):
    params = {}

    @property
    def display_name(self):
        return "Copy paths"

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        return shapes
