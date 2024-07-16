import typing
import numpy as np

from spdm.utils.logger import logger
from spdm.utils.tags import _not_found_

from spdm.core.entry import Entry
from spdm.core.htree import List
from spdm.core.path import Path
from spdm.core.sp_tree import SpTree, sp_property


class WithTime(SpTree):
    """循环记录记录状态树的历史改变"""

    time: float = sp_property(unit="s", default_value=0.0)  # type: ignore

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._history = []
        self._cache_cursor = 0
        self._cache_depth = 3

    def advance(self, time: float) -> typing.Self:
        """推进到下一个时间片"""
        assert time > self.time, f"{time} <= {self.time}"

        self.flush()
        self.time = time
        self._cache_cursor = (self._cache_cursor + 1) % self._cache_depth
        return self

    def flush(self):
        """将当前状态写入历史记录"""
        self._history[self._cache_cursor] = self.__getstate__()

    def previous(self) -> typing.Generator[typing.Self, None, None]:
        for shift in range(1, self._cache_depth):
            cache_cursor = (self._cache_cursor - shift + self._cache_depth) % self._cache_depth
            obj = object.__new__(self.__class__)
            obj.__setstate__(self._history[cache_cursor])
            yield obj


_TSlice = typing.TypeVar("_TSlice", bound=WithTime)


class TimeSequence(List[_TSlice]):
    """A series of time slices .

    用以管理随时间变化（time series）的一组状态（TimeSlice）。

    current:
        指向当前时间片，即为序列最后一个时间片吗。

    _TODO_
      1. 缓存时间片，避免重复创建，减少内存占用
      2. 缓存应循环使用
      3. cache 数据自动写入 entry 落盘
    """

    TimeSlice = _TSlice

    def __init__(self, *args, cache_depth=3, **kwargs):
        super().__init__(*args, **kwargs)

        self._entry_cursor = None
        self._cache_cursor = len(self._cache) - 1
        self._cache_depth = cache_depth

        if self._cache is _not_found_:
            self._cache = []

        if self._cache_cursor + 1 < self._cache_depth:
            self._cache += [_not_found_] * (self._cache_depth - self._cache_cursor - 1)
        else:
            self._cache_depth = self._cache_cursor + 1

    def __missing__(self, idx: int) -> _TSlice:
        """当循环队列满了或序号出界的时候调用
        :param o: 最老的 time_slice
        """
        return super().__missing__(idx)

    @property
    def time(self) -> float:
        return self.current.time

    @property
    def dt(self) -> float:
        return self._metadata.get("dt", 0.1)

    @property
    def current(self) -> _TSlice:
        return self.__get_node__(0)

    @property
    def previous(self) -> typing.Generator[_TSlice, None, None]:
        n = len(self._cache)
        for i in range(n - 2, -1, -1):
            yield self.__get_node__(i)

    def _find_by_time(self, time: float) -> _TSlice:
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

        return self.__get_node__(pos) if pos is not None else _not_found_

    def __get_node__(self, idx: int, entry=None, **kwargs) -> _TSlice:
        """获取时间片，若时间片不存在，则返回 _not_found_"""

        if not isinstance(idx, int):
            return super().__get_node__(idx, entry=entry, **kwargs)

        cache_cursor = (self._cache_cursor + idx + self._cache_depth) % self._cache_depth

        value = self._cache[cache_cursor]

        if entry is not None:
            pass
        elif not (value is _not_found_ or isinstance(value, WithTime)):
            if isinstance(self._entry, Entry) and self._entry_cursor is not None:
                # FIXME: 这里 entry_cursor 计算的不对
                entry_cursor = self._entry_cursor + idx
                entry = self._entry.child(entry_cursor)
            else:
                entry_cursor = 0

        return super().__as_node__(cache_cursor, value, entry=entry, **kwargs)

    def advance(self, *args, time: float, **kwargs) -> _TSlice:
        """推进到下一个时间片"""

        assert time > self.time, f"{time} <= {self.time}"

        if self._cache is _not_found_ or len(self._cache) == 0:
            self._cache = [_not_found_] * self._cache_depth

        cursor = (self._cache_cursor + 1) % self._cache_depth

        self._cache[cursor] = Path().update(_not_found_, *args, time=time, **kwargs)

        self._cache_cursor = cursor

        return self.__get_node__(-1)

    def fetch(self, *args, time: float, **kwargs) -> _TSlice:
        """返回 time 对应的时间片 _TSlice，默认返回 time_slice.current
        TODO: 当时间处于两个时间片之间时，对其插值
        """
        t_slice = self._find_by_time(time)
        if t_slice is _not_found_ or t_slice is None:
            raise RuntimeError(f"Can not find time silce at {time}")
        return t_slice.fetch(*args, **kwargs)
