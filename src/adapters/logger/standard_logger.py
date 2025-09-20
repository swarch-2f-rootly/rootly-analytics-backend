"""
Standard logger implementation using Python's built-in logging module.
This implements the Logger interface using the standard library.
"""

import logging
import sys
from typing import Any

from ...core.ports.logger import Logger


class StandardLogger(Logger):
    """
    Standard logger implementation that uses Python's built-in logging module.
    Provides structured logging with configurable formatters and handlers.
    """

    def __init__(self, name: str = "analytics", level: int = logging.INFO):
        """
        Initialize the standard logger.

        Args:
            name: Logger name for identification
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # Avoid duplicate handlers
        if not self._logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup logging handlers with appropriate formatters."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._logger.level)

        # Create formatter with structured output
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)

        self._logger.addHandler(console_handler)

    def info(self, message: str, **kwargs: Any) -> None:
        """
        Log an informational message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        if kwargs:
            # Format kwargs as key=value pairs
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            message = f"{message} {extra_info}"

        self._logger.info(message)

    def error(self, message: str, **kwargs: Any) -> None:
        """
        Log an error message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        if kwargs:
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            message = f"{message} {extra_info}"

        self._logger.error(message)

    def warn(self, message: str, **kwargs: Any) -> None:
        """
        Log a warning message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        if kwargs:
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            message = f"{message} {extra_info}"

        self._logger.warning(message)

    def debug(self, message: str, **kwargs: Any) -> None:
        """
        Log a debug message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        if kwargs:
            extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
            message = f"{message} {extra_info}"

        self._logger.debug(message)

    def set_level(self, level: int) -> None:
        """
        Set the logging level.

        Args:
            level: New logging level (e.g., logging.DEBUG, logging.INFO)
        """
        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)

    def get_logger(self) -> logging.Logger:
        """
        Get the underlying logging.Logger instance.

        Returns:
            The underlying Python logger instance
        """
        return self._logger
