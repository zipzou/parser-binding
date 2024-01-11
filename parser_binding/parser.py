'''
A custom ArgumentParser to analysis fields from the dataclass and construct the options for command-line.
'''
import time
from argparse import Action, ArgumentError, ArgumentParser, FileType, HelpFormatter
from dataclasses import dataclass, fields
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union, overload

from .types import DataclassType, DataWrapperType, FileTypeWithGzip
from .utils import analysis_dataclass, dequeue_wrapper, queue_wrapper


class BindingParser(ArgumentParser):
    '''
        A command-line argument parser designed to parse arguments and bind them to a specified data class. 
        This parser takes data class types as inputs, analyzes all the fields within the class, 
        and constructs the corresponding command-line arguments for the argument parser.

        Parameters:
        - clz (`iterable[type]`): The type of the data class to which the parsed arguments will be bound.

        Example:
        ```python
        from dataclasses import dataclass

        @dataclass
        class MyDataClass:
            arg1: int
            arg2: str

        # Create an instance of the argument parser
        parser = BindingParser(MyDataClass)

        # Parse command-line arguments and bind them to the data class
        args = parser.parse_args()

        # Access the parsed arguments as attributes of the data class
        print(args.arg1, args.arg2)

    '''

    def __init__(
        self,
        *clz: Type[DataclassType],
        prog: Optional[str] = None,
        usage: Optional[str] = None,
        description: Optional[str] = None,
        epilog: Optional[str] = None,
        parents: Sequence[ArgumentParser] = [],
        formatter_class=HelpFormatter,
        prefix_chars: str = "-",
        fromfile_prefix_chars: Optional[str] = None,
        argument_default: Any = None,
        conflict_handler: str = "error",
        add_help: bool = True,
        allow_abbrev: bool = True
    ) -> None:
        super(BindingParser, self).__init__(
            prog, usage, description, epilog, parents, formatter_class,
            prefix_chars, fromfile_prefix_chars, argument_default,
            conflict_handler, add_help, allow_abbrev
        )
        self._dataclasses = list(clz)

        self.parse_dataclasses()

    def parse_dataclasses(
        self, dataclasses: Optional[Sequence[Type[DataclassType]]] = None
    ):
        '''
            Parse one or more data classes into the argument parser.

            This method allows parsing the fields of one or more data classes into the argument parser.
            If no specific data classes are provided, it will use the data classes defined in the parser.

            Parameters:
            - dataclasses (`Optional[Sequence[Type[DataclassType]]]`): 
                A sequence of data class types to be parsed. If not provided, 
                the data classes previously set in the parser will be used.

            Example:

            ```python
            from dataclasses import dataclass

            @dataclass
            class MyDataClass:
                arg1: int
                arg2: str

            # Create an instance of the argument parser
            parser = BindingParser()

            # Parse the fields of a specific data class
            parser.parse_dataclasses([MyDataClass])

            # Alternatively, parse the fields of data classes previously set in the parser
            parser.parse_dataclasses()
            ```
        '''
        if dataclasses is not None:
            if dataclasses not in self._dataclasses:
                res = analysis_dataclass(*dataclasses)
        else:
            res = analysis_dataclass(*self._dataclasses)
        self._field_info = res
        for name, _type in res.items():
            kwargs = {
                'action': _type.action,
                'nargs':
                '*' if _type.multiple and _type.seperator is None else None,
                'default': _type.default,
                'type': _type.type,
                'choices': _type.choices,
                'help': ' '.join((_type.help, _type.help_suffix)),
                'required': _type.required
            }
            if _type.is_switch:
                for k in ('nargs', 'type', 'choices'):
                    kwargs.pop(k)
            if _type.wrapper_type is DataWrapperType.File or _type.file:
                kwargs['type'] = FileTypeWithGzip(
                    mode=_type.file_mode,
                    encoding=_type.file_encoding,
                    content_type=_type.type
                )
                kwargs['default'] = _type.default_file
                for k in ('nargs', 'choices', 'action'):
                    kwargs.pop(k)
            if _type.required:
                kwargs.pop('default')
            self.add_argument(*_type.options, **kwargs, dest=name)

    def _init_dataclass_with_args(
        self, cls: Type[DataclassType], kwargs: Dict
    ) -> DataclassType:
        all_fields = fields(cls)
        init_kwargs = {}
        for field in all_fields:
            if field.name in kwargs:
                arg_val = kwargs.pop(field.name)
                field = self._field_info[field.name]
                if arg_val is not None and DataWrapperType.is_basic_collection(
                    field.wrapper_type
                ):
                    if field.wrapper_type is DataWrapperType.List:
                        arg_val = list(arg_val)
                    elif field.wrapper_type is DataWrapperType.Tuple:
                        arg_val = tuple(arg_val)
                    elif field.wrapper_type is DataWrapperType.Set:
                        arg_val = set(arg_val)
                    elif field.wrapper_type is DataWrapperType.Queue:
                        arg_val = queue_wrapper(arg_val)
                    elif field.wrapper_type is DataWrapperType.Dequeue:
                        arg_val = dequeue_wrapper(arg_val)

                init_kwargs[field.name] = arg_val

        return cls(**init_kwargs)

    @overload
    def parse_into_dataclasses(
        self, types: Tuple[Type[DataclassType], ...]
    ) -> Union[DataclassType, DataclassType]:
        ...

    @overload
    def parse_into_dataclasses(
        self, types: Tuple[Type[DataclassType], ...], args: Sequence[str]
    ) -> Union[DataclassType, DataclassType]:
        ...

    @overload
    def parse_into_dataclasses(
        self,
        types: Tuple[Type[DataclassType], ...],
        args: Optional[Sequence[str]] = None,
        split_classes: bool = False
    ) -> Union[DataclassType, Tuple[DataclassType, ...]]:
        ...

    def parse_into_dataclasses(
        self,
        types: Tuple[Type[DataclassType], ...],
        args: Optional[Sequence[str]] = None,
        split_classes: bool = False
    ) -> Union[DataclassType, Tuple[DataclassType, ...]]:
        '''
            Parse command-line arguments into initialized dataclass instances.

            This method takes command-line arguments, parses them using the argument parser,
            and initializes instances of the registered dataclasses with the parsed values.

            Parameters:
            - types (`DataclassType`), the types to initialize from the command-line.
            - args (`Optional[Sequence[str]]`, optional):
                Command-line arguments to be parsed. If not provided, sys.argv is used.
            - split_classes (`bool`, optional): Whether to process all the dataclasses one by one, default False that return a merged dataclass.

            Returns:
            - `Tuple[DataclassType, ...]` or `DataclassType`:
                A tuple of initialized dataclass instances or a merged dataclass instance.
        '''
        target_dataclasses = list(types)
        args = self.parse_args(args=args)
        arg_dict = vars(args)
        results = []
        if not split_classes:
            _MergedDataClass = type(
                f'_MergedDataClass@{int(time.time() * 1000)}', types, {}
            )
            _MergedDataClass = dataclass(_MergedDataClass)
            item = self._init_dataclass_with_args(_MergedDataClass, arg_dict)
            return item
        else:
            for cls in target_dataclasses:
                item = self._init_dataclass_with_args(cls, arg_dict)
                results.append(item)

            return tuple(results)

    def add_datacalss(self, cls: Type[DataclassType]):
        '''
            Add a data class to be bound with the parser.

            This method allows adding a data class to the parser, enabling the parser to analyze 
            and bind its fields during argument parsing.

            Parameters:
            - cls (`Type[DataclassType]`): The type of the data class to be added to the parser.
        '''
        self._dataclasses.append(cls)
        self.parse_dataclasses([cls])

        return cls

    def _check_value(self, action: Action, value: Any) -> None:
        if action.choices is not None and action.type is not None and callable(
            action.type
        ):
            typed_choices = list(map(action.type, action.choices))
            if value not in typed_choices:
                args = {
                    'value': value,
                    'choices': ', '.join(map(repr, action.choices))
                }
                raise ArgumentError(
                    action,
                    'invalid choice: %(value)r (choose from %(choices)s)' %
                    args
                )
        else:
            return super(BindingParser, self)._check_value(action, value)


class ComamndLineParser:
    _classes: List[DataclassType] = []

    _parser_meta: Dict = {}

    @classmethod
    def prog(cls, prog: str):
        cls._parser_meta['prog'] = prog
        return cls

    @classmethod
    def desc(cls, desc: str):
        cls._parser_meta['description'] = desc
        return cls

    @classmethod
    def parser_meta(cls, meta: Dict):
        cls._parser_meta.update(meta)
        if 'clz' in cls._parser_meta:
            cls._parser_meta.pop('clz')
        return cls

    @classmethod
    def register(cls, dataclass: Type[DataclassType]) -> 'ComamndLineParser':
        cls._classes.append(dataclass)

        return cls

    @classmethod
    def parse_args(
        cls,
        args: Optional[Sequence[str]] = None,
        split_classes: bool = False
    ) -> Union[DataclassType, Tuple[DataclassType, ...]]:

        parser = BindingParser(*cls._classes, **cls._parser_meta)
        clz = parser.parse_into_dataclasses(
            tuple(cls._classes), args=args, split_classes=split_classes
        )

        cls._classes.clear()
        cls._parser_meta.clear()

        return clz


@overload
def parse_args(
    types: Tuple[Type[DataclassType], ...],
    args: Optional[Sequence[str]] = None,
) -> Union[DataclassType, DataclassType]:
    ...


@overload
def parse_args(
    types: Tuple[Type[DataclassType], ...],
    args: Optional[Sequence[str]] = None,
    split_classes: bool = False
) -> Union[DataclassType, DataclassType]:
    ...


def parse_args(types: Tuple[Type[DataclassType], ...], *args,
               **kwargs) -> Union[DataclassType, Tuple[DataclassType, ...]]:
    cmd_args_strs = None
    if len(args) > 0:
        cmd_args_strs = args[0]
    if 'args' in kwargs:
        cmd_args_strs = kwargs.pop('args')

    split_classes = False
    if len(args) > 1:
        split_classes = args[1]
    if 'split_classes' in kwargs:
        split_classes = kwargs.pop('split_classes')

    parser = BindingParser(*types)
    return parser.parse_into_dataclasses(
        types, args=cmd_args_strs, split_classes=split_classes
    )
