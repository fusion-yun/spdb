from copy import copy, deepcopy

import numpy as np
from spdm.utils.logger import logger
from spdm.core.htree import Dict
from spdm.core.htree import HTree
from spdm.core.htree import List
from spdm.core.sp_tree import sp_property


# class Foo(Dict[Node]):
#     def __init__(self, *args, **kwargs) -> None:
#         super().__init__(*args, **kwargs)
#     foo: str = sp_property()  # type: ignore
#     doo: int = sp_property(default_value=10)  # type: ignore

#     @sp_property
#     def goo(self) -> int:
#         return self.doo+100


class Ion(Dict):
    label: str = sp_property()  # type:ignore
    Z: int = sp_property()  # type:ignore
    m: float = sp_property()  # type:ignore
    density: float = sp_property()  # type:ignore


class TransModel(Dict):
    label: str = sp_property()  # type:ignore
    ions: List[Ion] = sp_property()  # type:ignore


if __name__ == "__main__":

    atom_list = List[TransModel](
        [
            {
                "id": "first",
                "ions": [
                    {"label": "H", "Z": 1, "m": 1, "density": 1.0},
                    {"label": "D", "Z": 1, "m": 3},
                    {"label": "T", "Z": 1, "m": 3},
                ],
            },
            {
                "id": "second",
                "ions": [
                    {"label": "H", "Z": 1, "m": 1, "density": 2.0},
                    {"label": "D", "Z": 1, "m": 3},
                    {"label": "T", "Z": 1, "m": 3},
                ],
            },
        ]
    )

    logger.debug(atom_list[0].ions[0].label)
    # ion = atom_list.combine(common_data={"id": "commbine"})

    # for d in ion.ions.find({"label": "H"}):
    #     logger.debug(d)

    # logger.debug(ion.ions[{"label": "H", "@only_first": False}].density)

    # logger.debug(ion.Z)
    # logger.debug(ion.density)

    # cache = {
    #     "a": [
    #         "hello world {name}!",
    #         "hello world2 {name}!",
    #         1.0, 2, 3, 4
    #     ],
    #     "c": "I'm {age}!",
    #     "d": {
    #         "e": "{name} is {age}",
    #         "foo": "{address}"
    #     }
    # }
    # d = Dict[Foo](cache)
    # logger.debug(d["d"])
    # tmp = d["d"]
    # logger.debug(tmp["foo"])
    # logger.debug(tmp.foo)
    # logger.debug(tmp["foo"])
    # logger.debug(tmp.foo)
    # logger.debug(tmp["doo"])
    # logger.debug(tmp.doo)
    # logger.debug(tmp["doo"])
    # logger.debug(tmp.goo)
    # logger.debug(tmp["goo"])
    # # d["b"] = "hello world {name}!"

    # # d["h"].append(1234)
    # # d["h"].append(5678)

    # # d.update({"d": {"g": 5}})

    # # print(cache)
