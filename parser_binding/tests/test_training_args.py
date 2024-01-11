from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from ..parser import BindingParser
from ..types import BindingField


class OptimizerType(Enum):
    Adam = 'adam'
    SGD = 'sgd'
    LAMB = 'lamb'


@dataclass
class DataArguments:
    train_file: Optional[List[str]] = None
    dev_file: Optional[List[str]] = None
    test_file: Optional[List[str]] = None


@dataclass
class TraningArguments:
    train: bool = True
    dev: bool = False
    test: bool = False
    batch_size: int = 32
    learning_rate: float = 1e-3
    optimizer: OptimizerType = OptimizerType.Adam
    weight_decay: float = .1
    eps: float = 1e-6
    beta1: float = .9
    beta2: float = .99
    gradients_accumulate_step: int = 1


@dataclass
class IOArguments:
    output_dir: str = BindingField(
        default='./output',
        aliases=['o'],
        help='The output path to save the data.'
    )
    save_step: int = 1
    dev_step: int = 100
    test_step: int = 100
    epoch: int = 1
    max_steps: int = 10000
    train_mode: Literal[1, 2] = 1


@dataclass
class ModelArguments:
    model_config: Dict[str, Any] = './config.json'


def test_bind_to_dataclasses():

    parser = BindingParser(
        DataArguments, TraningArguments, IOArguments, ModelArguments
    )

    parser.print_help()

    arg_strs = [
        '-o', 'checkpoints', '--train-file', './a.txt', './b.txt',
        '--optimizer', 'sgd', '--train-mode', '2'
    ]
    args = parser.parse_into_dataclasses(
        (DataArguments, TraningArguments, IOArguments, ModelArguments),
        arg_strs
    )

    assert tuple(args.train_file) == ('./a.txt', './b.txt')
    assert args.output_dir == 'checkpoints'
    assert args.train_mode == 2
    assert args.optimizer is OptimizerType.SGD
    assert args.gradients_accumulate_step == 1

    args2 = parser.parse_into_dataclasses(
        (DataArguments, TraningArguments), arg_strs
    )

    assert type(args) is not type(args2)
