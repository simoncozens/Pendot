import logging
import os
import glyphsLib
from gftools.builder.recipeproviders.googlefonts import GFBuilder, DEFAULTS
from pathlib import Path


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
        for instance in self.source.instances:
            self.build_a_static(instance)
        return self.recipe

    def build_a_static(self, instance):
        source = self.sources[0].path
        family_name = self.sources[0].family_name
        final_family_name = self.sources[0].family_name + " " + instance.name
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
        ufo_target = str(self.instance_dir / f"{filename}.ufo")
        self.recipe[target] += [
            # Manual reimplementation of instantiateUfo operation
            # because the source doesn't exist yet. We do this rather
            # than compiling the glyphs file directly because it allows us
            # to set instance-specific values (stylename, etc)
            {
                "operation": "exec",
                "exe": "fontmake",
                "args": f'-i "{family_name} {instance.name}" -o ufo -g {new_glyphs_file} --output-path {ufo_target}',
            },
            {
                "source": ufo_target,
            },
            {
                "operation": "buildTTF",
                "fontmake_args": self.fontmake_args(self.sources[0]),
            },
            {"operation": "rename", "name": final_family_name, "args": "--just-family"},
            self.fix(),
        ]

    def fix(self):
        if self.config.get("includeSourceFixes"):
            return {"operation": "fix", "args": "--include-source-fixes"}
        return {"operation": "fix"}

    @property
    def instance_dir(self):
        return Path("build") / "instance_ufos"
