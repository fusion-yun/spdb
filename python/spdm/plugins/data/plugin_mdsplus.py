import collections
import os
import typing

import numpy as np
from spdm.core.collection import Collection
from spdm.core.entry import Entry
from spdm.core.file import File
from spdm.utils.logger import logger
from spdm.utils.uri_utils import URITuple
from spdm.utils.tags import _not_found_

try:
    import MDSplus as mds
except ModuleNotFoundError as error:
    logger.error(f"Can not load MDSplus", exc_info=error)


@File.register(["mdsplus", "mds", "mds+"])
class MDSplusTree(File):
    MDS_MODE = {
        File.Mode.read: "ReadOnly",
        File.Mode.write: "Normal",
        File.Mode.read | File.Mode.write: "Normal",
        File.Mode.read | File.Mode.write | File.Mode.create: "Edit",
        File.Mode.write | File.Mode.create: "New",
    }

    def __init__(
        self, *args, fid=None, shot: typing.Optional[int] = None, tree_name: typing.Optional[str] = None, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self._envs = {}
        # {k: (v if not isinstance(v, slice) else f"{v.start}:{v.stop}:{v.step}")
        #   for k, v in self._envs.items()}

        query = self.url.query or {}

        self._mds_mode = MDSplusTree.MDS_MODE[self.mode]

        path = self.url.path.rstrip("/")

        if self.url.authority != "":
            path = f"{self.url.authority}::{path}"

        if self.url.protocol in ("ssh"):
            path = f"{self.url.protocol}://" + path

        if len(path) == 0:
            path = None

        self._default_tree_path = path

        if tree_name is None:
            tree_name = query.get("tree_name", None)

        self._old_env = {}

        if tree_name is None:
            self._default_tree_name = None
        elif self._default_tree_path is not None:
            tree_name = tree_name.split(",")
            self._default_tree_name = tree_name[0]
            for p in tree_name:
                env_path = f"{p}_path"
                if env_path in os.environ:
                    self._old_env[env_path] = os.environ[env_path]
                    os.environ[f"{p}_path"] = f"{path}:{self._old_env[env_path]}"
                else:
                    self._old_env[env_path] = None
                    os.environ[f"{p}_path"] = path

        self._shot = shot if shot is not None else (fid if fid is not None else query.get("shot", self.url.fragment))

        self._trees = {}

        self._entry = MDSplusEntry(self)

    def __del__(self):
        # del self._trees
        for k, tree in self._trees.items():
            tree.close()
            logger.debug(f"Close MDS Tree:{k}")

        self._trees = {}

        for k, v in self._old_env.items():
            if v is None:
                del os.environ[k]
            else:
                os.environ[k] = v

    @property
    def entry(self, lazy=True) -> Entry:
        return self._entry

    def get_tree(
        self,
        tree_name: typing.Optional[str] = None,
        tree_path: typing.Optional[str] = None,
    ):
        if tree_name is None:
            tree_name = self._default_tree_name

        if tree_name in self._trees:
            return self._trees[tree_name]

        mode = self._mds_mode

        shot = int(self._shot) if isinstance(self._shot, str) else self._shot

        if tree_path is None:
            tree_path = self._default_tree_path

        try:
            tree = mds.Tree(tree_name, shot, mode=mode, path=tree_path)
        except mds.mdsExceptions.TreeFOPENR as error:
            raise FileNotFoundError(
                f"Can not open mdsplus tree! tree_name={tree_name} shot={shot} tree_path={tree_path} mode={mode} \n {error}"
            )
        except mds.mdsExceptions.TreeNOPATH as error:
            raise FileNotFoundError(f"{tree_name}_path is not defined! tree_name={tree_name} shot={shot}  \n {error}")
        else:
            logger.debug(f"Open MDSplus Tree [{tree_name}] shot={shot}")

        self._trees[tree_name] = tree

        return tree

    def query(self, request, prefix=None, **kwargs) -> typing.Any:
        if request is None:
            return _not_found_

        if isinstance(request, str):
            request = {"query": request}

        request = collections.ChainMap(request, kwargs)

        # elif isinstance(request, collections.abc.Mapping):

        tree_name = request.get("@tree", self._default_tree_name)
        tree_path = request.get("@tree_path", None)

        tdi = request.get("query", None) or request.get("@text", None)

        if not tdi:
            raise RuntimeError(f"Illegal request {request}")

        try:
            tdi = tdi.format_map(self._envs)
        except KeyError as error:
            raise KeyError(f"Can not format tdi! {error} tdi={tdi} envs={self._envs} prefix={prefix}")

        res = None
        tree = self.get_tree(tree_name, tree_path)
        try:
            res = tree.tdiExecute(tdi).data()
        except mds.mdsExceptions.TdiException as error:
            # raise RuntimeError(f"MDSplus TDI error [{tdi}]! {error}")
            logger.warning(f'MDS TDI error! tree_name={tree_name} shot={self._shot} tdi="{tdi}" \n {error}')

        except mds.mdsExceptions.TreeNODATA as error:
            logger.warning(f'MDS No data! tree_name={tree_name} shot={self._shot} tdi="{tdi}" \n {error}')

        except Exception as error:
            raise RuntimeError(f'mds.mdsExceptions! tree_name={tree_name} shot={self._shot} tdi="{tdi}"') from error
            # raise error

        if not isinstance(res, np.ndarray):
            pass
        elif len(res.shape) == 2:
            if res.shape[1] == 1:
                res = res[:, 0]
            elif res.shape[0] == 1:
                res = res[0]
            else:
                res = res.transpose(1, 0)
        return res

    def update(self, *args, envs=None, **kwargs):
        raise NotImplementedError()


@Collection.register(["mdsplus", "mds", "mds+", "MDSplus"])
class MDSplusCollection(Collection):
    def insert_one(self, fid=None, *args, query=None, mode=None, **kwargs):
        fid = fid or self.guess_id(*args, **collections.ChainMap((query or {}), kwargs)) or self.next_id
        return MDSplusTree(self.url, fid=fid, mode=mode or "w", **kwargs)

    def search_one(self, predicate, projection=None, only_one=False, **kwargs) -> Entry:
        fid = self.guess_id(predicate, **kwargs)
        entry = self._mapping(MDSplusTree(self.url, fid=fid, **kwargs).entry)
        if projection is None:
            return entry
        else:
            return entry.find(projection)

    def count(self, predicate=None, *args, **kwargs) -> int:
        return NotImplemented()

    # def search_one(self, predicate: Document,  projection: Document = None, *args, **kwargs):
    #     shot = getitem(predicate, "shot", None) or getitem(predicate, "_id", None)
    #     if shot is not None:
    #         return MDSplusEntry(self._tree_name, shot, mode="r") .find(projection)
    #     else:
    #         for shot in self._foreach_shot():
    #             res = MDSplusEntry(self._tree_name, shot, mode="r").find_if(
    #                 projection, predicate)
    #             if res is not None:
    #                 return res
    #     return None

    # def _foreach_shot(self):
    #     f_prefix = f"{self._tree_name.lower()}_"
    #     f_prefix_l = len(f_prefix)
    #     glob = f"{f_prefix}*.tree"
    #     for fp in self._path.glob(glob):
    #         yield fp.stem[f_prefix_l:]

    # def search(self, predicate: Document = None, projection: Document = None, *args, **kwargs):

    #     for shot in self._foreach_shot():
    #         res = MDSplusEntry(self._tree_name, shot, mode="r").find_if(projection, predicate)
    #         logger.debug(res)

    #         if res is not None:
    #             yield res

    # def insert_one(self, document: Document, *args, **kwargs):
    #     self._count += 1

    #     shot = int(document.get("shot", self._count))

    #     MDSplusEntry(self._tree_name, shot, mode="x").update(document)

    #     return shot


@Entry.register(["mdsplus", "mds"])
class MDSplusEntry(Entry):
    def __init__(self, cache: MDSplusTree | str | URITuple, *args, **kwargs):
        if isinstance(cache, (str, URITuple)):
            cache: MDSplusTree = MDSplusTree(cache)
        if not isinstance(cache, MDSplusTree):
            raise TypeError(f"cache must be MDSplusEntry or str, but got {type(cache)}")
        super().__init__(cache, *args, **kwargs)

    def find(self, request, *args, **kwargs):
        return self._data.query(request, *args, prefix=self._path, **kwargs)

    def update(self, *args, **kwargs):
        return self._data.update(*args, prefix=self._path, **kwargs)

    def search(self, *args, **kwargs):
        yield from self._data.search(*args, prefix=self._path, **kwargs)


def open_mdstree(tree_name, shot, mode="NORMAL", path=None):
    if tree_name is None:
        raise ValueError(f"Treename is empty!")
    try:
        shot = int(shot)
        logger.info(f"Open MDSTree: tree_name={tree_name} shot={shot} mode=\"{mode}\" path='{path}'")
        tree = mds.Tree(tree_name, shot, mode=mode, path=path)
    except mds.mdsExceptions.TreeFOPENR as error:
        # tree_path = os.environ.get(f"{tree_name}_path", None)
        raise FileNotFoundError(
            f"Can not open mdsplus tree! tree_name={tree_name} shot={shot} tree_path={path} mode={mode} \n {error}"
        )
    except mds.mdsExceptions.TreeNOPATH as error:
        raise FileNotFoundError(f"{tree_name}_path is not defined! tree_name={tree_name} shot={shot}  \n {error}")
    return tree


