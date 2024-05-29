
import collections
import collections.abc
import copy
import inspect
import operator
import uuid
from .logger import logger

ELEMENT_TYPE_LIST = [int, float, str]

try:
    import numpy
except Exception:
    pass
else:
    ELEMENT_TYPE_LIST = ELEMENT_TYPE_LIST+[numpy.ndarray]


class LazyProxyHandler:
    @classmethod
    def put(cls, obj, path, value, *args, **kwargs):
        for p in path[:-1]:
            if type(p) is str and hasattr(obj, p):
                obj = getattr(obj, p)
            elif p in obj:
                obj = obj[p]
            else:
                obj[p] = {}
                obj = obj[p]
        if isinstance(path[-1], str) and hasattr(obj, path[-1]):
            setattr(obj, path[-1], value)
        else:
            obj[path[-1]] = value

        # if len(path) > 0:
        #     raise path

        return None

    @classmethod
    def get(cls, obj, path, *args, **kwargs):
        for idx, p in enumerate(path):
            if type(p) is str and hasattr(obj, p):
                obj = getattr(obj, p)
            else:
                if hasattr(obj.__class__, "__getitem__"):
                    obj = obj[p]
                elif isinstance(p, int) and p == 0:
                    pass
                else:
                    raise KeyError(path[:idx]+[p])

                # try:
                #     obj = obj[p]
                # except IndexError:
                #     raise KeyError(path)
                # except TypeError:
                #     raise KeyError(path)
        return obj

    @classmethod
    def get_value(cls, obj, path, *args, **kwargs):
        return cls.get(obj, path, *args, **kwargs)

    @classmethod
    def delete(cls, obj, path, *args, **kwargs):
        if len(path) > 1:
            obj = cls.get(obj,  path[:-1], *args, **kwargs)

        if hasattr(obj, path[-1]):
            delattr(obj, path[-1])
        else:
            del obj[path[-1]]

    @classmethod
    def push_back(cls, obj,  path, value, *args, **kwargs):
        if len(path) > 0:
            obj = cls.get_value(obj, path[:-1]).setdefault(path[-1], [])
        obj.append(value)
        return path+[len(obj)-1]

    @classmethod
    def count(cls, obj,  path, *args, **kwargs):
        obj = cls.get(obj, path, *args, **kwargs)
        return len(obj)

    @classmethod
    def resize(cls, obj,  path, *args, **kwargs):
        obj = cls.get(obj, path, *args, **kwargs)
        return len(obj)

    @classmethod
    def contains(cls, obj,  path, v, *args, **kwargs):
        obj = cls.get(obj, path, *args, **kwargs)
        return v in obj

    @classmethod
    def call(cls, obj, path, *args, **kwargs):
        obj = cls.get(obj, path)
        if callable(obj):
            return obj(*args, **kwargs)
        elif len(args)+len(kwargs) == 0:
            return obj
        else:
            raise TypeError(f"{obj.__class__.__name__} is not callable")

    @classmethod
    def iter(cls, obj, path, *args, **kwargs):
        for o in cls.get(obj, path, *args, **kwargs):
            if type(o) in ELEMENT_TYPE_LIST:
                yield o
            else:
                yield LazyProxy(o)


class LazyProxy:
    """ This is a lazy proxy to __getattr__ and __getitem__.
        The attribute operator (__getattr__) or index operator (__getitem__) of object is
        cached and chained as a path. Real value is only fetched when object is actually used.
        * inspired by lazy_object_proxy
        Example:
            >>> obj = {}
            >>> obj_proxy = LazyProxy(obj)
            >>> obj_proxy.e.f.d = "hello World"
            >>> self.assertEqual(obj, {"e": {"f": {"d": "hello World"}}})

        Example:
            >>> obj = {"a": {"b": {"f": 5, "c": {"d": [1, 2, 3, 4, 5]}}},
                "msg": "hello World"}

            >>> obj_proxy = LazyProxy(obj)

            >>> self.assertEqual(obj_proxy.a.b.c.d[1:5], obj["a"]["b"]["c"]["d"][1:5])
            >>> self.assertEqual(obj_proxy.a["b.c.d"][1:5],obj["a"]["b"]["c"]["d"][1:5])
            >>> self.assertEqual(obj_proxy["a.b.c.d[:]"], obj["a"]["b"]["c"]["d"][1:5])
            >>> self.assertEqual(obj_proxy.a.b.f*3, obj["a"]["b"]["f"]*3)

                equilibrium.time_slice[0].profiles_2d[0].psi[:,:] =>   PROFILES[0].PSIRZ[0,:,:]
                equilibrium.time_slice[:].profiles_2d[1].psi[:,:] =>   PROFILES[1].PSIRZ[:,:,:]

                [
                    {psi:345.7, a:1},
                    {psi:5.68,  a:4}
                ]
                =>
                {
                    psi:[345.7,5.678],
                    a  :[1,4]
                }

        Example:
            >>>   class Foo:
                __slots__ = 'a', 'b'

            >>> obj = Foo()
            >>> obj.a = [1, 2, 3, 4, 5]
            >>> obj.b = {"a": {"b": {"f": 5, "c": {"d": [1, 2, 3, 4, 5]}}},
                    "msg": "hello World"}
            >>> obj_proxy = LazyProxy(obj)

            >>> self.assertEqual(obj_proxy["a"][0]*3, obj.a[0]*3)
            >>> self.assertEqual(obj_proxy.b.a.b.c.d[1:5], obj.b["a"]["b"]["c"]["d"][1:5])

        TODO: support add/append
    """
    __slots__ = "__object__", "__path__", "__level__", "__handler__"

    DELIMITER = '.'

    @staticmethod
    def wrap(obj, handler=None, **kwargs):
        if handler is None and hasattr(obj.__class__, "__lazy_proxy__"):
            handler = obj.__class__.__lazy_proxy__

        if isinstance(handler, LazyProxyHandler) or inspect.isclass(handler):
            return handler
        elif isinstance(handler, (type(None), collections.abc.Mapping)):
            handler = collections.ChainMap(handler or {}, kwargs)
        elif inspect.isfunction(handler):
            handler = collections.ChainMap({"get": handler}, kwargs)
        else:
            raise TypeError(f"illegal ops type {type(handler)}!")

        n_cls = type(
            f"wrapped_{obj.__class__.__name__}_{uuid.uuid1().hex}",
            (LazyProxyHandler,),
            {k: classmethod(op) for k, op in handler.items()}
        )
        return n_cls()

    def __init__(self,   *args,    **kwargs):
        self.__reset__(*args, **kwargs)

    def __reset__(self, obj, prefix=[], *args, level=-1, handler=None, **kwargs):
        if prefix is None:
            prefix = []
        elif self.__class__.DELIMITER is not None and type(prefix) is str:
            prefix = prefix.split(self.__class__.DELIMITER)
        elif not isinstance(prefix, list):
            prefix = [prefix]

        if isinstance(obj, LazyProxy):
            object.__setattr__(self, "__object__",
                               object.__getattribute__(obj, "__object__"))
            object.__setattr__(self, "__path__",
                               object.__getattribute__(obj, "__path__")+prefix)
            object.__setattr__(self, "__level__",
                               object.__getattribute__(obj, "__level__")-1)
            object.__setattr__(self, "__handler__",
                               object.__getattribute__(obj, "__handler__")
                               if handler is None and len(kwargs) == 0 else LazyProxy.wrap_handler(obj, handler, **kwargs))

        else:
            object.__setattr__(self, "__object__", obj)
            object.__setattr__(self, "__path__", prefix)
            object.__setattr__(self, "__level__", level)
            object.__setattr__(self, "__handler__",  LazyProxy.wrap(obj, handler, **kwargs))

    def __fetch__(self):
        obj = object.__getattribute__(self, "__object__")
        path = object.__getattribute__(self, "__path__")
        handler = object.__getattribute__(self, "__handler__")

        if len(path) == 0:
            pass
        else:
            try:
                obj = handler.get(obj, path)
            except KeyError:
                raise KeyError(f"Unsolved path '{path}'")
            else:
                object.__setattr__(self, "__path__", [])
                object.__setattr__(self, "__object__", obj)

        return obj

    def __push_back__(self, v=None):
        obj = object.__getattribute__(self, "__object__")
        path = object.__getattribute__(self, "__path__")
        handler = object.__getattribute__(self, "__handler__")
        new_path = handler.push_back(obj, path, v)
        return LazyProxy(obj, prefix=new_path, handler=handler)

    def __pop_back__(self):
        obj = object.__getattribute__(self, "__object__")
        path = object.__getattribute__(self, "__path__")
        handler = object.__getattribute__(self, "__handler__")
        return handler.pop_back(obj, path)

    def __real_value__(self):
        obj = object.__getattribute__(self, "__object__")
        path = object.__getattribute__(self, "__path__")
        handler = object.__getattribute__(self, "__handler__")
        return handler.get_value(obj, path)

    def _value_(self):
        res = self.__real_value__()
        if isinstance(res, collections.abc.Mapping):
            return LazyProxy(res)
        else:
            return res

    def __do_get__(self, idx):
        res = LazyProxy(self, idx)
        return res.__fetch__() if self.__level__ == 0 else res

    def __do_set__(self, idx, value):
        object.__getattribute__(self, "__handler__").put(
            object.__getattribute__(self, "__object__"),
            object.__getattribute__(self, "__path__")+[idx],
            value
        )

    def __do_del__(self, idx):
        object.__getattribute__(self, "__handler__").delete(
            object.__getattribute__(self, "__path__")+[idx]
        )

    def __getitem__(self, idx):
        return self.__do_get__(idx)

    def __setitem__(self, idx, value):
        self.__do_set__(idx, value)

    def __delitem__(self, idx):
        self.__do_del__(idx)

    def __getattr__(self, idx):
        return self.__do_get__(idx)

    def __setattr__(self, idx, value):
        self.__do_set__(idx, value)

    def __delattr__(self, idx):
        self.__do_del__(idx)

    def __deepcopy__(self, memo=None):
        handler = object.__getattribute__(self, "__handler__")
        return LazyProxy(copy.deepcopy(self.__fetch__()),    handler=handler)

    def __copy__(self):
        handler = object.__getattribute__(self, "__handler__")
        return LazyProxy(copy.copy(self.__fetch__()),   handler=handler)

    # def __getslice__(self, i, j):
    #     return self.__do_get__(slice(i, j))

    # def __setslice__(self, i, j, value):
    #     self.__do_set__(slice(i, j), value)

    # def __delslice__(self, i, j):
    #     self.__do_del__(slice(i, j))

    def __iter__(self):
        return object.__getattribute__(self, "__handler__").iter(
            object.__getattribute__(self, "__object__"),
            object.__getattribute__(self, "__path__")
        )

    def __len__(self):
        return object.__getattribute__(self, "__handler__").count(
            object.__getattribute__(self, "__object__"),
            object.__getattribute__(self, "__path__")
        )

    def __resize__(self, *args, **kwargs):
        return object.__getattribute__(self, "__handler__").resize(
            object.__getattribute__(self, "__object__"),
            object.__getattribute__(self, "__path__"),
            * args, **kwargs)

    def __contains__(self, value):
        return object.__getattribute__(self, "__handler__").contains(
            object.__getattribute__(self, "__object__"),
            object.__getattribute__(self, "__path__"),
            value
        )

    def __call__(self, *args, **kwargs):

        res = self.__fetch__()
        if callable(res):
            return res(*args, **kwargs)
        else:
            return res
        # return object.__getattribute__(self, "__handler__").call(
        #     object.__getattribute__(self, "__object__"),
        #     object.__getattribute__(self, "__path__"),
        #     *args, **kwargs
        # )

    ###############################################################
    # from lazy_object_proxy

    # @property
    # def __name__(self):
    #     return self.__fetch__().__name__

    # @__name__.setter
    # def __name__(self, value):
    #     self.__fetch__().__name__ = value

    # @property
    # def __class__(self):
    #     return self.__fetch__().__class__

    # @property
    # def __annotations__(self):
    #     return self.__fetch__().__anotations__

    # def __dir__(self):
    #     return dir(self.__fetch__())

    def __str__(self):
        return str(self.__fetch__())

    def __bytes__(self):
        return bytes(self.__fetch__())

    def __reversed__(self):
        return reversed(self.__fetch__())

    def __round__(self):
        return round(self.__fetch__())

    def __hash__(self):
        return hash(self.__fetch__())

    def __nonzero__(self):
        return bool(self.__fetch__())

    def __bool__(self):
        return bool(self.__fetch__())

    def __int__(self):
        return int(self.__fetch__())

    # if PY2:
    #     def __long__(self):
    #         return long(self.__fetch__())  # noqa

    def __float__(self):
        return float(self.__fetch__())

    def __oct__(self):
        return oct(self.__fetch__())

    def __hex__(self):
        return hex(self.__fetch__())

    def __index__(self):
        return operator.index(self.__fetch__())

    def __enter__(self):
        return self.__fetch__().__enter__()

    def __exit__(self, *args, **kwargs):
        return self.__fetch__().__exit__(*args, **kwargs)

    def __reduce__(self):
        return lambda p: p, (self.__fetch__(),)

    def __reduce_ex__(self, protocol):
        return lambda p: p, (self.__fetch__(),)


__op_list__ = ['abs', 'add', 'and',
               #  'attrgetter',
               'concat',
               # 'contains', 'countOf',
               'delitem', 'eq', 'floordiv', 'ge',
               # 'getitem',
               'gt',
               'iadd', 'iand', 'iconcat', 'ifloordiv', 'ilshift', 'imatmul', 'imod', 'imul',
               'index', 'indexOf', 'inv', 'invert', 'ior', 'ipow', 'irshift',
               #    'is_', 'is_not',
               'isub',
               # 'itemgetter',
               'itruediv', 'ixor', 'le',
               'length_hint', 'lshift', 'lt', 'matmul',
               #    'methodcaller',
               'mod',
               'mul', 'ne', 'neg', 'not', 'or', 'pos', 'pow', 'rshift',
               #    'setitem',
               'sub', 'truediv', 'truth', 'xor']


for name in __op_list__:
    op = getattr(operator, f"__{name}__", None)
    setattr(LazyProxy,  f"__{name}__",
            lambda s, r, __fun__=op: __fun__(s.__fetch__(), r))
    setattr(LazyProxy,  f"__r{name}__",
            lambda s, l, *args, __fun__=op, **kwargs: __fun__(l, s.__fetch__(), *args, **kwargs))
