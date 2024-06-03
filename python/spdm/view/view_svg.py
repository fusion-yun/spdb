import collections.abc
import typing
import uuid

import numpy as np
from spdm.core.HTree import HTree
from spdm.geometry.BBox import BBox
from spdm.geometry.Circle import Circle
from spdm.geometry.Curve import Curve
from spdm.geometry.GeoObject import GeoObject
from spdm.geometry.Line import Line
from spdm.geometry.Point import Point
from spdm.geometry.PointSet import PointSet
from spdm.utils.logger import logger

from spdm.view.View import View

SVG_TEMPLATE = """<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns:xlink="http://www.w3.org/1999/xlink" width="{p_width}pt" height="{p_height}pt" viewBox="{xmin:.2f} {ymin:.2f} {width:.2f} {height:.2f}"  xmlns="http://www.w3.org/2000/svg" version="1.1">
<style>
    .sp_geo_object {{
        stroke: {color}; 
        stroke-linejoin: miter; 
        stroke-width:{line_width};
    }}
</style>
    <g id="{name}">
    {contents}
    </g>
</svg>"""


@View.register(["svg", "SVG"])
class SVGView(View):

    TEMPLATE = SVG_TEMPLATE

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def draw(self, obj, **kwargs) -> typing.Any:

        bbox = []
        contents = []

        logger.debug(obj)

        if isinstance(obj, tuple):
            obj, opts = obj
        else:
            opts = {}

        if hasattr(obj.__class__, "__view__"):
            geo, *_ = obj.__view__(view=self.viewpoint)
            contents.append(geo)
            bbox.append(geo.bbox)
        elif hasattr(obj, "bbox"):
            contents.append(obj.bbox.__repr_svg__(**opts))
            bbox.append(obj.bbox)
        else:
            logger.error(f"Can not plot {obj}")

        if bbox is None or len(bbox) == 0:
            raise RuntimeError(f"SVGView.show() requires a bbox attribute ")

        bbox = np.bitwise_or.reduce(bbox)

        (xmin, ymin), (xmax, ymax) = bbox
        width = xmax-xmin
        height = ymax-ymin
        p_width = 300
        p_height = int(p_width*height/width+10)
        contents = "\n\t".join(contents)

        padd_x = (width/50)
        padd_y = (height/50)

        line_width = min(width/100, height/100)

        return self.TEMPLATE.format(
            p_width=p_width,
            p_height=p_height,
            xmin=xmin-padd_x,
            ymin=ymin-padd_y,
            width=width+2*padd_x,
            height=height+2*padd_y,
            contents=contents,
            signature=self.signature,
            name=kwargs.pop("name", f"spdm_"),
            title=kwargs.pop("title", ""),
            xlabel=kwargs.pop("xlabel", ""),
            ylabel=kwargs.pop("ylabel", ""),
            line_width=line_width,
            color="black",)

    def _draw_geo(self, cancas, obj: GeoObject | HTree | BBox, styles=None, **kwargs) -> str:

        name = kwargs.pop('name', obj.name)

        if getattr(obj, "ndim", 0) != 2:
            raise NotImplementedError(f"{self.__class__.__name__}.draw ndim={obj.ndim}")

        elif isinstance(obj, BBox):
            xmin = obj._xmin
            xmax = obj._xmax

            if np.allclose(obj._xmin, obj._xmax):
                svg = f'<line  x1="{xmin[0]}" y1="{xmin[1]}" x2="{xmin[0]}" y2="{xmin[1]}" class="sp_geo_object" />'
            else:
                svg = f'<rect x="{xmin[0]}" y="{xmin[1]}" width="{xmax[0]-xmin[0]}" height="{xmax[1]-xmin[1]}" class="sp_geo_object_bbox" />'

        elif not isinstance(obj, GeoObject):
            svg = f"<text x='0' y='0' fill='red'>{obj}</text>"

        elif isinstance(obj, Point):
            svg = f'<point cx="{obj.x}" cy="{obj.y}" r="0.01" class="sp_geo_object" />'

        elif isinstance(obj, PointSet):
            fill_or_not = "fill='none'" if obj.rank == 1 else ""

            return f'<polyline class="sp_geo_object" points="{" ".join([f"{x},{y}" for x, y in obj._points])}" {fill_or_not} />'

        elif isinstance(obj, Curve):

            pts = "M "
            pts += '\nL'.join([f' {x} {y}' for x, y in obj._points])
            if obj.is_closed:
                pts += " Z"
            svg = f'<path class="sp_geo_object" d="{pts}" fill="none" />'

        elif isinstance(obj, Line):
            x0, y0 = obj.p0
            x1, y1 = obj.p1
            svg = f'<line  x1="{xmin[0]}" y1="{xmin[1]}" x2="{xmin[0]}" y2="{xmin[1]}" class="sp_geo_object" />'
        elif isinstance(obj, Circle):
            svg = f'<circle cx="{obj.x}" cy="{obj.y}" r="{obj.r}" class="sp_geo_object" />'

        elif isinstance(obj, GeoObject):
            svg = self.draw(obj.bbox, name=f"< {obj.__class__.__name__} {name}/>", **kwargs)

        else:
            raise NotImplementedError(f"Draw {obj.__class__.__name__}")
        return svg


__SP_EXPORT__ = SVGView
