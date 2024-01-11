'''
methods to bind the parser to the dataclass.
'''
import json
import os
import types
import warnings
from collections import deque
from dataclasses import MISSING, Field, fields, is_dataclass
from enum import Enum
from functools import partial
from inspect import isclass
from queue import Queue
from typing import (
    IO,
    Any,
    BinaryIO,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Set,
    TextIO,
    Tuple,
    Type,
    Union,
)

from .types import BindingType, DataclassType, DataWrapperType

try:
    from typing import Literal
except:
    Literal = None


def identity_type(x):
    '''
        Identity function that returns the input value unchanged.

        This function serves as a type method that does nothing but 
        returns the input value as is.

        Parameters:
            - x: `Any`
                The input value to be returned unchanged.

        Returns:
        - `Any`
            The input value x.
    '''
    return x


def queue_wrapper(collection):
    '''
        Convert a collection to a queue.

        This function takes a collection and converts it into a queue using the 
        `Queue` class. Each item in the collection is added to the queue using 
        the `put_nowait` method.

        Parameters:
        - collection: `Iterable`
            The collection to be converted to a queue.

        Returns:
        - `queue.Queue`
            A queue containing the elements from the input collection.
    '''
    q = Queue()
    for item in collection:
        q.put_nowait(item)

    return q


def dequeue_wrapper(collection):
    '''
        Convert a collection to a deque.

        This function takes a collection and converts it into a deque using the 
        `deque` class. Each item in the collection is appended to the deque.

        Parameters:
        - collection: `Iterable`
            The collection to be converted to a deque.

        Returns:
        - `collections.deque`
            A deque containing the elements from the input collection.
    '''
    q = deque(collection)

    return q


def collection_type_with_sep_fn(
    val: str, sep: str, dtype: Callable, wrapper_type: Callable
):
    '''
        Convert a string joined by a separator to another collection type.

        This function takes a string `val` that is joined by a specified separator `sep`,
        splits it into individual items, applies the specified data type conversion function
        `dtype` to each item, and then constructs a collection of the specified type
        using the provided `wrapper_type`.

        Parameters:
        - val (`str`): 
            The input string joined by the separator.
        - sep (`str`): 
            The separator used to split the input string.
        - dtype (`Callable`): 
            A callable representing the data type conversion function for each item.
        - wrapper_type (`Callable`): 
            A callable representing the type of collection to be constructed.

        Returns:
        - A collection of the specified type containing elements from the converted items.

        Example:
        ```python
        input_string = "1,2,3,4,5"
        separator = ","
        data_type_converter = int
        target_collection_type = list

        result = collection_type_with_sep_fn(input_string, separator, data_type_converter, target_collection_type)
        print(result)  # Output: [1, 2, 3, 4, 5]
        ```
    '''
    items = val.split(sep)
    items = wrapper_type(list(map(dtype, items)))

    return items


def dict_type_fn(
    val: Union[str, os.PathLike], k_type: Callable, v_type: Callable
):
    '''
        Convert a JSON string or a JSON file to a dictionary object.

        This function takes a JSON string `val` or the path to a JSON file, 
        loads it into a dictionary object, and then applies the specified key 
        and value type conversion functions `k_type` and `v_type` to each item.

        Parameters:
        - val (`Union[str, os.PathLike]`): 
            Either a JSON string or the path to a JSON file.
        - k_type (`Callable`): 
            A callable representing the key type conversion function.
        - v_type (`Callable`): 
            A callable representing the value type conversion function.

        Returns:
        - dict
            A dictionary with keys and values converted to the specified types.

        Raises:
        - Exception: 
            If the input `val` is neither a valid JSON string nor a valid JSON file.
    '''
    if v_type is Any:
        v_type = identity_type
    if k_type is Any:
        k_type = identity_type
    try:
        dict_data = json.loads(val)
        dict_data = {
            k_type(k): v_type(v)
            for k, v in dict_data.items()
        }
        return dict_data
    except:
        if os.path.isfile(val) and os.path.exists(val):
            with open(val, 'r', encoding='utf-8') as f:
                dict_data = json.load(f)
            dict_data = {
                k_type(k): v_type(v)
                for k, v in dict_data.items()
            }
            return dict_data
        raise TypeError(
            'The input value is neither a valid JSON string nor a valid JSON file'
        )


def enum_type_fn(val: str, enum_type: Type[Enum]) -> Enum:
    '''
        Convert a string to an enum value.

        This function takes a string `val` and an Enum type `enum_type`,
        iterates through the enum values, and returns the first enum value
        whose value matches the provided string after conversion.

        Parameters:
        - val (`str`): 
            The input string to be converted to an enum value.
        - enum_type (`Type[Enum]`): 
            The Enum type to which the string will be converted.

        Returns:
        - `Enum`
            The enum value corresponding to the converted string.

        Raises:
        - `ValueError`: 
            If no matching enum value is found for the provided string.
    '''
    for item in enum_type:
        if type(item.value)(val) == item.value:
            return item

    raise ValueError(f'No matching enum value found for the string: {val}')


def _get_choices(dtype) -> List:
    origin_type = getattr(dtype, '__origin__', dtype)
    if origin_type is Union or (
        hasattr(dtype, 'UnionType')
        and isinstance(origin_type, types.UnionType)
    ):
        dtype_generics = dtype.__args__
        dtype_generics = list(
            filter(lambda x: x is not type(None), dtype_generics)
        )
        return _get_choices(dtype_generics[0])
    else:
        if (
            Literal is not None
            and getattr(dtype, '__origin__', None) is Literal
        ):
            choices = dtype.__args__
        else:
            choices = [item.value for item in dtype]
        return tuple(map(str, choices))


def _analysis_type(dtype) -> Optional[Tuple[Callable, DataWrapperType]]:
    if dtype == MISSING:
        return None, DataWrapperType.Unknown
    if dtype is str or dtype is int or dtype is bytes or dtype is float:
        return dtype, DataWrapperType.Basic
    elif dtype is bool:
        return dtype, DataWrapperType.Bool
    else:
        origin_type = getattr(dtype, '__origin__', dtype)
        if origin_type is Union or (
            hasattr(dtype, 'UnionType')
            and isinstance(origin_type, types.UnionType)
        ):
            dtype_generics = dtype.__args__
            dtype_generics = list(
                filter(lambda x: x is not type(None), dtype_generics)
            )

            if len(dtype_generics) > 1:
                raise ValueError(
                    "Only `Union[X, NoneType]` (i.e., `Optional[X]`) is allowed for `Union` because"
                    " the argument parser only supports one type per argument."
                    f" Problem encountered in field."
                )
            return _analysis_type(dtype_generics[0])
        if (Literal is not None and origin_type is Literal
            ) or (isinstance(dtype, type) and issubclass(dtype, Enum)):
            if (Literal is not None and origin_type is Literal):
                choice_values = dtype.__args__
            else:
                choice_values = [item for item in dtype]
            choices = _get_choices(dtype)

            str2choice = {
                str(choice): val
                for choice, val in zip(choices, choice_values)
            }
            identity_map = {
                val: val
                for val in choice_values
                if val not in str2choice
            }
            str2choice.update(identity_map)
            return lambda x: str2choice.get(x), (
                DataWrapperType.Literal if Literal is not None
                and dtype is Literal else DataWrapperType.Enum
            )
        if dtype is Dict or (
            isclass(origin_type) and issubclass(origin_type, dict)
        ):
            if hasattr(dtype, '__args__'):
                dtype_generics = dtype.__args__
                dtype_generics = list(
                    filter(lambda x: x is not type(None), dtype_generics)
                )
            else:
                dtype_generics = [identity_type, identity_type]
            assert len(
                dtype_generics
            ) == 2, 'The dict dtype must has key type and value type.'

            if not all(
                [
                    t in (int, str, float, bytes, identity_type)
                    for t in dtype_generics
                ]
            ):
                return None, DataWrapperType.Complex

            dicttype = partial(
                dict_type_fn,
                k_type=dtype_generics[0],
                v_type=dtype_generics[1]
            )

            return dicttype, DataWrapperType.Dict

        if (
            dtype is List
            or (isclass(origin_type) and issubclass(origin_type, list))
        ):
            if hasattr(dtype, '__args__'):
                dtype_generics = dtype.__args__
                dtype_generics = list(
                    filter(
                        lambda x: x is not type(None) and x is not type(...),
                        dtype_generics
                    )
                )
            else:
                dtype_generics = [identity_type]
            if len(dtype_generics) > 1 or dtype_generics[0] not in (
                int, str, float, bytes, identity_type
            ):
                return None, DataWrapperType.Complex

            return dtype_generics[0], DataWrapperType.List
        if (
            dtype is Tuple
            or (isclass(origin_type) and issubclass(origin_type, tuple))
        ):
            if hasattr(dtype, '__args__'):
                dtype_generics = dtype.__args__
                dtype_generics = list(
                    filter(
                        lambda x: x is not type(None) and x is not type(...),
                        dtype_generics
                    )
                )
            else:
                dtype_generics = [identity_type]
            if len(dtype_generics) > 1 or dtype_generics[0] not in (
                int, str, float, bytes, identity_type
            ):
                return None, DataWrapperType.Complex
            return dtype_generics[0], DataWrapperType.Tuple
        if (
            dtype is Set
            or (isclass(origin_type) and issubclass(origin_type, set))
        ):
            if hasattr(dtype, '__args__'):
                dtype_generics = dtype.__args__
                dtype_generics = list(
                    filter(
                        lambda x: x is not type(None) and x is not type(...),
                        dtype_generics
                    )
                )
            else:
                dtype_generics = [identity_type]
            if len(dtype_generics) > 1 or dtype_generics[0] not in (
                int, str, float, bytes, identity_type
            ):
                return None, DataWrapperType.Complex
            return dtype_generics[0], DataWrapperType.Set
        if dtype is Deque or (
            isclass(origin_type) and issubclass(origin_type, deque)
        ):
            if hasattr(dtype, '__args__'):
                dtype_generics = dtype.__args__
                dtype_generics = list(
                    filter(
                        lambda x: x is not type(None) and x is not type(...),
                        dtype_generics
                    )
                )
            else:
                dtype_generics = [identity_type]
            if len(dtype_generics) > 1 or dtype_generics[0] not in (
                int, str, float, bytes, identity_type
            ):
                return None, DataWrapperType.Complex
            return dtype_generics[0], DataWrapperType.Dequeue
        if dtype is Queue or (
            isclass(origin_type) and issubclass(origin_type, Queue)
        ):
            if hasattr(dtype, '__args__'):
                dtype_generics = dtype.__args__
                dtype_generics = list(
                    filter(
                        lambda x: x is not type(None) and x is not type(...),
                        dtype_generics
                    )
                )
            else:
                dtype_generics = [identity_type]
            if len(dtype_generics) > 1 or dtype_generics[0] not in (
                int, str, float, bytes, identity_type
            ):
                return None, DataWrapperType.Complex
            return dtype_generics[0], DataWrapperType.Queue

        if (dtype is TextIO or (isclass(origin_type) and issubclass(origin_type, TextIO))) or \
            ((dtype is BinaryIO) or (isclass(origin_type) and issubclass(origin_type, BinaryIO))) or \
            (dtype is IO or (isclass(origin_type) and issubclass(origin_type, IO))):

            if hasattr(dtype, '__args__'):
                dtype_generics = dtype.__args__
                dtype_generics = list(
                    filter(
                        lambda x: x is not type(None) and x is not type(...),
                        dtype_generics
                    )
                )
            else:
                dtype_generics = [identity_type]
                if (
                    dtype is TextIO or
                    (isclass(origin_type) and issubclass(origin_type, TextIO))
                ):
                    dtype_generics = [str]

            return dtype_generics[0], DataWrapperType.File

        return None, DataWrapperType.Unknown


def analysis_filed(field: Field) -> Optional[BindingType]:
    if not field.init:
        return None

    dtype, wrapper_type = _analysis_type(field.type)

    if field.metadata.get('type', None):
        if dtype is not None:
            warnings.warn(
                f'The type for "{field.name}" will be occupied with meta.',
                UserWarning
            )
        dtype = field.metadata.get('type')

    default = None
    required = False
    if field.default is MISSING and field.default_factory is MISSING:
        required = True
    else:
        if field.default is not MISSING:
            default = field.default
        if callable(dtype) and default is not None:
            default = dtype(default)
        if field.default_factory is not MISSING:
            default = field.default_factory()

    choices = None
    if wrapper_type is DataWrapperType.Literal or wrapper_type is DataWrapperType.Enum:
        choices = _get_choices(field.type)

    multiple = False
    if wrapper_type is DataWrapperType.List or wrapper_type is DataWrapperType.Tuple or wrapper_type is DataWrapperType.Set or wrapper_type is DataWrapperType.Queue or wrapper_type is DataWrapperType.Dequeue:
        multiple = True
    sep = field.metadata.get('sep', None) if multiple else None
    if sep:
        wrapper_cls = lambda x: x
        if wrapper_type is DataWrapperType.List:
            wrapper_cls = list
        elif wrapper_type is DataWrapperType.Tuple:
            wrapper_cls = tuple
        elif wrapper_type is DataWrapperType.Set:
            wrapper_cls = set
        elif wrapper_type is DataWrapperType.Queue:
            wrapper_cls = queue_wrapper
        elif wrapper_type is DataWrapperType.Dequeue:
            wrapper_cls = dequeue_wrapper
        dtype = partial(
            collection_type_with_sep_fn,
            sep=sep,
            dtype=dtype,
            wrapper_type=wrapper_cls
        )

    if wrapper_type is DataWrapperType.Bool:
        dtype = None
    if wrapper_type is DataWrapperType.Complex and dtype is None:
        warnings.warn(
            f'The filed "{field.name}" is complex but there is no type specified, this could make an error.',
            UserWarning
        )

    if wrapper_type is DataWrapperType.Complex and field.metadata.get(
        'help', None
    ) is None:
        warnings.warn(
            f'The filed "{field.name}" is complex but there is no help doc provided, this could make the option confused.'
        )
    if wrapper_type is DataWrapperType.Unknown and field.metadata.get(
        'type', None
    ) is None:
        raise Exception(
            f'The filed "{field.name}" is unkown type, you have to specify the type convert function in the meta.'
        )

    if field.metadata.get('required', None) is not None:
        required = field.metadata.get('required')
    if field.metadata.get('choices', None) is not None:
        choices = field.metadata.get('choices')
    if field.metadata.get('multiple', None) is not None:
        multiple = field.metadata.get('multiple')
    if dtype is bytes:
        dtype = partial(bytes, encoding='utf-8')

    return BindingType(
        name=field.name,
        type=dtype,
        default=default,
        choices=choices,
        multiple=multiple,
        seperator=sep,
        wrapper_type=wrapper_type,
        required=required,
        aliases=field.metadata.get('aliases', None),
        help=field.metadata.get('help', ''),
        file=field.metadata.get('file', False),
        file_mode=field.metadata.get('file_mode', 'r'),
        file_encoding=field.metadata.get('file_encoding', 'utf-8')
    )


def analysis_dataclass(*clz: Type[DataclassType]) -> Dict[str, BindingType]:
    types: Dict[str, BindingType] = {}
    for cls in clz:
        if not is_dataclass(cls):
            continue
        for field in fields(cls):
            res = analysis_filed(field)
            if res:
                types[field.name] = res

    return types
