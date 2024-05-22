KEY = "co.uk.corvelsoftware.Dotter"
PREVIEW_MASTER_NAME = "Pendot Preview"
QUICK_PREVIEW_LAYER_NAME = "Pendot Quick Preview"


def getParams(layer, instance, default_params, cmd_line_params=None):
    params = {}
    for paramname in default_params.keys():
        # First try inside the layer
        layer_instance_override = KEY + "." + instance.name + "." + paramname
        if layer_instance_override in layer.userData:
            params[paramname] = layer.userData[layer_instance_override]
        # Then try inside the instance; but here we look in custom parameters
        elif KEY + "." + paramname in instance.customParameters:
            params[paramname] = instance.customParameters[KEY + "." + paramname]
        # Then try command line parameters
        elif cmd_line_params and paramname in cmd_line_params:
            params[paramname] = cmd_line_params[paramname]
        else:  # Take the default
            params[paramname] = default_params[paramname]
        pass
    return params
