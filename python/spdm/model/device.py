""" Device model 
装置模型
"""

from spdm.model.context import Context


class Device(Context, plugin_prefix="device/"):
    def __init__(self, *args, device=None, **kwargs):

        if device is not None:
            # Add device to the beginning of the args, 用以导入装置信息
            args = (f"{device}://", *args)

        super().__init__(*args, **kwargs)
