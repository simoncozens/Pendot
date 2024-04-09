from .constants import KEY
from .dotter import GSFont, DOTTER_PARAMS, doDotter, addComponentGlyph
from .stroker import doStroker, STROKER_PARAMS
from .guidelines import drawRect
from logging import getLogger

try:
    import tqdm

    progress = tqdm.tqdm
except ImportError:
    progress = list

PARAMS = {**STROKER_PARAMS, **DOTTER_PARAMS}

logger = getLogger(__name__)


# In the future we might want to create an output font with multiple
# instances; for now we just take a single instance name and apply
# its parameters to all master layers
def dot_font(font: GSFont, instance: str):
    gsinstance = None
    for i in font.instances:
        if i.name == instance:
            gsinstance = i
            break
    if not gsinstance:
        raise ValueError("Could not find instance " + instance)
    results = {}
    for glyph in progress(font.glyphs):
        for layer in glyph.layers:
            if layer.layerId == layer.associatedMasterId:
                results[layer] = doDotter(layer, gsinstance)
    for layer, shapes in results.items():
        layer.shapes = shapes
    addComponentGlyph(font, gsinstance)
    return font


# This is expected to be used in the Designer for previewing
def stroke_font(font: GSFont, params: dict = {}):
    for glyph in progress(font.glyphs):
        for layer in glyph.layers:
            doStroker(layer, params)


def add_guidelines_to_layer(layer, instance):
    glkey = KEY + ".guidelines"
    gloverlapkey = KEY + ".guidelineOverlap"
    if gloverlapkey not in instance.userData:
        gloverlap = 0
    else:
        gloverlap = instance.userData[gloverlapkey]
    if not layer.master:
        return
    fontmetrics = layer.parent.parent.metrics
    mastermetrics = layer.master.metrics
    if callable(mastermetrics):  # Glyphs.app
        mastermetrics = mastermetrics()
        fontmetrics = [x.title.lower() for x in fontmetrics]
    else:
        fontmetrics = [x.type.lower() for x in fontmetrics]
    metricsdict = {
        metric: value.position for metric, value in zip(fontmetrics, mastermetrics)
    }
    if glkey not in instance.userData:
        return
    for guideline in instance.userData[glkey]:
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
        layer.shapes.append(layerRect)
