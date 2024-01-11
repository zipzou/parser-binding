from ..parser import BindingParser
from .test_utils import TestClass


def test_parser():
    parser = BindingParser(TestClass)
    parser.print_help()
