# 使用文档

[EN-DOC](./README.md)

用于快速将dataclass类绑定到ArgumentParser，以实现快速定制化command-line参数。该绑定支持argument-parser大部分参数，如help文档，是否必须参数、多选值等，具体见下。同时，该工具尽可能地支持了Python内置的类型提示。

## 快速使用

**Python版本：`>=3.7`**

`pip install parser-binding`

`demo.py`：

```python
from dataclasses import dataclass, field
from enum import Enum

from parser_binding import BindingParser, Field


class LogLevel(Enum):
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


@dataclass
class TestOptions:

    input_file: str = Field(
        default=None, aliases=['i'], help='The input file to read.'
    )
    workers: int = 1
    logging_level: LogLevel = LogLevel.WARNING

    verbose: bool = False


if __name__ == '__main__':
    parser = BindingParser(TestOptions)

    options = parser.parse_into_dataclasses((TestOptions, ))

    print(options)

```

执行`python demo.py -h`，得到如下输出：

```shell
usage: demo.py [-h] [-i INPUT_FILE] [--workers WORKERS] [--logging-level {debug,info,warning,error}] [--with-verbose]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input-file INPUT_FILE, --input_file INPUT_FILE
                        The input file to read. Optional. Default `None`.
  --workers WORKERS     Optional. Default `1`.
  --logging-level {debug,info,warning,error}, --logging_level {debug,info,warning,error}
                        Optional. Default `warning`.
  --with-verbose, --with_verbose
                        Optional. Default `False` as verbose disabled.
```

执行`python demo.py -i ./test.txt --workers 2 --logging-level debug --with-verbose`，将自动得到一个从command-line读取对应参数的dataclass实例：

```shell
_MergedDataClass@1704877855657(input_file='./test.txt', workers=2, logging_level=<LogLevel.DEBUG: 'debug'>, verbose=True)
```

## 格式化说明
command-line参数名将统一格式化为三种类型：

- `--xxx-yyy`，当类属性名带有`_`时，将转换为使用`--`开头，`-`分割的command-line参数名；
- `--xxx_yyy`, 当类属性名带有`_`时，将转换为使用`--`开头，`_`分割的command-line参数名作为备选；
- `-x`，快捷选项支持，当属性名为单字符或指定的别名中含有单字符名称时，将使用快捷选项`-`开头，作为参数之一；

当前支持python中大部分类型：

- **基本类型**
    - `int`，整数类型，将自动将command-line的参数转化为整数；
    - `float`，浮点数类型，自动将command-line参数转化为浮点数；
    - `str`，字符串类型，自动将command-line参数转化为字符串；
    - `bytes`，字节类型，默认支持UTF8编码方式的字符串直接转换，其他复杂数据暂不支持，若需其他转换，可通过指定type实现；
    - `bool`，布尔类型，自动为command-line添加开关选项，开关名称受默认值影响；当默认值为`True`时，开关名称为`--without-xxx-yyy`或`--without_xxx_yyy`，当默认值为`False`时，则开关名称被格式化为以`--with`开头。**注意：布尔值类型仅会被格式化为开关，无需在command-line中传入参数，且注意默认值变化所带来的参数名变化**。

- **带有范型注释的类型**，在使用范型注释时，请明确指出范型内的类型，暂不直接支持`Union[str, int]`此类复杂类型：

    - `Optional`，用于定义可选属性，使用该注释时，请为属性提供默认值。**对于一切含有默认值的属性，command-line对应的参数将被视为可选参数，并提供默认值。**
    - `List`/`list`，在使用`List`注释时，**请明确指明列表元素的类型**，如`List[int]`，使用该类型时，自动将command-line对应的参数设为多值类型，并默认使用空格表示每个值，如`--multiple 1 2 3`。明确的元素类型，将使得传入的每个值进行目标类型的格式化，即`List[int]`属性中的每个元素为`int`，而不会得到`List[str]`的结果；
    若使用`list`注释，默认不对传入的元素进行额外的类型映射，若需要额外的类型映射，请指明type映射方法（使用可见后续介绍）；
    - `Tuple`/`tuple`，同`List`或`list`，区别在于输出的最终集合类不同；
    - `Set`/`set`，同上；
    - `Deueue`/`dequeue`，同上；
    - `Queue`，同上；上述集合类，均默认以空格作为多个值之间的分割，若需自定义分割符，需要使用`sep`指定，可参考后续实例使用方式。
    - `Dict`/`dict`，当使用`Dict`作为属性类型时，请明确指出key与value类型；若使用`dict`作为注释，则不对key/value类型做任何映射；默认情况下，command-line传入的参数，将被视为一个JSON-string解析，若无法解析，则尝试以JSON文件方式解析（此时传入一个JSON文件目录）；若两种方式均无法解析，则会导致失败；
    - `Enum`枚举，使用枚举类时，将使得command-line构造一个可选值的参数，并且将输入限定在固定的值列表内；command-line将传入字符串，但解析时将得到一个对应的枚举并提供给dataclass实例初始化；
    - `Literal`，需要`python >= 3.8`版本支持，与Enum等效，但不产出枚举；

- **复杂类型**
    
    - 文件类型，为便于从command-line中读取或设置输出设备，可以通过该方式快速打开文件，减少编码`open`的开销；
    - 嵌套或未知类型，为进一步扩展复杂类型的场景，支持自定义type对command-line传值进行转换；


### 使用实例

#### 基本类型场景

```python
from dataclasses import dataclass

from parser_binding import BindingParser


@dataclass
class TestOption():
    required_float: float
    a: int = 0
    string_type: str = None
    switch: bool = False
    bytes_data: bytes = None


parser = BindingParser(TestOption)
options = parser.parse_into_dataclasses((TestOption, ))

print(options)

```

`python3 basic-demo.py --required-float 0.1 -a 10 --string-type 'Hello Parser!' --with-switch --bytes-data 'Hello Parser!'`

结果：

`_MergedDataClass@1704880154551(required_float=0.1, a=10, string_type='Hello Parser!', switch=True, bytes_data=b'Hello Parser!')`

通过`-h`可观察到，此时`--required-float`为必传参数，否则将解析失败；
**对不不提供默认值的参数，parser-binding将视为必传参数处理，否则，请提供默认值。**

#### `typing`注释类型

```python
from dataclasses import dataclass
from typing import List

from parser_binding import BindingParser


@dataclass
class TestOption:
    data: List[int] = None
    items: list = None


parser = BindingParser(TestOption)

opt = parser.parse_into_dataclasses((TestOption, ))

print(opt)
```

执行`python list-demo.py --data 1 2 3 --items 1 2 3`将解析得到`_MergedDataClass@1704880514613(data=[1, 2, 3], items=['1', '2', '3'])`。

从上述区别可以看出，若使用`List[int]`注释，则列表中的每个元素将被转换为整数，否则将不进行任何转换。
若需要进行转换，需要指定type，如下，将`items`注释更换为：
```python
items: list = Field(default=None, type=int)
```
再次执行`python list-demo.py --data 1 2 3 --items 1 2 3`，解析得到结果`MergedDataClass@1704881428343(data=[1, 2, 3], items=[1, 2, 3])`，此时类型将进行对应的转换。

对于`set`、`tuple`、`deque`、`queue`等集合类型，具有相同效果。

**注意事项：若属性被`list`、`tuple`、`set`、`queue`等集合注释时，command-line将自动将对应的参数转化为以空格分割的多值参数。此时，若通过`Field`重新指定`type`时，`type`应该对应为元素的类，而非最终属性的集合类型。如上述`Field(default=None, type=int)`中，`type`指定元素类型为`int`，即属性类型为`List[int]`。**

鉴于默认command-line多值参数都默认以空格区分，为进一步扩展支持更多分割符，可通过`Filed`指定`sep`来定义。
如：`items: tuple = Field(sep=',', default=None, type=int)`，将会得到`Tuple[int]`的解析结果，并且传入参数使用`,`分割。此时，应当执行以下命令：`python list-demo.py --data 1 2 3 --items 1,2,3`，解析结果为：`_MergedDataClass@1704893904876(data=(1, 2, 3), items=(1, 2, 3))`。

`parser-binding`额外支持字典类型，用于支持类似JSON的格式。当使用`Dict`作为类型注释时，需要为其分配Key-Type与Value-Type，以便于能够正确的转换。若JSON字符串中，存在多样类型的key-value，可直接使用`dict`进行注释，如下实例：

```python
from dataclasses import dataclass
from typing import Dict

from parser_binding import BindingParser, Field


@dataclass
class TestOption:
    data: Dict[str, int] = None
    items: dict = None


parser = BindingParser(TestOption)

opt = parser.parse_into_dataclasses((TestOption, ), )

print(opt)
```

执行`python dict-demo.py --data '{"1": "1", "2": "2"}' --items '{"1": "1", "2": "2"}'`，得到解析结果为：`_MergedDataClass@1704944849798(data={'1': 1, '2': 2}, items={'1': '1', '2': '2'})`。

从上述解析结果可以看出，当使用`dict`进行注释时，key-type与value-type将与原JSON保持一致，但当使用`Dict`并指明类型时，key/value将进行对应的类型转换。

---------

**枚举类型**

枚举类型将使得command-line定义一个可选值的参数，使得输入固定在某个集合内选择方为有效参数。

如以下示例：
```python
from dataclasses import dataclass
from enum import Enum

from parser_binding import parse_args


class Mode(Enum):
    train: str = 'train'
    eval: str = 'eval'


@dataclass
class TestOption:
    mode: Mode = Mode.train


args = parse_args((TestOption, ))

print(args.mode)
```

此时，查看usage为`usage: enum-demo.py [-h] [--mode {train,eval}]`，即只支持`train`、`eval`二者之一的值；

枚举类在效果上与`Literal`注释等效。


#### 复杂类型场景

为进一步支持更多的场景，如嵌套集合，多类型推断，文件读写等场景，`parser-binding`支持通过`Field`结合`type`的方式实现。

我们允许使用`Optional`或`Union[x, None]`的方式，用于声明可选属性，但尚不支持多类型推断，如`Union[str, int]`，或嵌套类型`List[List[int]]`，这些类型都将被视为复杂类型，且需要额外提供`type`属性，用于类型转换。

**默认情况下，对于复杂类型且未指定`type`配置时，我们不会进行任何处理，因此读取的参数值是`str`类型，这可能会导致非预期的结果，请慎重！**

**推荐：推荐为复杂类型提供`help`属性，以帮助command-line理解应该如何传值。**

-------

**嵌套类型**

复杂场景下，我们以`List[List[int]]`为示例进行解析，如下代码：
```python
from dataclasses import dataclass
from typing import List

from parser_binding import parse_args


@dataclass
class TestOption:
    data: List[List[int]] = None


args = parse_args((TestOption, ))

print(args)
```

此时，属性`data`并未给定`type`属性，并且被视为复杂类型，将得到如下警告：
`UserWarning: The filed "data" is complex but there is no type specified, this could make an error.`

此时，直接通过command-line传值，将会得到结果：`_MergedDataClass@1704955154188(data='1,2,3')`，可见`data`与预期的`List[List[int]]`
类型不符。

因此，合理的实践应为：

```python
from dataclasses import dataclass
from typing import List

from parser_binding import Field, parse_args


@dataclass
class TestOption:
    data: List[List[int]] = Field(
        default=None,
        type=lambda x:
        list(map(lambda x: list(map(int, x.split(':'))), x.split(',')))
    )


args = parse_args((TestOption, ))

print(args)
```

执行`python complex-demo.py --data 1:4:5,2,3`，将会得到`_MergedDataClass@1704955285471(data=[[1, 4, 5], [2], [3]])`的结果，符合类型注释预期。

----------

**文件类型**

为便于command-line传入文件，`parser-binding`支持了简单的文本读、写方式，便于从dataclass中直接拿到文件实例，而避免`open`
方法调用，示例如下：

```python
from dataclasses import dataclass
from typing import IO, Iterable, TextIO

from parser_binding import Field, parse_args


@dataclass
class TestOption:
    in_file: Iterable[str] = Field(
        default=None, file=True, file_mode='r', file_encoding='utf-8'
    )
    # in_file: IO[str] = Field(default=None, file='r', file_encoding='utf-8')
    out_file: IO[str] = Field(
        default='-', file_mode='w', file_encoding='utf-8'
    )


args = parse_args((TestOption, ))

for l in args.in_file:
    print('o', l.strip(), sep='\t', file=args.out_file)
```

对于文件，存在两种注释方式，如上述示例中的`in_file`属性定义，区别在于，若通过`IO`注释属性，则可以不指明`file`为`True`，否则必须指定`file`为`True`，
不然则视为复杂类型处理。

现有`test-file.txt`内容为：
```shell
a
b
c
```

通过执行`python file-demo.py --in-file test-file.txt`，上述代码得到输出为：
```
o       a
o       b
o       c
```

**对于文件类型，当默认值为`'-'`时，则自动设默认值为`stdin`或`stdout`，这取决于文件的读/写的打开方式。**

文件类型支持纯文本文件，若文件名以`.gz`结尾，且属性类型注释为`str`的范型，如`IO[str]`/`TextIO`，则会以`gzip.open()` + `rt`的模式打开文件。
