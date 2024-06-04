import collections.abc
import typing
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np

from ..core.path import update_tree, merge_tree
from ..core.expression import Expression
from ..core.signal import Signal
from ..core.field import Field
from ..core.function import Function

from ..geometry.circle import Circle
from ..geometry.curve import Curve
from ..core.geo_object import GeoObject, BBox
from ..geometry.line import Line
from ..geometry.point import Point
from ..geometry.point_set import PointSet
from ..geometry.polygon import Polygon, Rectangle
from ..geometry.polyline import Polyline

from ..utils.envs import SP_DEBUG
from ..utils.logger import SP_DEBUG, logger
from ..utils.tags import _not_found_
from ..utils.typing import array_type, as_array, is_array, is_scalar

from .sp_view import SpView


@SpView.register(["matplotlib"])
class MatplotlibView(SpView):
    backend = "matplotlib"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _figure_post(
        self,
        fig: plt.Figure,
        title="",
        output=None,
        styles={},
        transparent=True,
        signature=None,
        width=1.0,
        height=1.0,
        **kwargs,
    ) -> typing.Any:
        fontsize = styles.get("fontsize", 16)

        fig.suptitle(title, fontsize=fontsize)

        fig.align_ylabels()

        fig.tight_layout()

        if signature is None:
            signature = self.signature

        if signature is not False:
            W, H = fig.get_size_inches()
            if H > 4:
                fig.text(
                    width,
                    0.0,  # 5 * height,
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
                    0.0,
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
            logger.debug(f"Write figure to  {output}")
            kwargs.setdefault("format", "svg")
            fig.savefig(output, transparent=transparent, **kwargs)
            plt.close(fig)
            fig = None

        return fig

    def draw(self, geo, *styles, view_point="rz", title=None, scaled=False, **kwargs) -> typing.Any:
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

        if obj is None or obj is _not_found_:
            pass

        elif hasattr(obj.__class__, "__view__"):
            try:
                obj = obj.__view__(view_point=view_point, **kwargs)
            except Exception as error:
                if SP_DEBUG == "strict":
                    raise RuntimeError(f"ignore unsupported view {obj.__class__.__name__} {obj}! ") from error
                else:
                    logger.exception(f"ignore unsupported view {obj.__class__.__name__} {obj}! ")

            else:
                self._draw(canvas, obj, *styles, view_point=view_point, **kwargs)

        elif isinstance(obj, list):
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
            canvas.add_patch(plt.Polygon(obj._points, fill=False, **s_styles))

        elif isinstance(obj, Polyline):
            canvas.add_patch(plt.Polygon(obj._points, fill=False, closed=obj.is_closed, **s_styles))

        elif isinstance(obj, Line):
            canvas.add_artist(plt.Line2D([obj.p0.x, obj.p1.x], [obj.p0.y, obj.p1.y], **s_styles))

        elif isinstance(obj, Curve):
            canvas.add_patch(plt.Polygon(obj._points, fill=False, closed=obj.is_closed, **s_styles))

        elif isinstance(obj, Rectangle):
            canvas.add_patch(plt.Rectangle((obj._x, obj._y), obj._width, obj._height, fill=False, **s_styles))

        elif isinstance(obj, Circle):
            canvas.add_patch(plt.Circle((obj.x, obj.y), obj.r, fill=False, **s_styles))

        elif isinstance(obj, Point):
            canvas.scatter(obj.x, obj.y, **s_styles)

        elif isinstance(obj, PointSet):
            canvas.scatter(*obj.points, **s_styles)

        elif isinstance(obj, GeoObject):
            self._draw(canvas, obj.bbox, *styles)

        elif isinstance(obj, BBox):
            canvas.add_patch(plt.Rectangle(obj.origin, *obj.dimensions, fill=False, **s_styles))

        else:
            raise RuntimeError(f"Unsupport type {(obj)} {obj}")

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

            self._draw(canvas, text, {f"${self.backend}": text_styles})

        return obj

    def plot(
        self,
        *args,
        x_axis: Expression | np.ndarray | str = None,
        x_label=None,
        styles=_not_found_,
        width=10,
        height=8,
        **kwargs,
    ) -> typing.Any:
        styles = update_tree({}, styles, kwargs)

        fontsize = styles.get("fontsize", 16)

        if len(args) > 1 and isinstance(args[0], array_type):
            x_value = args[0]
            args = args[1:]
        else:
            x_value = None

        nprofiles = len(args)

        height = max(2, height / nprofiles) * nprofiles

        fig, canvas = plt.subplots(ncols=1, nrows=nprofiles, sharex=True, figsize=(width, height))

        if nprofiles == 1:
            canvas = [canvas]

        if isinstance(x_axis, Expression):
            if x_label is None:
                units = x_axis._metadata.get("units", "-")
                x_label = f"{ x_value.__label__} [{units}]"
            if isinstance(x_value, array_type):
                x_axis = x_axis(x_value)
            elif x_value is None:
                x_value = as_array(x_axis)
                x_axis = None
        elif isinstance(x_axis, str):
            x_label = x_axis
            x_axis = None
        elif isinstance(x_axis, array_type):
            if x_value is None:
                x_value = x_axis
            elif x_value.size != x_value.size:
                raise RuntimeError(f"size mismatch {x_value.size} != {x_axis.size}")

        for idx, profiles in enumerate(args):
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
                    t_label, t_y_label = self._plot(canvas[idx], x_value, p, x_axis=x_axis, styles=p_styles)

                    labels.append(t_label)
                    if y_label is None:
                        y_label = t_y_label

                except Exception as error:
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

    def _plot(self, canvas, x_value, expr, x_axis=None, styles=None, **kwargs) -> str:
        if expr is None or expr is _not_found_:
            return None, None

        styles = update_tree(kwargs, styles)

        s_styles = styles.get(f"${self.backend}", {})

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

        if x_axis is None:
            x_axis = x_value

        if label is False:
            label = None
        elif not isinstance(label, str) or ("$" not in label and any(c in label for c in r"\{")):
            label = f"${label}$"

        canvas.plot(x_axis, y_value, **s_styles, label=label)

        units = getattr(expr, "_metadata", {}).get("units", "-")

        units = units.replace("^-1", "^{-1}").replace("^-2", "^{-2}").replace("^-3", "^{-3}").replace(".", " \cdot ")

        return label, f"[{units}]"

    # def profiles_(self, obj, *args,  x_axis=None, x=None,
    #               default_num_of_points=128, fontsize=10, grid=True,
    #               signature=None, title=None, **kwargs):
    #     fontsize = kwargs.get("fontsize", 10)
    #     nprofiles = len(obj)
    #     fig, canves = plt.subplots(
    #         ncols=1, nrows=nprofiles, sharex=True, figsize=(10, 2 * nprofiles)
    #     )
    #     self.draw(canves, obj, styles)
    #     x_label = kwargs.get("xlabel", "")
    #     if len(canves) == 1:
    #         canves[0].set_xlabel(x_label, fontsize=fontsize)
    #     else:
    #         canves[-1].set_xlabel(x_label, fontsize=fontsize)
    #     if not isinstance(profile_list, collections.abc.Sequence):
    #         profile_list = [profile_list]
    #     if isinstance(x_axis, collections.abc.Sequence) and not isinstance(
    #         x_axis, np.ndarray
    #     ):
    #         x_axis, x_label, *x_opts = x_axis
    #         x_opts = (x_opts or [{}])[0]
    #     else:
    #         x_axis = [0, 1]
    #         x_label = ""
    #         x_opts = {}
    #     if isinstance(x_axis, Function) and x is not None:
    #         x_axis = x_axis(x)
    #     elif x is None and isinstance(x_axis, np.ndarray):
    #         x = x_axis

    #     if isinstance(x_axis, np.ndarray):
    #         x_min = x_axis[0]
    #         x_max = x_axis[-1]
    #     elif isinstance(x_axis, collections.abc.Sequence) and len(x_axis) == 2:
    #         x_min, x_max = x_axis
    #         x_axis = np.linspace(x_min, x_max, default_num_of_points)
    #     else:
    #         raise TypeError(x_axis)

    #     if x is None and isinstance(x_axis, np.ndarray):
    #         x = x_axis
    #     elif callable(x_axis) or isinstance(x_axis, Function):
    #         x_axis = x_axis(x)

    #     nprofiles = len(profile_list)

    #     fig, sub_plot = plt.subplots(
    #         ncols=1, nrows=nprofiles, sharex=True, figsize=(10, 2 * nprofiles)
    #     )

    #     if not isinstance(sub_plot, (collections.abc.Sequence, np.ndarray)):
    #         sub_plot = [sub_plot]

    #     for idx, profile_grp in enumerate(profile_list):
    #         if not isinstance(profile_grp, list):
    #             profile_grp = [profile_grp]
    #         ylabel = None
    #         for jdx, p_desc in enumerate(profile_grp):
    #             profile, label, *o_args = p_desc
    #             opts = {}
    #             if len(o_args) > 0 and ylabel is None:
    #                 ylabel = o_args[0]
    #             if len(o_args) > 1:
    #                 opts = o_args[1]

    #             y = None

    #             if isinstance(profile, Function) or callable(profile):
    #                 try:
    #                     y = profile(x)
    #                 except Exception as error:
    #                     raise RuntimeError(
    #                         f"Can not get profile [idx={idx} jdx={jdx}]! name={getattr(profile,'_name',profile)}\n {error} "
    #                     ) from error

    #             elif isinstance(profile, np.ndarray) and len(profile) == len(x):
    #                 y = profile
    #             elif np.isscalar(profile):
    #                 y = np.full_like(x, profile, dtype=float)
    #             else:
    #                 raise RuntimeError(f"Illegal profile! {profile}!={x}")

    #             if not isinstance(y, np.ndarray) or not isinstance(x, np.ndarray):
    #                 logger.warning(f"Illegal profile! {(type(x) ,type(y), label, o_args)}")
    #                 continue
    #             elif x.shape != y.shape:
    #                 logger.warning(f"Illegal profile! {x.shape} !={y.shape}")
    #                 continue
    #             else:
    #                 # 删除 y 中的 nan
    #                 mark = np.isnan(y)
    #                 # if np.any(mark):
    #                 #     logger.warning(f"Found NaN in array  {np.argwhere(mark)}! {profile}  ")
    #                 sub_plot[idx].plot(x_axis[~mark], y[~mark], label=label, **opts)

    #         sub_plot[idx].legend(fontsize=fontsize)

    #         if grid:
    #             sub_plot[idx].grid()

    #         if ylabel is not None:
    #             sub_plot[idx].set_ylabel(ylabel, fontsize=fontsize)
    #         sub_plot[idx].labelsize = "media"
    #         sub_plot[idx].tick_params(labelsize=fontsize)

    #     if len(sub_plot) <= 1:
    #         sub_plot[0].set_xlabel(x_label, fontsize=fontsize)

    #     else:
    #         sub_plot[-1].set_xlabel(x_label, fontsize=fontsize)

    #     return fig

    # def draw_profile(self, profiles, x_axis, canves: plt.Axes = ..., style=None, **kwargs):
    #     if style is None:
    #         style = {}

    #     fontsize = style.get("fontsize", 10)

    #     ylabel = None

    #     x_value = x_axis

    #     if not isinstance(profiles, collections.abc.Sequence):
    #         profiles = [profiles]

    #     for profile, label, legend, *opts in profiles:
    #         y = None

    #         if isinstance(profile, Function) or callable(profile):
    #             try:
    #                 y = profile(x_value)
    #             except Exception as error:
    #                 raise RuntimeError(
    #                     f"Can not get profile! name={getattr(profile,'name',profile)}\n {error} "
    #                 ) from error

    #         elif isinstance(profile, array_type) and len(profile) == len(x_value):
    #             y = profile
    #         elif np.isscalar(profile):
    #             y = np.full_like(x_value, profile, dtype=float)
    #         else:
    #             raise RuntimeError(f"Illegal profile! {profile}!={x_value}")

    #         if not isinstance(y, array_type) or not isinstance(x_value, array_type):
    #             logger.warning(
    #                 f"Illegal profile! {(type(x_value) ,type(y), label, opts)}"
    #             )
    #             continue
    #         elif x.shape != y.shape:
    #             logger.warning(f"Illegal profile! {x_value.shape} !={y.shape}")
    #             continue
    #         else:
    #             # 删除 y 中的 nan
    #             mark = np.isnan(y)
    #             # if np.any(mark):
    #             #     logger.warning(f"Found NaN in array  {np.argwhere(mark)}! {profile}  ")
    #             canves.plot(x_axis[~mark], y[~mark], label=label, **opts)

    #     canves.legend(fontsize=fontsize)

    #     if kwargs.get("grid", True):
    #         canves.grid()

    #     if ylabel is not None:
    #         canves.set_ylabel(ylabel, fontsize=fontsize)
    #     canves.labelsize = "media"
    #     canves.tick_params(labelsize=fontsize)


# def sp_figure_signature(fig: plt.Figure, signature=None, x=1.0, y=0.1):
#     if signature is False:
#         return fig
#     elif not isinstance(signature, str):
#         signature = f"author: {getpass.getuser().capitalize()}. Create by SpDM at {datetime.datetime.now().isoformat()}."

#     pos = fig.gca().get_position()

#     fig.text(pos.xmax+0.01, 0.5*(pos.ymin+pos.ymax), signature,
#              verticalalignment='center', horizontalalignment='left',
#              fontsize='small', alpha=0.2, rotation='vertical')

#     # fig.text(x, y, signature, va='bottom', ha='left', fontsize='small', alpha=0.5, rotation='vertical')
#     return fig

# def plot(self, axis=None, *args, **kwargs):

#         if axis is None:
#             axis = plt.gca()

#         desc2d = self.description_2d[0]

#         # outline = desc2d.vessel.unit[0].annular.outline_inner

#         vessel_inner_points = np.array([desc2d.vessel.unit[0].annular.outline_inner.r,
#                                         desc2d.vessel.unit[0].annular.outline_inner.z]).transpose([1, 0])

#         vessel_outer_points = np.array([desc2d.vessel.unit[0].annular.outline_outer.r,
#                                         desc2d.vessel.unit[0].annular.outline_outer.z]).transpose([1, 0])

#         limiter_points = np.array([desc2d.limiter.unit[0].outline.r,
#                                    desc2d.limiter.unit[0].outline.z]).transpose([1, 0])

#         axis.add_patch(plt.Polygon(limiter_points, **
#                                    merge_tree(kwargs.get("limiter", {}), {"fill": False, "closed": True})))

#         axis.add_patch(plt.Polygon(vessel_outer_points, **merge_tree(kwargs.get("vessel_outer", {}),
#                                                                                kwargs.get("vessel", {}),
#                                                                                {"fill": False, "closed": True})))

#         axis.add_patch(plt.Polygon(vessel_inner_points, **merge_tree(kwargs.get("vessel_inner", {}),
#                                                                                kwargs.get("vessel", {}),
#                                                                                {"fill": False, "closed": True})))

#         return axis
#    def plot(self, axis=None, *args, with_circuit=False, **kwargs):

#         if axis is None:
#             axis = plt.gca()

#         for coil in self.coil:
#             rect = coil.element[0].geometry.rectangle

#             axis.add_patch(plt.Rectangle((rect.r - rect.width / 2.0,  rect.z - rect.height / 2.0),
#                                          rect.width,  rect.height,
#                                          **merge_tree(kwargs,  {"fill": False})))
#             axis.text(rect.r, rect.z, coil.name,
#                       horizontalalignment='center',
#                       verticalalignment='center',
#                       fontsize='xx-small')

#         return axis

# def plot(self, axis=None, *args, with_circuit=False, **kwargs):

#     if axis is None:
#         axis = plt.gca()
#     for idx, p_probe in enumerate(self.b_field_tor_probe):
#         pos = p_probe.position

#         axis.add_patch(plt.Circle((pos.r, pos.z), 0.01))
#         axis.text(pos.r, pos.z, idx,
#                   horizontalalignment='center',
#                   verticalalignment='center',
#                   fontsize='xx-small')

#     for p in self.flux_loop:
#         axis.add_patch(plt.Rectangle((p.position[0].r,  p.position[0].z), 0.01, 0.01))
#         axis.text(p.position[0].r, p.position[0].z, p.name,
#                   horizontalalignment='center',
#                   verticalalignment='center',
#                   fontsize='xx-small')
#     return axis
