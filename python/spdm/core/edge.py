from __future__ import annotations
import collections
import collections.abc
import typing
import math
from typing_extensions import Self
from copy import deepcopy
from .path import Path, as_path
from .htree import HTreeNode, Dict
from .sp_property import PropertyTree, SpTree
from ..utils.tags import _not_found_, _undefined_


class Port:
    def __init__(self, source: HTreeNode, fragment: Path | str = None, type_hint: typing.Type = None, **kwargs) -> None:
        self._node = source
        self._fragment: Path = as_path(fragment)
        self._type_hint: typing.Type = type_hint
        self._metadata = kwargs

    @property
    def node(self) -> HTreeNode:
        return self._node

    @property
    def type_hint(self) -> typing.Type:
        return self._type_hint

    @property
    def fragment(self) -> Path:
        return self._fragment

    @property
    def metadata(self) -> typing.Dict:
        return self._metadata

    def update(self, node, type_hint=None, **kwargs):
        if node is not None:
            self._node = node
        if type_hint is not None:
            self._type_hint = type_hint
        if len(kwargs) > 0:
            self._metadata.update(kwargs)

    def link(self, target, **kwargs) -> Edge:
        return Edge(self, target, **kwargs)

    def fetch(self, *args, **kwargs):
        node = self.fragment.find(self.node)
        res = HTreeNode._do_fetch(node, *args, **kwargs)
        if res is _not_found_:
            raise RuntimeError(f"Fetch result from  {self.fragment} failed! node={self._node}")
        return res

    @property
    def is_changed(self) -> bool:
        return not (
            math.isclose(getattr(self.node, "time", 0), self._time)
            and (getattr(self.node, "iteration", None) == self._iteration)
        )


class Ports(Dict[Port]):
    """Port 的汇总，

    Args:
        typing (_type_): _description_
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def put(self, path, value, *args, **kwargs):
        return as_path(path).update(self._cache, value, *args, **kwargs)

    def get(self, path, **kwargs) -> Port | None:
        pth = as_path(path)
        match len(pth):
            case 0:
                return Port()
            case 1:
                return self._cache.get(pth[0], **kwargs)
            case _:
                return pth.get(self._cache, **kwargs)

    def __missing__(self, key: str | int) -> typing.Any:
        raise KeyError(f"{self.__class__.__name__}.{key} is not assigned! ")

    # def __missing__(self, path: str) -> Port:
    #     self._cache[str(path)] = port = Port(None, fragment=path)
    #     return port

    # def refresh(self, *args, **kwargs) -> Self:
    #     attr_name = self.__class__.__name__.lower()

    #     if len(args) + len(kwargs) > 0:
    #         for obj in [*args, kwargs]:
    #             if isinstance(obj, Ports):
    #                 for k, n in self.items():
    #                     n.link(obj.get_cache(k, _not_found_) or obj.get_cache(n.identifier, _not_found_))
    #             elif isinstance(obj, collections.abc.Mapping):
    #                 for k, n in self.items():
    #                     n.link(obj.get(k, obj.get(n.identifier, _not_found_)))

    #     else:
    #         parent: HTreeNode = as_path("../../").get(self, _not_found_)
    #         if isinstance(parent, collections.abc.Sequence):
    #             parent = getattr(parent, "_parent", _not_found_)

    #         if isinstance(parent, SpTree):
    #             for n in self.values():
    #                 node = getattr(parent, n.identifier, _not_found_)
    #                 n.link(node)

    #         self.refresh(getattr(parent, attr_name, _not_found_))

    #     return self


class InPorts(Ports):
    def edge(self, name: str, source: Port, **kwargs) -> Edge:
        if not isinstance(source, Port):
            source = Port(source)
        return source.link(self[name], **kwargs)


class OutPorts(Ports):
    def edge(self, name: str, target: Port, **kwargs) -> Edge:
        if not isinstance(target, Port):
            target = Port(target)
        return self[name].link(target, **kwargs)


class Edge:
    """`Edge` defines a connection between two `Port`s

    Attribute

    - source      : the start of edge which must be `OUTPUT Port`
    - target      : the start of edge which must be `INPUT Port`
    - dtype       : defines what `Port`s it can be connected, (default: string)
    - label       : short string
    - description : long string
    """

    def __init__(
        self,
        source=None,
        target=None,
        source_type_hint=None,
        target_type_hint=None,
        graph=None,
        **kwargs,
    ):
        self._source = Port(source, source_type_hint)

        self._target = Port(target, target_type_hint)

        self._graph = graph

        self._metadata = PropertyTree(kwargs)

    def __copy__(self):
        return Edge(self._source, self._target, graph=self._graph, **self._metadata._cache)

    @property
    def metadata(self) -> PropertyTree:
        return self._metadata

    @property
    def source(self) -> Port:
        return self._source

    @property
    def target(self) -> Port:
        return self._target

    @property
    def is_linked(self):
        return self._target.node is not None and self._source.node is not None

    def __str__(self):
        return f"""<{self.__class__.__name__} source='{self._source}' target='{self._target}' label='{self._metadata.get('label','')}'/>"""

    def _repr_s(self):
        def _str(s):
            if s is None:
                return ""
            elif type(s) is str:
                return "." + s
            elif isinstance(s, slice):
                if s.stop is None:
                    return f"[{s.start or ''}:{s.step or ''}]"
                else:
                    return f"[{s.start or ''}:{s.step or ''}:{s.stop or ''}]"

            elif isinstance(s, collections.abc.Sequence):
                return "".join([f"{_str(t)}" for t in s])
            else:
                return f"[{s}]"

        return "".join([_str(s) for s in self._path])

    def split(self, *args, **kwargs):
        """
        using Slot Node split edge into chain, add In(Out)Slot not to graph

        return list of splitted edges
        """
        source = self._source
        target = self._target

        s = collections.deque([source._parent] if source is not None else [])
        t = collections.deque([target._parent] if target is not None else [])

        if getattr(s[0], "parent", None) is getattr(t[0], "parent", None):
            return self

        while s[0] is not None:
            s.appendleft(s[0]._parent)

        while t[0] is not None:
            t.appendleft(t[0]._parent)

        s_rank = len(s)
        t_rank = len(t)
        pos = s_rank - 2
        tag = ""
        while pos >= t_rank or (pos >= 0 and s[pos] is not t[pos]):
            tag = f"{tag}_{source._parent.name}"

            s[pos].slot[tag] = source

            source = s[pos].port[tag]

            pos = pos - 1

        tag = f"{tag}_{source._parent.name}"

        while pos < t_rank - 2:
            pos = pos + 1
            tag = f"{tag}_{source._parent.parent.name}"
            t[pos].port[tag] = source

            source = t[pos].slot[tag]

        src, prefix = self._unwrap(source)
        self._source = src
        self._path = prefix + self._path
        return self
