"""
Main application entry point for AdsPower Automation Framework
File: main.py
"""

import asyncio
import sys
import argparse
from typing import Optional
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adspower_automation.config.settings import load_config, AdsPowerConfig
from adspower_automation.services.profile_service import AdsPowerProfileService
from adspower_automation.core.interfaces import AutomationMethod
from adspower_automation.core.exceptions import AdsPowerAutomationError
from adspower_automation.models.profile import ProfileConfig, PlatformType
from adspower_automation.utils.logger import get_logger


class AdsPowerApp:
    """Main application class for AdsPower automation"""
    
    def __init__(self, config: Optional[AdsPowerConfig] = None):
        self.config = config or load_config()
        self.logger = get_logger("AdsPowerApp", self.config)
        self.service: Optional[AdsPowerProfileService] = None
    
    async def initialize(self, automation_method: Optional[AutomationMethod] = None) -> bool:
        """Initialize the application"""
        try:
            self.logger.info("Initializing AdsPower Automation Application")
            
            # Create and start the profile service
            self.service = AdsPowerProfileService(
                config=self.config,
                preferred_method=automation_method
            )
            
            success = await self.service.start()
            if success:
                self.logger.info("Application initialized successfully")
                await self._show_status()
                return True
            else:
                self.logger.error("Failed to initialize application")
                return False
                
        except Exception as e:
            self.logger.error(f"Application initialization failed: {str(e)}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the application gracefully"""
        try:
            self.logger.info("Shutting down application")
            
            if self.service:
                await self.service.stop()
                self.service = None
            
            self.logger.info("Application shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during application shutdown: {str(e)}")
    
    async def _show_status(self) -> None:
        """Show current application status"""
        if not self.service:
            return
        
        health = await self.service.health_check()
        
        print("\n" + "="*60)
        print("AdsPower Automation Framework - Status")
        print("="*60)
        print(f"Service Status: {health.get('service_status', 'Unknown')}")
        print(f"Current Strategy: {health.get('current_strategy', 'None')}")
        print(f"Available Strategies: {', '.join(health.get('available_strategies', []))}")
        
        if 'strategy_health' in health:
            strategy_health = health['strategy_health']
            print(f"Strategy Available: {strategy_health.get('available', False)}")
            if strategy_health.get('current_url'):
                print(f"Current URL: {strategy_health.get('current_url')}")
        
        print("="*60 + "\n")
    
    async def create_profile_interactive(self) -> None:
        """Interactive profile creation"""
        try:
            print("\n--- Create New Profile ---")
            
            # Get profile name
            name = input("Enter profile name: ").strip()
            if not name:
                print("Profile name cannot be empty!")
                return
            
            # Get platform (optional)
            print("\nAvailable platforms:")
            for i, platform in enumerate(PlatformType, 1):
                print(f"{i}. {platform.value}")
            
            platform_choice = input("Select platform (press Enter for general): ").strip()
            platform = PlatformType.GENERAL
            
            if platform_choice.isdigit():
                try:
                    platforms = list(PlatformType)
                    platform = platforms[int(platform_choice) - 1]
                except (IndexError, ValueError):
                    platform = PlatformType.GENERAL
            
            # Create profile
            print(f"\nCreating profile '{name}' for platform '{platform.value}'...")
            
            result = await self.service.create_profile(
                name=name,
                platform=platform
            )
            
            if result.success:
                print(f"✅ Profile created successfully: {result.message}")
            else:
                print(f"❌ Failed to create profile: {result.error}")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    async def open_profile_interactive(self) -> None:
        """Interactive profile opening"""
        try:
            print("\n--- Open Profile ---")
            
            # List existing profiles first
            profiles = await self.service.list_profiles()
            if profiles:
                print("Available profiles:")
                for i, profile in enumerate(profiles, 1):
                    print(f"{i}. {profile.get('name', 'Unknown')}")
            
            profile_id = input("Enter profile name/ID to open: ").strip()
            if not profile_id:
                print("Profile ID cannot be empty!")
                return
            
            print(f"Opening profile '{profile_id}'...")
            
            result = await self.service.open_profile(profile_id)
            
            if result.success:
                print(f"✅ Profile opened successfully: {result.message}")
            else:
                print(f"❌ Failed to open profile: {result.error}")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    async def demo_workflow(self) -> None:
        """Demonstrate the complete workflow"""
        try:
            print("\n--- Demo Workflow ---")
            print("This will create a new profile and attempt to open it")
            
            # Generate demo profile name
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            demo_name = f"Demo_Profile_{timestamp}"
            
            print(f"Creating demo profile: {demo_name}")
            
            # Create and open profile in one step
            result = await self.service.create_and_open_profile(
                name=demo_name,
                platform=PlatformType.GENERAL,
                notes="Demo profile created by automation framework"
            )
            
            if result.success:
                print(f"✅ Demo completed successfully: {result.message}")
                
                # Take a screenshot
                screenshot_path = await self.service.take_screenshot(f"demo_success_{timestamp}.png")
                print(f"📸 Screenshot saved: {screenshot_path}")
                
            else:
                print(f"❌ Demo failed: {result.error}")
                
        except Exception as e:
            print(f"❌ Demo error: {str(e)}")
    
    async def run_interactive_menu(self) -> None:
        """Run interactive menu for user operations"""
        while True:
            try:
                print("\n" + "="*50)
                print("AdsPower Automation Framework")
                print("="*50)
                print("1. Create Profile")
                print("2. Open Profile")
                print("3. List Profiles")
                print("4. Run Demo Workflow")
                print("5. Show Status")
                print("6. Take Screenshot")
                print("7. Switch Strategy")
                print("0. Exit")
                print("-"*50)
                
                choice = input("Select option (0-7): ").strip()
                
                if choice == "0":
                    break
                elif choice == "1":
                    await self.create_profile_interactive()
                elif choice == "2":
                    await self.open_profile_interactive()
                elif choice == "3":
                    profiles = await self.service.list_profiles()
                    print(f"\nFound {len(profiles)} profiles:")
                    for profile in profiles:
                        print(f"  - {profile}")
                elif choice == "4":
                    await self.demo_workflow()
                elif choice == "5":
                    await self._show_status()
                elif choice == "6":
                    screenshot_path = await self.service.take_screenshot()
                    print(f"📸 Screenshot saved: {screenshot_path}")
                elif choice == "7":
                    await self._switch_strategy_interactive()
                else:
                    print("Invalid option. Please try again.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    async def _switch_strategy_interactive(self) -> None:
        """Interactive strategy switching"""
        try:
            available = self.service.get_available_strategies()
            current = self.service.get_current_strategy_name()
            
            print(f"\nCurrent strategy: {current}")
            print("Available strategies:")
            
            methods = []
            for i, strategy in enumerate(available, 1):
                print(f"{i}. {strategy}")
                methods.append(AutomationMethod(strategy))
            
            choice = input("Select strategy (or press Enter to cancel): ").strip()
            
            if choice.isdigit():
                try:
                    selected_method = methods[int(choice) - 1]
                    print(f"Switching to {selected_method.value}...")
                    
                    success = await self.service.switch_strategy(selected_method)
                    if success:
                        print(f"✅ Successfully switched to {selected_method.value}")
                    else:
                        print(f"❌ Failed to switch to {selected_method.value}")
                        
                except (IndexError, ValueError):
                    print("Invalid selection")
            
        except Exception as e:
            print(f"❌ Error switching strategy: {str(e)}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AdsPower Automation Framework")
    parser.add_argument("--method", choices=["selenium", "pyautogui"], 
                       help="Preferred automation method")
    parser.add_argument("--headless", action="store_true", 
                       help="Run in headless mode (for Selenium)")
    parser.add_argument("--demo", action="store_true", 
                       help="Run demo workflow and exit")
    parser.add_argument("--create", metavar="NAME", 
                       help="Create profile with specified name and exit")
    parser.add_argument("--open", metavar="ID", 
                       help="Open profile with specified ID and exit")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    if args.headless:
        config.headless = True
    
    # Determine automation method
    automation_method = None
    if args.method:
        automation_method = AutomationMethod(args.method)
    
    # Create and initialize application
    app = AdsPowerApp(config)
    
    try:
        # Initialize the application
        if not await app.initialize(automation_method):
            print("❌ Failed to initialize application")
            return 1
        
        # Handle command-line operations
        if args.demo:
            await app.demo_workflow()
        elif args.create:
            result = await app.service.create_profile(name=args.create)
            if result.success:
                print(f"✅ Profile '{args.create}' created successfully")
            else:
                print(f"❌ Failed to create profile: {result.error}")
        elif args.open:
            result = await app.service.open_profile(args.open)
            if result.success:
                print(f"✅ Profile '{args.open}' opened successfully")
            else:
                print(f"❌ Failed to open profile: {result.error}")
        else:
            # Run interactive menu
            await app.run_interactive_menu()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Application error: {str(e)}")
        return 1
    finally:
        await app.shutdown()


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)