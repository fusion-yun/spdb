""" WithHistory 类的定义"""

import abc
import typing
from copy import deepcopy
import numpy as np

from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger
from spdm.core.path import Path
from spdm.core.entry import Entry, as_entry
from spdm.core.sp_tree import annotation


class WithTime(abc.ABC):
    """循环记录状态树的历史改变"""

    _DEFALUT_CACHE_DEEPTH = 4

    def __init__(self, *args, history=_not_found_, **kwargs):
        super().__init__(*args, **kwargs)

        if getattr(self, "_entry", None) is not None:
            history_entry = self._entry.child(["time_slice"])

            time = Path(["time"]).get(self._cache, _not_found_)

            if time is not _not_found_:
                entry = history_entry.child([{"time": time}])
            else:
                entry = history_entry.child([-1])

            if entry.exists:
                self._entry = entry
                self._history = as_entry([history, history_entry])
            else:
                self._history = as_entry(history)
        else:
            self._history = as_entry(history)

    time: float = annotation(input=True, output=True, default_value=0.0)

    def __hash__(self) -> int:
        return hash(tuple([self.time, super().__hash__()]))

    def flush(self):
        """复制当前状态，并写入历史记录"""
        self._history.append(super().__getstate__())

    @property
    def previous(self) -> typing.Self:
        if self._history.count == 0:
            return None
        else:
            self._parent.__as_node__(None, type_hint=self.__class__, _entry=self._history.child([-1]))

    def history(self) -> typing.Generator[typing.Self, None, None]:

        for idx in range(self._history.count - 1, -1, -1):
            yield self._parent.__as_node__(None, type_hint=self.__class__, _entry=self._history.child([idx]))

    def at(self, time: float) -> typing.Self:
        if np.isclose(time, self.time):
            return self
        elif time > self.time:
            raise KeyError(f"Can not get future state time={time}. ")
        else:
            return self._parent.__as_node__(
                None, type_hint=self.__class__, _entry=self._history.child({"time": time})
            )

    def refresh(self, *args, time=None, **kwargs) -> None:
        prev_hash = hash(self)

        if time is not None:
            self.time = time

        super().refresh(*args, time=self.time, **kwargs)

        if prev_hash != hash(self):
            self.flush()

    def find(self, *args, time: float = _not_found_, **kwargs):
        if time is _not_found_ or np.isclose(time, self.time):
            return super().find(*args, **kwargs)
        else:
            return self.at(time).find(*args, **kwargs)

    def update(self, *args, time: float = _not_found_, **kwargs):
        if time is _not_found_ or time >= self.time:
            return super().update(*args, time=time, **kwargs)
        else:
            self._history.child({"time": time}).update(*args, **kwargs)

    def insert(self, *args, time: float = _not_found_, **kwargs):
        if time is _not_found_ or np.isclose(time, self.time):
            super().insert(*args, **kwargs)
        elif time > self.time:
            self.advance(*args, time=time, **kwargs)
        else:
            self._history.child({"time": time}).insert(*args, **kwargs)

    def delete(self, *args, time=None, **kwargs) -> None:
        if time is None or np.isclose(time, self.time):
            super().delete(*args, **kwargs)
        elif time > self.time:
            logger.warning("Try to delete future slice time={time}")
        else:
            self._history.child({"time": time}).delete(*args, **kwargs)

    def __as_node__(self, key, *args, **kwargs) -> typing.Self:
        node = super().__as_node__(key, *args, **kwargs)
        if isinstance(node, WithTime) and (node._history is None):
            node._history = self._history.child(key)
        return node  # type:ignore

    def _find_by_time(self, time: float) -> int:
        # TODO: 时间片插值

        if time is not None:
            pass
        elif len(self._cache) > 0:
            return self[-1]
        else:
            return _not_found_

        time_coord = getattr(self, "_time_coord", _not_found_)

        # if time_coord is _not_found_:
        #     time_coord = self._metadata.get("coordinate1", _not_found_)

        if isinstance(time_coord, str):
            time_coord = self.get(time_coord, default_value=_not_found_)
            if time_coord is None:
                time_coord = self._entry.child(time_coord).find()

        self._time_coord = time_coord

        pos = None

        if isinstance(time_coord, np.ndarray):
            indices = np.where(time_coord < time)[0]
            if len(indices) > 0:
                pos = indices[-1] + 1
                time = time_coord[pos]

        elif self._entry is not None:
            pos = self._entry_cursor or 0

            while True:
                t_time = self._entry.child(f"{pos}/time").get()

                if t_time is _not_found_ or t_time is None or t_time > time:
                    time = None
                    break
                elif np.isclose(t_time, time):
                    time = t_time
                    break
                else:
                    pos = pos + 1

        return pos
