"""
Browser automation tools using Selenium
"""
import time
from typing import Tuple
import base64

class ScreenCapture:
    """Handle browser automation with Selenium"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.driver = None
        
    def start_browser(self):
        """Start Selenium WebDriver with Chrome"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('window-size=1920,1080')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("✓ Browser started")
        except Exception as e:
            print(f"✗ Failed to start browser: {e}")
            raise
        
    def navigate(self, path: str) -> str:
        """Navigate to a page"""
        url = f"{self.base_url}{path}"
        self.driver.get(url)
        time.sleep(1)
        return self.get_screenshot()
    
    def get_screenshot(self) -> str:
        """Take screenshot and return as base64"""
        try:
            screenshot = self.driver.get_screenshot_as_png()
            return base64.b64encode(screenshot).decode()
        except Exception as e:
            print(f"Screenshot error: {e}")
            return ""
    
    def click(self, x: int, y: int) -> str:
        """Click at coordinates"""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_by_offset(x - 960, y - 540)
            actions.click()
            actions.perform()
            time.sleep(0.5)
            return self.get_screenshot()
        except Exception as e:
            print(f"Click error: {e}")
            return self.get_screenshot()
    
    def type_text(self, text: str) -> str:
        """Type text in focused element"""
        try:
            active = self.driver.switch_to.active_element
            active.send_keys(text)
            time.sleep(0.3)
            return self.get_screenshot()
        except Exception as e:
            print(f"Type error: {e}")
            return self.get_screenshot()
    
    def get_page_text(self) -> str:
        """Get all text content from page"""
        try:
            return self.driver.find_element("tag name", "body").text
        except:
            return ""
    
    def find_button(self, text: str) -> Tuple[int, int]:
        """Find button by text and return coordinates"""
        try:
            buttons = self.driver.find_elements("tag name", "button")
            for btn in buttons:
                if text.lower() in btn.text.lower():
                    location = btn.location
                    size = btn.size
                    return (location['x'] + size['width']//2, location['y'] + size['height']//2)
        except:
            pass
        return None
    
    def scroll(self, direction: str = "down") -> str:
        """Scroll page"""
        try:
            from selenium.webdriver.common.keys import Keys
            body = self.driver.find_element("tag name", "body")
            if direction == "down":
                body.send_keys(Keys.PAGE_DOWN)
            else:
                body.send_keys(Keys.PAGE_UP)
            time.sleep(0.5)
            return self.get_screenshot()
        except Exception as e:
            print(f"Scroll error: {e}")
            return self.get_screenshot()
    
    def close(self):
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
                print("✓ Browser closed")
            except:
                pass