"""
Unit tests for the Logger interface and StandardLogger implementation.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from src.core.ports.logger import Logger
from src.adapters.logger.standard_logger import StandardLogger


class TestLoggerInterface:
    """Test the Logger interface contract."""

    def test_logger_is_abstract(self):
        """Test that Logger cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Logger()


class TestStandardLogger:
    """Test cases for the StandardLogger implementation."""

    def test_standard_logger_creation(self):
        """Test creating a StandardLogger instance."""
        logger = StandardLogger("test")
        assert isinstance(logger, Logger)
        assert logger._logger.name == "test"

    def test_standard_logger_default_name(self):
        """Test creating a StandardLogger with default name."""
        logger = StandardLogger()
        assert logger._logger.name == "analytics"

    def test_standard_logger_info_logging(self):
        """Test info level logging."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("Test message")
            mock_info.assert_called_once_with("Test message")

    def test_standard_logger_error_logging(self):
        """Test error level logging."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'error') as mock_error:
            logger.error("Test error")
            mock_error.assert_called_once_with("Test error")

    def test_standard_logger_warn_logging(self):
        """Test warning level logging."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'warning') as mock_warning:
            logger.warn("Test warning")
            mock_warning.assert_called_once_with("Test warning")

    def test_standard_logger_debug_logging(self):
        """Test debug level logging."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'debug') as mock_debug:
            logger.debug("Test debug")
            mock_debug.assert_called_once_with("Test debug")

    def test_standard_logger_info_with_kwargs(self):
        """Test info logging with additional key-value pairs."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("Test message", key1="value1", key2="value2")
            mock_info.assert_called_once_with("Test message key1=value1 key2=value2")

    def test_standard_logger_error_with_kwargs(self):
        """Test error logging with additional key-value pairs."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'error') as mock_error:
            logger.error("Test error", error_code=500, user_id="123")
            mock_error.assert_called_once_with("Test error error_code=500 user_id=123")

    def test_standard_logger_warn_with_kwargs(self):
        """Test warning logging with additional key-value pairs."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'warning') as mock_warning:
            logger.warn("Test warning", component="api", action="retry")
            mock_warning.assert_called_once_with("Test warning component=api action=retry")

    def test_standard_logger_debug_with_kwargs(self):
        """Test debug logging with additional key-value pairs."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'debug') as mock_debug:
            logger.debug("Debug info", request_id="abc123", duration=150)
            mock_debug.assert_called_once_with("Debug info request_id=abc123 duration=150")

    def test_standard_logger_empty_kwargs(self):
        """Test logging with empty kwargs."""
        logger = StandardLogger("test")
        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("Test message", **{})
            mock_info.assert_called_once_with("Test message")

    def test_standard_logger_get_logger(self):
        """Test getting the underlying logger instance."""
        logger = StandardLogger("test")
        underlying = logger.get_logger()
        assert isinstance(underlying, logging.Logger)
        assert underlying.name == "test"

    def test_standard_logger_set_level(self):
        """Test setting the logging level."""
        logger = StandardLogger("test")
        logger.set_level(logging.DEBUG)

        # Check that the logger level was set
        assert logger._logger.level == logging.DEBUG

        # Check that handlers also have the correct level
        for handler in logger._logger.handlers:
            assert handler.level == logging.DEBUG

    def test_standard_logger_multiple_handlers(self):
        """Test that logger works with multiple handlers."""
        logger = StandardLogger("test")

        # The logger should have at least one handler (console)
        assert len(logger._logger.handlers) >= 1

        # Test logging still works
        with patch.object(logger._logger, 'info') as mock_info:
            logger.info("Test with multiple handlers")
            mock_info.assert_called_once()

    def test_standard_logger_formatter(self):
        """Test that the logger has proper formatting."""
        logger = StandardLogger("test")

        # Check that handlers have formatters
        for handler in logger._logger.handlers:
            assert handler.formatter is not None
            assert "%(asctime)s" in handler.formatter._fmt
            assert "%(name)s" in handler.formatter._fmt
            assert "%(levelname)s" in handler.formatter._fmt
            assert "%(message)s" in handler.formatter._fmt
