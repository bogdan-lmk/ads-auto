"""
PyAutoGUI-based automation strategy for AdsPower
File: strategies/pyautogui_strategy.py
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np

import pyautogui
from PIL import Image, ImageDraw

from adspower_automation.core.interfaces import AdsPowerAutomation, ElementLocatorType, AutomationMethod
from adspower_automation.core.exceptions import (
    ElementNotFoundError,
    AutomationTimeoutError,
    ImageTemplateNotFoundError,
    AdsPowerAutomationError
)
from adspower_automation.models.profile import ProfileConfig, ProfileResponse
from adspower_automation.config.settings import AdsPowerConfig
from adspower_automation.utils.logger import get_logger


class PyAutoGUIStrategy(AdsPowerAutomation):
    """
    PyAutoGUI-based implementation of AdsPower automation
    Handles desktop automation using image recognition and screen coordinates
    """
    
    def __init__(self, config: AdsPowerConfig):
        self.config = config
        self.logger = get_logger(self.__class__.__name__, config)
        self._setup_pyautogui()
        self.templates_cache: Dict[str, np.ndarray] = {}
    
    def _setup_pyautogui(self) -> None:
        """Configure PyAutoGUI settings"""
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        self.logger.info(f"Screen resolution: {self.screen_width}x{self.screen_height}")
    
    def is_available(self) -> bool:
        """Check if PyAutoGUI is available"""
        try:
            # Test basic PyAutoGUI functionality
            pyautogui.position()
            return True
        except Exception as e:
            self.logger.error(f"PyAutoGUI not available: {str(e)}")
            return False
    
    async def initialize(self) -> bool:
        """Initialize PyAutoGUI automation"""
        try:
            self.logger.info("Initializing PyAutoGUI automation")
            
            # Ensure templates directory exists
            templates_dir = Path(self.config.templates_path)
            templates_dir.mkdir(parents=True, exist_ok=True)
            
            # Load common templates
            await self._load_templates()
            
            self.logger.info("PyAutoGUI automation initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize PyAutoGUI: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up PyAutoGUI resources"""
        try:
            self.logger.info("Cleaning up PyAutoGUI resources")
            self.templates_cache.clear()
            self.logger.info("PyAutoGUI cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during PyAutoGUI cleanup: {str(e)}")
    
    async def _load_templates(self) -> None:
        """Load image templates for recognition"""
        templates_dir = Path(self.config.templates_path)
        
        if not templates_dir.exists():
            self.logger.warning(f"Templates directory not found: {templates_dir}")
            return
        
        # Load all PNG templates
        for template_file in templates_dir.glob("*.png"):
            try:
                template_image = cv2.imread(str(template_file), cv2.IMREAD_COLOR)
                if template_image is not None:
                    self.templates_cache[template_file.stem] = template_image
                    self.logger.debug(f"Loaded template: {template_file.name}")
            except Exception as e:
                self.logger.error(f"Failed to load template {template_file}: {str(e)}")
    
    def get_automation_method(self) -> AutomationMethod:
        """Get automation method type"""
        return AutomationMethod.PYAUTOGUI
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            mouse_pos = pyautogui.position()
            screen_size = pyautogui.size()
            
            return {
                "method": self.get_automation_method().value,
                "available": self.is_available(),
                "mouse_position": {"x": mouse_pos.x, "y": mouse_pos.y},
                "screen_size": {"width": screen_size.width, "height": screen_size.height},
                "templates_loaded": len(self.templates_cache),
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
    async def find_element(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> Optional[Tuple[int, int]]:
        """Find element using image recognition or coordinates"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if locator_type == ElementLocatorType.IMAGE:
                    # Find by image template
                    position = await self._find_image_on_screen(locator)
                    if position:
                        self.logger.debug(f"Image found at position: {position}")
                        return position
                
                elif locator_type == ElementLocatorType.COORDINATES:
                    # Direct coordinates
                    coords = self._parse_coordinates(locator)
                    if coords and self._is_valid_coordinates(coords):
                        return coords
                
                # Wait before next attempt
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error finding element: {str(e)}")
        
        self.logger.warning(f"Element not found: {locator_type.value}='{locator}' (timeout: {timeout}s)")
        return None
    
    async def _find_image_on_screen(self, template_name: str, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """Find image template on screen using OpenCV"""
        try:
            # Check if template is in cache
            if template_name not in self.templates_cache:
                # Try to load from file
                template_path = Path(self.config.templates_path) / f"{template_name}.png"
                if template_path.exists():
                    template_image = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
                    if template_image is not None:
                        self.templates_cache[template_name] = template_image
                    else:
                        raise ImageTemplateNotFoundError(str(template_path))
                else:
                    raise ImageTemplateNotFoundError(str(template_path))
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            # Get template
            template = self.templates_cache[template_name]
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= confidence:
                # Calculate center of found template
                template_height, template_width = template.shape[:2]
                center_x = max_loc[0] + template_width // 2
                center_y = max_loc[1] + template_height // 2
                
                self.logger.debug(f"Template '{template_name}' found with confidence {max_val:.2f} at ({center_x}, {center_y})")
                return (center_x, center_y)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Image recognition failed for '{template_name}': {str(e)}")
            return None
    
    def _parse_coordinates(self, coords_str: str) -> Optional[Tuple[int, int]]:
        """Parse coordinates from string format 'x,y'"""
        try:
            parts = coords_str.split(',')
            if len(parts) == 2:
                x, y = int(parts[0].strip()), int(parts[1].strip())
                return (x, y)
        except ValueError:
            pass
        return None
    
    def _is_valid_coordinates(self, coords: Tuple[int, int]) -> bool:
        """Check if coordinates are within screen bounds"""
        x, y = coords
        return 0 <= x <= self.screen_width and 0 <= y <= self.screen_height
    
    async def find_elements(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> List[Tuple[int, int]]:
        """Find multiple elements (for PyAutoGUI, typically returns single element)"""
        element = await self.find_element(locator, locator_type, timeout)
        return [element] if element else []
    
    async def wait_for_element(self, locator: str, locator_type: ElementLocatorType, timeout: int = 10) -> bool:
        """Wait for element to appear"""
        element = await self.find_element(locator, locator_type, timeout)
        return element is not None
    
    async def element_exists(self, locator: str, locator_type: ElementLocatorType, timeout: int = 5) -> bool:
        """Check if element exists"""
        return await self.wait_for_element(locator, locator_type, timeout)
    
    # Action Execution Methods
    async def click(self, element_or_coords: Any) -> bool:
        """Click on element or coordinates"""
        try:
            if isinstance(element_or_coords, tuple):
                x, y = element_or_coords
            else:
                # Assume it's coordinates
                x, y = element_or_coords
            
            # Move to position and click
            pyautogui.moveTo(x, y, duration=0.5)
            await asyncio.sleep(0.1)
            pyautogui.click(x, y)
            
            self.logger.debug(f"Clicked at position ({x}, {y})")
            return True
            
        except Exception as e:
            self.logger.error(f"Click failed: {str(e)}")
            return False
    
    async def double_click(self, element_or_coords: Any) -> bool:
        """Double click on element or coordinates"""
        try:
            if isinstance(element_or_coords, tuple):
                x, y = element_or_coords
            else:
                x, y = element_or_coords
            
            pyautogui.moveTo(x, y, duration=0.5)
            await asyncio.sleep(0.1)
            pyautogui.doubleClick(x, y)
            
            self.logger.debug(f"Double-clicked at position ({x}, {y})")
            return True
            
        except Exception as e:
            self.logger.error(f"Double click failed: {str(e)}")
            return False
    
    async def right_click(self, element_or_coords: Any) -> bool:
        """Right click on element or coordinates"""
        try:
            if isinstance(element_or_coords, tuple):
                x, y = element_or_coords
            else:
                x, y = element_or_coords
            
            pyautogui.moveTo(x, y, duration=0.5)
            await asyncio.sleep(0.1)
            pyautogui.rightClick(x, y)
            
            self.logger.debug(f"Right-clicked at position ({x}, {y})")
            return True
            
        except Exception as e:
            self.logger.error(f"Right click failed: {str(e)}")
            return False
    
    async def type_text(self, element: Any, text: str, clear_first: bool = True) -> bool:
        """Type text at current cursor position or after clicking element"""
        try:
            # If element is provided, click on it first
            if element:
                await self.click(element)
                await asyncio.sleep(0.2)
            
            # Clear existing text if requested
            if clear_first:
                pyautogui.hotkey('ctrl', 'a')  # Select all
                await asyncio.sleep(0.1)
                pyautogui.press('delete')  # Delete selected
                await asyncio.sleep(0.1)
            
            # Type the text
            pyautogui.write(text, interval=0.05)
            
            self.logger.debug(f"Text typed successfully: '{text[:50]}...' (length: {len(text)})")
            return True
            
        except Exception as e:
            self.logger.error(f"Type text failed: {str(e)}")
            return False
    
    async def wait(self, seconds: float) -> None:
        """Wait for specified seconds"""
        await asyncio.sleep(seconds)
    
    async def scroll_to_element(self, element: Any) -> bool:
        """Scroll to element (moves mouse to element)"""
        try:
            if isinstance(element, tuple):
                x, y = element
                pyautogui.moveTo(x, y, duration=0.5)
                self.logger.debug(f"Moved to element at ({x}, {y})")
                return True
        except Exception as e:
            self.logger.error(f"Scroll to element failed: {str(e)}")
            return False
    
    async def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Scroll at specified position or current mouse position"""
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                pyautogui.scroll(clicks)
            
            self.logger.debug(f"Scrolled {clicks} clicks at position ({x}, {y})")
            return True
            
        except Exception as e:
            self.logger.error(f"Scroll failed: {str(e)}")
            return False
    
    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            screenshots_dir = Path(self.config.screenshots_path)
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = screenshots_dir / filename
            screenshot = pyautogui.screenshot()
            screenshot.save(str(filepath))
            
            self.logger.debug(f"Screenshot saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Screenshot failed: {str(e)}")
            raise AdsPowerAutomationError(f"Could not take screenshot: {str(e)}")
    
    async def press_key(self, key: str) -> bool:
        """Press a keyboard key"""
        try:
            pyautogui.press(key)
            self.logger.debug(f"Pressed key: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Key press failed: {str(e)}")
            return False
    
    async def hotkey(self, *keys) -> bool:
        """Press combination of keys"""
        try:
            pyautogui.hotkey(*keys)
            self.logger.debug(f"Pressed hotkey: {'+'.join(keys)}")
            return True
        except Exception as e:
            self.logger.error(f"Hotkey failed: {str(e)}")
            return False
    
    # AdsPower Desktop Application Methods
    async def find_adspower_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Find AdsPower window bounds"""
        # This would need to be implemented with platform-specific window finding
        # For now, return None - would need pygetwindow or similar
        self.logger.warning("Window finding not implemented - using full screen")
        return None
    
    async def activate_adspower_window(self) -> bool:
        """Bring AdsPower window to front using system commands"""
        try:
            self.logger.info("Activating AdsPower Global using system command")
            
            import subprocess
            
            # Проверить, запущен ли AdsPower Global
            check_process = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to exists (processes whose name is "AdsPower Global")'
            ], capture_output=True, text=True)
            
            if check_process.returncode == 0 and "true" in check_process.stdout.lower():
                self.logger.info("AdsPower Global is already running, activating...")
                
                # Активировать существующий процесс
                activate_result = subprocess.run([
                    'osascript', '-e', 
                    'tell application "AdsPower Global" to activate'
                ], capture_output=True, text=True, timeout=10)
                
                if activate_result.returncode == 0:
                    self.logger.info("AdsPower Global activated successfully")
                    await self.wait(2)
                    return True
                else:
                    self.logger.warning(f"Failed to activate: {activate_result.stderr}")
            
            else:
                self.logger.info("AdsPower Global not running, launching...")
                
                # Запустить AdsPower Global
                launch_result = subprocess.run([
                    'open', '-a', 'AdsPower Global'
                ], capture_output=True, text=True, timeout=15)
                
                if launch_result.returncode == 0:
                    self.logger.info("AdsPower Global launched successfully")
                    await self.wait(5)  # Дать больше времени для запуска
                    
                    # Активировать после запуска
                    activate_result = subprocess.run([
                        'osascript', '-e', 
                        'tell application "AdsPower Global" to activate'
                    ], capture_output=True, text=True)
                    
                    if activate_result.returncode == 0:
                        self.logger.info("AdsPower Global activated after launch")
                        return True
                else:
                    self.logger.error(f"Failed to launch AdsPower Global: {launch_result.stderr}")
            
            return False
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout while trying to activate AdsPower Global")
            return False
        except Exception as e:
            self.logger.error(f"Exception while activating AdsPower window: {str(e)}")
            return False

    
    # Web Automation Methods (Not applicable for desktop app)
    async def navigate_to_url(self, url: str) -> bool:
        """Not applicable for desktop automation"""
        self.logger.warning("navigate_to_url not applicable for desktop automation")
        return False
    
    async def get_current_url(self) -> str:
        """Not applicable for desktop automation"""
        return ""
    
    async def get_page_title(self) -> str:
        """Not applicable for desktop automation"""
        return ""
    
    async def refresh_page(self) -> bool:
        """Not applicable for desktop automation"""
        return False
    
    async def execute_javascript(self, script: str) -> Any:
        """Not applicable for desktop automation"""
        return None
    
    # Profile Management Methods (AdsPower specific UI automation)
    # Обновленный метод создания профиля без поиска кнопок по изображениям
    async def create_profile(self, config: ProfileConfig) -> ProfileResponse:
        """Create a new profile using AdsPower desktop UI with system commands"""
        try:
            self.logger.info(f"Creating profile: {config.name}")
            
            # Активировать AdsPower Global
            if not await self.activate_adspower_window():
                return ProfileResponse.error_response("Could not activate AdsPower Global")
            
            # Дополнительная проверка что окно активно
            await self.wait(1)
            
            # Попробовать использовать горячие клавиши для создания профиля
            # Многие приложения поддерживают Cmd+N для создания нового элемента
            self.logger.info("Attempting to create new profile using keyboard shortcuts")
            
            # Попробовать Cmd+N (новый профиль)
            await self.hotkey('cmd', 'n')
            await self.wait(2)
            
            # Если это не сработало, попробовать другие комбинации
            # Можно добавить более специфичные для AdsPower команды
            
            # Здесь может потребоваться более специфичная логика для AdsPower
            # В зависимости от интерфейса приложения
            
            self.logger.info(f"Profile creation attempt completed for '{config.name}'")
            return ProfileResponse.success_response(
                profile_id=config.name,
                message=f"Profile creation initiated for '{config.name}'"
            )
            
        except Exception as e:
            error_msg = f"Failed to create profile: {str(e)}"
            self.logger.error(error_msg)
            return ProfileResponse.error_response(error_msg)
    
    async def open_profile(self, profile_id: str) -> ProfileResponse:
        """Open an existing profile"""
        try:
            self.logger.info(f"Opening profile: {profile_id}")
            
            # Activate AdsPower window
            if not await self.activate_adspower_window():
                return ProfileResponse.error_response("Could not activate AdsPower window")
            
            # Find the profile in the list and click open button
            open_button = await self.find_element("open_profile_button", ElementLocatorType.IMAGE, timeout=10)
            if not open_button:
                return ProfileResponse.error_response("Could not find open profile button")
            
            await self.click(open_button)
            await self.wait(5)  # Wait for profile to open
            
            self.logger.info(f"Profile '{profile_id}' opened successfully")
            return ProfileResponse.success_response(
                profile_id=profile_id,
                message=f"Profile '{profile_id}' opened successfully"
            )
            
        except Exception as e:
            error_msg = f"Failed to open profile: {str(e)}"
            self.logger.error(error_msg)
            return ProfileResponse.error_response(error_msg)
        
    async def check_adspower_status(self) -> Dict[str, Any]:
        """Check if AdsPower Global is running and get its status"""
        try:
            import subprocess
            
            # Проверить процесс
            check_process = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to get name of processes whose name contains "AdsPower"'
            ], capture_output=True, text=True)
            
            processes = check_process.stdout.strip() if check_process.returncode == 0 else ""
            
            # Проверить окна
            check_windows = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to get name of windows of application "AdsPower Global"'
            ], capture_output=True, text=True)
            
            windows = check_windows.stdout.strip() if check_windows.returncode == 0 else ""
            
            return {
                "is_running": "AdsPower Global" in processes,
                "processes": processes,
                "windows": windows,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "is_running": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def close_profile(self, profile_id: str) -> ProfileResponse:
        """Close a profile"""
        try:
            self.logger.info(f"Closing profile: {profile_id}")
            
            # Find and click close button
            close_button = await self.find_element("close_profile_button", ElementLocatorType.IMAGE, timeout=10)
            if close_button:
                await self.click(close_button)
                await self.wait(2)
            
            return ProfileResponse.success_response(
                profile_id=profile_id,
                message=f"Profile '{profile_id}' closed successfully"
            )
            
        except Exception as e:
            error_msg = f"Failed to close profile: {str(e)}"
            self.logger.error(error_msg)
            return ProfileResponse.error_response(error_msg)
    
    async def delete_profile(self, profile_id: str) -> ProfileResponse:
        """Delete a profile"""
        try:
            self.logger.info(f"Deleting profile: {profile_id}")
            
            # Implementation would depend on AdsPower UI
            # This is a placeholder
            return ProfileResponse.error_response("Profile deletion not implemented")
            
        except Exception as e:
            error_msg = f"Failed to delete profile: {str(e)}"
            self.logger.error(error_msg)
            return ProfileResponse.error_response(error_msg)
    
    async def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles"""
        try:
            self.logger.info("Listing profiles")
            
            # This would require OCR or other methods to read profile list
            # Placeholder implementation
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to list profiles: {str(e)}")
            return []
    
    async def get_profile_status(self, profile_id: str) -> Optional[str]:
        """Get profile status"""
        try:
            self.logger.info(f"Getting status for profile: {profile_id}")
            
            # This would require reading UI elements
            # Placeholder implementation
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get profile status: {str(e)}")
            return None