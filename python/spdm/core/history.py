""" WithHistory 类的定义"""

import abc
import typing
from copy import deepcopy
import numpy as np

from spdm.utils.tags import _not_found_

from spdm.core.path import Path
from spdm.core.entry import Entry, as_entry


class WithHistory(abc.ABC):
    """循环记录状态树的历史改变"""

    _DEFALUT_CACHE_DEEPTH = 4

    def __init__(self, *args, history: list | Entry = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._history: Entry = as_entry(history)

    time: float = 0.0

    def flush(self):
        """复制当前状态，并写入历史记录"""
        self._history.append(deepcopy(super().__getstate__()))

    def previous(self) -> typing.Generator[typing.Self, None, None]:
        depth = len(self._history)
        for shift in range(1, depth):
            cache_cursor = (self._history_cursor - shift + depth) % depth
            obj = object.__new__(self.__class__)
            obj.__setstate__(self._history[cache_cursor])
            if (entry := getattr(self, "_entry", None)) is not None:
                parent = entry.parent
                obj._entry = parent.child(entry._path[-1] - shift)

            yield obj

    def history(self, time: float) -> typing.Self:
        if time is None or np.isclose(time, self.time):
            return self
        elif time > self.time:
            raise RuntimeError(f"Can not get future slice at time={time}. ")

        depth = len(self._history)
        for shift in range(depth):
            history_cursor = (self._history_cursor - shift + depth) % depth
            cache_time = Path([history_cursor, "time"]).get(self._history, _not_found_)
            if cache_time is _not_found_:
                continue
            elif time > cache_time:
                raise RuntimeError(f"Can not get past slice at time={time}. ")
        else:
            history_cursor = (self._history_cursor + depth) % depth
            new_obj = object.__new__(self.__class__)
            new_obj.__setstate__(self._history[history_cursor])
            new_obj._history = self._history
            new_obj._history_cursor = history_cursor
            new_obj.time = time

        return new_obj

    def advance(self, dt: float = None, time: float = None, new_state: dict = None) -> typing.Self:
        """移动到指定时间片"""

        self.flush()
        if time is not None:
            pass
        elif dt is not None:
            time = self.time + dt
        elif isinstance(new_state, dict):
            time = new_state.get("time", None)

        if time is None:
            raise RuntimeError("Time is not specified. ")
        elif time < self.time:
            raise RuntimeError(f"Can not move to past time. {time}<{self.time}")

        self._history_cursor = (self._history_cursor + 1) % len(self._history)

        super().__setstate__(new_state)

        self.time = time

        return self

    def find(self, *args, time=None, **kwargs):
        if time is None or np.isclose(time, self.time):
            return super().find(*args, **kwargs)
        else:
            return self.history(time).find(*args, **kwargs)

    def update(self, *args, time=None, **kwargs):
        if time is None or np.isclose(time, self.time):
            return super().update(*args, **kwargs)
        else:
            return self.advance(time - self.time).update(*args, **kwargs)

    def insert(self, *args, time=None, **kwargs):
        if time is None or np.isclose(time, self.time):
            return super().insert(*args, **kwargs)
        else:
            return self.advance(time - self.time).update(*args, **kwargs)

    def delete(self, *args, time=None, **kwargs) -> None:
        if time is None or np.isclose(time, self.time):
            super().delete(*args, **kwargs)
        elif len(args) + len(kwargs) > 0:
            self.history(time).delete(*args, **kwargs)
        else:
            idx = self._find_by_time(time)
            if idx is not None:
                self._history[idx] = _not_found_

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
