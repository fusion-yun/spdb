"""
定义一个property, 要求其所在的class必须有一个_as_child方法，用于将其转换为type_hint 指定的类型。
    ```python
        class Foo(Dict):
            pass

        class Doo(Dict):

            f0 = SpProperty(type_hint=Foo)      # 优先级最高, 不兼容IDE的类型提示

            f1: Foo = SpProperty()              # 推荐，可以兼容IDE的类型提示

            ######################################################
            @sp_property
            def f3(self) -> Foo:                 # 用于定义f3的getter操作，与@property.getter类似
                'This is  f3!'
                return self.get("f3", {})

            @f3.setter
            def f3(self,value)->None:            # 功能与@property.setter  类似, NOT IMPLEMENTED YET!!
                self._entry.put("f3",value)

            @f3.deleter
            def f3(self)->None:                  # 功能与@property.deleter 类似, NOT IMPLEMENTED YET!!
                self._entry.child("f3").erase()
            ######################################################
                                                 # 完整版本
            def get_f4(self,default={})->Foo:
                return self.get("f4", default)

            def set_f4(self,value)->None:
                return self.set("f4", value)

            def del_f4(self,value)->None:
                return self.set("f4", value)

            f4 = sp_property(get_f4,set_f4,del_f4,"I'm f4",type_hint=Foo)
        ```

"""

import abc
import inspect
import typing
import collections.abc
from copy import deepcopy
from _thread import RLock

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_, _undefined_
from spdm.core.htree import HTree, HTreeNode, List
from spdm.core.path import Path, as_path


def _copy(obj, *args, **kwargs):
    if isinstance(obj, dict):
        return {k: _copy(v, *args, **kwargs) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [_copy(v, *args, **kwargs) for k, v in obj]

    elif isinstance(obj, SpTree):
        cache = {}

        for k, attr in inspect.getmembers(obj.__class__, lambda c: isinstance(c, SpProperty)):
            if attr.getter is None and attr.alias is None:

                value = getattr(obj, k, _not_found_)

                if value is not _not_found_:
                    cache[k] = _copy(value, *args, **kwargs)

        return cache

    elif isinstance(obj, HTreeNode):
        return obj.fetch(*args, **kwargs)

    else:
        return deepcopy(obj)


_T = typing.TypeVar("_T")
_TR = typing.TypeVar("_TR")


class SpProperty:
    """
    具有语义的属性
    - 自动绑定
    - 自动类型转换

    用于为 SpTree 类（及其子类）定义一个property, 并确保其类型为type_hint 指定的类型。

    例如：
    ``` python
        class Foo(SpPropertyClass):
            # 方法一
            @sp_property
            def a(self) -> float: return 128

            # 方法二
            @sp_property(coordinate1="../psi")
            def dphi_dpsi(self) -> Profile[float]: return self.a*2

            # 方法三
            phi: Profile[float] = sp_property(coordinate1="../psi")

    ```
    方法二、三中参数 coordinate1="../psi"，会在构建 Profile时传递给构造函数  Profile.__init__。

    方法三 会在创建class 是调用 __set_name__,
            会在读写property phi 时调用 __set__,__get__ 方法，
            从Node的_cache或entry获得名为 'phi' 的值，将其转换为 type_hint 指定的类型 Profile[float]。
    """

    is_property = True

    def __init__(
        self,
        getter: typing.Callable[[typing.Any], typing.Any] = None,
        setter=None,
        deleter=None,
        type_hint: typing.Type = None,
        alias: str = None,
        default_value: typing.Any = _not_found_,
        doc: str = None,
        strict: bool = False,
        **kwargs,
    ):
        """
        Parameters
        ----------
        getter : typing.Callable[[typing.Any], typing.Any]
            用于定义属性的getter操作，与@property.getter类似
        setter : typing.Callable[[typing.Any, typing.Any], None]
            用于定义属性的setter操作，与@property.setter类似
        deleter : typing.Callable[[typing.Any], None]
            用于定义属性的deleter操作，与@property.deleter类似
        type_hint : typing.Type
            用于指定属性的类型
        alias:string
            声明当前 property 是 alias 所指 path 下property的别名
        default_value : typing.Any
            用于指定属性的默认值
        doc : typing.Optional[str]
            用于指定属性的文档字符串
        strict : bool
            用于指定是否严格检查属性的值是否已经被赋值
        kwargs : typing.Any
            用于指定属性的元数据

        """

        self.lock = RLock()

        self.getter = getter
        self.setter = setter
        self.deleter = deleter

        self.alias = as_path(alias) if alias is not None and len(alias) > 0 else None
        self.property_name: str = None

        self.type_hint = type_hint
        self.default_value = default_value
        self.doc = doc or ""

        self.strict = strict
        self.metadata = kwargs

    def __call__(self, func: typing.Callable[..., _TR]) -> _TR:
        """用于定义属性的getter操作，与@property.getter类似
        例如：
        @sp_property
         def a(self) -> float: return 128
        """
        if self.getter is not None:
            raise RuntimeError("Can not reset getter!")
        self.getter = func
        return self

    def __set_name__(self, owner_cls, name: str):
        # TODO：
        #    若 owner 是继承自具有属性name的父类，则默认延用父类sp_property的设置
        self.property_name = name

        tp = None
        if callable(self.getter):
            tp = typing.get_type_hints(self.getter).get("return", None)

        if tp is None:
            try:
                tp = typing.get_type_hints(owner_cls).get(name, None)
            except Exception as error:
                logger.exception(owner_cls)
                raise error

        if tp is not None:
            self.type_hint = tp

        if self.getter is not None:
            self.doc += self.getter.__doc__ or ""

        for base_cls in owner_cls.__bases__:
            prop = getattr(base_cls, name, _not_found_)
            if isinstance(prop, SpProperty):
                # TODO: 区分 annotation 和 sp_property，
                #       在class类定义中为 annotation
                #       在instance 实例中为 sp_property
                if self.default_value is _not_found_:
                    self.default_value = prop.default_value

                if self.alias is None and prop.alias is not None:
                    self.alias = prop.alias

                self.doc += prop.doc

                self.metadata = Path().update(deepcopy(prop.metadata), self.metadata)
        # owner_cls.__annotations__[name] = self.type_hint

        self.metadata["name"] = name

        if self.doc == "":
            self.doc = f"{owner_cls.__name__}.{self.property_name}"

    def __set__(self, instance: HTree, value: typing.Any) -> None:
        assert instance is not None

        with self.lock:
            if self.alias is not None:
                instance.__set_node__(self.alias, value)
            elif self.property_name is not None:
                instance.__set_node__(self.property_name, value, setter=self.setter)
            else:
                logger.error("Can not use sp_property instance without calling __set_name__ on it.")

    def __get__(self, instance: HTree, owner_cls=None):
        if instance is None:
            # 当调用 getter(cls, <name>) 时执行
            return self
        elif not isinstance(instance, HTree):
            raise TypeError(f"Class '{instance.__class__.__name__}' must be a subclass of 'HTree'.")

        with self.lock:
            value = _not_found_
            if self.alias is not None:
                value = self.alias.get(instance, _not_found_)

                if inspect.isclass(self.type_hint) and isinstance(value, self.type_hint):
                    pass
                else:
                    value = instance.__as_node__(
                        self.property_name,
                        value,
                        type_hint=self.type_hint,
                        default_value=self.default_value,
                        metadata=self.metadata,
                    )

            else:
                value = instance.__get_node__(
                    self.property_name,
                    type_hint=self.type_hint,
                    getter=self.getter,
                    default_value=self.default_value,
                    metadata=self.metadata,
                )

            if self.strict and (value is _undefined_ or value is _not_found_):
                raise AttributeError(
                    f"The value of property '{owner_cls.__name__ if owner_cls is not None else 'none'}.{self.property_name}' is not assigned!"
                )

        return value

    def __delete__(self, instance: HTree) -> None:
        with self.lock:
            instance.__del_node__(self.property_name, deleter=self.deleter)


def sp_property(getter: typing.Callable[..., _T] | None = None, **kwargs) -> _T:
    if getter is None:

        def wrapper(func: typing.Callable[..., _TR]) -> _TR:
            return SpProperty(getter=func, **kwargs)

        return typing.cast(_TR, wrapper)
    else:
        return typing.cast(_T, SpProperty(getter=getter, **kwargs))


def annotation(**kwargs):
    """alias of sp_property"""
    return SpProperty(**kwargs)


class WithProperty:
    """自动添加 SpProperty
    ==============================================
    根据 type hint 在创建子类时自动添加 SpProperty"""

    def __init_subclass__(cls, default_value: typing.Any = _not_found_, final: bool = True, **kwargs) -> None:
        """根据 cls 的 type hint，为 cls 属性"""

        if not final:
            return super().__init_subclass__(**kwargs)

        if default_value is _not_found_:
            default_value = {}

        for name, type_hint in typing.get_type_hints(cls).items():
            attr = getattr(cls, name, default_value.get(name, _not_found_))

            if isinstance(attr, property):
                continue

            if getattr(attr.__class__, "is_property", False):
                if name not in cls.__dict__:
                    attr = SpProperty(getter=attr.getter, setter=attr.setter, deleter=attr.deleter, **attr.metadata)
            else:
                attr = SpProperty(default_value=attr)

            attr.type_hint = type_hint

            setattr(cls, name, attr)

            attr.__set_name__(cls, name)

        super().__init_subclass__(**kwargs)

        cls.__properties__ = set(
            [
                name
                for name, _ in inspect.getmembers(cls, lambda a: isinstance(a, SpProperty))
                if not name.startswith("_")
            ]
        )

    def __getstate__(self) -> dict:
        state = super().__getstate__()

        for k, value in state.items():
            if k not in self.__properties__:
                continue

            if isinstance(value, HTreeNode):
                value = value.__getstate__()
                state[k] = value

        return state

    # def fetch(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
    #     if len(args) == 0:
    #         projection = None
    #     else:
    #         projection = args[0]
    #     args = args[1:]

    #     if projection is None:
    #         names = self.__properties__
    #     elif isinstance(projection, dict):
    #         names = projection.values()
    #     elif isinstance(projection, str):
    #         names = [projection]
    #     elif isinstance(projection, collections.abc.Sequence):
    #         names = projection
    #     else:
    #         raise TypeError(f"Illegal type! {projection}")

    #     res = {}
    #     for k in names:
    #         value = Path(k).get(self, _not_found_)
    #         if isinstance(value, WithProperty):
    #             value = value.fetch(None, *args, **kwargs)
    #         elif callable(value):
    #             value = value(*args, **kwargs)
    #         res[k] = value

    #     if isinstance(projection, dict):
    #         res = {k: res.get(v, _not_found_) for k, v in projection.items()}
    #     elif projection is None:
    #         res = self.__class__(res, _parent=self._parent)
    #     return res


class WithMetadata:
    """元数据
    ===============================================
    在创建子类时候，添加 metadata 作为类变量"""

    _metadata = {}

    def __init_subclass__(cls, **metadata):
        if len(metadata) > 0:
            cls._metadata = Path().update(deepcopy(cls._metadata), metadata)

        super().__init_subclass__()

    # def __init__(self, *args, _metadata=None, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if _metadata is not None and _metadata is not _not_found_ and len(_metadata) > 0:
    #         self._metadata = Path().update(deepcopy(self._metadata), _metadata)


class WithAttribute:
    """Attribute 绑定
    ===============================================
    属性树，通过 __getattr__ 访问成员，并转换为对应的类型
    MRO 中需要有 __getnode__ 和 __setnode__
    """

    def __as_node__(self, *args, **kwargs) -> typing.Self | List[typing.Self]:

        node = super().__as_node__(*args, **kwargs)
        if node.__class__ is HTree:
            node = node._entry.get()

        if node is _not_found_:
            pass
        # elif node.__class__ is HTree and node._entry.is_list:
        #     node = List[PropertyTree](node._cache, _entry=node._entry)
        # elif node.__class__ is HTree and node._entry.is_dict:
        #     node.__class__ = PropertyTree
        elif isinstance(node, dict):
            node = AttributeTree(node)
        elif isinstance(node, list) and (len(node) == 0 or any(isinstance(n, dict) for n in node)):
            node = List[AttributeTree](node)

        return node

    def __getattr__(self, key: str) -> typing.Self | List[typing.Self]:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self.__get_node__(key, default_value=_not_found_)  # type:ignore

    def __setattr__(self, key: str, value: typing.Any):
        if key.startswith("_"):
            return super().__setattr__(key, value)

        return self.__set_node__(key, value)  # type:ignore


class AttributeTree(WithAttribute, WithProperty, HTree):
    pass


class SpTree(WithProperty, WithMetadata, HTree):
    """SpTree 根据 class 的 typhint 自动绑定转换类型
    ===============================================
    """

    # def name(self) -> str:
    #     return self._metadata.get("name", self.__class__.__name__)


def _make_sptree(cls, **metdata) -> typing.Type[SpTree]:
    if not inspect.isclass(cls):
        raise TypeError(f"Not a class {cls}")

    if not issubclass(cls, HTree):
        n_cls = type(cls.__name__, (cls, SpTree), {"_metadata": metdata})
        n_cls.__module__ = cls.__module__
    else:
        n_cls = cls
        n_cls._metadata.update(metdata)

    return n_cls


def sp_tree(cls: _T = None, /, **metadata) -> _T:
    """装饰器，将一个类转换为 SpTree 类"""

    if cls is None:
        return lambda c: sp_tree(c, **metadata)
    else:
        return _make_sptree(cls, **metadata)


class AsDataclass:
    def __init__(self, *args, **kwargs):
        keys = [*typing.get_type_hints(self.__class__).keys()]

        for idx, value in enumerate(args):
            key = keys[idx]
            if kwargs.get(key, _not_found_) is not _not_found_:
                raise KeyError(f"Redefined argument '{key}'!")
            kwargs[key] = value
        super().__init__(**kwargs)


class Dataclass(AsDataclass, HTree, WithProperty):
    pass


def sp_dataclass(cls=None, /, **metadata):
    """SpTree 类型装饰器。 将__init__的 args 根据 cls type_hint 转换为 kwargs
    例如：
       @sp_dataclass
        class Foo1:
            x: float
            y: float
            z: float = 0.1

        foo0 = Foo1(1, 2)
        self.assertEqual(foo0.x, 1)
        self.assertEqual(foo0.y, 2)
        self.assertEqual(foo0.z, 0.1)
    """

    def wrapper(*args, _entry=None, _parent=None, **kwargs):
        keys = [*typing.get_type_hints(cls).keys()]

        n_cls = _make_sptree(cls, **metadata)

        for idx, value in enumerate(args):
            key = keys[idx]
            if kwargs.get(key, _not_found_) is not _not_found_:
                raise KeyError(f"Redefined argument '{key}'!")
            kwargs[key] = value

        return n_cls(kwargs, _entry, _parent)

    if cls is None:
        return lambda c: sp_dataclass(c, **metadata)
    else:
        return wrapper
