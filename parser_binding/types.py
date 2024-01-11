'''
defined the data classes to bind the argument parser.
'''
import gzip
import sys
from argparse import ArgumentTypeError, FileType
from dataclasses import MISSING, dataclass, field
from enum import Enum
from typing import IO, Any, Callable, List, Optional, Set, TypeVar

DataclassType = TypeVar('DataclassType')
_ActualDType = TypeVar('_ActualDType')


def is_shortcut(name: str) -> bool:
    '''
        Check whether the argument name is a shortcut.

        Args:
            - name: `str`, the name of argument.
        
        Returns:
            True if the name is a shortcut option, otherwise False.
    '''
    if '_' in name or len(name) > 1:
        return False

    return True


class DataWrapperType(Enum):
    '''
        Enum representing wrapper types for dataclass fields.

        This enum defines various wrapper types that can be applied to dataclass fields,
        determining the conversion method used to obtain the final field value.

        Wrapper Types:
        - Basic: Simple or primitive data types.
        - List: List collection type.
        - Tuple: Tuple collection type.
        - Dict: Dictionary collection type.
        - Set: Set collection type.
        - Queue: Queue collection type.
        - Dequeue: Deque collection type.
        - Literal: Literal types (e.g., str, int, bool).
        - Enum: Enumerated types.
        - Bool: Boolean type.
        - Complex: Complex class types (e.g. user defined classes or nested types).
        - Unknown: Unidentified or unspecified type.

        The type is used to determine which conversion method is applied to obtain the
        final field value during dataclass instantiation.
    '''
    Basic = 'basic'
    List = 'list'
    Tuple = 'tuple'
    Dict = 'dict'
    Set = 'set'
    Queue = 'queue'
    Dequeue = 'dequeue'
    Literal = 'literal'
    Enum = 'enum'
    Bool = 'bool'
    File = 'file'
    Complex = 'complex'
    Unknown = 'unknown'

    @staticmethod
    def is_basic_collection(type: 'DataWrapperType') -> bool:
        if type is DataWrapperType.List or \
            type is DataWrapperType.Tuple or \
            type is DataWrapperType.Set or \
            type is DataWrapperType.Queue or \
            type is DataWrapperType.Dequeue:
            return True
        return False


class FileTypeWithGzip(FileType):

    def __init__(
        self,
        mode: str = "r",
        bufsize: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        content_type: Optional[_ActualDType] = None
    ) -> None:
        super(FileTypeWithGzip, self).__init__(mode, bufsize, encoding, errors)
        self.content_type = content_type

    def __call__(self, string: str) -> IO[Any]:
        if not string.endswith('.gz'):
            return super(FileTypeWithGzip, self).__call__(string)
        else:
            try:
                mode = self._mode
                if self.content_type is str:
                    mode = 'rt' if mode == 'r' else self._mode
                return gzip.open(string, mode, self._encoding)
            except OSError as e:
                raise ArgumentTypeError("can't open '%s': %s" % (string, e))


@dataclass
class BindingType:
    '''
        The binding type used to store the value from dataclass fields and bind to the argument parser.

        Attributes:
        - name (str):
            The name of the binding type.
        - type (Optional[Callable], optional):
            The type conversion function for the binding type.
        - aliases (Optional[List[str]], optional):
            List of alternative names for the binding type.
        - choices (Optional[List[_ActualDType]], optional):
            List of valid choices for the binding type.
        - multiple (bool, optional):
            Indicates whether the binding type supports multiple values.
        - default (Optional[_ActualDType], optional):
            Default value for the binding type.
        - separator (Optional[str], optional):
            Separator for multiple values (e.g., for choices).
        - wrapper_type (DataWrapperType, optional):
            The wrapper type for the binding type.
        - required (bool, optional):
            Indicates whether the binding type is required.
        - help (str, optional):
            Help text for the binding type.
        - file (bool, optional):
            Indicates whether the binding type represents a file path.
        - file_mode (str, optional):
            File mode (e.g., 'r' or 'w') for file fields.
        - file_encoding (str, optional):
            File encoding for file fields.

        The BindingType class is used to define metadata for storing values from dataclass fields
        and facilitating binding to the argument parser.
    '''
    name: str
    type: Optional[Callable] = None
    aliases: Optional[List[str]] = None
    choices: Optional[List[_ActualDType]] = None
    multiple: bool = False
    default: Optional[_ActualDType] = None
    seperator: Optional[str] = None
    wrapper_type: DataWrapperType = DataWrapperType.Basic
    required: bool = False
    help: str = ''
    file: bool = False
    file_mode: str = 'r'
    file_encoding: str = 'utf-8'

    @property
    def default_file(self):
        if (
            self.default == '-' and self.file_mode == 'r'
        ) or self.default is sys.stdin:
            return sys.stdin
        elif (
            self.default == '-' and self.file_mode == 'w'
        ) or self.default is sys.stdout:
            return sys.stdout
        else:
            return self.default

    @property
    def help_suffix(self) -> str:
        doc_suffix = []
        if self.multiple and self.seperator is not None:
            doc_suffix.append(
                f'A string with multiple values, and each is splitted with "{self.seperator}"'
            )
        if self.wrapper_type is DataWrapperType.Dict:
            doc_suffix.append(
                'A JSON string or a JSON file to convert to a dictionary object.'
            )
        if not self.required:
            fmt_default_val = self.default
            if isinstance(fmt_default_val, Enum):
                fmt_default_val = fmt_default_val.value
            if self.wrapper_type is not DataWrapperType.Bool:
                doc_suffix.append(f'Optional. Default `{fmt_default_val}`.')
            else:
                if self.default:
                    doc_suffix.append(
                        f'Optional. Default `False` as {self.name} enabled.'
                    )
                else:
                    doc_suffix.append(
                        f'Optional. Default `False` as {self.name} disabled.'
                    )
        else:
            doc_suffix.append(f'REQUIRED.')

        return ' '.join(doc_suffix)

    @property
    def action(self) -> Optional[bool]:
        if self.wrapper_type is not DataWrapperType.Bool:
            return None
        if self.default is True:
            return 'store_false'
        else:
            return 'store_true'

    @property
    def is_switch(self) -> bool:
        if self.wrapper_type is not DataWrapperType.Bool:
            return False
        else:
            return True

    @property
    def options(self) -> List[str]:
        names = set([self.name])
        if self.aliases is not None:
            names.update(self.aliases)

        final_options: Set[str] = set()
        for name in names:
            if self.wrapper_type is DataWrapperType.Bool:
                if self.default is True:
                    final_options.add('--without-' + name.replace('_', '-'))
                    final_options.add('--without_' + name.replace('-', '_'))
                else:
                    final_options.add('--with-' + name.replace('_', '-'))
                    final_options.add('--with_' + name.replace('-', '_'))
            else:
                if is_shortcut(name):
                    final_options.add('-' + name)
                else:
                    final_options.add('--' + name.replace('-', '_'))
                    final_options.add('--' + name.replace('_', '-'))

        def compare_option(option: str):
            if len(option[1:]) <= 1:
                return -1
            if option.startswith('--'):
                if '_' not in option:
                    return 0
                elif '-' in option:
                    return 1
            else:
                return 2

        final_options = sorted(list(final_options), key=compare_option)

        return final_options


def BindingField(
    default: Optional[Any] = MISSING,
    default_factory: Optional[Callable] = MISSING,
    type: Optional[Callable] = None,
    required: bool = False,
    sep: Optional[str] = None,
    choices: Optional[List[str]] = None,
    aliases: Optional[List[str]] = None,
    help: Optional[str] = None,
    file: bool = False,
    file_mode: Optional[str] = None,
    file_encoding: Optional[str] = None
):
    '''
        Create a dataclass field with additional parsing information.

        This function generates a dataclass field with metadata based on the provided
        parameters. It is designed to facilitate the integration of the field with
        argument parsers.

        Note: The priority in the metadata is higher than inference based on the logic.

        Parameters:
        - default (`Optional[Any]`, optional):
            Default value for the field. Defaults to MISSING.
        - default_factory (`Optional[Callable]`, optional):
            Default factory for the field. Defaults to MISSING. If all the `default` and the `default_factory` are MISSING, this option is expected to be required.
        - type (`Optional[Callable]`, optional):
            Type conversion function for the field. Use type hint if this is not provided.
        - required (`bool`, optional):
            Indicates whether the field is required. Defaults to False.
        - sep (`Optional[str]`, optional):
            Separator for multiple values (e.g., for choices). Defaults to None.
        - choices (`Optional[List[str]]`, optional):
            List of valid choices for the field.
        - aliases (`Optional[List[str]]`, optional):
            List of alternative names for the field.
        - help (`Optional[str]`, optional):
            Help text for the field.
        - file (`bool`, optional):
            Indicates whether the field represents a file path. Defaults to False.
        - file_mode (`Optional[str]`, optional):
            File mode (e.g., 'r' or 'w') for file fields.
        - file_encoding (`Optional[str]`, optional):
            File encoding for file fields.

        Returns:
        - `dataclasses.Field`:
            A dataclass field with the specified metadata.
    '''
    meta_info = {}
    if type is not None:
        meta_info['type'] = type
    meta_info['required'] = required
    meta_info['choices'] = choices
    meta_info['sep'] = sep

    if help is not None:
        meta_info['help'] = help
    if file is not None:
        meta_info['file'] = file
        meta_info['type'] = file
        meta_info.pop('sep')
        meta_info.pop('choices')
    if file_mode is not None:
        meta_info['file_mode'] = file_mode
    if file_encoding is not None:
        meta_info['file_encoding'] = file_encoding
    if aliases is not None:
        meta_info['aliases'] = aliases

    if required or (default is MISSING and default_factory is MISSING):
        return field(metadata=meta_info)
    elif default is not MISSING:
        return field(default=default, metadata=meta_info)
    else:
        return field(default_factory=default_factory, metadata=meta_info)
