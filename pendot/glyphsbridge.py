from typing import Union


try:
    from GlyphsApp import (
        GSFont,
        GSInstance,
        GSPath,
        GSComponent,
        GSGlyph,
        GSNode,
        GSLayer,
        OFFCURVE,
        GSLINE,
        CURVE,
        LINE,
        Message,
    )
except ImportError:
    from glyphsLib.classes import (
        GSFont,
        GSInstance,
        GSPath,
        GSLayer,
        GSComponent,
        GSGlyph,
        GSNode,
        OFFCURVE,
        CURVE,
        LINE,
        GSLINE,
    )
    import sys

    def Message(message):
        print(message)
        sys.exit(1)


GSShape = Union[GSPath, GSComponent]
