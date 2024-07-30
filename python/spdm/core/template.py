import collections
import functools
import inspect
import re
import os
import typing

from ..utils.tags import _not_found_

from .htree import Dict, HTreeNode
from .path import Path


class Template(Dict):
    """
    SpBag with template support
    """

    OP_TAG = "$op"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def env(self, p):
        return Path(p).get(os.environ)

    def this(self, p):
        return Path(p).get(self)

    def find_handler(self, tag):
        handler = None
        if isinstance(self._parent, HTreeNode):
            handler = self._parent.get(tag, None)

        if handler is None and isinstance(tag, str):
            handler = getattr(self._parent, tag) or getattr(self, tag)

        return handler

    def handle_template_n(self, value, *args, **kwargs):
        if not isinstance(value, str):
            handle = self.find_handler(type(value)) or self.find_handler(None)
            if handle is not None:
                value = handle(value, *args, **kwargs)

        if not isinstance(value, str):
            return value, 0

        def _parser(o, message, *_args, **_kwargs):
            ops = message[2:-1].split(":", 1)
            if len(ops) == 1:
                res = Path(ops[0].split(".")).get(o, _not_found_)
                if res is _not_found_:
                    raise LookupError(f"Can not find {ops[0]}")
            else:
                handler = o.find_handler(ops[0])
                if handler is None:
                    raise LookupError(ops[0])
                res = handler(ops[1], *_args, **_kwargs)
            if not isinstance(res, str):
                res = o.handle(res, *_args, **_kwargs)
            return str(res)

        count = 0
        while True:
            value, num = re.subn(
                r"\$\{([^\$\{\}]+)\}",
                lambda _m, _o=self, _args=args, _kwargs=kwargs, _parser=_parser: _parser(
                    _o, _m.group(0), *_args, **_kwargs
                ),
                value,
            )
            if num == 0 or count > 10:
                break
            else:
                count += num

        if count >= 10:
            raise RuntimeError(f"Recursive template replace too much times {value}")

        return value, count

    def handle_template(self, value, *args, **kwargs):
        value, n = self.handle_template_n(value, *args, **kwargs)
        return value

    def handle_object_n(self, value, *args, **kwargs):
        ops = {}
        count = 0
        if isinstance(value, collections.abc.Mapping):
            ops = value.get(Template.OP_TAG, None)
            if ops is None:
                ops = {}
                value = {k: v for k, v in value.items() if not (isinstance(k, str) and k.startswith("$"))}
            elif not isinstance(ops, collections.abc.Mapping):
                ops = {ops: []}

        for op_name, a in ops.items():
            handle = self.find_handler(op_name)
            if handle is not None:
                value = handle(value, *a, *args, **kwargs)
                count += 1

        return value, count

    def handle_object(self, value, *args, **kwargs):
        value, n = self.handle_object_n(value, *args, **kwargs)
        return value

    def handle_n(self, value, *args, **kwargs):
        if value is _not_found_:
            return value, 0

        count = 0
        if isinstance(value, str) or not isinstance(value, collections.abc.Sequence):
            # handle non-dict node, i.e. string,int,float,bool...
            value, num = self.handle_template_n(value, *args, **kwargs)
            count += num

        if isinstance(value, collections.abc.Mapping):
            # handle dict or list
            value, num = self.handle_object_n(value, *args, **kwargs)
            count += num

        return value, count

    def handle(self, value, *args, **kwargs):
        count = 0
        num = 1
        while num > 0 and count < 255:
            value, num = self.handle_n(value, *args, **kwargs)
            count += num
        if count >= 255:
            raise RuntimeError(f"Rescurive call template replace too musch times! {value}")

        return value

    def apply(self, d: typing.Dict, *args, **kwargs):
        if d is None or len(d) == 0:
            return d
        res = []
        stack = [(d, res)]

        while len(stack) > 0:
            cursor, parent = stack.pop()
            value = _not_found_

            if isinstance(cursor, (collections.abc.Mapping,)):
                stack.append((cursor, parent))
                stack.append((iter(cursor.items()), {}))
            elif isinstance(cursor, collections.abc.Sequence) and not isinstance(cursor, str):
                stack.append((cursor, parent))
                stack.append((iter(cursor), []))
            elif hasattr(cursor, "__next__"):
                n_iter = cursor
                try:
                    cursor = next(n_iter)
                except StopIteration:
                    value = parent
                    cursor, parent = stack.pop()
                else:
                    stack.append((n_iter, parent))
                    stack.append((cursor, parent))
            else:
                value = cursor

            value = self.handle(value, *args, **kwargs)

            if value is _not_found_:
                pass
            elif isinstance(parent, collections.abc.Sequence):
                parent.append(value)
            elif isinstance(parent, collections.abc.Mapping):
                k, v = value
                parent.update({k: v})
            else:
                raise TypeError(f"type mismatch! {type(value)}")

        return res[0]

    def get(self, k, *args, **kwargs):
        return self.apply(super().get(k), *args, **kwargs)
