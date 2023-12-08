from .ufostroker import constant_width_stroke as cws_rust
# from ufo2ft.filters import BaseFilter
# from beziers.cubicbezier import CubicBezier
# from beziers.point import Point


# def constant_width_stroke(
#     glyph,
#     width,
#     startcap="round",
#     endcap="round",
#     jointype="bevel",
#     height=None,
#     angle=0,
#     remove_internal=False,
#     remove_external=False,
#     segmentwise=False,
# ):
#     """Applies a constant-width stroke effect to a glyph, in place.

#     Parameters:
#         glyph: A ufoLib2 or defcon glyph object
#         width: The stroke width, in points.
#         startcap: Cap to add at the start of the stroke (One of: "round", "square", "circle")
#         endcap: Cap to add at the end of the stroke (One of: "round", "square", "circle")
#         jointype: Joining type (One of: "round", "bevel", "mitre", "circle")
#         remove_internal: Remove the internal path when stroking closed curves
#         remove_external: Remove the external path when stroking closed curves
#         segmentwise: Whether to apply a noodle to each segment, or to the whole curve

#     Returns nothing, but modifies the glyph.
#     """

#     if startcap not in ["round", "square", "circle"]:
#         raise ValueError("Unknown start cap type")
#     if endcap not in ["round", "square", "circle"]:
#         raise ValueError("Unknown end cap type")
#     if jointype not in ["round", "bevel", "mitre", "circle"]:
#         raise ValueError("Unknown join type")
#     list_of_list_of_points = [list(c) for c in list(glyph)]
#     if height is None:
#         height = width / 2.0
#         width = width / 2.0
#     res = cws_rust(
#         list_of_list_of_points,
#         width,
#         height,
#         angle,
#         startcap,
#         endcap,
#         jointype,
#         remove_internal,
#         remove_external,
#         segmentwise,
#     )
#     contour_class = glyph[0].__class__
#     point_class = glyph[0][0].__class__
#     contours = []
#     glyph.clearContours()
#     for contour in res:
#         points = []
#         for pt in contour:
#             x, y, typ = pt
#             if not typ:
#                 typ = None
#             # Unfortunately defcon and ufoLib2 have different Point constructors...
#             try:
#                 point = point_class(x, y, typ)
#             except Exception:
#                 point = point_class((x, y), typ)
#             points.append(point)
#         contour = contour_class()
#         # And contour constructors...
#         try:
#             contour.extend(points)
#         except Exception:
#             for point in points:
#                 contour.appendPoint(point)
#         glyph.appendContour(contour)


# class StrokeFilter(BaseFilter):

#     _kwargs = {
#         "Width": 10,
#         "StartCap": "round",
#         "EndCap": "round",
#         "JoinType": "bevel",
#         "RemoveInternal": False,
#         "RemoveExternal": False,
#         "Segmentwise": False,
#     }

#     def filter(self, glyph):
#         if not len(glyph):
#             return False

#         constant_width_stroke(
#             glyph,
#             self.options.Width,
#             startcap=self.options.StartCap,
#             endcap=self.options.StartCap,
#             jointype=self.options.JoinType,
#             remove_external=self.options.RemoveExternal,
#             remove_internal=self.options.RemoveInternal,
#             segmentwise=self.options.Segmentwise,
#         )

#         # We have to tunnify it...
#         for contour in glyph:
#             for i in range(0, len(contour)):
#                 i1 = (i + 1) % len(contour)
#                 i2 = (i + 2) % len(contour)
#                 i3 = (i + 3) % len(contour)
#                 if (
#                     contour[i].segmentType
#                     and not contour[i1].segmentType
#                     and not contour[i2].segmentType
#                     and contour[i3].segmentType
#                 ):
#                     cbez = CubicBezier(
#                         Point(contour[i].x, contour[i].y),
#                         Point(contour[i1].x, contour[i1].y),
#                         Point(contour[i2].x, contour[i2].y),
#                         Point(contour[i3].x, contour[i3].y),
#                     )
#                     cbez.balance()
#                     contour[i1].x = cbez[1].x
#                     contour[i1].y = cbez[1].y
#                     contour[i2].x = cbez[2].x
#                     contour[i2].y = cbez[2].y
#                     pass
#         return True
