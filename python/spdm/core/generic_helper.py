""" Generic Helper """

import typing

_Ts = typing.TypeVarTuple("_Ts")


class _TGenericAlias(typing._GenericAlias, _root=True):  # pylint: disable=protected-access

    def __getitem__(self, params) -> typing.Self | type:
        """若类型参数完全特化（specification），则返回新的类，而不是 typing._GenericAlias。
        例如：typing.List[int] -> List[int]，而不是 typing._GenericAlias。
        List[int] 类型具有类属性 __args__，用于存储类型参数。

        """

        if isinstance(params, tuple) and len(params) == 0:
            new_alias = self
        else:
            new_alias = super().__getitem__(params)

        if any(isinstance(arg, typing.TypeVar) for arg in new_alias.__args__):
            return new_alias
        else:

            new_cls: typing.Type[GenericHelper] = new_alias.__origin__

            cls_name = f"{new_cls.__name__}[" + ",".join(typing._type_repr(a) for a in new_alias.__args__) + "]"

            n_cls = new_cls._generic_cache.get(cls_name, None)

            if n_cls is None:
                n_cls = type(
                    cls_name,
                    (new_cls,),
                    {
                        "__args__": new_alias.__args__,
                        "__module__": new_cls.__module__,
                        "__package__": getattr(new_cls, "__package__", None),
                    },
                )
                new_cls._generic_cache[cls_name] = n_cls

            return n_cls


class GenericHelper(typing.Generic[*_Ts]):
    """A helper class for typing generic."""

    _generic_cache = {}

    def __class_getitem__(cls, item) -> _TGenericAlias | type:
        alias = super().__class_getitem__(item)
        alias.__class__ = _TGenericAlias
        return alias[()]

        # return _TGenericAlias(
        #     alias.__origin__,
        #     alias.__args__,
        #     inst=alias._inst,
        #     name=alias._name,
        #     _paramspec_tvars=alias._paramspec_tvars,
        # )[()]
