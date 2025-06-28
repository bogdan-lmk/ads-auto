"""
Data models for AdsPower profiles
File: models/profile.py
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator


class ProfileStatus(Enum):
    """Profile status enumeration"""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    CREATING = "Creating"
    ERROR = "Error"


class PlatformType(Enum):
    """Supported platform types"""
    FACEBOOK = "facebook"
    GOOGLE = "google"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    GENERAL = "general"


class ProxyType(Enum):
    """Proxy types"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
    NONE = "none"


@dataclass
class ProxySettings:
    """Proxy configuration for profiles"""
    proxy_type: ProxyType = ProxyType.NONE
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if proxy settings are valid"""
        if self.proxy_type == ProxyType.NONE:
            return True
        return bool(self.host and self.port)


@dataclass
class BrowserSettings:
    """Browser configuration settings"""
    user_agent: Optional[str] = None
    resolution: str = "1920x1080"
    timezone: Optional[str] = None
    language: str = "en-US"
    canvas_protection: bool = True
    webgl_protection: bool = True
    webrtc_protection: bool = True
    font_protection: bool = True


class ProfileConfig(BaseModel):
    """Profile configuration using Pydantic for validation"""
    
    # Basic profile information
    name: str = Field(..., min_length=1, max_length=100, description="Profile name")
    platform: PlatformType = Field(default=PlatformType.GENERAL, description="Target platform")
    group_name: Optional[str] = Field(default=None, description="Profile group name")
    notes: Optional[str] = Field(default=None, max_length=500, description="Profile notes")
    
    # Browser settings
    browser_settings: BrowserSettings = Field(default_factory=BrowserSettings)
    
    # Proxy settings
    proxy_settings: ProxySettings = Field(default_factory=ProxySettings)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    status: ProfileStatus = Field(default=ProfileStatus.CREATING)
    profile_id: Optional[str] = None
    
    # Additional settings
    startup_url: Optional[str] = Field(default=None, description="URL to open on startup")
    extensions: List[str] = Field(default_factory=list, description="Browser extensions")
    cookies: Dict[str, Any] = Field(default_factory=dict, description="Cookies to set")
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        """Validate profile name is not empty"""
        if not v.strip():
            raise ValueError('Profile name cannot be empty')
        return v.strip()
    
    @validator('browser_settings')
    def validate_browser_resolution(cls, v):
        """Validate browser settings resolution format"""
        if hasattr(v, 'resolution') and 'x' not in v.resolution:
            raise ValueError('Resolution must be in format WIDTHxHEIGHT')
        if hasattr(v, 'resolution'):
            try:
                width, height = v.resolution.split('x')
                int(width)
                int(height)
            except ValueError:
                raise ValueError('Invalid resolution format')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        return {
            "name": self.name,
            "platform": self.platform.value,
            "group_name": self.group_name,
            "notes": self.notes,
            "browser_settings": self.browser_settings.__dict__,
            "proxy_settings": self.proxy_settings.__dict__,
            "startup_url": self.startup_url,
            "extensions": self.extensions,
        }


@dataclass
class ProfileResponse:
    """Response model for profile operations"""
    success: bool
    profile_id: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @classmethod
    def success_response(cls, profile_id: str, message: str = "Success", data: Optional[Dict[str, Any]] = None):
        """Create successful response"""
        return cls(success=True, profile_id=profile_id, message=message, data=data)
    
    @classmethod
    def error_response(cls, error: str, data: Optional[Dict[str, Any]] = None):
        """Create error response"""
        return cls(success=False, error=error, data=data)