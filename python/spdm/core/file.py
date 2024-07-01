from __future__ import annotations

from spdm.utils.uri_utils import uri_split

from spdm.core.document import Document
from spdm.core.path import as_path


class File(Document, plugin_name="file"):
    """
    File like object
    """

    _plugin_prefix = "spdm.plugins.data."

    def __new__(cls, uri, *args, _plugin_name=None, **kwargs):
        if cls is not File.Entry and _plugin_name is not None:
            return super().__new__(cls, _plugin_name=_plugin_name)
        uri = uri_split(uri)

        if uri.protocol in ["", "file"]:
            ext = as_path(uri.path)[-1].rsplit(".", maxsplit=1)[-1]
            _plugin_name = f"file+{ext}"
        elif uri.protocol.startswith("file+"):
            _plugin_name = uri.protocol
        else:
            raise RuntimeError(f"Invalid protocol '{uri.protocol}'!")

        return super().__new__(cls, _plugin_name=_plugin_name)

    def __init_subclass__(cls, *args, plugin_name=None, **kwargs) -> None:
        if plugin_name is not None:
            if not isinstance(plugin_name, list):
                plugin_name = [plugin_name]

            plugin_name = [f"file+{p}" for p in plugin_name]

        return super().__init_subclass__(*args, plugin_name=plugin_name, **kwargs)
