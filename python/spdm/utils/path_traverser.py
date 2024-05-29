import functools

from .logger import logger
from .misc import normalize_path


class PathTraverser:
    MAX_SLICE_LENGTH = 10

    def __init__(self, path, *args, **kwargs):
        self._path = normalize_path(path)

    @property
    def is_multiple(self):
        return self._path != None and len(self._path) > 0 and functools.reduce(lambda a, b: a and b, [isinstance(p, slice) for p in self._path], True)

    def append(self, seg):
        self._path.append(seg)

    @property
    def path(self):
        return self._path

    def traverse(self,  visitor, prev=[], idx=0):
        res = None
        if self._path is None or idx >= len(self._path):
            res = visitor(prev)
        elif isinstance(self._path[idx], str) or isinstance(self._path[idx], int):
            res = self.traverse(visitor, prev+[self._path[idx]], idx+1)
        elif isinstance(self._path[idx], slice):
            start = self._path[idx].start or 0
            step = self._path[idx].step or 1
            stop = self._path[idx].stop
            if stop is not None:
                res = [self.traverse(visitor, prev+[sidx], idx+1) for sidx in range(start,  stop, step)]
            else:
                res = []
                count = 0
                while count < PathTraverser.MAX_SLICE_LENGTH:
                    try:
                        res.append(self.traverse(visitor, prev+[start], idx+1))
                    except StopIteration:
                        break
                    except IndexError:
                        break
                    count = count + 1
                    start = start+step
                if count >= PathTraverser.MAX_SLICE_LENGTH:
                    logger.warning("List length > {PathTraverser.MAX_SLICE_LENGTH}")

        return res

    def apply(self, visitor):
        res = self.traverse(visitor, [], 0)
        return res[0] if self.is_multiple else res

    def iter_traverse(self, prev=[], idx=0):
        if idx >= len(self._path):
            yield prev
        elif isinstance(self._path[idx], str) or isinstance(self._path[idx], int):
            yield from self.iter_traverse(prev+[self._path[idx]], idx+1)
        elif isinstance(self._path[idx], slice):
            start = self._path[idx].start or 0
            step = self._path[idx].step or 1
            stop = self._path[idx].stop
            if stop is not None:
                for sidx in range(start,  stop, step):
                    yield from self.iter_traverse(prev+[sidx], idx+1)
            else:
                res = []
                count = 0
                while count < PathTraverser.MAX_SLICE_LENGTH:
                    try:
                        yield from self.iter_traverse(prev+[start], idx+1)
                    except StopIteration:
                        break
                    except IndexError:
                        break
                    count = count + 1
                    start = start+step
                if count >= PathTraverser.MAX_SLICE_LENGTH:
                    logger.warning(f"Index > MAX_SLICE_LENGTH({PathTraverser.MAX_SLICE_LENGTH})! {prev+[start]}")

    def __iter__(self):
        yield from self.iter_traverse()
