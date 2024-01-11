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
    a: bool = False


if __name__ == '__main__':
    parser = BindingParser(TestOptions)

    options = parser.parse_into_dataclasses((TestOptions, ))

    print(options)
