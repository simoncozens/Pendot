from .dotter import GSFont, KEY, PARAMS
from pendot import dot_font
import argparse

parser = argparse.ArgumentParser()
# Parse subcommands "dot" and "stroke"
subparsers = parser.add_subparsers(dest="command")
dot_parser = subparsers.add_parser("dot")
dot_parser.add_argument("input", help="Input font file")
dot_parser.add_argument("--output", "-o", help="Output font file")
dot_parser.add_argument("--dot-size", type=float, help="Dot size")
dot_parser.add_argument("--dot-spacing", type=float, help="Dot spacing")
dot_parser.add_argument("--prevent-overlaps", action="store_true", help="Prevent overlaps")
dot_parser.add_argument("--split-paths", action="store_true", help="Split paths at intersections")
stroke_parser = subparsers.add_parser("stroke")
stroke_parser.add_argument("input", help="Input font file")
stroke_parser.add_argument("--output", "-o", help="Output font file")

args = parser.parse_args()
if not args.command:
    parser.print_help()
    exit(1)
font = GSFont(args.input)
output = args.output or args.input.replace(".glyphs", "-"+args.command+".glyphs")

if args.command == "dot":
    params = {}
    if args.dot_size:
        params["dotSize"] = args.dot_size
    if args.dot_spacing:
        params["dotSpacing"] = args.dot_spacing
    if args.prevent_overlaps:
        params["preventOverlaps"] = True
    if args.split_paths:
        params["splitPaths"] = True
    dot_font(font, params)
print("Saving to", output)
font.save(output)
