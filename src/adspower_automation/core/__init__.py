"""Core interfaces and exceptions for AdsPower automation"""

from adspower_automation.core.interfaces import (
    AutomationStrategy,
    ElementLocator,
    ActionExecutor,
    ProfileManager,
    WebAutomation,
    AdsPowerAutomation,
    AutomationMethod,
    ElementLocatorType
)

from adspower_automation.core.exceptions import (
    AdsPowerAutomationError,
    ProfileCreationError,
    ProfileNotFoundError,
    ElementNotFoundError,
    AutomationTimeoutError,
    AdsPowerAPIError,
    BrowserNotFoundError,
    ConfigurationError,
    StrategyNotAvailableError,
    RetryExhaustedError,
    ImageTemplateNotFoundError,
    ValidationError
)

__all__ = [
    # Interfaces
    "AutomationStrategy",
    "ElementLocator", 
    "ActionExecutor",
    "ProfileManager",
    "WebAutomation",
    "AdsPowerAutomation",
    "AutomationMethod",
    "ElementLocatorType",
    # Exceptions
    "AdsPowerAutomationError",
    "ProfileCreationError",
    "ProfileNotFoundError", 
    "ElementNotFoundError",
    "AutomationTimeoutError",
    "AdsPowerAPIError",
    "BrowserNotFoundError",
    "ConfigurationError",
    "StrategyNotAvailableError",
    "RetryExhaustedError",
    "ImageTemplateNotFoundError",
    "ValidationError"
]
