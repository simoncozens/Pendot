import logging
import os
import glyphsLib
from gftools.builder.recipeproviders.googlefonts import GFBuilder, DEFAULTS


log = logging.getLogger("pendot")


class Pendot(GFBuilder):
    def write_recipe(self):
        self.recipe = {}
        self.config = {**DEFAULTS, **self.config}
        for field in ["vfDir", "ttDir", "otDir", "woffDir"]:
            self.config[field] = self.config[field].replace(
                "$outputDir", self.config["outputDir"]
            )
        self.source = glyphsLib.load(self.sources[0].path)
        for guideline in self.guidelines:
            for instance in self.source.instances:
                self.build_a_static(instance, guidelines=guideline)
        return self.recipe

    @property
    def guidelines(self):
        if self.config.get("doGuidelines"):
            return [False, True]
        return [False]

    def build_a_static(self, instance, guidelines):
        source = self.sources[0].path
        family_name = self.sources[0].family_name
        filename = family_name.replace(" ", "") + "-" + instance.name.replace(" ", "")
        new_glyphs_file = "build/{}.glyphs".format(filename)
        outdir = self.config["ttDir"]
        target = os.path.join(outdir, f"{filename}.ttf")

        self.recipe[target] = [
            {"source": self.sources[0].path},
            {
                "operation": "exec",
                "exe": "pendot",
                "args": f'-o {new_glyphs_file} {source} "{instance.name}"',
            },
            {"source": new_glyphs_file},
        ]
        # Do guidelines here...
        self.recipe[target] += [
            {
                "operation": "buildTTF",
                "fontmake_args": self.fontmake_args(self.sources[0]),
            },
            self.fix(),
        ]

    def fix(self):
        if self.config.get("includeSourceFixes"):
            return {"operation": "fix", "args": "--include-source-fixes"}
        return {"operation": "fix"}
