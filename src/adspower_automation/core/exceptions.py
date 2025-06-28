"""
Custom exceptions for AdsPower Automation Framework
File: core/exceptions.py
"""

from typing import Optional, Dict, Any


class AdsPowerAutomationError(Exception):
    """Base exception for AdsPower automation errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ProfileCreationError(AdsPowerAutomationError):
    """Exception raised when profile creation fails"""
    pass


class ProfileNotFoundError(AdsPowerAutomationError):
    """Exception raised when profile is not found"""
    pass


class ElementNotFoundError(AdsPowerAutomationError):
    """Exception raised when element cannot be found"""
    
    def __init__(self, locator: str, locator_type: str, timeout: int, **kwargs):
        message = f"Element not found: {locator_type}='{locator}' (timeout: {timeout}s)"
        super().__init__(message, **kwargs)
        self.locator = locator
        self.locator_type = locator_type
        self.timeout = timeout


class AutomationTimeoutError(AdsPowerAutomationError):
    """Exception raised when automation operation times out"""
    
    def __init__(self, operation: str, timeout: int, **kwargs):
        message = f"Operation '{operation}' timed out after {timeout} seconds"
        super().__init__(message, **kwargs)
        self.operation = operation
        self.timeout = timeout


class AdsPowerAPIError(AdsPowerAutomationError):
    """Exception raised when AdsPower API returns an error"""
    
    def __init__(self, api_response: Dict[str, Any], **kwargs):
        message = f"AdsPower API error: {api_response.get('msg', 'Unknown error')}"
        super().__init__(message, **kwargs)
        self.api_response = api_response


class BrowserNotFoundError(AdsPowerAutomationError):
    """Exception raised when browser cannot be found or started"""
    pass


class ConfigurationError(AdsPowerAutomationError):
    """Exception raised when configuration is invalid"""
    pass


class StrategyNotAvailableError(AdsPowerAutomationError):
    """Exception raised when automation strategy is not available"""
    
    def __init__(self, strategy_name: str, reason: str, **kwargs):
        message = f"Strategy '{strategy_name}' is not available: {reason}"
        super().__init__(message, **kwargs)
        self.strategy_name = strategy_name
        self.reason = reason


class RetryExhaustedError(AdsPowerAutomationError):
    """Exception raised when retry attempts are exhausted"""
    
    def __init__(self, operation: str, attempts: int, last_error: Optional[Exception] = None, **kwargs):
        message = f"Operation '{operation}' failed after {attempts} retry attempts"
        if last_error:
            message += f". Last error: {str(last_error)}"
        super().__init__(message, **kwargs)
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error


class ImageTemplateNotFoundError(AdsPowerAutomationError):
    """Exception raised when image template cannot be found"""
    
    def __init__(self, template_path: str, **kwargs):
        message = f"Image template not found: {template_path}"
        super().__init__(message, **kwargs)
        self.template_path = template_path


class ValidationError(AdsPowerAutomationError):
    """Exception raised when data validation fails"""
    
    def __init__(self, field: str, value: Any, reason: str, **kwargs):
        message = f"Validation failed for field '{field}' with value '{value}': {reason}"
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.reason = reason