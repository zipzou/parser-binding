# Documentation

> Translated from [中文文档](./README_ZH.md) by [GPT 3.5](https://chat.openai.com)

A tool for quickly binding dataclass classes to ArgumentParser to achieve rapid customization of command-line parameters. This binding supports most parameters of ArgumentParser, such as help documentation, whether it is a required parameter, multiple values, etc., as detailed below. At the same time, this tool supports Python's type hints as much as possible.

## Quick Start

**Python version: `>=3.7`**

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

Execute `python demo.py -h`, you will get the following output:

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

Execute `python demo.py -i ./test.txt --workers 2 --logging-level debug --with-verbose`, and you will automatically get an instance of the dataclass with corresponding parameters read from the command-line:

```shell
_MergedDataClass@1704877855657(input_file='./test.txt', workers=2, logging_level=<LogLevel.DEBUG: 'debug'>, verbose=True)
```

## Formatting Guide

Command-line parameter names will be formatted into three types:

- `--xxx-yyy`, when the class property name contains `_`, it will be converted to a command-line parameter name starting with `--` and separated by `-`.
- `--xxx_yyy`, when the class property name contains `_`, it will be converted to a command-line parameter name starting with `--` and separated by `_` as an alternative.
- `-x`, shortcut option support, when the property name is a single character or contains a single character in the specified alias, it will use the shortcut option `-` as one of the parameters.

Currently, it supports most types in Python:

- **Basic Types**
    - `int`: Integer type, automatically converts command-line parameters to integers.
    - `float`: Floating-point type, automatically converts command-line parameters to floating-point numbers.
    - `str`: String type, automatically converts command-line parameters to strings.
    - `bytes`: Byte type, supports direct conversion of strings in UTF-8 encoding, does not support other complex data, if other conversions are needed, it can be implemented by specifying the type.
    - `bool`: Boolean type, automatically adds a switch option to the command-line, the switch name is influenced by the default value; when the default value is `True`, the switch name is formatted as `--without-xxx-yyy` and `--without_xxx_yyy`, when the default value is `False`, the switch name is formatted as starting with `--with`. 
    **Note: Boolean value types will only be formatted as switches and do not need to pass parameters on the command-line. Pay attention to the change in parameter names caused by changes in default values.**

- **Types with Generic Annotations**: When using generic annotations, please explicitly specify the type inside the generic. Complex types such as `Union[str, int]` are not directly supported：

    - `Optional`，Used to define optional properties, provide a default value when using this annotation. **For all properties with default values, the corresponding parameters on the command-line will be treated as optional parameters and provide default values.**
    - `List`/`list`: When using the `List` annotation, please specify the type of the list elements explicitly, such as `List[int]`. When using this type, the command-line parameter corresponding to it will be set as a multi-value type, and spaces will be used as the default separator for each value, such as `--multiple 1 2 3`. The explicit element type will format each value passed in as the target type, that is, each element in the `List[int]` property will be of type `int`, and not the result of `List[str]`.
    If using the `list` annotation, there is no additional type mapping for the passed elements by default. If additional type mapping is needed, please specify the type mapping using the type parameter (as shown in the example later).
    - `Tuple`/`tuple`: Same as `List` or `list`, the difference lies in the final collection class output.
    - `Set`/`set`: Same as above.
    - `Deueue`/`dequeue`: Same as above.
    - `Queue`: Same as above. These collection classes default to using a space as the separator between multiple values. If a custom separator is needed, it should be specified using `sep` (as shown in the subsequent example).
    - `Dict`/`dict`: When using `Dict` as the property type, please explicitly specify the key and value types. If using `dict` as an annotation, no mapping will be done for the key/value types. By default, the command-line parameters passed in will be treated as a JSON-string for parsing. If it cannot be parsed, it will try to parse it as a JSON file (in this case, pass in a JSON file directory). If both methods fail, it will result in failure.
    - `Enum`: When using an enumeration class, the command-line will construct an optional value parameter, and the input will be limited to a fixed list of values. The command-line will pass in a string, but during parsing, it will get a corresponding enumeration and provide it to the dataclass instance initialization.
    - `Literal`: Requires `python >= 3.8` support, equivalent to `Enum`, but does not produce an enumeration.

- **Complex Types**
    
    - File type: For ease of reading from the command-line or setting output devices, you can quickly open files using this method to reduce the overhead of calling `open` in the code.
    - Nested or unknown types: To further expand the scenarios of complex types, support custom type conversion for command-line passing values through the `Field` and `type` parameters.


### Usage Examples

#### Basic Type Scenario

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

Result:

`_MergedDataClass@1704880154551(required_float=0.1, a=10, string_type='Hello Parser!', switch=True, bytes_data=b'Hello Parser!')`

You can observe that `--required-float` is a required parameter; otherwise, parsing will fail.
**For parameters without default values, `parser-binding` will consider them as required parameters; otherwise, provide default values.**

#### `typing` Annotation Types

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

Execute `python list-demo.py --data 1 2 3 --items 1 2 3` to parse and get the result `_MergedDataClass@1704880514613(data=[1, 2, 3], items=['1', '2', '3'])`。

From the above difference, if using the `List[int]` annotation, each element in the list will be converted to an integer, otherwise, no conversion will be performed.
If conversion is required, the `type` should be specified, as shown below, changing the `items` annotation to:

```python
items: list = Field(default=None, type=int)
```

Execute `python list-demo.py --data 1 2 3 --items 1 2 3`, and the parsed result will be `_MergedDataClass@1704881428343(data=[1, 2, 3], items=[1, 2, 3])`, where the type is now correctly converted.

For `set`, `tuple`, `deque`, `queue`, and other collection types, the effect is the same.

**Note: If the property is annotated with `list`, `tuple`, `set`, `queue`, etc., the command-line will automatically convert the corresponding parameter to a multi-value parameter separated by spaces. At this time, if you specify type using `Field`, type should correspond to the class of the elements, not the final property collection type. For example, in the above `Field(default=None, type=int)`, `type` specifies the element `type` as `int`, i.e., the property type is `List[int]`.**

Given the default behavior of command-line multi-value parameters, which default to being separated by spaces, further support for more separators can be achieved through `Filed` by specifying `sep`.
For example: `items: tuple = Field(sep=',', default=None, type=int)`, will result in a `Tuple[int]` parsing result, and the input parameters will be separated by `,`. In this case, you should run the following command: `python list-demo.py --data 1 2 3 --items 1,2,3`, and the parsing result will be `_MergedDataClass@1704893904876(data=(1, 2, 3), items=(1, 2, 3)).`。


`parser-binding` also supports dictionary types, used to support JSON-like formats. When using `Dict` as the type annotation, you need to specify the key and value types so that they can be correctly converted. If the JSON string contains key-value pairs of multiple types, you can directly use `dict` for annotation, as shown in the following example:

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

Execute `python dict-demo.py --data '{"1": "1", "2": "2"}' --items '{"1": "1", "2": "2"}'`, and the parsing result will be `_MergedDataClass@1704944849798(data={'1': 1, '2': 2}, items={'1': '1', '2': '2'})`。

From the above parsing result, when using `dict` for annotation, the key-type and value-type will remain consistent with the original JSON, but when using `Dict` and specifying types, the key/value will be converted to the corresponding types.

---------

**Enum Types**

Enum types allow the command-line to define an optional value parameter, restricting the input to a fixed list of values, making the selection from the command-line effective.

As shown in the example below:

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

At this point, check the usage with usage: `enum-demo.py [-h] [--mode {train,eval}]`, indicating that only the values `train` and `eval` are supported.

Enum classes are equivalent in effect to annotations like `Literal`。


#### Complex Type

To further support more scenarios, such as nested collections, multi-type inference, file reading and writing, etc., `parser-binding` supports implementation through `Field` combined with `type`.

We allow the use of `Optional` or `Union[x, None]` to declare optional properties, but we do not yet support multi-type inference, such as `Union[str, int]`, or nested types like `List[List[int]]`. 
These types are considered complex types and require additional type configuration!


**By default, for complex types when no `type` configuration is specified, we won't perform any processing. Consequently, the parameter values read will be of type `str`. This may lead to unexpected results, so please use caution.**

**Recommended: Provide the `help` argument for complex types to help the command-line understand how to pass values.**

-------

**Nested Types**

In complex scenarios, we use `List[List[int]]` as an example for parsing, as shown in the following code:

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

At this time, the `data` property is not given a `type` argument and is treated as a complex type, resulting in the following warning:

`UserWarning: The filed "data" is complex but there is no type specified, this could make an error.`

At this time, directly passing values from the command-line will result in the result: `_MergedDataClass@1704955154188(data='1,2,3')`, indicating that `data` does not match the expected type `List[List[int]]`.

Therefore, a reasonable practice should be:

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

Executing `python complex-demo.py --data 1:4:5,2,3` will result in `_MergedDataClass@1704955285471(data=[[1, 4, 5], [2], [3]])`, which aligns with the expected type annotations.

----------

**File Type**

To facilitate the input of files from the command line, `parser-binding` supports simple text reading and writing methods, making it easy to obtain file instances directly from a data class without the need for `open` method calls. Here is an example:

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

For file handling, there are two annotation methods, as seen in the example above with the `in_file` property. The difference lies in whether the `file` argument needs to be specified as `True` when using the `IO` annotation. Otherwise, it must be specified as `True`, or else it will be treated as a complex type.

Suppose the content of the existing `test-file.txt` is:
```shell
a
b
c
```

By executing `python file-demo.py --in-file test-file.txt`, the above code will produce the output: 
```
o       a
o       b
o       c
```

**For file types, when the default value is `'-'`, it is automatically set to `stdin` or `stdout`, depending on the file's read/write opening mode.**

File types support plain text files. If the file name ends with `.gz` and the property type annotation is a generic `str`, such as `IO[str]`/`TextIO`, it will open the file using `gzip.open()` + `rt` mode.
