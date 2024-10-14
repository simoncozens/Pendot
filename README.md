# Pendot

Pendot is a collection of tools for adding dotting, stroking and other effects to fonts, typically for creating variants of handwriting fonts. It consists of:

- [pendot](pendot/README.md): a Python library for adding "effects" to a Glyphs font instance. This is intended to be used _inside Glyphs_ (as part of the other tools below) and as part of an automated build process when building the resulting fonts.
- Dotter Controller: A Glyphs reporter plugin allowing you to set certain nodes of your font to have, or not have, fixed dot positions.
- Pendot Designer: A Glyphs script allowing you to set your dotting parameters (dot size, spacing, etc.) on a font-wide, per-instance, and per-glyph basis.
- ufostroker: A pre-compiled version of the [ufostroker-py](https://github.com/simoncozens/ufostroker-py) library for stroking fonts.
- kurbopy: A pre-compiled version of the [kurbopy](https://github.com/simoncozens/kurbopy) library for fast curve manipulation.

## Installation

As this collection contains both a Glyphs plugin and a Glyphs script, the installation is slightly involved:

1. Change to your Glyphs _plugins_ directory:

```
cd ~/Library/Application Support/Glyphs 3/Plugins/
```

2. Clone the Pendot repository:

```
git clone https://github.com/simoncozens/Pendot/
```

3. Change to your Glyphs _scripts_ directory:

```
cd ~/Library/Application Support/Glyphs 3/Scripts
```

4. Link the Pendot Designer script into the scripts directory:

```
ln -s ../Plugins/Pendot/Pendot\ Designer.py .
```

You will also need the "fontTools" and "vanilla" libraries installed in your copy of Glyphs. These can be added from the "Modules" tab of the Glyphs plugin manager.
