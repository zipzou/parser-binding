from argparse import ArgumentParser
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..types import BindingField
from ..utils import analysis_dataclass


class TestEnum(Enum):
    a = 0
    b = 1


@dataclass
class TestClass:
    must: int
    complex_field: List[str] = BindingField(
        required=False, choices=['one', 'two'], aliases=['f']
    )
    a: int = 0
    b: str = 0
    c: float = 0.0
    name: Optional[str] = 'hello'
    long_param: Optional[int] = None
    json: Optional[Dict[str, str]] = None
    kind: TestEnum = TestEnum.a
    values: List[str] = None
    multiple: Tuple[str] = field(default=None, metadata={
        'sep': ','
    })
    success: bool = True
    failed: Optional[bool] = None
    mode: set = None
    two_dim_arr: Optional[List[List[str]]] = None
    input_file: Optional[str] = field(
        default='./.style.yapf',
        metadata={
            'aliases': ['i'],
            'file': True,
            'file_mode': 'r',
            'file_encoding': 'utf-8'
        }
    )


def test_utils():

    res = analysis_dataclass(TestClass)

    parser = ArgumentParser()
    for name, _type in res.items():
        kwargs = {
            'action': _type.action,
            'nargs':
            '*' if _type.multiple and _type.seperator is None else None,
            'default': _type.default,
            'type': _type.type,
            'choices': _type.choices,
            'help': ' '.join((_type.help, _type.help_suffix))
        }
        if _type.is_switch:
            for k in ('nargs', 'type', 'choices'):
                kwargs.pop(k)
        parser.add_argument(*_type.options, **kwargs)

    parser.print_help()
