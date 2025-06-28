"""
Core interfaces and abstract classes for AdsPower Automation Framework
File: core/interfaces.py
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
import asyncio
from enum import Enum

from adspower_automation.models.profile import ProfileConfig, ProfileResponse


class AutomationMethod(Enum):
    """Automation method types"""
    SELENIUM = "selenium"
    PYAUTOGUI = "pyautogui" 
    API = "api"
    HYBRID = "hybrid"


class ElementLocatorType(Enum):
    """Element locator types"""
    XPATH = "xpath"
    CSS_SELECTOR = "css"
    ID = "id"
    CLASS_NAME = "class"
    TAG_NAME = "tag"
    LINK_TEXT = "link_text"
    PARTIAL_LINK_TEXT = "partial_link_text"
    IMAGE = "image"
    COORDINATES = "coordinates"


class AutomationStrategy(ABC):
    """Abstract base class for automation strategies"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the automation strategy is available and can be used"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the automation strategy"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources used by the strategy"""
        pass
    
    @abstractmethod
    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot and return the file path"""
        pass


class ElementLocator(ABC):
    """Abstract base class for element location strategies"""
    
    @abstractmethod
    async def find_element(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> Optional[Any]:
        """Find a single element"""
        pass
    
    @abstractmethod
    async def find_elements(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> List[Any]:
        """Find multiple elements"""
        pass
    
    @abstractmethod
    async def wait_for_element(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> bool:
        """Wait for element to be present"""
        pass
    
    @abstractmethod
    async def element_exists(self, locator: str, locator_type: ElementLocatorType, timeout: int = 5) -> bool:
        """Check if element exists without waiting long"""
        pass


class ActionExecutor(ABC):
    """Abstract base class for action execution"""
    
    @abstractmethod
    async def click(self, element_or_coords: Any) -> bool:
        """Click on element or coordinates"""
        pass
    
    @abstractmethod
    async def type_text(self, element: Any, text: str, clear_first: bool = True) -> bool:
        """Type text into element"""
        pass
    
    @abstractmethod
    async def wait(self, seconds: float) -> None:
        """Wait for specified seconds"""
        pass
    
    @abstractmethod
    async def scroll_to_element(self, element: Any) -> bool:
        """Scroll to make element visible"""
        pass


class ProfileManager(ABC):
    """Abstract base class for profile management"""
    
    @abstractmethod
    async def create_profile(self, config: ProfileConfig) -> ProfileResponse:
        """Create a new profile"""
        pass
    
    @abstractmethod
    async def open_profile(self, profile_id: str) -> ProfileResponse:
        """Open an existing profile"""
        pass
    
    @abstractmethod
    async def close_profile(self, profile_id: str) -> ProfileResponse:
        """Close a profile"""
        pass
    
    @abstractmethod
    async def delete_profile(self, profile_id: str) -> ProfileResponse:
        """Delete a profile"""
        pass
    
    @abstractmethod
    async def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles"""
        pass
    
    @abstractmethod
    async def get_profile_status(self, profile_id: str) -> Optional[str]:
        """Get profile status"""
        pass


class WebAutomation(ABC):
    """Abstract base class for web automation tasks"""
    
    @abstractmethod
    async def navigate_to_url(self, url: str) -> bool:
        """Navigate to a specific URL"""
        pass
    
    @abstractmethod
    async def get_current_url(self) -> str:
        """Get current page URL"""
        pass
    
    @abstractmethod
    async def get_page_title(self) -> str:
        """Get current page title"""
        pass
    
    @abstractmethod
    async def refresh_page(self) -> bool:
        """Refresh the current page"""
        pass
    
    @abstractmethod
    async def execute_javascript(self, script: str) -> Any:
        """Execute JavaScript code"""
        pass


class AdsPowerAutomation(AutomationStrategy, ElementLocator, ActionExecutor, ProfileManager, WebAutomation):
    """
    Main automation interface that combines all capabilities
    This will be implemented by concrete automation classes
    """
    
    @abstractmethod
    def get_automation_method(self) -> AutomationMethod:
        """Get the automation method used by this implementation"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the automation system"""
        pass