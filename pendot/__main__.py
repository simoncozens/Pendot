from pendot.constants import getParams
from .dotter import GSFont
from pendot import dot_font, find_instance, stroke_font
import argparse
import sys


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
        "auto", help="Either dot or stroke a font depending on the instance parameters"
    )
    auto_parser.add_argument("--output", "-o", help="Output font file")
    auto_parser.add_argument("input", help="Input font file")
    auto_parser.add_argument("instance", help="Instance name")

    dot_parser = subparsers.add_parser("dot", help="Add dots to a font")
    dot_parser.add_argument("--output", "-o", help="Output font file")
    dot_parser.add_argument("--dot-size", type=float, help="Dot size")
    dot_parser.add_argument("--dot-spacing", type=float, help="Dot spacing")
    dot_parser.add_argument(
        "--prevent-overlaps", action="store_true", help="Prevent overlaps"
    )
    dot_parser.add_argument(
        "--split-paths", action="store_true", help="Split paths at intersections"
    )

    stroke_parser = subparsers.add_parser("stroke", help="Create a stroked font")
    stroke_parser.add_argument("input", help="Input font file")
    stroke_parser.add_argument("--output", "-o", help="Output font file")

    parser.set_default_subparser("auto")
    args = parser.parse_args(args)
    if not args.command:
        parser.print_help()
        exit(1)
    font = GSFont(args.input)
    output = args.output or args.input.replace(
        ".glyphs", "-" + args.command + ".glyphs"
    )

    if args.command == "auto":
        gsinstance = find_instance(font, args.instance)
        params = getParams(font, gsinstance, {"mode": "auto"})
        mode = params["mode"]
        if mode == "auto":
            print(
                f"Instance {args.instance} is not set up for pendot; "
                "use Pendot Designer to choose a mode"
            )
            sys.exit(1)
        elif mode == "dotter":
            args.command = "dot"
        elif mode == "stroker":
            args.command = "stroke"
        else:
            print("Unknown mode", mode)
            sys.exit(1)
    if args.command == "dot":
        params = {}
        if hasattr(args, "dot_spacing") and args.dot_spacing:
            params["dotSpacing"] = args.dot_spacing
        if hasattr(args, "prevent_overlaps") and args.prevent_overlaps:
            params["preventOverlaps"] = True
        if hasattr(args, "split_paths") and args.split_paths:
            params["splitPaths"] = True
        dot_font(font, args.instance, params)
    elif args.command == "stroke":
        stroke_font(font, args.instance)
    else:
        print("Unknown command", args.command)
        sys.exit(1)

    print("Saving to", output)
    font.save(output)


if __name__ == "__main__":
    main()
