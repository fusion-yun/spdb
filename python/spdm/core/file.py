from __future__ import annotations

import pathlib
import typing

from spdm.utils.uri_utils import URITuple, uri_split
from spdm.core.document import Document
from spdm.utils.tags import _not_found_

from spdm.utils.logger import logger


class File(Document):
    """
    File like object
    """

    class Entry(Document.Entry, plugin_name="file"):
        def __new__(cls, *args, plugin_name=None, **kwargs):
            if plugin_name is None and len(args) > 0 and isinstance(args[0], (str, URITuple)):

                schemes = uri_split(args[0]).protocol.split("+")
                if len(schemes) == 1 or schemes[0] != "file":
                    plugin_name = f"file_{schemes[0]}"
                else:
                    plugin_name = "_".join(schemes)

            return super().__new__(cls, *args, plugin_name=plugin_name, **kwargs)

        def __init_subclass__(cls, *args, plugin_name=None, **kwargs) -> None:
            if plugin_name is not None:
                if not isinstance(plugin_name, list):
                    plugin_name = [plugin_name]

                plugin_name = [f"file_{p}" for p in plugin_name]

            return super().__init_subclass__(*args, plugin_name=plugin_name, **kwargs)
