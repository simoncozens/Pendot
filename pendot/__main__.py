import argparse
import json
import sys

from glyphsLib import load

from pendot import create_effects, find_instance, transform_font
from pendot.effect.dotter import Dotter
from pendot.effect.guidelines import Guidelines
from pendot.effect.stroker import Stroker


# https://stackoverflow.com/questions/6365601
def set_default_subparser(self, name, args=None, positional_args=0):
    subparser_found = False
    for arg in sys.argv[1:]:
        if arg in ["-h", "--help"]:  # global help if no subparser
            break
    else:
        for x in self._subparsers._actions:
            if not isinstance(x, argparse._SubParsersAction):
                continue
            for sp_name in x._name_parser_map.keys():
                if sp_name in sys.argv[1:]:
                    subparser_found = True
        if not subparser_found:
            if args is None:
                sys.argv.insert(1, name)
            else:
                args.insert(0, name)


argparse.ArgumentParser.set_default_subparser = set_default_subparser


def main(args=None):
    parser = argparse.ArgumentParser()
    # Parse subcommands "auto", "dot" and "stroke"
    subparsers = parser.add_subparsers(dest="command")

    auto_parser = subparsers.add_parser(
        "auto",
        help="Either dot or stroke a font depending on the instance parameters",
    )
    auto_parser.add_argument("--output", "-o", help="Output font file")
    auto_parser.add_argument("--config", help="JSON configuration as text")
    auto_parser.add_argument("--config-file", help="JSON configuration file")
    auto_parser.add_argument("input", help="Input font file")
    auto_parser.add_argument("instance", help="Instance name", nargs="?")

    dot_parser = subparsers.add_parser(
        "dot",
        help="Add dots to a font",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    dot_parser.add_argument("--output", "-o", help="Output font file")
    Dotter.add_parser_args(dot_parser)
    dot_parser.add_argument("input", help="Input font file")
    dot_parser.add_argument("instance", help="Instance name", nargs="?")

    stroke_parser = subparsers.add_parser(
        "stroke",
        help="Create a stroked font",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    Stroker.add_parser_args(stroke_parser)
    stroke_parser.add_argument("input", help="Input font file")
    stroke_parser.add_argument("--output", "-o", help="Output font file")
    stroke_parser.add_argument("instance", help="Instance name", nargs="?")

    parser.set_default_subparser("auto")
    args = parser.parse_args(args)
    if not args.command:
        parser.print_help()
        exit(1)
    font = load(args.input)
    output = args.output or args.input.replace(
        ".glyphs", "-" + args.command + ".glyphs"
    )
    gsinstance = find_instance(font, args.instance)

    if args.command == "auto":
        overrides = {}
        if args.config:
            overrides = json.loads(args.config)
        if args.config_file:
            with open(args.config_file) as f:
                overrides = json.load(f)
        effects = create_effects(font, gsinstance, overrides)
    elif args.command == "dot":
        effects = [Dotter(font, gsinstance, args.__dict__)]
    elif args.command == "stroke":
        effects = [Stroker(font, gsinstance, args.__dict__)]
    elif args.command == "guidelines":
        effects = [Guidelines(font, gsinstance, args.__dict__)]
    else:
        print("Unknown command", args.command)
        sys.exit(1)

    transform_font(font, effects)
    print("Saving to", output)
    font.save(output)


if __name__ == "__main__":
    main()
