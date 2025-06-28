"""
Logging utility for AdsPower Automation Framework
File: utils/logger.py
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import json
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from adspower_automation.config.settings import AdsPowerConfig


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'profile_id'):
            log_entry["profile_id"] = record.profile_id
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
        if hasattr(record, 'duration'):
            log_entry["duration"] = record.duration
            
        return json.dumps(log_entry, ensure_ascii=False)


class AdsPowerLogger:
    """
    Centralized logger for AdsPower automation framework
    Provides both console and file logging with structured output
    """
    
    _instances = {}
    
    def __new__(cls, name: str, config: Optional[AdsPowerConfig] = None):
        """Ensure singleton pattern per logger name"""
        if name not in cls._instances:
            cls._instances[name] = super().__new__(cls)
        return cls._instances[name]
    
    def __init__(self, name: str, config: Optional[AdsPowerConfig] = None):
        if hasattr(self, '_initialized'):
            return
            
        self.name = name
        self.config = config
        self.logger = logging.getLogger(name)
        self._setup_logger()
        self._initialized = True
    
    def _setup_logger(self) -> None:
        """Setup logger with console and file handlers"""
        if self.logger.handlers:
            return  # Already configured
            
        self.logger.setLevel(getattr(logging, self.config.log_level if self.config else "INFO"))
        
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            fmt=self.config.log_format if self.config else 
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for detailed logs
        if self.config and self.config.logs_path:
            self._setup_file_handler()
    
    def _setup_file_handler(self) -> None:
        """Setup rotating file handler"""
        logs_dir = Path(self.config.logs_path)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file with rotation
        log_file = logs_dir / f"{self.name}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # JSON formatter for file logs
        json_formatter = JSONFormatter()
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)
        
        # Error log file for errors only
        error_log_file = logs_dir / f"{self.name}_errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        self.logger.addHandler(error_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message"""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback"""
        self.logger.exception(message, extra=kwargs)
    
    def log_operation_start(self, operation: str, **kwargs) -> None:
        """Log the start of an operation"""
        self.info(f"Starting operation: {operation}", operation=operation, **kwargs)
    
    def log_operation_end(self, operation: str, duration: float, success: bool = True, **kwargs) -> None:
        """Log the end of an operation"""
        status = "completed" if success else "failed"
        self.info(
            f"Operation {status}: {operation} (duration: {duration:.2f}s)",
            operation=operation,
            duration=duration,
            success=success,
            **kwargs
        )
    
    def log_profile_action(self, profile_id: str, action: str, message: str, **kwargs) -> None:
        """Log profile-specific actions"""
        self.info(f"Profile {profile_id} - {action}: {message}", profile_id=profile_id, operation=action, **kwargs)


def get_logger(name: str, config: Optional[AdsPowerConfig] = None) -> AdsPowerLogger:
    """
    Get or create a logger instance
    
    Args:
        name: Logger name (usually module name)
        config: AdsPower configuration
        
    Returns:
        AdsPowerLogger instance
    """
    return AdsPowerLogger(name, config)