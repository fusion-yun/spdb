import collections
import html
import itertools
import collections.abc

import numpy as np
import pygraphviz as pgv

from networkx.drawing.nx_agraph import to_agraph

from spdm.utils.tags import _not_found_
from spdm.core.htree import Dict

from spdm.view.render import Render

MAX_LABEL_LENGTH = 15

PredefinedTheme = {
    "shapes": {
        "SpObject": {
            "color": "${theme.color.third}",
            "fontcolor": "${theme.color.third}",
        },
        "SpObject.initialized": {
            "style": "dotted",
            "color": "${theme.color.second}",
            "fontcolor": "${theme.color.second}",
        },
        "SpObject.ready": {
            "style": "dashed",
            "color": "${theme.color.main}",
            "fontcolor": "${theme.color.main}",
        },
        "SpObject.active": {
            "color": "${theme.color.active}",
            "fontcolor": "${theme.color.active}",
        },
        "SpObject.valid": {
            "style": "solid",
            "color": "${theme.color.valid}",
            "fontcolor": "${theme.color.valid}",
        },
        "SpObject.pending": {
            "style": "dashed",
        },
        "SpObject.error": {
            "color": "${theme.color.error}",
            "fontcolor": "${theme.color.error}",
        },
        "Node": {"style": "rounded, ${_base.style}", "label": "", "shape": "square", "width": 0.2, "height": 0.2},
        "Graph": {"penwidth": 1},
        "Graph.active": {"style": "${_base.style},dashed", "penwidth": 4},
        "Graph.InPort": {"port": "w", "arrow": "none"},
        "Graph.OutPort": {"port": "e", "arrow": "none"},
        "Edge": {"headlabel": "${.attribute:label}"},
        "Actor": {
            "shape": "record",
            "label": "${.as_actor:}",
        },
        "Expression": {"shape": "record", "label": "${.as_expression:}"},
        "Function": {"shape": "record", "label": "${.as_expression:}"},
        "Resource": {"shape": "folder", "orientation": 0, "label": "${.attribute:label}"},
        "Resource.InPort": {"port": "none"},
        "Resource.OutPort": {"port": "e"},
        "BreakPoint.InPort": {"port": "w"},
        "BreakPoint.OutPort": {"port": "e"},
        "Constant": {"shape": "signature", "label": "${.attribute:label}"},
        "Constant.InPort": {"port": "w"},
        "Constant.OutPort": {"port": "e"},
        "Figure": {"label": ""},
        "Display": {
            "shape": "rectangle",
            "peripheries": 2,
            "height": 0.2,
        },
        "Display.valid": "${.display:}",
        "Display.InPort": {"port": "w"},
        "Display.OutPort": {"port": "e"},
        "FlowControlNode": {"shape": "record", "label": "${.as_record:}"},
        "InPort": {
            "port": "${.attribute:name}:w",
            "arrow": "odot",
            "label": "",
        },
        "OutPort": {
            "port": "${.attribute:name}:e",
            "arrow": "none",
            "label": "",
        },
        "Slot": {
            "shape": "${.conditional:${.attribute:label}?component:circle}",
            "width": 0,
            "height": 0,
            "label": "${.attribute:label}",
        },
        "Slot.InPort": {"port": "w", "arrow": "none"},
        "Slot.OutPort": {"port": "e", "arrow": "none"},
        "Input": {"shape": "signature"},
        "Output": {"shape": "record"},
        "ControlPoint": {"shape": "square", "width": 0.25, "height": 0.25},
        "Join": {"shape": "circle", "width": 0.5, "height": 0.5},
        "Stop": {
            "shape": "triangle",
            "orientation": 270,
            "style": "${_base.style},filled",
            "peripheries": 2,
            "width": 0.25,
            "height": 0.25,
            "pin": "true",
            "pos": "2,2",
        },
        "Stop.valid": {
            "color": "${.conditional:${.cache:value}?${theme.color.break}:${theme.color.pass}}",
            "shape": "${.conditional:${.cache:value}?circle:${shapes.Stop.shape}}",
        },
        "Continue": {"shape": "triangle", "orientation": 270, "width": 0.5, "height": 0.5},
        "IF": {
            "shape": "diamond",
        },
    }
}


class GraphvizRender(Render, plugin_name="graphviz"):

    def __init__(self, theme=None, *args, **kwargs):
        super().__init__(*args, theme=[*(theme or []), PredefinedTheme], **kwargs)

    def node_style(self, nobj):
        n_style = super().node_style(nobj)
        return n_style

    def port_style(self, pobj) -> Dict:
        p_style = super().port_style(pobj)
        return p_style

    def edge_style(self, eobj):
        e_style = super().edge_style(eobj)

        s_style = self.port_style(eobj.source)
        t_style = self.port_style(eobj.target)

        e_style["headport"] = t_style.get("port", "_")
        e_style["tailport"] = s_style.get("port", "_")
        e_style.setdefault("headlabel", t_style.get("label", ""))
        e_style.setdefault("taillabel", s_style.get("label", ""))
        e_style["arrowhead"] = t_style.get("arrow", "none")
        e_style["arrowtail"] = s_style.get("arrow", "none")

        return e_style

    def graph_style(self, gobj, *args, **kwargs):
        g_style = super().graph_style(gobj)
        return g_style

    def by_state(self, d, obj, *args, **kwargs):
        state = self.get([obj.id, "state"], _not_found_)
        res = d.get(state, None) or d.get(_not_found_)
        return res

    def display(self, k, nobj, *args, **kwargs):
        value = self.get([nobj.id, "value"], None)
        if not isinstance(value, collections.abc.Mapping):
            return {"label": html.escape(str(value))}
        schema = value.get("$schema", None)
        if schema == "image":
            return {"image": value.get("path", None)}

    def as_record(self, k, nobj, *args, **kwargs):
        if nobj is None:
            RuntimeError(f"Null node")
        in_iter = iter(nobj.in_ports.values())
        out_iter = iter(nobj.out_ports.values())

        head_label = f" <{next(out_iter).name}> {html.escape(nobj.label)}"

        port_label = "|".join(
            itertools.chain(
                map(lambda p: f"<{p.name}>{html.escape(p.label or '' )} \\r", out_iter),
                map(lambda p: f"<{p.name}>{html.escape(p.label or '')} \\l", in_iter),
            )
        )

        return f" {head_label} | {port_label} "

    def as_actor(self, k, nobj, *args, **kwargs):
        if nobj is None:
            RuntimeError(f"Null node")
        in_iter = iter(nobj.in_ports.values())
        out_iter = iter(nobj.out_ports.values())
        in_port = next(in_iter)
        out_port = next(out_iter)
        head_label = f"{{ <{in_port.name}> |{html.escape(nobj.label)} |<{out_port.name}>  }}"

        return "|".join(
            itertools.chain(
                iter([head_label]),
                map(lambda p: f"<{p.name}>{html.escape(p.label or '' )} \\r", out_iter),
                map(lambda p: f"<{p.name}>{html.escape(p.label or '')} \\l", in_iter),
            )
        )

    def as_expression(self, k, nobj, *args, **kwargs):
        if nobj is None:
            RuntimeError(f"Null node")
        in_iter = iter(nobj.in_ports.values())
        # out_iter = iter(nobj.out_ports.values())

        head_label = f" <{OutPort.TAG}> {html.escape(nobj.label)}"

        port_label = "|".join(map(lambda p: f"<{p.name}>{html.escape(p.label or '' )} \\l", in_iter))

        return f"{{ {{ {port_label} }} | {head_label} }}"

    def show_label(self, k, nobj, *args, **kwargs):
        return html.escape(str(nobj.label))

    def show_value(self, k, nobj, *args, **kwargs):
        value = self.get([nobj.id, "value"], "")
        return html.escape(str(value))

    def get_dtype_label(self, dtype):

        if dtype in [collections.abc.Mapping, object]:
            return "{}"
        elif isinstance(dtype, (np.ndarray, list, set)):
            return "[]"
        elif hasattr(dtype, "__name__"):
            return dtype.__name__
        else:
            return ""

    def apply(self, g, *args, format="svg", **kwargs):
        ag: pgv.AGraph = to_agraph(g)

        ag.graph_attr.update(self.get_style("theme.global.graph", {}))

        ag.edge_attr.update(self.get_style("theme.global.edge", {}))

        ag.node_attr.update(self.get_style("theme.global.node", {}))

        self.render_ag(g, ag)

        ag.draw("graph.png", format=format, prog="dot")

        return

    def render_ag(self, ag: pgv.AGraph):

        for node in ag.nodes():
            node.attr["color"] = "blue"
            node.attr["style"] = "filled"
            node.attr["fillcolor"] = "lightgray"
            node.attr["fontcolor"] = "red"

        for edge in ag.edges():
            edge.attr["color"] = "blue"
            edge.attr["style"] = "filled"
            edge.attr["fillcolor"] = "lightgray"
            edge.attr["fontcolor"] = "red"

        for sg in ag.subgraphs():
            self.render_ag(sg)

        outside_edges = []

        with ag.subgraph(name=f"cluster_{g.full_name}", graph_attr={**self.graph_style(g), "rank": "source"}) as sg:
            sg.attr(label=g.label)

            for n in g.nodes:
                sub_edges = self.render_ag(n, sg)
                for eobj in itertools.chain(n.in_edges, sub_edges):
                    if not eobj.is_linked:
                        continue
                    elif not g.has_child(eobj.source.parent):
                        outside_edges.append(eobj)
                    else:

                        s_id = eobj.source.parent.full_name
                        t_id = eobj.target.parent.full_name

                        if isinstance(eobj.source.parent, Graph):
                            s_id = f"{eobj.source.parent.full_name}._{Slot.TAG}_{eobj.source.name}"

                        if isinstance(eobj.target.parent, Graph):
                            t_id = f"{eobj.target.parent.full_name}._{Slot.TAG}_{eobj.target.name}"

                        sg.edge(s_id, t_id, **self.edge_style(eobj))

            n_in = None
            with sg.subgraph(name="_inslots", graph_attr={"rank": "min"}) as in_slots:
                for n in g.nodes:
                    if not isinstance(n, InSlot):
                        continue
                    elif n_in is not None:
                        in_slots.edge(
                            n_in.full_name, n.full_name, style="invisible", spline="false", arrowhead="none"
                        )
                    n_in = n
            n_out = None
            with sg.subgraph(name="_outslots", graph_attr={"rank": "max"}) as out_slots:
                for n in g.nodes:
                    if not isinstance(n, OutSlot):
                        continue
                    elif n_out is not None:
                        out_slots.edge(
                            n_out.full_name, n.full_name, style="invisible", spline="false", arrowhead="none"
                        )
                    n_out = n

        return outside_edges


__SP_EXPORT__ = GraphvizRender
