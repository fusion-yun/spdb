from spdm.core.sp_tree import AttributeTree, SpTree, sp_property, sp_tree


class Data(SpTree):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class Foo(SpTree):
    boo: Data = sp_property(label="boo", default_value=1.0)


class Bar(Foo):
    boo: Data = sp_property(label="boo", units="m")


@sp_tree
class Bar2(Foo):
    boo: Data = 2.1234


a = Bar()
b = Bar2()
print(a.boo._metadata)
print(b.boo._metadata)
print(b.get("boo")._metadata)
