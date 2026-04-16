import asyncio
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from groq import Groq, AsyncGroq
import json
from dataclasses import dataclass
from typing import List, Dict, Optional

load_dotenv()

@dataclass
class ActionResult:
    """Track action execution results"""
    action: str
    success: bool
    reason: str = ""
    retry_count: int = 0
    timestamp: float = 0.0

class FailedActionsTracker:
    """Track and avoid repeating failed actions"""
    def __init__(self, max_consecutive_fails=3):
        self.failed_actions: Dict[str, int] = {}
        self.max_consecutive_fails = max_consecutive_fails
    
    def record_failure(self, action_key: str):
        """Record a failed action"""
        self.failed_actions[action_key] = self.failed_actions.get(action_key, 0) + 1
    
    def is_action_blocked(self, action_key: str) -> bool:
        """Check if action has failed too many times"""
        return self.failed_actions.get(action_key, 0) >= self.max_consecutive_fails
    
    def reset_failures(self):
        """Reset failure tracking"""
        self.failed_actions.clear()

class LocalOllamaAgent:
    
    def __init__(self, model="openai/gpt-oss-120b"):
        self.model = model
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.driver = None
        self.base_url = "http://localhost:5000"
        self.visited_pages = set()
        self.form_data_filled = {}
        self.action_history: List[ActionResult] = []
        self.failed_actions_tracker = FailedActionsTracker(max_consecutive_fails=2)
        self.retry_wait_time = 1.0
        print(f"Agent initialized with Groq model: {model}")
    
    def start_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(15)
        print("Browser started\n")
    
    def stop_browser(self):
        if self.driver:
            self.driver.quit()
            print("\nBrowser closed")
    
    def get_current_url(self):
        try:
            return self.driver.current_url
        except:
            return "unknown"
    
    def get_page_text(self):
        try:
            return self.driver.find_element(By.TAG_NAME, "body").text
        except:
            return "Page loading..."
    
    def get_page_structure(self):
        """Extract page structure with better element detection"""
        try:
            page_text = self.get_page_text()
            current_url = self.get_current_url()
            
            buttons = []
            for btn in self.driver.find_elements(By.TAG_NAME, "button"):
                if btn.is_displayed():
                    text = btn.text.strip()
                    if text:
                        buttons.append(text)
            
            for link in self.driver.find_elements(By.TAG_NAME, "a"):
                if link.is_displayed():
                    text = link.text.strip()
                    if text and text not in buttons:
                        buttons.append(text)
            
            inputs = {}
            for inp in self.driver.find_elements(By.TAG_NAME, "input"):
                if inp.is_displayed():
                    name = inp.get_attribute("name") or inp.get_attribute("placeholder") or inp.get_attribute("id") or "unknown"
                    inp_type = inp.get_attribute("type") or "text"
                    inputs[name] = inp_type
            
            selects = {}
            for sel in self.driver.find_elements(By.TAG_NAME, "select"):
                if sel.is_displayed():
                    name = sel.get_attribute("name") or sel.get_attribute("id") or "unknown"
                    options = [opt.text for opt in sel.find_elements(By.TAG_NAME, "option")]
                    selects[name] = options
            
            return {
                "url": current_url,
                "page_text": page_text[:1500],
                "buttons": buttons[:20],
                "inputs": inputs,
                "selects": selects,
                "visited": current_url in self.visited_pages
            }
        except Exception as e:
            return {"error": str(e), "url": self.get_current_url()}
    
    async def call_groq(self, prompt):
        """Call Groq API with better error handling"""
        try:
            message = await self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200,
                top_p=0.9,
            )
            return message.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq error: {e}")
            return "wait: 2"  # Fallback: wait and retry
    
    def click_element(self, text: str) -> tuple[bool, str]:
        """Click element with detailed feedback"""
        try:
            search_text = text.lower().strip()
            
            # Try exact match first
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                btn_text = btn.text.strip().lower()
                if btn_text == search_text and btn.is_displayed():
                    btn.click()
                    time.sleep(1)
                    return True, f"Clicked button: {text}"
            
            # Try partial match
            for btn in buttons:
                btn_text = btn.text.strip().lower()
                if search_text in btn_text or btn_text in search_text:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(1)
                        return True, f"Clicked button (partial): {text}"
            
            # Try links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                link_text = link.text.strip().lower()
                if link_text == search_text and link.is_displayed():
                    link.click()
                    time.sleep(1)
                    return True, f"Clicked link: {text}"
            
            for link in links:
                link_text = link.text.strip().lower()
                if search_text in link_text or link_text in search_text:
                    if link.is_displayed():
                        link.click()
                        time.sleep(1)
                        return True, f"Clicked link (partial): {text}"
            
            return False, f"Button/link not found: '{text}'"
        except Exception as e:
            return False, f"Click failed: {str(e)}"
    
    def type_text(self, field_name: str, text: str) -> tuple[bool, str]:
        """Type text with detailed feedback"""
        try:
            search_field = field_name.lower().strip()
            
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if not inp.is_displayed():
                    continue
                
                name = (inp.get_attribute("name") or "").lower()
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                field_id = (inp.get_attribute("id") or "").lower()
                
                # Try exact match first
                if name == search_field or placeholder == search_field or field_id == search_field:
                    inp.clear()
                    inp.send_keys(text)
                    time.sleep(0.5)
                    return True, f"Typed into '{field_name}': {text[:30]}"
                
                # Try partial match
                if (search_field in name or search_field in placeholder or 
                    search_field in field_id or name.startswith(search_field[:4])):
                    inp.clear()
                    inp.send_keys(text)
                    time.sleep(0.5)
                    return True, f"Typed into '{field_name}' (partial): {text[:30]}"
            
            return False, f"Input field '{field_name}' not found"
        except Exception as e:
            return False, f"Type failed: {str(e)}"
    
    def select_dropdown(self, field_name: str, value: str) -> tuple[bool, str]:
        """Select dropdown with detailed feedback"""
        try:
            search_field = field_name.lower().strip()
            search_value = value.lower().strip()
            
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for sel in selects:
                if not sel.is_displayed():
                    continue
                
                name = (sel.get_attribute("name") or "").lower()
                field_id = (sel.get_attribute("id") or "").lower()
                
                if search_field in name or search_field in field_id or name == search_field:
                    select = Select(sel)
                    
                    # Try exact value match
                    try:
                        select.select_by_value(value)
                        time.sleep(0.5)
                        return True, f"Selected '{field_name}': {value}"
                    except:
                        pass
                    
                    # Try text match
                    try:
                        for option in select.options:
                            opt_text = option.text.lower()
                            if opt_text == search_value or search_value in opt_text:
                                select.select_by_value(option.get_attribute("value"))
                                time.sleep(0.5)
                                return True, f"Selected '{field_name}': {value}"
                    except Exception as e:
                        return False, f"Selection failed: {str(e)}"
            
            return False, f"Dropdown '{field_name}' not found"
        except Exception as e:
            return False, f"Select failed: {str(e)}"
    
    def record_action(self, action: str, success: bool, reason: str = ""):
        """Record action for loop detection"""
        result = ActionResult(
            action=action,
            success=success,
            reason=reason,
            timestamp=time.time()
        )
        self.action_history.append(result)
        if len(self.action_history) > 10:
            self.action_history.pop(0)
    
    def is_stuck_in_loop(self) -> bool:
        """Detect if stuck in loop by tracking FAILED actions"""
        if len(self.action_history) < 3:
            return False
        
        # Check if last 3 actions all FAILED with same action type
        recent = self.action_history[-3:]
        if all(not r.success for r in recent):
            # All failed, check if they're the same action type
            action_types = [r.action.split(":")[0].lower() for r in recent]
            if action_types[0] == action_types[1] == action_types[2]:
                return True
        
        return False
    
    async def run_task(self, task_description: str):
        print(f"\n{'='*75}")
        print(f"Task: {task_description}")
        print(f"Model: {self.model}")
        print(f"{'='*75}\n")
        
        self.start_browser()
        self.driver.get(f"{self.base_url}/login")
        self.visited_pages.clear()
        self.form_data_filled.clear()
        self.action_history.clear()
        self.failed_actions_tracker.reset_failures()
        time.sleep(2)
        
        system_prompt = """You are an IT admin assistant controlling a web panel.
Complete tasks by navigating and interacting with the web interface.

IMPORTANT RULES:
1. Read page content carefully
2. Wait for page to load (use wait: [seconds])
3. Click buttons/links that EXIST on the page
4. Fill ALL required form fields
5. Submit forms properly
6. Stop when task is complete

Available actions:
- click: [button/link text]
- type: [field_name]:[value]
- select: [dropdown_name]:[option]
- navigate: [/url/path]
- wait: [seconds]
- TASK_COMPLETE: [summary]
- TASK_FAILED: [reason]

CRITICAL:
- Do NOT repeat the same action if it fails
- Do NOT click the same button multiple times in a row
- Wait 1-2 seconds after actions for page load
- STOP if you see error messages
- Try alternative approaches if actions fail
"""
        
        step_count = 0
        consecutive_failures = 0
        
        for step in range(25):
            step_count += 1
            
            # Check for loop
            if self.is_stuck_in_loop():
                print(f"\nStep {step_count}: LOOP DETECTED - Last 3 actions all failed")
                print("Action History:")
                for r in self.action_history[-3:]:
                    print(f"  - {r.action}: {r.success} ({r.reason})")
                break
            
            page_info = self.get_page_structure()
            
            if "error" in page_info:
                print(f"Step {step_count}: Page error: {page_info['error']}")
                time.sleep(2)
                continue
            
            self.visited_pages.add(page_info['url'])
            
            # Build recent action feedback
            recent_actions_feedback = ""
            if self.action_history:
                recent_actions_feedback = "\nRecent actions:\n"
                for r in self.action_history[-5:]:
                    status = "✓" if r.success else "✗"
                    recent_actions_feedback += f"  {status} {r.action}: {r.reason}\n"
            
            prompt = f"""{system_prompt}

Current page:
URL: {page_info['url']}
Previously visited: {page_info['visited']}

Available buttons/links ({len(page_info['buttons'])}):
{', '.join(page_info['buttons'][:15])}

Form fields available:
{json.dumps(page_info['inputs'], indent=2)}

Dropdowns available:
{json.dumps({k: v[:6] for k, v in page_info['selects'].items()}, indent=2)}

Page content (first 1500 chars):
{page_info['page_text']}
{recent_actions_feedback}

Task to complete: {task_description}

What is your NEXT action? Respond with ONE action only."""
            
            print(f"\nStep {step_count}:", end=" ")
            action = await self.call_groq(prompt)
            print(f"[{action[:70]}...]" if len(action) > 70 else f"[{action}]")
            
            action_lower = action.lower().strip()
            
            # Check for task completion
            if "task_complete" in action_lower:
                print(f"✓ TASK COMPLETED\n   {action}\n")
                self.record_action("TASK_COMPLETE", True, action)
                break
            
            if "task_failed" in action_lower:
                print(f"✗ TASK FAILED\n   {action}\n")
                self.record_action("TASK_FAILED", False, action)
                break
            
            success = False
            reason = ""
            
            # Parse and execute action
            if "click:" in action_lower:
                button_text = action.split("click:")[-1].strip().split("\n")[0].strip()
                success, reason = self.click_element(button_text)
                self.record_action(f"click: {button_text}", success, reason)
            
            elif "type:" in action_lower:
                try:
                    parts = action.split("type:")[-1].strip().split(":", 1)
                    if len(parts) >= 2:
                        field = parts[0].strip()
                        value = parts[1].strip()
                        success, reason = self.type_text(field, value)
                        self.record_action(f"type: {field}", success, reason)
                except Exception as e:
                    reason = f"Parse error: {str(e)}"
                    self.record_action("type: [parse_error]", False, reason)
            
            elif "select:" in action_lower:
                try:
                    parts = action.split("select:")[-1].strip().split(":", 1)
                    if len(parts) >= 2:
                        field = parts[0].strip()
                        value = parts[1].strip()
                        success, reason = self.select_dropdown(field, value)
                        self.record_action(f"select: {field}", success, reason)
                except Exception as e:
                    reason = f"Parse error: {str(e)}"
                    self.record_action("select: [parse_error]", False, reason)
            
            elif "navigate:" in action_lower:
                try:
                    url = action.split("navigate:")[-1].strip().split("\n")[0].strip()
                    full_url = url if url.startswith("http") else f"{self.base_url}{url}"
                    self.driver.get(full_url)
                    success, reason = True, f"Navigated to {url}"
                    self.record_action(f"navigate: {url}", success, reason)
                    time.sleep(1)
                except Exception as e:
                    reason = f"Navigate failed: {str(e)}"
                    self.record_action("navigate: [error]", False, reason)
            
            elif "wait:" in action_lower:
                try:
                    seconds = int(action.split("wait:")[-1].split()[0])
                    seconds = min(seconds, 5)  # Cap at 5 seconds
                    print(f"   → Waiting {seconds}s...")
                    time.sleep(seconds)
                    success, reason = True, f"Waited {seconds}s"
                    self.record_action(f"wait: {seconds}", success, reason)
                except Exception as e:
                    reason = f"Wait error: {str(e)}"
                    self.record_action("wait: [error]", False, reason)
            else:
                reason = "Unknown action format"
                self.record_action("unknown", False, reason)
            
            # Track consecutive failures
            if not success:
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    print(f"\n✗ Too many consecutive failures. Aborting task.\n")
                    break
            else:
                consecutive_failures = 0
            
            time.sleep(0.3)
        
        self.stop_browser()
        print("="*75 + "\n")


async def main():
    
    print("\n" + "="*75)
    print("IT ADMIN AGENT - GROQ VERSION")
    print("="*75)
    print("LLM: Groq (groq )")
    print("Browser: Selenium")
    print("Features: Action tracking, loop detection, detailed feedback")
    print("="*75 + "\n")
    
    print("Task 1: CREATE NEW USER")
    print("-"*75)
    agent1 = LocalOllamaAgent(model="openai/gpt-oss-120b")
    await agent1.run_task(
        "Login with admin/admin123. "
        "Navigate to Create User page. "
        "Fill form with: username=john_doe, email=john@company.com, full_name=John Doe, department=Engineering, password=SecurePass123. "
        "Click Submit button."
    )
    
    await asyncio.sleep(2)
    
    print("\nTask 2: RESET PASSWORD FOR USER")
    print("-"*75)
    agent2 = LocalOllamaAgent(model="openai/gpt-oss-120b")
    await agent2.run_task(
        "Login with admin/admin123. "
        "Navigate to Users page. "
        "Find and click on user john@company.com. "
        "Reset password to NewPass456. "
        "Submit and confirm."
    )
    
    await asyncio.sleep(2)
    
    print("\nTask 3: ASSIGN LICENSE TO USER")
    print("-"*75)
    agent3 = LocalOllamaAgent(model="openai/gpt-oss-120b")
    await agent3.run_task(
        "Login with admin/admin123. "
        "Go to Licenses page. "
        "Click Assign License button. "
        "Select user john@company.com. "
        "Choose license Jira. "
        "Submit form."
    )


if __name__ == "__main__":
    asyncio.run(main())
if __name__ == "__main__":
    asyncio.run(main())
