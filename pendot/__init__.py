from .dotter import GSFont, KEY, doDotter, PARAMS
from .stroker import doStroker # Not yet!
from logging import getLogger
try:
    import tqdm
    progress = tqdm.tqdm
except ImportError:
    progress = list

logger = getLogger(__name__)

def dot_font(font: GSFont, params: dict = {}):
    for param in PARAMS.keys():
        if param in params:
            logger.info(f"Using param {param}={params[param]} from command line")
        elif KEY in font.userData and param in font.userData[KEY]:
            params[param] = font.userData[KEY][param]
            logger.info(f"Using param {param}={params[param]} from font")
        else:
            logger.info(f"Using default value {param}={params[param]}")
            params[param] = PARAMS[param]
    for glyph in progress(font.glyphs):
        for layer in glyph.layers:
            doDotter(layer, params)
    return font

# This is expected to be used in the Designer for previewing
def stroke_font(font: GSFont, params: dict = {}):
    # For now
    params = {
        "width": 20,
        "height": 20,
        "startcap": "round",
        "endcap": "round",
        "jointype": "round",
        "remove_internal": False,
        "remove_external": False,
        "segmentwise": False,
    }
    for glyph in progress(font.glyphs):
        for layer in glyph.layers:
            doStroker(layer, params)
