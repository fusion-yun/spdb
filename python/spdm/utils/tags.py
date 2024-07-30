from enum import Flag, auto


class tags(Flag):
    not_found = 0
    undefined = auto()
    empty = auto()
    next_ = auto()


_not_found_ = ...

_undefined_ = tags.undefined

_next_ = tags.next_

_empty = tags.empty
