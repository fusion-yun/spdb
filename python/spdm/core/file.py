from __future__ import annotations

import pathlib
import typing

from spdm.core.document import Document
from spdm.core.path import as_path

from spdm.utils.uri_utils import URITuple, uri_split
from spdm.utils.tags import _not_found_
from spdm.utils.logger import logger


class File(Document):
    """
    File like object
    """

    class Entry(Document.Entry, plugin_name=["file", "local"]):

        def __new__(cls, uri, *args, plugin_name=None, **kwargs):
            if cls is not File.Entry and plugin_name is not None:
                return super().__new__(cls, plugin_name=plugin_name)
            uri = uri_split(uri)

            if uri.protocol in ["", "local", "file"]:
                ext = as_path(uri.path)[-1].split(".")[-1]
                plugin_name = f"file_{ext}"

            return super().__new__(cls, plugin_name=plugin_name)

        def __init_subclass__(cls, *args, plugin_name=None, **kwargs) -> None:
            if plugin_name is not None:
                if not isinstance(plugin_name, list):
                    plugin_name = [plugin_name]

                plugin_name = [f"file_{p}" for p in plugin_name]

            return super().__init_subclass__(*args, plugin_name=plugin_name, **kwargs)
