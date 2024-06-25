""" Generic Helper """

import typing
import inspect
from copy import deepcopy, copy
import functools
from spdm.utils.logger import logger

_Ts = typing.TypeVarTuple("_Ts")


def generic_specification(tp: type | typing.TypeVar, tp_map: dict) -> type:
    """若类型参数完全特化（specification），则返回新的类，而不是 typing._GenericAlias。
    例如：typing.List[int] -> List[int]，而不是 typing._GenericAlias。
    List[int] 类型具有类属性 __args__，用于存储类型参数。

    """

    if isinstance(tp, typing.TypeVar):
        new_tp = tp_map.get(tp, None)
    elif isinstance(tp, typing._GenericAlias):
        args = tuple([generic_specification(a, tp_map) for a in tp.__args__ if a is not type(None)])
        args = tuple([a for a in args if a is not None])
        if len(args) > 0:
            new_tp = tp.__getitem__(args)
        else:
            new_tp = None
    elif isinstance(tp, type):
        new_tp = tp
    elif inspect.isfunction(tp) or inspect.ismethod(tp):
        annotations = generic_specification(getattr(tp, "__annotations__", {}), tp_map)
        if annotations is None:
            new_tp = None
        else:
            new_tp = deepcopy(tp)
            new_tp.__annotations__.update(annotations)
    else:
        new_tp = None
    return new_tp


def spec_members(members: dict, cls, tp_map) -> dict:
    if not issubclass(cls, typing.Generic) or cls is typing.Generic:
        return members

    if members is None:
        members = {}

    for k, m in inspect.getmembers(cls):
        if k not in members and not k.startswith("__") and (tp_hint := generic_specification(m, tp_map)) is not None:
            members[k] = tp_hint

    ann = members.get("__annotations__", {})

    ann.update({k: generic_specification(v, tp_map) for k, v in cls.__annotations__.items() if k not in ann})

    members["__annotations__"] = ann

    for idx, orig_base in enumerate(cls.__orig_bases__):
        if not isinstance(orig_base, typing._GenericAlias):
            continue

        base = cls.__bases__[idx]

        if not issubclass(base, typing.Generic) or base is typing.Generic:
            continue
        base_tp_map = {k: generic_specification(v, tp_map) for k, v in (zip(base.__parameters__, orig_base.__args__))}

        members = spec_members(members, base, base_tp_map)

    return members


class GenericHelper(typing.Generic[*_Ts]):
    """A helper class for typing generic."""

    @typing._tp_cache
    def __class_getitem__(cls, item):
        alias = super().__class_getitem__(item)

        if cls is GenericHelper or len(alias.__parameters__) > 0:
            return alias

        orig_cls = alias.__origin__

        cls_name = f"{cls.__name__}[" + ",".join(typing._type_repr(a) for a in alias.__args__) + "]"

        n_cls = type(
            cls_name,
            (cls,),
            {
                **spec_members(None, orig_cls, dict(zip(orig_cls.__parameters__, alias.__args__))),
                "__module__": cls.__module__,
                "__package__": getattr(cls, "__package__", None),
            },
        )

        return n_cls


__all__ = ["GenericHelper"]
# if len(alias.__parameters__) > 0:
#     # alias.__origin__ = n_cls
# else:
#     return n_cls

# return _TGenericAlias(
#     alias.__origin__,
#     alias.__args__,
#     inst=alias._inst,
#     name=alias._name,
#     _paramspec_tvars=alias._paramspec_tvars,
# )[()]
