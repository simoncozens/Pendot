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
        GSFont,  # noqa: F401
        GSInstance,  # noqa: F401
        GSPath,
        GSLayer,  # noqa: F401
        GSComponent,
        GSGlyph,  # noqa: F401
        GSNode,  # noqa: F401
        OFFCURVE,  # noqa: F401
        CURVE,  # noqa: F401
        LINE,  # noqa: F401
        GSLINE,  # noqa: F401
    )
    import sys

    def Message(message):
        print(message)
        sys.exit(1)


GSShape = Union[GSPath, GSComponent]
