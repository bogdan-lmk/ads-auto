"""
Configuration settings for AdsPower Automation Framework
File: config/settings.py
"""

from pydantic import BaseModel, Field
from typing import Optional
import os
from pathlib import Path


class AdsPowerConfig(BaseModel):
    """Main configuration model using Pydantic for validation"""
    
    # AdsPower API settings
    base_url: str = Field(default="http://local.adspower.net:50325", description="AdsPower API base URL")
    api_timeout: int = Field(default=30, description="API request timeout in seconds")
    
    # Automation settings
    default_timeout: int = Field(default=10, description="Default element wait timeout")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    # File paths
    screenshots_path: str = Field(default="./screenshots", description="Path to store screenshots")
    templates_path: str = Field(default="./templates", description="Path to image templates")
    logs_path: str = Field(default="./logs", description="Path to log files")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Browser settings
    headless: bool = Field(default=False, description="Run browser in headless mode")
    browser_width: int = Field(default=1920, description="Browser window width")
    browser_height: int = Field(default=1080, description="Browser window height")
    
    # AdsPower specific settings
    adspower_path: Optional[str] = Field(default=None, description="Path to AdsPower installation")
    
    class Config:
        env_prefix = "ADSPOWER_"
        case_sensitive = False
    
    def create_directories(self) -> None:
        """Create necessary directories if they don't exist"""
        directories = [
            self.screenshots_path,
            self.templates_path,
            self.logs_path
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


def load_config() -> AdsPowerConfig:
    """Load configuration from environment variables or defaults"""
    config = AdsPowerConfig()
    config.create_directories()
    return config