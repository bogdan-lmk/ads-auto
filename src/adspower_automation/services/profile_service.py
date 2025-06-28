"""
Main profile service for AdsPower automation
File: services/profile_service.py
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from adspower_automation.core.interfaces import AdsPowerAutomation, AutomationMethod
from adspower_automation.core.exceptions import (
    AdsPowerAutomationError,
    StrategyNotAvailableError,
    RetryExhaustedError
)
from adspower_automation.models.profile import ProfileConfig, ProfileResponse, ProfileStatus
from adspower_automation.config.settings import AdsPowerConfig
from adspower_automation.strategies.selenium_strategy import SeleniumStrategy
from adspower_automation.strategies.pyautogui_strategy import PyAutoGUIStrategy
from adspower_automation.utils.logger import get_logger


class AdsPowerProfileService:
    """
    Main service class for AdsPower profile automation
    Handles strategy selection and provides high-level automation methods
    """
    
    def __init__(self, config: AdsPowerConfig, preferred_method: Optional[AutomationMethod] = None):
        self.config = config
        self.preferred_method = preferred_method or AutomationMethod.PYAUTOGUI  # Default to PyAutoGUI for desktop
        self.logger = get_logger(self.__class__.__name__, config)
        
        # Available strategies
        self.strategies: Dict[AutomationMethod, AdsPowerAutomation] = {}
        self.current_strategy: Optional[AdsPowerAutomation] = None
        
        # Initialize strategies
        self._initialize_strategies()
    
    def _initialize_strategies(self) -> None:
        """Initialize all available automation strategies"""
        try:
            self.logger.info("Initializing automation strategies")
            
            # Initialize PyAutoGUI strategy (primary for desktop apps)
            pyautogui_strategy = PyAutoGUIStrategy(self.config)
            if pyautogui_strategy.is_available():
                self.strategies[AutomationMethod.PYAUTOGUI] = pyautogui_strategy
                self.logger.info("PyAutoGUI strategy initialized")
            
            # Initialize Selenium strategy (for web-based operations)
            selenium_strategy = SeleniumStrategy(self.config)
            if selenium_strategy.is_available():
                self.strategies[AutomationMethod.SELENIUM] = selenium_strategy
                self.logger.info("Selenium strategy initialized")
            
            if not self.strategies:
                raise StrategyNotAvailableError("No automation strategies available")
            
            self.logger.info(f"Initialized {len(self.strategies)} automation strategies")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize strategies: {str(e)}")
            raise
    
    async def start(self) -> bool:
        """Start the automation service"""
        try:
            self.logger.info("Starting AdsPower automation service")
            
            # Select and initialize the preferred strategy
            if self.preferred_method in self.strategies:
                self.current_strategy = self.strategies[self.preferred_method]
            else:
                # Fallback to first available strategy
                self.current_strategy = next(iter(self.strategies.values()))
            
            # Initialize the selected strategy
            success = await self.current_strategy.initialize()
            if success:
                self.logger.info(f"Service started with {self.current_strategy.get_automation_method().value} strategy")
                return True
            else:
                self.logger.error("Failed to initialize current strategy")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start service: {str(e)}")
            return False
    
    async def stop(self) -> None:
        """Stop the automation service"""
        try:
            self.logger.info("Stopping AdsPower automation service")
            
            if self.current_strategy:
                await self.current_strategy.cleanup()
                self.current_strategy = None
            
            # Cleanup all strategies
            for strategy in self.strategies.values():
                await strategy.cleanup()
            
            self.logger.info("Service stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping service: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            health_status = {
                "service_status": "running" if self.current_strategy else "stopped",
                "current_strategy": self.current_strategy.get_automation_method().value if self.current_strategy else None,
                "available_strategies": [method.value for method in self.strategies.keys()],
                "timestamp": datetime.now().isoformat()
            }
            
            # Check current strategy health
            if self.current_strategy:
                strategy_health = await self.current_strategy.health_check()
                health_status["strategy_health"] = strategy_health
            
            return health_status
            
        except Exception as e:
            return {
                "service_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def switch_strategy(self, method: AutomationMethod) -> bool:
        """Switch to a different automation strategy"""
        try:
            if method not in self.strategies:
                raise StrategyNotAvailableError(method.value, "Strategy not initialized")
            
            self.logger.info(f"Switching strategy to {method.value}")
            
            # Cleanup current strategy
            if self.current_strategy:
                await self.current_strategy.cleanup()
            
            # Initialize new strategy
            self.current_strategy = self.strategies[method]
            success = await self.current_strategy.initialize()
            
            if success:
                self.logger.info(f"Successfully switched to {method.value} strategy")
                return True
            else:
                self.logger.error(f"Failed to initialize {method.value} strategy")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to switch strategy: {str(e)}")
            return False
    
    async def create_profile_with_retry(self, config: ProfileConfig) -> ProfileResponse:
        """Create profile with retry logic"""
        if not self.current_strategy:
            return ProfileResponse.error_response("No automation strategy available")
        
        operation = f"create_profile_{config.name}"
        last_error = None
        
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                self.logger.info(f"Creating profile '{config.name}' - Attempt {attempt}/{self.config.retry_attempts}")
                
                # Take screenshot before operation
                screenshot_path = await self.current_strategy.take_screenshot(
                    f"before_create_{config.name}_{attempt}.png"
                )
                
                # Execute profile creation
                result = await self.current_strategy.create_profile(config)
                
                if result.success:
                    self.logger.info(f"Profile '{config.name}' created successfully on attempt {attempt}")
                    
                    # Take success screenshot
                    success_screenshot = await self.current_strategy.take_screenshot(
                        f"after_create_{config.name}_success.png"
                    )
                    
                    return result
                else:
                    last_error = AdsPowerAutomationError(result.error or "Unknown error")
                    self.logger.warning(f"Attempt {attempt} failed: {result.error}")
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt} failed with exception: {str(e)}")
                
                # Take error screenshot
                try:
                    error_screenshot = await self.current_strategy.take_screenshot(
                        f"error_create_{config.name}_{attempt}.png"
                    )
                except:
                    pass
            
            # Wait before retry (except for last attempt)
            if attempt < self.config.retry_attempts:
                await asyncio.sleep(self.config.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to create profile after {self.config.retry_attempts} attempts"
        self.logger.error(error_msg)
        
        raise RetryExhaustedError(operation, self.config.retry_attempts, last_error)
    
    async def open_profile_with_retry(self, profile_id: str) -> ProfileResponse:
        """Open profile with retry logic"""
        if not self.current_strategy:
            return ProfileResponse.error_response("No automation strategy available")
        
        operation = f"open_profile_{profile_id}"
        last_error = None
        
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                self.logger.info(f"Opening profile '{profile_id}' - Attempt {attempt}/{self.config.retry_attempts}")
                
                # Take screenshot before operation
                screenshot_path = await self.current_strategy.take_screenshot(
                    f"before_open_{profile_id}_{attempt}.png"
                )
                
                # Execute profile opening
                result = await self.current_strategy.open_profile(profile_id)
                
                if result.success:
                    self.logger.info(f"Profile '{profile_id}' opened successfully on attempt {attempt}")
                    
                    # Take success screenshot
                    success_screenshot = await self.current_strategy.take_screenshot(
                        f"after_open_{profile_id}_success.png"
                    )
                    
                    return result
                else:
                    last_error = AdsPowerAutomationError(result.error or "Unknown error")
                    self.logger.warning(f"Attempt {attempt} failed: {result.error}")
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt} failed with exception: {str(e)}")
                
                # Take error screenshot
                try:
                    error_screenshot = await self.current_strategy.take_screenshot(
                        f"error_open_{profile_id}_{attempt}.png"
                    )
                except:
                    pass
            
            # Wait before retry (except for last attempt)
            if attempt < self.config.retry_attempts:
                await asyncio.sleep(self.config.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to open profile after {self.config.retry_attempts} attempts"
        self.logger.error(error_msg)
        
        raise RetryExhaustedError(operation, self.config.retry_attempts, last_error)
    
    async def close_profile_with_retry(self, profile_id: str) -> ProfileResponse:
        """Close profile with retry logic"""
        if not self.current_strategy:
            return ProfileResponse.error_response("No automation strategy available")
        
        operation = f"close_profile_{profile_id}"
        last_error = None
        
        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                self.logger.info(f"Closing profile '{profile_id}' - Attempt {attempt}/{self.config.retry_attempts}")
                
                result = await self.current_strategy.close_profile(profile_id)
                
                if result.success:
                    self.logger.info(f"Profile '{profile_id}' closed successfully on attempt {attempt}")
                    return result
                else:
                    last_error = AdsPowerAutomationError(result.error or "Unknown error")
                    self.logger.warning(f"Attempt {attempt} failed: {result.error}")
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt} failed with exception: {str(e)}")
            
            # Wait before retry (except for last attempt)
            if attempt < self.config.retry_attempts:
                await asyncio.sleep(self.config.retry_delay)
        
        # All attempts failed
        error_msg = f"Failed to close profile after {self.config.retry_attempts} attempts"
        self.logger.error(error_msg)
        
        raise RetryExhaustedError(operation, self.config.retry_attempts, last_error)
    
    # High-level convenience methods
    async def create_profile(self, name: str, **kwargs) -> ProfileResponse:
        """Create a new profile with simplified interface"""
        try:
            # Create profile configuration
            config = ProfileConfig(name=name, **kwargs)
            
            # Validate configuration
            if not config.name.strip():
                return ProfileResponse.error_response("Profile name cannot be empty")
            
            self.logger.log_operation_start("create_profile", profile_name=name)
            start_time = datetime.now()
            
            # Execute with retry
            result = await self.create_profile_with_retry(config)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_operation_end("create_profile", duration, result.success, profile_name=name)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create profile '{name}': {str(e)}")
            return ProfileResponse.error_response(str(e))
    
    async def open_profile(self, profile_id: str) -> ProfileResponse:
        """Open an existing profile"""
        try:
            self.logger.log_operation_start("open_profile", profile_id=profile_id)
            start_time = datetime.now()
            
            result = await self.open_profile_with_retry(profile_id)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_operation_end("open_profile", duration, result.success, profile_id=profile_id)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to open profile '{profile_id}': {str(e)}")
            return ProfileResponse.error_response(str(e))
    
    async def close_profile(self, profile_id: str) -> ProfileResponse:
        """Close a profile"""
        try:
            self.logger.log_operation_start("close_profile", profile_id=profile_id)
            start_time = datetime.now()
            
            result = await self.close_profile_with_retry(profile_id)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_operation_end("close_profile", duration, result.success, profile_id=profile_id)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to close profile '{profile_id}': {str(e)}")
            return ProfileResponse.error_response(str(e))
    
    async def delete_profile(self, profile_id: str) -> ProfileResponse:
        """Delete a profile"""
        try:
            if not self.current_strategy:
                return ProfileResponse.error_response("No automation strategy available")
            
            self.logger.log_operation_start("delete_profile", profile_id=profile_id)
            start_time = datetime.now()
            
            result = await self.current_strategy.delete_profile(profile_id)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_operation_end("delete_profile", duration, result.success, profile_id=profile_id)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to delete profile '{profile_id}': {str(e)}")
            return ProfileResponse.error_response(str(e))
    
    async def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles"""
        try:
            if not self.current_strategy:
                self.logger.error("No automation strategy available")
                return []
            
            self.logger.log_operation_start("list_profiles")
            start_time = datetime.now()
            
            profiles = await self.current_strategy.list_profiles()
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log_operation_end("list_profiles", duration, True, profile_count=len(profiles))
            
            return profiles
            
        except Exception as e:
            self.logger.error(f"Failed to list profiles: {str(e)}")
            return []
    
    async def get_profile_status(self, profile_id: str) -> Optional[str]:
        """Get the status of a specific profile"""
        try:
            if not self.current_strategy:
                return None
            
            status = await self.current_strategy.get_profile_status(profile_id)
            self.logger.debug(f"Profile '{profile_id}' status: {status}")
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get status for profile '{profile_id}': {str(e)}")
            return None
    
    # AdsPower-specific workflow methods
    async def create_and_open_profile(self, name: str, **kwargs) -> ProfileResponse:
        """Create a profile and immediately open it"""
        try:
            self.logger.info(f"Creating and opening profile: {name}")
            
            # Create the profile
            create_result = await self.create_profile(name, **kwargs)
            if not create_result.success:
                return create_result
            
            # Wait a moment for profile to be ready
            await asyncio.sleep(2)
            
            # Open the profile
            open_result = await self.open_profile(create_result.profile_id or name)
            if not open_result.success:
                self.logger.warning(f"Profile created but failed to open: {open_result.error}")
                return ProfileResponse.error_response(
                    f"Profile created successfully but failed to open: {open_result.error}"
                )
            
            self.logger.info(f"Profile '{name}' created and opened successfully")
            return ProfileResponse.success_response(
                profile_id=create_result.profile_id or name,
                message=f"Profile '{name}' created and opened successfully"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create and open profile '{name}': {str(e)}")
            return ProfileResponse.error_response(str(e))
    
    async def batch_create_profiles(self, profile_configs: List[Dict[str, Any]]) -> List[ProfileResponse]:
        """Create multiple profiles in batch"""
        results = []
        
        try:
            self.logger.info(f"Starting batch creation of {len(profile_configs)} profiles")
            
            for i, config_dict in enumerate(profile_configs, 1):
                try:
                    profile_name = config_dict.get('name', f'Profile_{i}')
                    self.logger.info(f"Creating profile {i}/{len(profile_configs)}: {profile_name}")
                    
                    result = await self.create_profile(**config_dict)
                    results.append(result)
                    
                    # Brief pause between creations
                    if i < len(profile_configs):
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    error_result = ProfileResponse.error_response(f"Failed to create profile {i}: {str(e)}")
                    results.append(error_result)
                    self.logger.error(f"Failed to create profile {i}: {str(e)}")
            
            successful = sum(1 for r in results if r.success)
            self.logger.info(f"Batch creation completed: {successful}/{len(profile_configs)} profiles created successfully")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch profile creation failed: {str(e)}")
            return [ProfileResponse.error_response(str(e)) for _ in profile_configs]
    
    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot of current state"""
        if not self.current_strategy:
            raise AdsPowerAutomationError("No automation strategy available")
        
        return await self.current_strategy.take_screenshot(filename)
    
    def get_current_strategy_name(self) -> Optional[str]:
        """Get the name of the currently active strategy"""
        if self.current_strategy:
            return self.current_strategy.get_automation_method().value
        return None
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available automation strategies"""
        return [method.value for method in self.strategies.keys()]