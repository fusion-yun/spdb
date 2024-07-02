from __future__ import annotations
from spdm.utils.uri_utils import uri_split

from spdm.core.document import Document
from spdm.core.path import as_path


class File(Document):
    """
    File like object
    """

    _plugin_prefix = Document._plugin_prefix + "file_"

    def __new__(cls, uri, *args, format=None, **kwargs):
        if isinstance(format, str) and format.startswith("file+"):
            format = format[5:]
        if format == "file":
            format = None
            
        if cls is not File or format is not None:
            return super().__new__(cls, _plugin_name=format)

        if format is None:
            uri = uri_split(uri)
            format = uri.protocol
            if format in ["", "file"]:
                ext = as_path(uri.path)[-1].rsplit(".", maxsplit=1)[-1]
                format = ext

        if format.startswith("file+"):
            format = format[5:]

        return super().__new__(cls, *args, _plugin_name=format, **kwargs)

    # def __init_subclass__(cls, *args, plugin_name=None, **kwargs) -> None:
    #     if plugin_name is not None:
    #         if not isinstance(plugin_name, list):
    #             plugin_name = [plugin_name]

    #         plugin_name = [f"file+{p}" for p in plugin_name]

    #     return super().__init_subclass__(*args, plugin_name=plugin_name, **kwargs)
