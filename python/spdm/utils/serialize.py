"""  
"""

import collections.abc
from spdm.core.generic import primary_type


def serialize(obj):
    """serialize object"""

    if isinstance(obj, primary_type):
        return obj
    elif hasattr(obj.__class__, "__serialize__"):
        return obj.__serialize__()
    elif isinstance(obj, collections.abc.Mapping):
        return {k: serialize(v) for k, v in obj.items()}
    elif isinstance(obj, collections.abc.Iterable):
        return [serialize(v) for idx, v in enumerate(obj)]
    else:
        raise TypeError(f"{obj.__class__} is not serialzable!")
