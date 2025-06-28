# File: __init__.py (main package)
"""
AdsPower Automation Framework

A modern, modular Python automation framework for AdsPower profile management.
Supports both desktop automation (PyAutoGUI) and web automation (Selenium).
"""

__version__ = "1.0.0"
__author__ = "AdsPower Automation Team"

# Import only the most essential components to avoid circular imports
from adspower_automation.config.settings import load_config
from adspower_automation.models.profile import ProfileConfig, ProfileResponse

__all__ = [
    "load_config",
    "AdsPowerConfig", 
    "AdsPowerProfileService",
    "ProfileConfig",
    "ProfileResponse",
    "PlatformType",
    "AutomationMethod"
]

# File: config/__init__.py
"""Configuration module for AdsPower automation"""

from .config.settings import load_config, AdsPowerConfig

__all__ = ["load_config", "AdsPowerConfig"]

# File: models/__init__.py
"""Data models for AdsPower automation"""

from .models.profile import (
    ProfileConfig,
    ProfileResponse, 
    ProfileStatus,
    PlatformType,
    ProxyType,
    ProxySettings,
    BrowserSettings
)

__all__ = [
    "ProfileConfig",
    "ProfileResponse",
    "ProfileStatus", 
    "PlatformType",
    "ProxyType",
    "ProxySettings",
    "BrowserSettings"
]

# File: core/__init__.py
"""Core interfaces and exceptions for AdsPower automation"""

from .interfaces import (
    AutomationStrategy,
    ElementLocator,
    ActionExecutor,
    ProfileManager,
    WebAutomation,
    AdsPowerAutomation,
    AutomationMethod,
    ElementLocatorType
)

from .exceptions import (
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

# File: strategies/__init__.py
"""Automation strategy implementations"""

from .selenium_strategy import SeleniumStrategy
from .pyautogui_strategy import PyAutoGUIStrategy

__all__ = ["SeleniumStrategy", "PyAutoGUIStrategy"]

# File: services/__init__.py
"""Service layer for AdsPower automation"""

from .profile_service import AdsPowerProfileService

__all__ = ["AdsPowerProfileService"]

# File: utils/__init__.py
"""Utility modules for AdsPower automation"""

from .logger import get_logger, AdsPowerLogger

__all__ = ["get_logger", "AdsPowerLogger"]

# File: requirements.txt
"""
# Core automation libraries
selenium>=4.15.0
pyautogui>=0.9.54
opencv-python>=4.8.0
Pillow>=10.0.0

# Data validation and configuration
pydantic>=2.4.0

# Async support
asyncio

# Image processing (for template matching)
numpy>=1.24.0

# Optional: Web driver management
webdriver-manager>=4.0.0

# Optional: Window management (for better desktop automation)
pygetwindow>=0.0.9

# Optional: API client for AdsPower API integration
requests>=2.31.0
aiohttp>=3.8.0

# Development dependencies (optional)
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.9.0
flake8>=6.0.0
mypy>=1.6.0
"""
