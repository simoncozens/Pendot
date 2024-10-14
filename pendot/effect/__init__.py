import re
from typing import Optional, List

from pendot.constants import KEY
from pendot.glyphsbridge import GSLayer, GSFont, GSInstance, GSShape


class Effect:
    params = {}

    @property
    def display_name(self):
        return self.__class__.__name__

    def __init__(
        self,
        font: GSFont,
        instance: Optional[GSInstance],
        overrides: Optional[dict] = None,
        preview: bool = False,
    ):
        self.font = font
        self.instance = instance
        self.overrides = overrides or {}
        self.preview = preview

    def parameter(self, paramname: str, layer: Optional[GSLayer]):
        # First try inside the layer
        # print("Getting parameter ", paramname)
        if self.instance:
            layer_instance_override = KEY + "." + self.instance.name + "." + paramname
            if layer and layer_instance_override in layer.userData:
                # print("Resolved from layer")
                return layer.userData[layer_instance_override]
            # Then try inside the instance; but here we look in custom parameters
            elif KEY + "." + paramname in self.instance.customParameters:
                # print("Resolved from instance params")
                return self.instance.customParameters[KEY + "." + paramname]
        # Then try command line parameters
        if (
            self.overrides
            and paramname in self.overrides
            and self.overrides[paramname] is not None
        ):
            # print("Resolved from command line")
            return self.overrides[paramname]
        else:  # Take the default
            # print("Resolved from default")
            return self.params[paramname]["default"]

    def process_layer_shapes(self, layer: GSLayer, shapes: List[GSShape]):
        pass

    def postprocess_font(self):
        pass

    @property
    def display_params(self):
        return self.params.keys()

    def description(self):
        params = [f"{k}={self.parameter(k,None)}" for k in self.display_params]
        return self.__class__.__name__ + "(" + ("; ".join(params)) + ")"

    @classmethod
    def add_parser_args(cls, parser):
        for key, value in cls.params.items():
            # Turn camel-cased key into kebab-case
            arg_key = key[0].lower() + re.sub(r"([A-Z])", r"-\1", key[1:]).lower()
            argparse_kwargs = {
                "default": value["default"],
                "type": value.get("type", type(value["default"])),
                "dest": key,
            }
            if "help" in value:
                argparse_kwargs["help"] = value["help"]
            if "choices" in value:
                argparse_kwargs["choices"] = value["choices"]
            if argparse_kwargs["type"] is bool:
                del argparse_kwargs["type"]
                if argparse_kwargs["default"]:
                    arg_key = "no-" + arg_key
                    argparse_kwargs["action"] = "store_false"
                    argparse_kwargs["help"] = (
                        "Don't "
                        + argparse_kwargs["help"][0].lower()
                        + argparse_kwargs["help"][1:]
                    )
                else:
                    argparse_kwargs["action"] = "store_true"
            parser.add_argument(f"--{arg_key}", **argparse_kwargs)
