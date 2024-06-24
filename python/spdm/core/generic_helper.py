""" Generic Helper """

import typing
import types
import inspect
from copy import deepcopy, copy
import functools
from spdm.utils.logger import logger

_Ts = typing.TypeVarTuple("_Ts")


def generic_specification(tp: type | typing.TypeVar, specification: dict, name=None) -> type:
    """若类型参数完全特化（specification），则返回新的类，而不是 typing._GenericAlias。
    例如：typing.List[int] -> List[int]，而不是 typing._GenericAlias。
    List[int] 类型具有类属性 __args__，用于存储类型参数。

    """
    new_tp = tp
    if isinstance(tp, typing.TypeVar):
        new_tp = specification.get(tp, None)
    elif isinstance(tp, typing._GenericAlias):
        args = tuple([generic_specification(a, specification) for a in tp.__args__ if a is not type(None)])
        args = tuple([a for a in args if a is not None])
        if len(args) > 0:
            new_tp = tp.__getitem__(args)
        else:
            new_tp = None

    # elif isinstance(tp, type):
    #     new_tp = type(name, (tp,), generic_specification(tp.__dir__, specification))

    elif isinstance(tp, dict):
        new_tp = {k: generic_specification(v, specification, k) for k, v in tp.items()}
        new_tp = {k: v for k, v in new_tp.items() if v is not None}
        if len(new_tp) == 0:
            new_tp = None
    elif inspect.isfunction(tp):
        annotations = generic_specification(getattr(tp, "__annotations__", {}), specification)
        if annotations is None:
            new_tp = None
        else:
            new_tp = deepcopy(tp)
            new_tp.__annotations__.update(annotations)
    else:
        new_tp = None
    return new_tp


class GenericHelper(typing.Generic[*_Ts]):
    """A helper class for typing generic."""

    @typing._tp_cache
    def __class_getitem__(cls, item):

        alias = super().__class_getitem__(item)

        if cls is GenericHelper:
            return alias

        cls_name = f"{cls.__name__}[" + ",".join(typing._type_repr(a) for a in alias.__args__) + "]"

        specification = dict(zip(cls.__parameters__, alias.__args__))

        # specification = {k: v for k, v in specification.items() if k is not v}

        # if len(specification) == 0:
        #     return alias
            # tp_spec = {k: generic_specification(getattr(cls, k, None), specification, k) for k in dir(cls)}

            # tp_spec = {k: v for k, v in tp_spec.items() if v is not None}
        members = generic_specification(
            {
                k: member
                for k, member in inspect.getmembers(cls)
                if inspect.isfunction(member)
                or inspect.ismethod(member)
                or isinstance(member, (typing._GenericAlias, typing.TypeVar))
            },
            specification,
        )

        if members is None:
            members = {}

        annotations = generic_specification(typing.get_type_hints(cls), specification)

        if annotations is not None:
            members["__annotations__"] = annotations

        n_cls = type(
            cls_name,
            (cls,),
            {
                **members,
                "__module__": cls.__module__,
                "__package__": getattr(cls, "__package__", None),
            },
        )

        if len(alias.__parameters__) > 0:
            alias.__origin__ = n_cls
            return alias
        else:
            return n_cls

    # return _TGenericAlias(
    #     alias.__origin__,
    #     alias.__args__,
    #     inst=alias._inst,
    #     name=alias._name,
    #     _paramspec_tvars=alias._paramspec_tvars,
    # )[()]
