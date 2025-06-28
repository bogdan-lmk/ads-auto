"""AdsPower Automation Framework package."""

from .config.settings import AdsPowerConfig, load_config
from .services.profile_service import AdsPowerProfileService
from .models.profile import (
    ProfileConfig,
    ProfileResponse,
    ProfileStatus,
    PlatformType,
    ProxyType,
    ProxySettings,
    BrowserSettings,
)
from .core.interfaces import (
    AutomationStrategy,
    ElementLocator,
    ActionExecutor,
    ProfileManager,
    WebAutomation,
    AdsPowerAutomation,
    AutomationMethod,
    ElementLocatorType,
)
from .core.exceptions import (
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
    ValidationError,
)
from .strategies.selenium_strategy import SeleniumStrategy
from .strategies.pyautogui_strategy import PyAutoGUIStrategy
from .utils.logger import get_logger, AdsPowerLogger

__all__ = [
    "load_config",
    "AdsPowerConfig",
    "AdsPowerProfileService",
    "ProfileConfig",
    "ProfileResponse",
    "ProfileStatus",
    "PlatformType",
    "ProxyType",
    "ProxySettings",
    "BrowserSettings",
    "AutomationStrategy",
    "ElementLocator",
    "ActionExecutor",
    "ProfileManager",
    "WebAutomation",
    "AdsPowerAutomation",
    "AutomationMethod",
    "ElementLocatorType",
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
    "ValidationError",
    "SeleniumStrategy",
    "PyAutoGUIStrategy",
    "get_logger",
    "AdsPowerLogger",
]

__version__ = "1.0.0"
__author__ = "AdsPower Automation Team"
