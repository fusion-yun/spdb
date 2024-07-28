""" MatplotlibView class definition
"""

import collections.abc
import typing
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np

from spdm.core.path import update_tree, merge_tree
from spdm.core.expression import Expression
from spdm.core.signal import Signal
from spdm.core.htree import List

from spdm.geometry.circle import Circle
from spdm.geometry.curve import Curve
from spdm.core.geo_object import GeoObject, BBox
from spdm.geometry.line import Line
from spdm.geometry.point import Point
from spdm.geometry.point_set import PointSet
from spdm.geometry.polygon import Polygon, Rectangle
from spdm.geometry.polyline import Polyline

from spdm.utils.envs import SP_DEBUG
from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.utils.type_hint import array_type, as_array, is_scalar

from spdm.view.sp_view import SpView


class MatplotlibView(SpView, plugin_name="matplotlib"):
    """MatplotlibView class definition"""

    def _figure_post(
        self,
        fig,
        title="",
        output=None,
        styles=None,
        transparent=True,
        signature=None,
        width=1.0,
        height=1.0,
        **kwargs,
    ) -> typing.Any:
        if styles is None:
            styles = {}
        fontsize = styles.get("fontsize", 16)

        fig.suptitle(title, fontsize=fontsize)

        fig.align_ylabels()

        fig.tight_layout()

        if signature is None:
            signature = self.signature

        if signature is not False:
            _, h = fig.get_size_inches()
            if h > 4:
                fig.text(
                    width,
                    0.05,  # 5 * height,
                    signature,
                    verticalalignment="bottom",
                    horizontalalignment="left",
                    fontsize="small",
                    alpha=0.2,
                    rotation="vertical",
                )
            else:
                fig.text(
                    width,
                    0.05,
                    signature,
                    verticalalignment="bottom",
                    horizontalalignment="right",
                    fontsize="small",
                    alpha=0.2,
                    # rotation="vertical",
                )

        if output == "svg":
            buf = BytesIO()
            fig.savefig(buf, format="svg", transparent=transparent, **kwargs)
            buf.seek(0)
            fig_html = buf.getvalue().decode("utf-8")
            plt.close(fig)
            fig = fig_html

        elif output is not None:
            logger.verbose("Write figure to %s", output)
            kwargs.setdefault("format", "svg")
            fig.savefig(output, transparent=transparent, **kwargs)
            plt.close(fig)
            fig = None

        return fig

    def draw(self, geo, *styles, view_point="rz", title=None, **kwargs) -> typing.Any:
        fig, canvas = plt.subplots()

        geo = self._draw(canvas, geo, *styles, view_point=view_point)

        g_styles = geo.get("$styles", {}) if isinstance(geo, dict) else {}
        g_styles = merge_tree(g_styles, *styles)

        xlabel = g_styles.get("xlabel", None)

        if xlabel is not None:
            canvas.set_xlabel(xlabel)
        elif view_point.lower() == "rz":
            canvas.set_xlabel(r" $R$ [m]")
        else:
            canvas.set_xlabel(r" $X$ [m]")

        ylabel = g_styles.get("ylabel", None)
        if ylabel is not None:
            canvas.set_ylabel(ylabel)
        elif view_point.lower() == "rz":
            canvas.set_ylabel(r" $Z$ [m]")
        else:
            canvas.set_ylabel(r" $Y$ [m]")

        pos = canvas.get_position()

        canvas.set_aspect("equal")

        canvas.axis("scaled")

        new_pos = canvas.get_position()

        width = 1.0 + (new_pos.xmax - pos.xmax)
        height = 1.0 + (new_pos.ymax - pos.ymax)

        title = title or g_styles.get("title", None)

        return self._figure_post(fig, title=title, styles=g_styles, width=width, height=height, **kwargs)

    def _draw(
        self,
        canvas,
        obj: GeoObject | str | BBox | dict | list,
        *styles,
        view_point=None,
        **kwargs,
    ):
        if False in styles:
            return
        g_styles = getattr(obj, "_metadata", {}).get("styles", {})
        g_styles = update_tree(g_styles, *styles)
        s_styles = g_styles.get("$matplotlib", {})

        if hasattr(obj.__class__, "__view__"):
            try:
                obj = obj.__view__(view_point=view_point, **kwargs)
            except RuntimeError as error:
                if SP_DEBUG == "strict":
                    raise RuntimeError(f"ignore unsupported view {obj.__class__.__name__} {obj}! ") from error
                logger.exception(f"ignore unsupported view {obj.__class__.__name__} {obj}! ", exc_info=error)

        if obj is None or obj is _not_found_:
            pass

        elif isinstance(obj, (list, List)):
            for idx, g in enumerate(obj):
                self._draw(canvas, g, {"id": idx}, *styles, view_point=view_point, **kwargs)

            self._draw(canvas, None, *styles, view_point=view_point, **kwargs)

        elif isinstance(obj, dict) and "$type" not in obj:
            s_styles = obj.get("$styles", {})

            for s in [k for k in obj.keys() if not k.startswith("$")]:
                self._draw(canvas, obj[s], {"id": s}, s_styles, *styles, view_point=view_point, **kwargs)
            else:
                self._draw(canvas, obj.get("$data"), s_styles, *styles, view_point=view_point, **kwargs)

            self._draw(canvas, None, s_styles, *styles, **kwargs)

        elif isinstance(obj, dict) and "$type" in obj:
            match view_type := obj.get("$type"):
                case "contour":
                    *x, y = obj.get("$data")

                    if len(x) != 2 or y.ndim != 2:
                        raise RuntimeError(f"Illegal dimension {[d.shape for d in x]} {y.shape} ")

                    canvas.contour(*x, y, **merge_tree(s_styles, {"levels": 20, "linewidths": 0.5}))

                case _:
                    logger.warning(f"ignore unknown view type {view_type}")
        elif isinstance(obj, tuple):
            g, t_styles = obj
            self._draw(canvas, g, t_styles, *styles, view_point=view_point, **kwargs)

        elif isinstance(obj, (str, int, float, bool)):
            pos = g_styles.get("position", None)

            if pos is None:
                return

            canvas.text(
                *pos,
                str(obj),
                **collections.ChainMap(
                    s_styles,
                    {
                        "horizontalalignment": "center",
                        "verticalalignment": "center",
                        "fontsize": "xx-small",
                    },
                ),
            )

        elif isinstance(obj, Polygon):
            canvas.add_patch(plt.Polygon(obj.points, fill=False, **(s_styles | obj.styles.get("$matplotlib", {}))))

        elif isinstance(obj, Polyline):
            canvas.add_patch(
                plt.Polygon(
                    obj.points, fill=False, closed=obj.is_closed, **(s_styles | obj.styles.get("$matplotlib", {}))
                )
            )

        elif isinstance(obj, Line):
            canvas.add_artist(
                plt.Line2D(
                    [obj.p0[0], obj.p1[0]], [obj.p0[1], obj.p1[1]], **(s_styles | obj.styles.get("$matplotlib", {}))
                )
            )

        elif isinstance(obj, Curve):
            canvas.add_patch(
                plt.Polygon(
                    obj.points, fill=False, closed=obj.is_closed, **(s_styles | obj.styles.get("$matplotlib", {}))
                )
            )

        elif isinstance(obj, Rectangle):
            p0 = obj.points[0]
            p1 = obj.points[1]
            w = p1[0] - p0[0]
            h = p1[1] - p0[1]
            canvas.add_patch(
                plt.Rectangle((p0[0], p0[1]), w, h, fill=False, **(s_styles | obj.styles.get("$matplotlib", {})))
            )

        elif isinstance(obj, Circle):
            canvas.add_patch(
                plt.Circle(
                    (obj.origin[0], obj.origin[1]),
                    obj.radius,
                    fill=False,
                    **(s_styles | obj.styles.get("$matplotlib", {})),
                )
            )

        elif isinstance(obj, Point):
            canvas.scatter(obj[0], obj[1], **(s_styles | obj.styles.get("$matplotlib", {})))

        elif isinstance(obj, PointSet):
            canvas.scatter(*obj.points, **(s_styles | obj.styles.get("$matplotlib", {})))

        elif isinstance(obj, GeoObject):
            self._draw(canvas, obj.bbox, *styles)

        elif isinstance(obj, BBox):
            canvas.add_patch(
                plt.Rectangle(
                    obj.origin, *obj.dimensions, fill=False, **(s_styles | obj.styles.get("$matplotlib", {}))
                )
            )

        else:
            # raise RuntimeError(f"Unsupport type {(obj)} {obj}")
            logger.warning(f"ignore unsupported view {obj.__class__.__name__}! ")

        text_styles = g_styles.get("text", False)

        if text_styles:
            if not isinstance(text_styles, dict):
                text_styles = {}

            if isinstance(obj, Line):
                text = obj.name
                pos = [obj.p1.x, obj.p1.y]
            elif isinstance(obj, GeoObject):
                text = obj.name
                pos = obj.bbox.center
            elif hasattr(obj, "mesh"):
                text = obj.name
                pos = obj.mesh.bbox.center
            else:
                text = str(obj)
                pos = None

            text_styles.setdefault("position", pos)

            self._draw(canvas, text, {"$matplotlib": text_styles})

        return obj

    def plot(
        self,
        *args,
        x_axis: np.ndarray = None,
        x_label: str = None,
        styles=_not_found_,
        width=10,
        height=8,
        **kwargs,
    ) -> typing.Any:
        if len(args) == 1:
            if isinstance(args[0], (list, tuple)):
                profiles = args[0]
                x_value = None
            else:
                profiles = [args[0]]
                x_value = None

        elif len(args) > 1:
            x_value = args[0]
            profiles = args[1:]
        else:
            x_value = None
            profiles = []

        styles = update_tree({}, styles, kwargs)

        fontsize = styles.get("fontsize", 16)

        # if len(args) > 1:
        #     x_value = args[0]
        #     args = args[1:]
        # else:
        #     x_value = None

        if isinstance(x_value, tuple):
            x_value, x_label = x_value

        if isinstance(x_value, Expression):
            if x_label is None:
                units = x_value._kwargs.get("units", "-")
                x_label = f"{ x_value.__label__} [{units}]"
            if isinstance(x_axis, array_type):
                x_value = x_value(x_axis)
            else:
                x_value = as_array(x_value)
                x_axis = None

        nprofiles = len(profiles)

        if nprofiles > 0:
            height = max(2, height / nprofiles) * nprofiles

        fig, canvas = plt.subplots(ncols=1, nrows=nprofiles, sharex=True, figsize=(width, height))

        if nprofiles == 1:
            canvas = [canvas]

        for idx, profiles in enumerate(profiles):
            if isinstance(profiles, tuple):
                profiles, sub_styles = profiles
            else:
                sub_styles = {}

            if sub_styles is False:
                continue
            elif isinstance(sub_styles, str):
                sub_styles = {"label": sub_styles}

            elif not isinstance(sub_styles, dict):
                raise RuntimeError(f"Unsupport sub_styles {sub_styles}")

            sub_styles = collections.ChainMap(sub_styles, styles)

            y_label = sub_styles.get("y_label", None)

            if not isinstance(profiles, (list)):
                profiles = [profiles]

            labels = []
            for p in profiles:
                if isinstance(p, tuple) and isinstance(p[1], (str, dict)):
                    p, p_styles = p
                else:
                    p_styles = {}

                if isinstance(p_styles, str) or p_styles is None:
                    p_styles = {"label": p_styles}

                p_styles = collections.ChainMap(p_styles, sub_styles)

                try:
                    t_label, t_y_label = self._plot(canvas[idx], x_value, p, styles=p_styles)

                    labels.append(t_label)
                    if y_label is None:
                        y_label = t_y_label

                except RuntimeError as error:
                    if SP_DEBUG == "strict":
                        raise RuntimeError(f'Plot [index={idx}] failed! y_label= "{y_label}"  ') from error
                    else:
                        raise RuntimeError(f'Plot [index={idx}] failed! y_label= "{y_label}" ') from error

            if (vline := sub_styles.get("vline", _not_found_)) is not _not_found_:
                canvas[idx].axvline(**vline)

            if (hline := sub_styles.get("hline", _not_found_)) is not _not_found_:
                canvas[idx].axhline(**hline)

            if any(labels):
                canvas[idx].legend(fontsize=fontsize)
            if "$" not in y_label:
                y_label = f"${y_label}$"
            canvas[idx].set_ylabel(ylabel=y_label, fontsize=fontsize)

        if isinstance(x_label, str):
            if "$" not in x_label and "\\" in x_label:
                x_label = f"${x_label}$"

            canvas[-1].set_xlabel(x_label, fontsize=fontsize)

        return self._figure_post(fig, styles=styles, **kwargs)

    def _plot(self, canvas, x_value, expr, styles=None, **kwargs) -> str:
        if expr is None or expr is _not_found_:
            return None, None

        styles = update_tree(kwargs, styles)

        s_styles = styles.get("matplotlib", {})

        label = styles.get("label", None)

        y_value = None

        if isinstance(expr, Expression):
            if label is None:
                label = expr.__label__
            y_value = expr(x_value)

        elif isinstance(expr, Signal):
            if x_value is None:
                y_value = expr.data
                x_value = expr.time
            else:
                y_value = expr(x_value)

            if label is None:
                label = expr.name

        elif isinstance(expr, array_type):
            y_value = expr

        elif hasattr(expr.__class__, "__array__"):
            y_value = expr.__array__()

        elif isinstance(expr, tuple) and len(expr) == 2 and all([isinstance(v, array_type) for v in expr]):
            x_value, y_value = expr

        else:
            y_value = expr

        if is_scalar(y_value):
            y_value = np.full_like(x_value, y_value, dtype=float)

        elif x_value is None:
            x_value = np.arange(len(expr))

        elif not isinstance(x_value, array_type):
            raise RuntimeError(f"ignore unsupported profiles label={label} {(y_value)}")

        if label is False:
            label = None
        elif not isinstance(label, str) or ("$" not in label and any(c in label for c in r"\{")):
            label = f"${label}$"

        canvas.plot(x_value, y_value, **s_styles, label=label)

        units = getattr(expr, "_metadata", {}).get("units", "-")

        units = units.replace("^-1", "^{-1}").replace("^-2", "^{-2}").replace("^-3", "^{-3}").replace(".", r" \cdot ")

        return label, f"[{units}]"
