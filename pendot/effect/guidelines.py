from typing import List

from pendot.effect import Effect
from pendot.glyphsbridge import GSLayer, GSShape
from pendot.utils import makeRect


class Guidelines(Effect):
    params = {
        "guidelines": [
            {"height": "Descender", "thickness": 10},
            {"height": "x-Height", "thickness": 10},
            {"height": "Cap Height", "thickness": 10},
            {"height": "Ascender", "thickness": 10},
        ],
        "guidelineOverlap": 0,
    }

    @property
    def display_params(self):
        return []

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        if not layer.master:
            return []
        gloverlap = self.parameter("guidelineOverlap", layer)
        guidelines = self.parameter("guidelines", layer)

        fontmetrics = layer.parent.parent.metrics
        mastermetrics = layer.master.metrics

        newshapes = []

        if callable(mastermetrics):  # Glyphs.app
            mastermetrics = mastermetrics()
            fontmetrics = [x.title.lower() for x in fontmetrics]
        else:
            fontmetrics = [x.type.lower() for x in fontmetrics]
        metricsdict = {
            metric: value.position for metric, value in zip(fontmetrics, mastermetrics)
        }
        for guideline in guidelines:
            height, thickness = guideline["height"], guideline["thickness"]
            if height.lower() in metricsdict:
                height = metricsdict[height.lower()]
            else:
                try:
                    height = float(height)
                except ValueError:
                    continue
            try:
                thickness = float(thickness)
            except ValueError:
                continue

            bottomLeft = (-gloverlap, height)
            topRight = (layer.width + gloverlap, height + thickness)
            layerRect = makeRect(bottomLeft, topRight)
            newshapes.append(layerRect)
        return newshapes
