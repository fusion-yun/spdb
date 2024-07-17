""" Theme manager of graph display
    - (salmon 20190726): implement Theme
"""

import collections.abc
import collections
import inspect

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_
from spdm.core.htree import HTreeNode, Dict
from spdm.core.template import Template
from spdm.core.sp_object import SpObject

SpGraphLightTheme = Dict(
    {
        "theme": {
            "color": {
                "main": "white",
                "second": "lightgray",
                "third": "gray",
                "active": "darkgreen",
                "ready": "darkgreen",
                "valid": "${theme.color.main}",
                "error": "red",
                "warning": "yellow",
                "success": "darkgreen",
                "break": "${theme.color.error}",
                "pass": "${theme.color.success}",
                "true": "darkgreen",
                "false": "red",
                "none": "lightgray",
            },
            "style": {
                "shape": "rounded",
                "main": "solid",
                "invalid": "dashed",
                "active": "dashed",
                "ready": "dashed",
                "executed": "bold",
                "valid": "solid",
                "released": "solid",
                "error": "dashed",
            },
            "global": {
                "edge": {"color": "${theme.color.main}", "fontcolor": "${theme.color.main}", "arrowhead": "odot"},
                "node": {
                    "style": "rounded",
                    "shape": "square",
                    "fontname": "NotoSansCJK-Regular",
                    "color": "${theme.color.main}",
                    "fontcolor": "${theme.color.main}",
                },
                "graph": {
                    "style": "rounded",
                    "compound": "true",
                    "fontname": "NotoSansCJK-Regular",
                    "color": "${theme.color.main}",
                    "fontcolor": "${theme.color.main}",
                    "bgcolor": "transparent",
                    "rankdir": "LR",
                },
            },
        }
    }
)  # SpGraphLightTheme = {

SpGraphDarkTheme = SpGraphLightTheme.update(
    {"theme": {"color": {"main": "black", "second": "gray", "third": "lightgray"}}}
)
DefaultTheme = SpGraphDarkTheme


class Render(SpObject):

    _plugin_prefix = "spdm.view.render_"
    _plugin_singletons = {}
    _plugin_registry = {}

    def __init__(self, *args, envs=None, theme=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._theme = Template(
            [theme, DefaultTheme], _parent=self, convert={int: str, float: str, bool: str}, default_value=""
        )

        self._theme.setdefault("$id", self.__class__.__qualname__)
        self._envs = envs

    @property
    def envs(self):
        return self._envs

    def attribute(self, k, obj, *args, **kwargs):
        return str(obj.get(obj, k))

    def cache(self, k, obj, *args, **kwargs):
        k = k.split(",", 1)
        if len(k) > 1:
            default_value = k[1]
        else:
            default_value = ""
        return str(self.get([obj.id, *k[0].split(".")], default_value))

    def get_style(self, p, *args, **kwargs):
        return self._theme.apply(self._theme.get(p, *args, **kwargs))

    def node_style(self, nobj: HTreeNode):
        state = self.get([nobj.id, "state"], _not_found_)
        suffix = [None] + [s.name for s in SpState if s in state]
        shape = self.shape_by_class(nobj.__class__, None, suffix, nobj)
        return self._theme.apply(shape, nobj)

    def port_style(self, pobj: HTreeNode):
        prefix = [c.__name__ for c in pobj._parent.__class__.__mro__] + [None]
        prefix.reverse()
        shape = self.shape_by_class(pobj.__class__, prefix, None, pobj)
        return self._theme.apply(shape, pobj)

    def edge_style(self, eobj: HTreeNode):
        state = self.get([eobj.source._parent.id, "state"], _not_found_)
        suffix = [None] + [s.name for s in SpState if s in state][1:]
        shape = self.shape_by_class(eobj.__class__, None, suffix, eobj)
        return self._theme.apply(shape, eobj)

    def graph_style(self, gobj: HTreeNode):
        state = self.get([gobj.id, "state"], _not_found_)
        suffix = [None] + [s.name for s in SpState if s in state]
        shape = self.shape_by_class(gobj.__class__, None, suffix, gobj)
        return self._theme.apply(shape, gobj)

    def shape_by_class(self, n_cls, prefix=None, suffix=None, *args, **kwargs):
        if isinstance(n_cls, str):
            n_list = [n_cls]
        elif inspect.isclass(n_cls):
            bases = list(n_cls.__mro__)
            bases.reverse()
            n_list = [c.__name__ for c in bases[1:]]

        if not isinstance(prefix, list):
            prefix = [prefix]

        if not isinstance(suffix, list):
            suffix = [suffix]

        res = Dict()

        for n in n_list:
            for p in prefix:
                for s in suffix:
                    if p is not None:
                        n_name_list = [p]
                    else:
                        n_name_list = []
                    n_name_list.append(n)
                    if s is not None:
                        n_name_list.append(s)

                    n_name = ".".join(n_name_list)

                    patch = self._theme.get(["shapes", n_name], None)

                    patch = self._theme.apply(patch, *args, _base=res, **kwargs)

                    if isinstance(patch, collections.abc.Mapping):
                        res.update(patch)
                    elif patch is not None:
                        logger.error(f"illegal shape: {patch}")

        return res

    def apply(self, g, *args, **kwargs):
        return NotImplemented
