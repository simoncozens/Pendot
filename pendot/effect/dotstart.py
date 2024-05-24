from typing import List

from pendot.effect import Effect
from pendot.glyphsbridge import GSLayer, GSShape
from pendot.utils import makeCircle


class DotStart(Effect):
    params = {"dotSize": 30}

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        newshapes = []
        for shape in shapes:
            if not shape.nodes:
                continue
            start = (shape.nodes[0].position.x, shape.nodes[0].position.y)
            newshapes.append(makeCircle(start, self.parameter("dotSize", layer) / 2))
        return newshapes
