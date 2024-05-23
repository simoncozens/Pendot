from logging import getLogger
from typing import Callable, List, Optional

from pendot.constants import PREVIEW_MASTER_NAME, QUICK_PREVIEW_LAYER_NAME, KEY
from pendot.dotter import Dotter
from pendot.effect import Effect
from pendot.glyphsbridge import GSFont, GSInstance, GSLayer
from pendot.guidelines import Guidelines
from pendot.stroker import Stroker
from pendot.utils import decomposedPaths

try:
    import tqdm

    progress = tqdm.tqdm
except ImportError:
    progress = list

logger = getLogger(__name__)


def find_instance(font: GSFont, instance: str) -> GSInstance:
    gsinstance = None
    for i in font.instances:
        if i.name == instance:
            gsinstance = i
            break
    if not gsinstance:
        raise ValueError("Could not find instance " + instance)
    return gsinstance


def create_effects(
    font: GSFont,
    instance: GSInstance,
    args: Optional[object] = None,
    preview: bool = False,
):
    effectlist = instance.customParameters[KEY + ".effects"]
    if isinstance(effectlist, str):
        effectlist = [effectlist]
    effects = []
    for name in effectlist:
        effectmap = {
            "Stroker": Stroker,
            "Dotter": Dotter,
            "Guidelines": Guidelines,
        }
        if name not in effectmap:
            raise ValueError("Unknown effect " + name)
        effects.append(effectmap[name](font, instance, args, preview))
    return effects


def transform_font(font: GSFont, effects: List[Effect]):
    results = {}
    font.masters = [m for m in font.masters if m.name != PREVIEW_MASTER_NAME]
    for glyph in progress(font.glyphs):
        for layer in glyph.layers:
            if layer.layerId == layer.associatedMasterId:
                results[layer] = transform_layer(layer, effects)
    for layer, shapes in results.items():
        if shapes:
            layer.shapes = shapes
    for effect in effects:
        effect.postprocess_font()
    # Delete preview master
    return font


def transform_layer(layer: GSLayer, effects: List[Effect]):
    if layer.name == QUICK_PREVIEW_LAYER_NAME or layer.name == PREVIEW_MASTER_NAME:
        return []
    paths = decomposedPaths(layer)
    results = []
    for effect in effects:
        newshapes = effect.process_layer_shapes(layer, paths)
        results += newshapes
    return results
