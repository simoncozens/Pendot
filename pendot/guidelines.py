from typing import List

from .effect import Effect
from .glyphsbridge import GSPath, GSNode, GSLINE, GSLayer, GSShape


# from https://github.com/mekkablue/Glyphs-Scripts/blob/a4421210dd17305e3205b7ca998cab579b778bf6/Paths/Fill%20Up%20with%20Rectangles.py
def drawRect(myBottomLeft, myTopRight):
    myRect = GSPath()
    myCoordinates = [
        [myBottomLeft[0], myBottomLeft[1]],
        [myTopRight[0], myBottomLeft[1]],
        [myTopRight[0], myTopRight[1]],
        [myBottomLeft[0], myTopRight[1]],
    ]

    for thisPoint in myCoordinates:
        newNode = GSNode((thisPoint[0], thisPoint[1]), GSLINE)
        myRect.nodes.append(newNode)

    myRect.closed = True
    return myRect


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

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        if not layer.master:
            return
        gloverlap = self.parameter("overlap", layer)
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
            layerRect = drawRect(bottomLeft, topRight)
            newshapes.append(layerRect)
        return newshapes
