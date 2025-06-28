"""Automation strategy implementations."""

from .selenium_strategy import SeleniumStrategy
from .pyautogui_strategy import PyAutoGUIStrategy

__all__ = ["SeleniumStrategy", "PyAutoGUIStrategy"]
