import math
from typing import List

from pendot.constants import KEY
from pendot.effect import Effect
from pendot.glyphsbridge import GSLayer, GSShape
from pendot.utils import makeRect


class Guidelines(Effect):
    params = {
        "guidelines": {
            "default": [
                {"height": "Descender", "thickness": 10},
                {"height": 0, "thickness": 20},
                {"height": "x-Height", "thickness": 5},
                {"height": "Cap Height", "thickness": 10},
                # {"height": "Ascender", "thickness": 10},
            ]
        },
        "guidelineOverlap": {
            "default": 0,
            "help": "Overlap of the guidelines on left and right in font units",
        },
        "guidelineQuantize": {
            "default": 0,
            "help": "Quantize the guidelines to a multiple of this value",
        },
    }

    @property
    def display_params(self):
        return []

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        if not layer.master:
            return []
        if layer.parent.userData.get(KEY + ".disableGuidelines"):
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

            left = -gloverlap
            right = layer.width + gloverlap
            quantization = self.parameter("guidelineQuantize", layer)
            dashlength = 0
            dashPattern = guideline.get("dashPattern")
            if dashPattern:
                dashlength = sum(dashPattern)
                # dashlength_nogap = sum(dashPattern[:-1])
                # Adjust quantization to fit the nearest
                quantization = math.ceil(quantization / dashlength) * dashlength
            if quantization:
                left = math.floor(left / quantization) * quantization
                right = math.ceil(right / quantization) * quantization

            if not dashPattern:
                lrs = [(left, right)]
            else:
                lrs = []
                while True:
                    for i in range(0, len(dashPattern), 2):
                        lrs.append((left, left + dashPattern[i]))
                        left += dashPattern[i]
                        if left > right:
                            break
                        left += dashPattern[i + 1]
                        if left > right:
                            break
                    if left > right:
                        break

            for left, right in lrs:
                bottomLeft = (left, height)
                topRight = (right, height + thickness)
                layerRect = makeRect(bottomLeft, topRight)
                newshapes.append(layerRect)
        return newshapes
