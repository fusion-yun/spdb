# 泛型模式

灵感来自 《Modern C++ Design: Generic Programming and Design Patterns Applied》作者 Andrei Alexandrescu

- 重载 `__class_getitem__`，实现泛型

```python

class GenricHelper:
    def __class_getitem__(cls,item):
        # 根据 item 创建新的类

class Foo(GenericHelper[_T]):
    value:_T

foo = Foo[int]()
```

## 策略模式

利用 Python MRO 实现基于策略的组装。

- 重载 `__new__`, 定义属性和方法，实现某个语义
- WithXXXX 重载 `__init_subclass__` 修改类属性。
- AsXXXXX 重载 `__init__` 修改类创建方式
- XXXable
  将策略组装（特化），顺序为 AsXXX , Base, WithXXX,XXXable

```python
class Foo(AsXXX,Base,  WithXXX,XXXable)
    pass
```
