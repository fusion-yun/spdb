import collections
import collections.abc
import getpass
import datetime
from logging import log
from typing import Type
import matplotlib.pyplot as plt
from numpy.lib.arraysetops import isin
import numpy as np
from spdm.data import Dict
from spdm.data import Function
from spdm.logger import logger
from spdm.util.utilities import try_get


# def signaturebar(fig, text, fontsize=10, pad=5, xpos=20, ypos=7.5,
#                  rect_kw={"facecolor": "grey", "edgecolor": None},
#                  text_kw={"color": "w"}):
#     w, h = fig.get_size_inches()
#     height = ((fontsize+2*pad)/72.)/h
#     rect = plt.Rectangle((0, 0), 1, height, transform=fig.transFigure, clip_on=False, **rect_kw)
#     fig.axes[0].add_patch(rect)
#     fig.text(xpos/72./h, ypos/72./h, text, fontsize=fontsize, **text_kw)
#     fig.subplots_adjust(bottom=fig.subplotpars.bottom+height)


def sp_figure_signature(fig: plt.Figure, signature=None):
    if signature is False:
        return fig
    elif not isinstance(signature, str):
        signature = f"Create by SpDM at {datetime.datetime.now().isoformat()}. [user: '{getpass.getuser().capitalize()}']"

    fig.text(1.0, 0.1, signature, va='bottom', ha='right', fontsize='small', alpha=0.5, rotation='vertical')
    return fig


def parse_profile(desc, holder=None, **kwargs):
    opts = {}
    if desc is None:
        return None, {}
    elif isinstance(desc, str):
        data = desc
        opts = {"label": desc}
    elif isinstance(desc, collections.abc.Mapping):
        data = desc.get("name", None)
        if data is None:
            data = desc.get("data", None)
        opts = desc.get("opts", {})
    elif isinstance(desc, tuple):
        data, opts = desc
    elif isinstance(desc, Dict):
        data = desc.data
        opts = desc.opts
    elif isinstance(desc, np.ndarray):
        data = desc
        opts = {}
    else:
        raise TypeError(f"Illegal profile type! {desc}")

    if isinstance(opts, str):
        opts = {"label": opts}

    if opts is None:
        opts = {}

    opts.setdefault("label", "")

    if isinstance(data, str):
        data = try_get(holder, data, None)
    elif isinstance(data, np.ndarray):
        pass
    elif data == None:
        logger.error(f"Value error { (data)}")
    else:
        logger.error(f"Type error {data}")
    return data, opts


def plot_profiles(profile_list, *args,   x_axis=None, default_num_of_points=128, fontsize=6,  grid=False, signature=None, title=None, **kwargs):
    if not isinstance(profile_list, collections.abc.Sequence):
        profile_list = [profile_list]

    if isinstance(x_axis, collections.abc.Sequence) and not isinstance(x_axis, np.ndarray):
        x_axis, x_label,  *x_opts = x_axis
        x_opts = (x_opts or [{}])[0]
    else:
        x_axis = [0, 1]
        x_label = ""
        x_opts = {}

    if isinstance(x_axis, Function):
        x_axis = np.asarray(x_axis)

    if isinstance(x_axis, np.ndarray):
        x_min = x_axis[0]
        x_max = x_axis[-1]
    elif isinstance(x_axis, collections.abc.Sequence) and len(x_axis) == 2:
        x_min, x_max = x_axis
        x_axis = np.linspace(x_min, x_max, default_num_of_points)
    else:
        raise TypeError(x_axis)

    nprofiles = len(profile_list)

    fig, sub_plot = plt.subplots(ncols=1, nrows=nprofiles, sharex=True, figsize=(10, 2*nprofiles))

    if not isinstance(sub_plot,  (collections.abc.Sequence, np.ndarray)):
        sub_plot = [sub_plot]

    for idx, profile_grp in enumerate(profile_list):

        if not isinstance(profile_grp, list):
            profile_grp = [profile_grp]
        ylabel = None
        for p_desc in profile_grp:
            profile, label, *o_args = p_desc
            opts = {}
            if len(o_args) > 0 and ylabel is None:
                ylabel = o_args[0]
            if len(o_args) > 1:
                opts = o_args[1]

            y = None

            try:
                if isinstance(profile, Function):
                    profile = profile.resample(x_min, x_max)
                    if profile.x_axis is None:
                        x = x_axis
                        y = np.asarray(profile(x_axis))
                    else:
                        x = profile.x_axis
                        y = np.asarray(profile())
                elif isinstance(profile, np.ndarray):
                    if len(profile) != len(x_axis):
                        x = np.linspace(x_min, x_max, len(profile))
                    else:
                        x = x_axis
                    y = profile
                elif isinstance(profile, (int, float)):
                    x = x_axis
                    y = np.full(x.shape, profile)
                elif callable(profile):
                    x = x_axis
                    y = profile(x)
            except Exception as error:
                y = None
                x = x_axis
                logger.exception(error)

            if not isinstance(y, np.ndarray) or not isinstance(x, np.ndarray):
                logger.warning(f"Illegal profile! {(type(y),type(x) ,label, o_args)} ")
                continue
            elif x.shape != y.shape:
                logger.warning(f"Illegal profile! {x.shape} !={y.shape} ")
                continue
            else:
                sub_plot[idx].plot(x, y, label=label, **opts)

        sub_plot[idx].legend(fontsize=fontsize)

        if grid:
            sub_plot[idx].grid()

        if ylabel is not None:
            sub_plot[idx].set_ylabel(ylabel, fontsize=fontsize)
        sub_plot[idx].labelsize = "media"
        sub_plot[idx].tick_params(labelsize=fontsize)

    if len(sub_plot) <= 1:
        sub_plot[0].set_xlabel(x_label,  fontsize=fontsize)
    else:
        sub_plot[-1].set_xlabel(x_label,  fontsize=fontsize)
    if title is not None:
        fig.suptitle(title, fontsize=fontsize)
    fig = sp_figure_signature(fig, signature=signature)
    fig.align_ylabels()
    fig.tight_layout()
    return fig


def sp_figure(obj, *args, signature=None, **kwargs):
    fig = plt.figure()
    if not hasattr(obj, 'plot'):
        raise NotImplementedError(type(obj))
    else:
        obj.plot(fig.gca(), *args, **kwargs)

    fig = sp_figure_signature(fig, signature=signature)
    # fig.tight_layout()
    # fig.gca().axis('scaled')
    fig.align_ylabels()
    fig.tight_layout()
    return fig
