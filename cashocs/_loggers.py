# Copyright (C) 2020-2022 Sebastian Blauth
#
# This file is part of cashocs.
#
# cashocs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cashocs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cashocs.  If not, see <https://www.gnu.org/licenses/>.

"""Logging module for cashocs."""

from __future__ import annotations

import logging
from typing import Any


class ColorFormatter(logging.Formatter):
    """Logging Formatter for colored output."""

    black = "\x1b[0;30m"
    grey = "\x1b[0;37m"
    green = "\x1b[0;32m"
    yellow = "\x1b[0;33m"
    red = "\x1b[0;31m"
    bold_red = "\x1b[1;31m"
    purple = "\x1b[0;35m"
    blue = "\x1b[0;34m"
    light_blue = "\x1b[0;36m"
    reset = "\x1b[0m"

    my_format = "%(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: green + my_format + reset,
        logging.INFO: blue + my_format + reset,
        logging.WARNING: yellow + my_format + reset,
        logging.ERROR: red + my_format + reset,
        logging.CRITICAL: bold_red + my_format + reset,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """See base class."""
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """See base class."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)

        return formatter.format(record)


class LogLevel:
    """Stores the various log levels of cashocs."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


_cashocs_logger = logging.getLogger("cashocs")
_cashocs_handler = logging.StreamHandler()
_cashocs_formatter = ColorFormatter()
_cashocs_handler.setFormatter(_cashocs_formatter)
_cashocs_logger.addHandler(_cashocs_handler)
_cashocs_logger.setLevel(LogLevel.INFO)


def set_log_level(level: int) -> None:
    """Determines the log level of cashocs.

    Can be used to show, e.g., info and warning messages or to hide them. There are a
    total of five different levels for the logs: ``DEBUG``, ``INFO``, ``WARNING``,
    ``ERROR``, and ``CRITICAL``. The usage of this method is explained in the examples
    section.

    Args:
        level: Should be one of ``cashocs.LogLevel.DEBUG``, ``cashocs.LogLevel.INFO``,
            ``cashocs.LogLevel.WARNING``, ``cashocs.LogLevel.ERROR``,
            ``cashocs.LogLevel.CRITICAL``

    Notes:
        The log level setting is global, so if you use this interactively, you have to
        restart / reload your interactive console to return to the default settings.

    Examples:
        To set the log level of cashocs, use this method as follows::

            import cashocs

            cashocs.set_log_level(cashocs.LogLevel.WARNING)

        which only shows messages with a level of ``WARNING`` or higher.
        To use a different level, replace ``WARNING`` by ``DEBUG``, ``INFO``, ``ERROR``,
        or ``CRITICAL``.

    """
    _cashocs_logger.setLevel(level)


def debug(message: str) -> None:
    """Issues a debug level logging message.

    Args:
        message: The message to be issued.

    """
    _cashocs_logger.debug(message)


def info(message: str) -> None:
    """Issues an info level logging message.

    Args:
        message: The message to be issued.

    """
    _cashocs_logger.info(message)


def warning(message: str) -> None:
    """Issues a warning level logging message.

    Args:
        message: The message to be issued.

    """
    _cashocs_logger.warning(message)


def error(message: str) -> None:
    """Issues a error level logging message.

    Args:
        message: The message to be issued.

    """
    _cashocs_logger.error(message)


def critical(message: str) -> None:
    """Issues a critical level logging message.

    Args:
        message: The message to be issued.

    """
    _cashocs_logger.critical(message)
