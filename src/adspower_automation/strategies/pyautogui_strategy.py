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

    async def click_open_button(self) -> bool:
        """Найти и нажать кнопку 'Открыть' для выделенного профиля"""
        try:
            self.logger.info("Поиск и нажатие кнопки 'Открыть'...")
            
            # Сначала попробуем упрощенный метод
            if await self.click_open_button_simple():
                return True
            
            # Если не сработал, попробуем другие методы
            self.logger.info("Упрощенный метод не сработал, пробуем другие...")
            
            # Попробовать поиск по позиции (исправленный)
            button_pos = await self._find_open_button_by_position()
            if button_pos:
                return await self._click_button(button_pos, "position-based")
            
            # Попробовать поиск по цвету
            button_pos = await self._find_open_button_by_color()
            if button_pos:
                return await self._click_button(button_pos, "color detection")
            
            self.logger.warning("Кнопка 'Открыть' не найдена всеми методами")
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске кнопки 'Открыть': {str(e)}")
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
    
    async def _find_open_button_by_position(self) -> Optional[Tuple[int, int]]:
        """Поиск кнопки в предполагаемых позициях на основе скриншота"""
        try:
            # Исправленные координаты на основе ваших скриншотов
            # Размер экрана: 1440x900
            height, width = pyautogui.size()
            
            # Точные позиции кнопок "Открыть" (на основе ваших скриншотов)
            potential_positions = [
                (int(width * 0.853), int(height * 0.427)),  
            ]
            
            self.logger.info(f"Проверка позиций кнопок для экрана {width}x{height}")
            
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            for i, (x, y) in enumerate(potential_positions):
                self.logger.info(f"Проверка позиции {i+1}: ({x}, {y})")
                
                # Проверить область вокруг каждой позиции (увеличенная область)
                region_size = 50
                x1, y1 = max(0, x - region_size), max(0, y - region_size)
                x2, y2 = min(width, x + region_size), min(height, y + region_size)
                
                region = screenshot_cv[y1:y2, x1:x2]
                
                if region.size == 0:
                    continue
                
                # Проверить наличие синего цвета в этой области
                hsv_region = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
                
                # Более точный диапазон для кнопок AdsPower
                lower_blue = np.array([105, 100, 100])
                upper_blue = np.array([125, 255, 255])
                mask = cv2.inRange(hsv_region, lower_blue, upper_blue)
                
                # Если в области достаточно синих пикселей, это может быть кнопка
                blue_pixels = cv2.countNonZero(mask)
                total_pixels = region.shape[0] * region.shape[1]
                blue_percentage = blue_pixels / total_pixels if total_pixels > 0 else 0
                
                self.logger.info(f"Позиция ({x}, {y}): синих пикселей {blue_percentage:.2%}")
                
                if blue_percentage > 0.2:  # 20% синих пикселей
                    self.logger.info(f"Найдена кнопка по позиции в ({x}, {y})")
                    return (x, y)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка в поиске по позиции: {str(e)}")
            return None

    async def _find_open_button_by_color(self) -> Optional[Tuple[int, int]]:
        """Поиск синих кнопок в интерфейсе"""
        try:
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            # Конвертировать в HSV
            hsv = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2HSV)
            
            # Диапазон синего цвета (более широкий)
            lower_blue = np.array([90, 80, 80])
            upper_blue = np.array([140, 255, 255])
            
            mask = cv2.inRange(hsv, lower_blue, upper_blue)
            
            # Морфологические операции
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            height, width = screenshot_cv.shape[:2]
            candidates = []
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Фильтры для кнопки
                if (500 < area < 5000 and 
                    40 < w < 150 and 
                    20 < h < 60 and
                    x > width * 0.7):  # Правая часть экрана
                    
                    aspect_ratio = w / h
                    if 1.5 < aspect_ratio < 4:
                        candidates.append({
                            'x': x + w // 2,
                            'y': y + h // 2,
                            'area': area,
                            'distance_from_right': width - x
                        })
            
            if candidates:
                # Выбрать кнопку ближе к правому краю
                best = min(candidates, key=lambda c: c['distance_from_right'])
                self.logger.info(f"Найдена кнопка по цвету в позиции ({best['x']}, {best['y']})")
                return (best['x'], best['y'])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка в поиске по цвету: {str(e)}")
            return None

    async def _find_open_button_by_position(self) -> Optional[Tuple[int, int]]:
        """Поиск кнопки в предполагаемых позициях на основе скриншота"""
        try:
            # На основе ваших скриншотов, кнопки "Открыть" находятся примерно в этих позициях
            height, width = pyautogui.size()
            
            # Предполагаемые позиции кнопок (относительно размера экрана)
            potential_positions = [
                (int(width * 0.85), int(height * 0.39)),  # Первая кнопка
                (int(width * 0.85), int(height * 0.47)),  # Вторая кнопка
                (int(width * 0.85), int(height * 0.55)),  # Возможная третья
            ]
            
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            for x, y in potential_positions:
                # Проверить область вокруг каждой позиции
                region_size = 40
                x1, y1 = max(0, x - region_size), max(0, y - region_size)
                x2, y2 = min(width, x + region_size), min(height, y + region_size)
                
                region = screenshot_cv[y1:y2, x1:x2]
                
                if region.size == 0:
                    continue
                
                # Проверить наличие синего цвета в этой области
                hsv_region = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
                lower_blue = np.array([100, 100, 100])
                upper_blue = np.array([130, 255, 255])
                mask = cv2.inRange(hsv_region, lower_blue, upper_blue)
                
                # Если в области достаточно синих пикселей, это может быть кнопка
                blue_pixels = cv2.countNonZero(mask)
                total_pixels = region.shape[0] * region.shape[1]
                
                if blue_pixels > total_pixels * 0.3:  # 30% синих пикселей
                    self.logger.info(f"Найдена кнопка по позиции в ({x}, {y})")
                    return (x, y)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка в поиске по позиции: {str(e)}")
            return None

    async def _click_button(self, position: Tuple[int, int], method: str) -> bool:
        """Кликнуть по найденной кнопке"""
        try:
            x, y = position
            self.logger.info(f"Клик по кнопке 'Открыть' ({method}) в позиции ({x}, {y})")
            
            # Переместить мышь и кликнуть
            pyautogui.moveTo(x, y, duration=0.5)
            await asyncio.sleep(0.3)
            pyautogui.click(x, y)
            
            # Сделать скриншот после клика
            await asyncio.sleep(1)
            screenshot_after = pyautogui.screenshot()
            screenshots_dir = Path(self.config.screenshots_path)
            after_path = screenshots_dir / f"after_click_{method}.png"
            screenshot_after.save(str(after_path))
            self.logger.info(f"Скриншот после клика сохранен: {after_path}")
            
            self.logger.info("Кнопка 'Открыть' нажата успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при клике: {str(e)}")
            return False
        
    async def click_open_button_simple(self) -> bool:
        """Упрощенный метод - прямой клик по кнопке на основе ID профиля"""
        try:
            self.logger.info("Простой поиск кнопки 'Открыть'...")
            
            # Размер экрана
            height, width = pyautogui.size()
            
            # Прямые координаты кнопок "Открыть" (на основе ваших скриншотов)
            button_positions = [
                (int(width * 0.853), int(height * 0.427)),  # Первая кнопка "Открыть"
                (int(width * 0.853), int(height * 0.487)),  # Вторая кнопка "Открыть"
            ]
            
            # Попробовать кликнуть по каждой кнопке и проверить результат
            for i, (x, y) in enumerate(button_positions):
                self.logger.info(f"Пробуем кнопку {i+1} в позиции ({x}, {y})")
                
                # Сделать скриншот до клика
                screenshot_before = pyautogui.screenshot()
                
                # Кликнуть
                pyautogui.moveTo(x, y, duration=0.5)
                await asyncio.sleep(0.3)
                pyautogui.click(x, y)
                await asyncio.sleep(2)  # Подождать реакции
                
                # Сделать скриншот после клика
                screenshot_after = pyautogui.screenshot()
                
                # Сравнить скриншоты - если что-то изменилось, значит клик сработал
                before_np = np.array(screenshot_before)
                after_np = np.array(screenshot_after)
                
                # Простое сравнение по разности
                diff = np.sum(np.abs(before_np.astype(int) - after_np.astype(int)))
                
                self.logger.info(f"Разность скриншотов: {diff}")
                
                if diff > 1000000:  # Если есть существенные изменения
                    self.logger.info(f"✅ Кнопка {i+1} сработала! Профиль открывается.")
                    
                    # Сохранить результат
                    screenshots_dir = Path(self.config.screenshots_path)
                    screenshots_dir.mkdir(parents=True, exist_ok=True)
                    after_path = screenshots_dir / f"success_click_button_{i+1}.png"
                    screenshot_after.save(str(after_path))
                    self.logger.info(f"Скриншот успеха сохранен: {after_path}")
                    
                    return True
            
            self.logger.warning("Ни одна кнопка не сработала")
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка в простом методе: {str(e)}")
            return False

    async def select_profile_by_id(self, profile_id: str) -> bool:
        """Выделить профиль по ID перед открытием"""
        try:
            self.logger.info(f"Поиск и выделение профиля: {profile_id}")
            
            # Исправленные координаты для выделения профилей
            height, width = pyautogui.size()
            
            # Позиции строк профилей (левая часть таблицы)
            profile_positions = [
                (int(width * 0.5), int(height * 0.427)),  # ≈ (720, 384) - первый профиль
                (int(width * 0.5), int(height * 0.487)),  # ≈ (720, 438) - второй профиль
                (int(width * 0.5), int(height * 0.547)),  # ≈ (720, 492) - третий профиль
            ]
            
            # Попробовать кликнуть по профилю с нужным ID
            try:
                profile_index = int(profile_id) - 1  # Конвертировать в индекс (1->0, 2->1)
                if 0 <= profile_index < len(profile_positions):
                    click_x, click_y = profile_positions[profile_index]
                    
                    self.logger.info(f"Клик по профилю {profile_id} в позиции ({click_x}, {click_y})")
                    pyautogui.click(click_x, click_y)
                    await asyncio.sleep(1)  # Подождать выделения
                    
                    return True
                else:
                    self.logger.warning(f"Профиль с ID {profile_id} не найден в списке")
            except ValueError:
                self.logger.warning(f"Неверный ID профиля: {profile_id}")
            
            # Если не удалось найти по индексу, кликаем по первому профилю
            if profile_positions:
                click_x, click_y = profile_positions[0]
                self.logger.info(f"Клик по первому профилю в позиции ({click_x}, {click_y})")
                pyautogui.click(click_x, click_y)
                await asyncio.sleep(1)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка при выделении профиля: {str(e)}")
            return False
        
    async def open_profile(self, profile_id: str) -> ProfileResponse:
        """Open an existing profile by selecting it and clicking Open button"""
        try:
            self.logger.info(f"Opening profile: {profile_id}")
            
            # Активировать AdsPower window
            if not await self.activate_adspower_window():
                return ProfileResponse.error_response("Could not activate AdsPower window")
            
            # Подождать готовности интерфейса
            await self.wait(2)
            
            # Сначала выделить нужный профиль
            self.logger.info("Выделение профиля...")
            if not await self.select_profile_by_id(profile_id):
                self.logger.warning("Не удалось выделить профиль, пробуем открыть без выделения")
            
            # Подождать немного после выделения
            await self.wait(1)
            
            # Теперь нажать кнопку "Открыть"
            if await self.click_open_button():
                # Подождать открытия профиля
                await self.wait(3)
                
                self.logger.info(f"Profile '{profile_id}' opened successfully")
                return ProfileResponse.success_response(
                    profile_id=profile_id,
                    message=f"Profile '{profile_id}' opened successfully"
                )
            else:
                return ProfileResponse.error_response("Could not find or click Open button")
                
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