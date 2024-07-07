""" Generic Helper """

import typing
import inspect
from copy import copy

_Ts = typing.TypeVarTuple("_Ts")


def generic_specification(tp: type | typing.TypeVar, tp_map: dict) -> type:
    """若类型参数完全特化（specification），则返回新的类，而不是 typing._GenericAlias。
    例如：typing.List[int] -> List[int]，而不是 typing._GenericAlias。
    List[int] 类型具有类属性 __args__，用于存储类型参数。

    """

    if isinstance(tp, typing.TypeVar):
        new_tp = tp_map.get(tp, tp)
    elif isinstance(tp, dict):
        new_tp = {k: generic_specification(v, tp_map) for k, v in tp.items()}
    elif isinstance(tp, typing._GenericAlias):
        args = tuple([generic_specification(a, tp_map) for a in tp.__parameters__])
        # args = tuple([generic_specification(a, tp_map) for a in tp.__args__ if a is not type(None)])
        # args = tuple([a for a in args if a is not None])
        new_tp = tp.__getitem__(args) if len(args) > 0 else None
    elif isinstance(tp, type):
        new_tp = tp
    elif inspect.isfunction(tp) or inspect.ismethod(tp):
        annotations = generic_specification(getattr(tp, "__annotations__", {}), tp_map)
        if annotations is None:
            new_tp = None
        else:
            new_tp = copy(tp)
            new_tp.__annotations__.update(annotations)
    else:
        new_tp = None
    return new_tp


def spec_members(members: dict, cls, tp_map) -> dict:
    if not issubclass(cls, typing.Generic) or cls is typing.Generic:
        return members

    if members is None:
        members = {}

    for k in cls.__dict__:  # inspect.getmembers(cls):
        if k not in members and not k.startswith("__"):
            tp_hint = generic_specification(getattr(cls, k), tp_map)
            if tp_hint is not None:
                members[k] = tp_hint

    ann = members.get("__annotations__", {})

    ann.update(
        {
            k: generic_specification(v, tp_map)
            for k, v in typing.get_type_hints(cls).items()
            if k not in ann and k in cls.__annotations__
        }
    )

    members["__annotations__"] = ann

    for idx, orig_base in enumerate(cls.__orig_bases__):
        if not isinstance(orig_base, typing._GenericAlias):
            continue

        base = cls.__bases__[idx]

        if not issubclass(base, typing.Generic) or base is typing.Generic or base is Generic:
            continue

        base_tp_map = {k: generic_specification(v, tp_map) for k, v in (zip(base.__parameters__, orig_base.__args__))}

        members = spec_members(members, base, base_tp_map)

    return members


class _GenericAlias(typing._GenericAlias, _root=True):
    """重载了 typing._GenericAlias 类，使得 Generic 类型的实例化更加方便。"""

    @typing._tp_cache
    def __getitem__(self, args):
        if len(args) > 0:
            alias = super().__getitem__(args)
        else:
            alias = self

        if len(alias.__parameters__) > 0:
            return alias

        orig_cls = alias.__origin__

        cls_name = f"{orig_cls.__name__}[" + ",".join(typing._type_repr(a) for a in alias.__args__) + "]"

        n_cls = type(
            cls_name,
            (orig_cls,),
            {
                **spec_members(None, orig_cls, dict(zip(orig_cls.__parameters__, alias.__args__))),
                "__module__": orig_cls.__module__,
                "__package__": getattr(orig_cls, "__package__", None),
                "__args__": alias.__args__,
            },
        )

        return n_cls


class Generic(typing.Generic[*_Ts]):
    """重载 typing.Generic 类，强化类型参数的特化 (specification) 能力。
    - 所有类参数都被特化时，返回新的类，而不是 typing._GenericAlias。
    - 类型中的 typevar 会被替换为具体的类型。
    - 类参数未被特化时，依然返回._GenericAlias
    """

    @typing._tp_cache
    def __class_getitem__(cls, item):
        alias = super().__class_getitem__(item)
        alias.__class__ = _GenericAlias
        if cls is not Generic and len(alias.__parameters__) == 0:
            return alias[()]
        else:
            return alias


__all__ = ["Generic"]
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
