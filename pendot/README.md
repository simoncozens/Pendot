# Pendot

This is a Python module used to add "effects" to Glyphs font source files;
it will take an existing source file; add a number of transformations to the
paths such as stroking or dotting open paths, adding guidelines, showing
starting positions and so on; and save the result to a new Glyphs file.

It is designed to be used in conjunction with the Glyphs [Pendot Designer](https://github.com/simoncozens/Pendot)
script, but is available as a standalone Python package so that Dotter files
can be built from the command line. The effects have various parameters
which can be specified on the command line, or by using custom parameter
values attached to a Glyphs instance; the parameters can also be overriden
per glyph.

## Simple use

To add dots to all open paths in a Glyphs font, with no custom settings
added by the Pendot Designer script:

```
$ pendot dot -o Font-dots.glyphs --dot-size 30 --dot-spacing 20 Font.glyphs
```

To add strokes to all open paths in a Glyphs font, with no custom settings
added by the Pendot Designer script:

```
$ pendot stroke -o Font-stroke.glyphs --stroke-width 30 Font.glyphs
```

However, _these will not give optimal results_. For better results, use
Pendot Designer to tune the parameters on a per-glyph and per-instance basis,
and run with

```
$ pendot -o Font-dots.glyphs Font.glyphs Regular
```

which will look for custom parameters stored in the Regular instance.

To run a combination of effects (small strokes, big dots, and guidelines!)
either use Pendot Designer, or provide a JSON string or file on the command
line:

```
$ pendot --config '{"effects": ["Stroker", "Dotter", "Guidelines"], \
  "strokeWidth": 10, "dotSize": 50 }' --output Font-fancy.glyphs Font.glyphs
```
