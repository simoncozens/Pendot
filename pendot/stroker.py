from ufostroker import constant_width_stroke
from ufoLib2.objects import Glyph
from glyphsLib.builder.builders import UFOBuilder

def doStroker(layer, params: dict):
    ufoglyph: Glyph = Glyph()
    if not layer.paths:
        return
    UFOBuilder(layer.parent.parent).to_ufo_paths(ufoglyph, layer)
    constant_width_stroke(ufoglyph, **params)
    layer.paths = []
    ufoglyph.draw(layer.getPen())