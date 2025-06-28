"""
Selenium-based automation strategy for AdsPower
File: strategies/selenium_strategy.py
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementNotInteractableException
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from adspower_automation.core.interfaces import AdsPowerAutomation, ElementLocatorType, AutomationMethod
from adspower_automation.core.exceptions import (
    ElementNotFoundError,
    AutomationTimeoutError,
    BrowserNotFoundError,
    AdsPowerAutomationError
)
from adspower_automation.models.profile import ProfileConfig, ProfileResponse
from adspower_automation.config.settings import AdsPowerConfig
from adspower_automation.utils.logger import get_logger


class SeleniumStrategy(AdsPowerAutomation):
    """
    Selenium-based implementation of AdsPower automation
    Handles web browser automation using Selenium WebDriver
    """
    
    def __init__(self, config: AdsPowerConfig):
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.actions: Optional[ActionChains] = None
        self.logger = get_logger(self.__class__.__name__, config)
        self._locator_map = self._create_locator_map()
    
    def _create_locator_map(self) -> Dict[ElementLocatorType, By]:
        """Create mapping between our locator types and Selenium By types"""
        return {
            ElementLocatorType.XPATH: By.XPATH,
            ElementLocatorType.CSS_SELECTOR: By.CSS_SELECTOR,
            ElementLocatorType.ID: By.ID,
            ElementLocatorType.CLASS_NAME: By.CLASS_NAME,
            ElementLocatorType.TAG_NAME: By.TAG_NAME,
            ElementLocatorType.LINK_TEXT: By.LINK_TEXT,
            ElementLocatorType.PARTIAL_LINK_TEXT: By.PARTIAL_LINK_TEXT
        }
    
    def is_available(self) -> bool:
        """Check if Selenium WebDriver is available"""
        try:
            # Try to create a headless browser instance
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            test_driver = webdriver.Chrome(options=options)
            test_driver.quit()
            return True
        except Exception as e:
            self.logger.error(f"Selenium not available: {str(e)}")
            return False
    
    async def initialize(self) -> bool:
        """Initialize Selenium WebDriver"""
        try:
            self.logger.info("Initializing Selenium WebDriver")
            
            options = Options()
            
            # Configure Chrome options
            if self.config.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument(f'--window-size={self.config.browser_width},{self.config.browser_height}')
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Initialize wait and actions
            self.wait = WebDriverWait(self.driver, self.config.default_timeout)
            self.actions = ActionChains(self.driver)
            
            self.logger.info("Selenium WebDriver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Selenium: {str(e)}")
            raise BrowserNotFoundError(f"Could not initialize Selenium WebDriver: {str(e)}")
    
    async def cleanup(self) -> None:
        """Clean up Selenium resources"""
        try:
            if self.driver:
                self.logger.info("Cleaning up Selenium WebDriver")
                self.driver.quit()
                self.driver = None
                self.wait = None
                self.actions = None
                self.logger.info("Selenium cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during Selenium cleanup: {str(e)}")
    
    def get_automation_method(self) -> AutomationMethod:
        """Get automation method type"""
        return AutomationMethod.SELENIUM
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            is_available = self.is_available()
            driver_active = self.driver is not None
            
            if driver_active:
                current_url = await self.get_current_url()
            else:
                current_url = None
            
            return {
                "method": self.get_automation_method().value,
                "available": is_available,
                "driver_active": driver_active,
                "current_url": current_url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "method": self.get_automation_method().value,
                "available": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # Element Location Methods
    async def find_element(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> Optional[Any]:
        """Find a single element using Selenium"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        if locator_type not in self._locator_map:
            raise AdsPowerAutomationError(f"Unsupported locator type: {locator_type}")
        
        try:
            by_type = self._locator_map[locator_type]
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by_type, locator))
            )
            self.logger.debug(f"Element found: {locator_type.value}='{locator}'")
            return element
        except TimeoutException:
            self.logger.warning(f"Element not found: {locator_type.value}='{locator}' (timeout: {timeout}s)")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element: {str(e)}")
            return None
    
    async def find_elements(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> List[Any]:
        """Find multiple elements using Selenium"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        if locator_type not in self._locator_map:
            raise AdsPowerAutomationError(f"Unsupported locator type: {locator_type}")
        
        try:
            by_type = self._locator_map[locator_type]
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by_type, locator))
            )
            elements = self.driver.find_elements(by_type, locator)
            self.logger.debug(f"Found {len(elements)} elements: {locator_type.value}='{locator}'")
            return elements
        except TimeoutException:
            self.logger.warning(f"No elements found: {locator_type.value}='{locator}' (timeout: {timeout}s)")
            return []
        except Exception as e:
            self.logger.error(f"Error finding elements: {str(e)}")
            return []
    
    async def wait_for_element(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> bool:
        """Wait for element to be present"""
        element = await self.find_element(locator, locator_type, timeout)
        return element is not None
    
    async def element_exists(self, locator: str, locator_type: ElementLocatorType, timeout: int = 5) -> bool:
        """Check if element exists"""
        return await self.wait_for_element(locator, locator_type, timeout)
    
    # Action Execution Methods
    async def click(self, element_or_coords: Any) -> bool:
        """Click on element or coordinates"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            if isinstance(element_or_coords, tuple):
                # Click on coordinates
                x, y = element_or_coords
                self.actions.move_by_offset(x, y).click().perform()
                self.actions.reset_actions()
            else:
                # Click on element
                element = element_or_coords
                WebDriverWait(self.driver, self.config.default_timeout).until(
                    EC.element_to_be_clickable(element)
                )
                element.click()
            
            self.logger.debug("Click action performed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Click failed: {str(e)}")
            return False
    
    async def type_text(self, element: Any, text: str, clear_first: bool = True) -> bool:
        """Type text into element"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            WebDriverWait(self.driver, self.config.default_timeout).until(
                EC.element_to_be_clickable(element)
            )
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            self.logger.debug(f"Text typed successfully: '{text[:50]}...' (length: {len(text)})")
            return True
            
        except Exception as e:
            self.logger.error(f"Type text failed: {str(e)}")
            return False
    
    async def wait(self, seconds: float) -> None:
        """Wait for specified seconds"""
        await asyncio.sleep(seconds)
    
    async def scroll_to_element(self, element: Any) -> bool:
        """Scroll to make element visible"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            await self.wait(0.5)  # Small delay for smooth scrolling
            self.logger.debug("Scrolled to element successfully")
            return True
        except Exception as e:
            self.logger.error(f"Scroll to element failed: {str(e)}")
            return False
    
    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            screenshots_dir = Path(self.config.screenshots_path)
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = screenshots_dir / filename
            self.driver.save_screenshot(str(filepath))
            
            self.logger.debug(f"Screenshot saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Screenshot failed: {str(e)}")
            raise AdsPowerAutomationError(f"Could not take screenshot: {str(e)}")
    
    # Web Automation Methods
    async def navigate_to_url(self, url: str) -> bool:
        """Navigate to a specific URL"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            self.logger.info(f"Navigating to URL: {url}")
            self.driver.get(url)
            await self.wait(2)  # Wait for page to load
            self.logger.info("Navigation completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Navigation failed: {str(e)}")
            return False
    
    async def get_current_url(self) -> str:
        """Get current page URL"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            return self.driver.current_url
        except Exception as e:
            self.logger.error(f"Could not get current URL: {str(e)}")
            return ""
    
    async def get_page_title(self) -> str:
        """Get current page title"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            return self.driver.title
        except Exception as e:
            self.logger.error(f"Could not get page title: {str(e)}")
            return ""
    
    async def refresh_page(self) -> bool:
        """Refresh the current page"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            self.driver.refresh()
            await self.wait(2)
            self.logger.debug("Page refreshed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Page refresh failed: {str(e)}")
            return False
    
    async def execute_javascript(self, script: str) -> Any:
        """Execute JavaScript code"""
        if not self.driver:
            raise AdsPowerAutomationError("WebDriver not initialized")
        
        try:
            result = self.driver.execute_script(script)
            self.logger.debug(f"JavaScript executed successfully")
            return result
        except Exception as e:
            self.logger.error(f"JavaScript execution failed: {str(e)}")
            return None
    
    # Profile Management Methods (Implementation depends on AdsPower API integration)
    async def create_profile(self, config: ProfileConfig) -> ProfileResponse:
        """Create a new profile - placeholder for API integration"""
        # This would integrate with AdsPower API
        self.logger.info(f"Creating profile: {config.name}")
        return ProfileResponse.error_response("Profile creation not implemented in Selenium strategy")
    
    async def open_profile(self, profile_id: str) -> ProfileResponse:
        """Open an existing profile"""
        self.logger.info(f"Opening profile: {profile_id}")
        return ProfileResponse.error_response("Profile opening not implemented in Selenium strategy")
    
    async def close_profile(self, profile_id: str) -> ProfileResponse:
        """Close a profile"""
        self.logger.info(f"Closing profile: {profile_id}")
        return ProfileResponse.error_response("Profile closing not implemented in Selenium strategy")
    
    async def delete_profile(self, profile_id: str) -> ProfileResponse:
        """Delete a profile"""
        self.logger.info(f"Deleting profile: {profile_id}")
        return ProfileResponse.error_response("Profile deletion not implemented in Selenium strategy")
    
    async def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles"""
        self.logger.info("Listing profiles")
        return []
    
    async def get_profile_status(self, profile_id: str) -> Optional[str]:
        """Get profile status"""
        self.logger.info(f"Getting status for profile: {profile_id}")
        return None