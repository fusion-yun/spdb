"""Module containing the Graph class."""

import typing
import collections
import collections.abc
import functools
import networkx as nx
from networkx.classes.reportviews import DegreeView, EdgeView, NodeView

from spdm.utils.type_hint import Generic, type_convert


TNode = typing.TypeVar("TNode")


class _TNodeView(Generic[TNode], NodeView):
    """泛型版本的 NodeView 类。仅用以了解其类型。"""

    def __iter__(self) -> typing.Generator[TNode, None, None]:
        return NodeView.__iter__(self)  # pylint: disable=no-member

    def __getitem__(self, n) -> TNode:
        return NodeView.__getitem__(self, n)

    def __getstate__(self) -> dict:  # pylint: disable=useless-parent-delegation
        """应返回一个可以代表对象状态的字典。"""
        return NodeView.__getstate__(self)


class _TEdgeView(Generic[TNode], EdgeView):
    """泛型版本的 EdgeView 类。"""


class _TDegreeView(Generic[TNode], DegreeView):
    """A view of node degrees as returned by the degree method."""


class _TGraphHelper(Generic[TNode]):
    """A helper class for typing generic Graph.

    Note: 在 Python 中使用多重继承时，如果多个基类都包含相同名字的方法，
    调用 super() 时会遵循方法解析顺序 (MRO, Method Resolution Order)
    来确定哪个基类的方法被调用。super() 在多重继承中的行为基于 MRO 的
    线性化顺序，这个顺序可以通过 ClassName.__mro__ 或 ClassName.mro() 来查看。

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()

        if len(args) == 1 and isinstance(args[0], collections.abc.Mapping):
            self.__setstate__(args[0])
        elif len(args) == 0:
            self.__setstate__(kwargs)
        else:
            raise RuntimeError(f"Too much args! [{len(args)}]")

    def __getstate__(self) -> dict:  # pylint: disable=useless-parent-delegation
        """应返回一个可以代表对象状态的字典。"""
        # return super().__getstate__()
        return {**self.nodes.__getstate__(), **self.edges.__getstate__()}

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        """接受一个字典，并使用这个字典来恢复对象的状态。"""
        # super().__setstate__(state)
        self.add_nodes_from(state.get("nodes", None))
        self.add_edges_from(state.get("edges", None))
        self.graph.update(state.get("metadata", {}))

    @functools.cached_property
    def nodes(self) -> _TNodeView[TNode]:
        """A NodeView of the Graph."""
        return _TNodeView[self.__tp_params__](self)

    @functools.cached_property
    def edges(self) -> _TEdgeView[TNode]:
        """A NodeView of the Graph."""
        return _TEdgeView[self.__tp_params__](self)

    @functools.cached_property
    def degree(self) -> _TDegreeView[TNode]:
        """A NodeView of the Graph."""
        return _TDegreeView[self.__tp_params__](self)

    def add_node(self, node_for_adding, **attr):
        """Add a single node n and update node attributes."""
        return super().add_node(  # pylint: disable=no-member
            type_convert(self.__tp_params__, node_for_adding, _parent=self),
            **attr,
        )

    def add_nodes_from(self, nodes_for_adding, **attr):
        """Add multiple nodes."""
        if isinstance(nodes_for_adding, collections.abc.Iterable):
            super().add_nodes_from(  # pylint: disable=no-member
                map(lambda n: type_convert(self.__tp_params__, n), nodes_for_adding),
                **attr,
            )

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        """Add an edge between u and v."""
        return super().add_edge(  # pylint: disable=no-member
            self._type_convert(u_of_edge),
            self._type_convert(v_of_edge),
            **attr,
        )

    def add_edges_from(self, ebunch_for_adding, **attr):
        """Add all the edges in ebunch_to_add."""
        if isinstance(ebunch_for_adding, collections.abc.Iterable):
            super().add_edges_from(  # pylint: disable=no-member
                (
                    (type_convert(self.__tp_params__, u), type_convert(self.__tp_params__, v), *dd)
                    for u, v, *dd in ebunch_for_adding
                ),
                **attr,
            )


class Graph(_TGraphHelper[TNode], nx.Graph):  # pylint: disable=missing-class-docstring
    pass


class DiGraph(_TGraphHelper[TNode], nx.DiGraph):  # pylint: disable=missing-class-docstring
    pass


class MultiGraph(_TGraphHelper[TNode], nx.MultiGraph):  # pylint: disable=missing-class-docstring
    pass


class MultiDiGraph(_TGraphHelper[TNode], nx.MultiDiGraph):  # pylint: disable=missing-class-docstring
    pass
