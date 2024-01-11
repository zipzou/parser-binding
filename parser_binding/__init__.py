'''
Custom parser to bind the command-line arguments to the dataclass.
'''
from .parser import BindingParser, ComamndLineParser, parse_args
from .types import BindingField

Field = BindingField
