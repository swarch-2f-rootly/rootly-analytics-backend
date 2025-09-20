"""
Custom exceptions for the analytics service.
These exceptions represent domain-specific errors and are part of the core business logic.
"""


class AnalyticsServiceError(Exception):
    """Base exception for analytics service errors."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(message)


class InvalidMetricError(AnalyticsServiceError):
    """Raised when an unsupported metric is requested."""
    
    def __init__(self, metric_name: str, supported_metrics: list = None):
        self.metric_name = metric_name
        self.supported_metrics = supported_metrics
        message = f"Metric '{metric_name}' is not supported"
        if supported_metrics:
            message += f". Supported metrics: {', '.join(supported_metrics)}"
        super().__init__(message)


class RepositoryError(AnalyticsServiceError):
    """Raised when data repository operations fail."""
    
    def __init__(self, message: str, source_error: Exception = None):
        self.source_error = source_error
        details = str(source_error) if source_error else None
        super().__init__(message, details)


class DataIntegrityError(AnalyticsServiceError):
    """Raised when data integrity issues are detected."""
    pass


class InsufficientDataError(AnalyticsServiceError):
    """Raised when there's not enough data to perform analytics calculations."""
    
    def __init__(self, required_data: str, available_data: str = None):
        self.required_data = required_data
        self.available_data = available_data
        message = f"Insufficient data for calculation: {required_data}"
        if available_data:
            message += f". Available: {available_data}"
        super().__init__(message)


class ConfigurationError(AnalyticsServiceError):
    """Raised when service configuration is invalid."""
    pass


class ExternalServiceError(RepositoryError):
    """Raised when external service (Go backend) is unavailable or returns errors."""
    
    def __init__(self, service_name: str, status_code: int = None, response_body: str = None):
        self.service_name = service_name
        self.status_code = status_code
        self.response_body = response_body
        
        message = f"External service '{service_name}' error"
        if status_code:
            message += f" (HTTP {status_code})"
        
        details = response_body if response_body else None
        super().__init__(message, details)
