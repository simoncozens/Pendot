from logging import getLogger
import sys
from typing import List, Optional

from pendot.constants import KEY, PREVIEW_MASTER_NAME, QUICK_PREVIEW_LAYER_NAME
from pendot.effect import Effect
from pendot.effect.startdot import StartDot
from pendot.effect.copy import Copy
from pendot.effect.dotter import Dotter
from pendot.effect.guidelines import Guidelines
from pendot.effect.stroker import Stroker
from pendot.glyphsbridge import GSFont, GSInstance, GSLayer
from pendot.utils import decomposedPaths

try:
    import tqdm

    progress = tqdm.tqdm
except ImportError:
    progress = list

logger = getLogger(__name__)


def find_instance(font: GSFont, instance: str) -> Optional[GSInstance]:
    gsinstance = None
    for i in font.instances:
        if i.name == instance:
            gsinstance = i
            break
    return gsinstance


def create_effects(
    font: GSFont,
    instance: Optional[GSInstance],
    args: Optional[object] = None,
    preview: bool = False,
):
    effectlist = []
    if args is not None and args.get("effects"):
        effectlist = args["effects"]
    elif instance:
        effectlist = instance.customParameters[KEY + ".effects"] or []
    if isinstance(effectlist, str):
        effectlist = [effectlist]
    effects = []
    for name in effectlist:
        effectmap = {
            "Copy": Copy,
            "Stroker": Stroker,
            "Dotter": Dotter,
            "Guidelines": Guidelines,
            "StartDot": StartDot,
        }
        if name not in effectmap:
            raise ValueError("Unknown effect " + name)
        effects.append(effectmap[name](font, instance, args, preview))
    return effects


def transform_font(
    font: GSFont, effects: List[Effect], instance: Optional[GSInstance] = None
):
    results = {}
    font.masters = [m for m in font.masters if m.name != PREVIEW_MASTER_NAME]
    if len(font.masters) > 1:
        if instance is None and len(font.instances) == 1:
            instance = font.instances[0]
        if instance is None:
            print("No instance provided, using first master as relevant master.")
            relevant_master = font.masters[0]
        else:
            relevant_masters = [m for m in font.masters if m.axes == instance.axes]
            if len(relevant_masters) > 1:
                print(
                    "Multiple masters found for instance, using first one as relevant master."
                )
            elif len(relevant_masters) == 0:
                print(
                    f"Couldn't find master for instance {instance}, check your axis values."
                )
                sys.exit(1)
            relevant_master = relevant_masters[0]
    else:
        relevant_master = font.masters[0]

    for glyph in progress(font.glyphs):
        relevant_layers = [
            layer for layer in glyph.layers if layer.layerId == relevant_master.id
        ]
        if not relevant_layers:
            logger.warning(
                f"Glyph {glyph.name} has no layer for master {relevant_master.name}, skipping."
            )
            continue
        if len(relevant_layers) > 1:
            logger.warning(
                f"Glyph {glyph.name} has multiple layers for master {relevant_master.name}, don't know which to use."
            )
            sys.exit(1)

        for layer in relevant_layers:
            if layer.layerId == relevant_master.id:
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
        if newshapes is None:
            raise ValueError(f"Effect {effect} did not return shapes")
        results += newshapes
    return results
