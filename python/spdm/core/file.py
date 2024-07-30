import typing
from spdm.utils.uri_utils import uri_split

from spdm.core.document import Document
from spdm.core.path import as_path


class File(Document, plugin_prefix="file_"):
    """
    File like object
    """

    def __new__(cls, uri, *args, kind=None, **kwargs) -> typing.Self:
        if isinstance(kind, str) and kind.startswith("file+"):
            kind = kind[5:]
        if kind == "file":
            kind = None

        if cls is not File or kind is not None:
            return super().__new__(cls, _plugin_name=kind)

        if kind is None:
            uri = uri_split(uri)
            kind = uri.protocol
            if kind in ["", "file"]:
                ext = as_path(uri.path)[-1].rsplit(".", maxsplit=1)[-1]
                kind = ext

        if kind.startswith("file+"):
            kind = kind[5:]

        return super().__new__(cls, *args, _plugin_name=kind, **kwargs)

    # def __init_subclass__(cls, *args, plugin_name=None, **kwargs) -> None:
    #     if plugin_name is not None:
    #         if not isinstance(plugin_name, list):
    #             plugin_name = [plugin_name]

    #         plugin_name = [f"file+{p}" for p in plugin_name]

    #     return super().__init_subclass__(*args, plugin_name=plugin_name, **kwargs)
