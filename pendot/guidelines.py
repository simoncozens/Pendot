try:
    from GlyphsApp import GSLINE, GSFont, GSNode, GSPath, GSGlyph, GSLayer
except:
    from glyphsLib.classes import GSLINE, GSFont, GSNode, GSPath, GSGlyph, GSLayer


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


def decomposed_paths(layer):
    newpaths = [l.clone() for l in layer.paths]
    for component in layer.components:
        transform = component.transform
        to_append = decomposed_paths(component.layer)
        for path in to_append:
            path.applyTransform(transform)
        newpaths += to_append
    return newpaths


def decompose_all_layers(font):
    for glyph in font.glyphs:
        for layer in glyph.layers:
            layer.shapes = list(layer.paths) + decomposed_paths(layer)


def add_guidelines(font, args):
    for glyph in font.glyphs:
        if glyph.name.startswith("_"):
            continue
        if not glyph.export:
            continue
        for layer in glyph.layers:
            # If this has any components which don't start in "_part", skip it
            if layer.components and not all(
                component.name.startswith("_part") for component in layer.components
            ):
                continue
            # Skip anything with underscore anchors
            if any(anchor.name.startswith("_") for anchor in layer.anchors):
                continue
            master = layer.master
            if not master:
                continue
            heightsAndThicknesses = [
                (master.descender, args.default_thickness),
                (0, args.thicker_thickness),
                (master.xHeight, args.default_thickness),
                (master.ascender, args.default_thickness),
            ]

            for height, thickness in heightsAndThicknesses:
                bottomLeft = (-args.overlap, height)
                topRight = (layer.width + args.overlap, height + thickness)
                layerRect = drawRect(bottomLeft, topRight)
                layer.shapes.append(layerRect)


def add_guideline_glyph(font, thickness):
    if "_guide" in font.glyphs:
        return
    font.glyphs.append(GSGlyph("_guide"))
    for master in font.masters:
        layer = GSLayer()
        layer.associatedMasterId = master.id
        layer.layerId = master.id
        layer.width = 1000
        layer.shapes = [GSPath()]
        layer.shapes[0].nodes = [
            GSNode((0, 0), GSLINE),
            GSNode((1000, 0), GSLINE),
            GSNode((1000, thickness), GSLINE),
            GSNode((0, thickness), GSLINE),
        ]
        font.glyphs["_guide"].layers.append(layer)
