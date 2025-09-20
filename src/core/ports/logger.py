"""
Logger interface for the analytics service.
This defines the contract for logging operations, allowing technology-agnostic
logging that can be easily replaced or mocked.
"""

from abc import ABC, abstractmethod
from typing import Any


class Logger(ABC):
    """
    Logger defines the interface for logging operations.
    This allows for technology-agnostic logging that can be easily replaced or mocked.
    """

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """
        Log an informational message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        pass

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """
        Log an error message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        pass

    @abstractmethod
    def warn(self, message: str, **kwargs: Any) -> None:
        """
        Log a warning message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        pass

    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """
        Log a debug message.

        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log
        """
        pass
