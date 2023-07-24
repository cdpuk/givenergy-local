import binascii
import inspect
import logging
import sys
from typing import Any

from loguru import logger


class InterceptHandler(logging.Handler):
    """Install loguru by intercepting logging."""

    def emit(self, record):
        """Redirect logging emissions to loguru instead."""
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def friendly_class_name(c: Any):
    """Provides an easy way to only show the class name."""
    if inspect.isclass(c):
        return str(c)[8:-2].rsplit(".", maxsplit=1)[-1]
    return friendly_class_name(c.__class__)  # + f'({vars(c)})'


def hexlify(val) -> str:
    """Provides an easy way to print long byte strings as hex strings."""
    if isinstance(val, int):
        val = val.to_bytes((val.bit_length() + 8) // 8, 'big')
    if isinstance(val, bytes):
        if sys.version_info < (3, 8):
            # TODO remove once 3.7 is unsupported
            return binascii.hexlify(val).decode('ascii')
        return binascii.hexlify(val, sep=' ', bytes_per_sep=4).decode('ascii')
    return str(val)


def hexxed(val):
    """Provides an easy way to print hex values when you might not always have ints."""
    if isinstance(val, (int, bytes)):
        return f'0x{val:04x}'
    return val
