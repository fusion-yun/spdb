from spdm.utils.uri_utils import uri_split
from spdm.core.document import Document


class Service(Document, plugin_name="service"):

    _plugin_prefix = Document._plugin_prefix + "service_"

    def __new__(cls, uri, *args, _plugin_name=None, **kwargs):
        if cls is not Service:
            return super().__new__(cls)

        if _plugin_name is None:
            _plugin_name = uri_split(uri).protocol

        if not _plugin_name.startswith("service"):
            _plugin_name = f"service+{_plugin_name}"

        return super().__new__(cls, *args, _plugin_name=_plugin_name, **kwargs)
