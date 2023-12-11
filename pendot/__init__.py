from .constants import KEY
from .dotter import GSFont, DOTTER_PARAMS, doDotter
from .stroker import doStroker, STROKER_PARAMS
from logging import getLogger
try:
    import tqdm
    progress = tqdm.tqdm
except ImportError:
    progress = list

PARAMS = {**STROKER_PARAMS, **DOTTER_PARAMS}

logger = getLogger(__name__)

def dot_font(font: GSFont, params: dict = {}):
    for param in DOTTER_PARAMS.keys():
        if param in params:
            logger.info(f"Using param {param}={params[param]} from command line")
        elif KEY in font.userData and param in font.userData[KEY]:
            params[param] = font.userData[KEY][param]
            logger.info(f"Using param {param}={params[param]} from font")
        else:
            params[param] = PARAMS[param]
            logger.info(f"Using default value {param}={params[param]}")
    for glyph in progress(font.glyphs):
        for layer in glyph.layers:
            doDotter(layer, params)
    return font

# This is expected to be used in the Designer for previewing
def stroke_font(font: GSFont, params: dict = {}):
    for glyph in progress(font.glyphs):
        for layer in glyph.layers:
            doStroker(layer, params)
