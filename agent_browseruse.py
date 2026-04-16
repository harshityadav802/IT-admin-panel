import asyncio
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from ollama import AsyncClient
import json

load_dotenv()

class LocalOllamaAgent:
    
    def __init__(self, model="llama3"):
        self.model = model
        self.ollama_client = AsyncClient(host="http://localhost:11434")
        self.driver = None
        self.base_url = "http://localhost:5000"
        self.visited_pages = set()
        self.form_data_filled = {}
        print(f"Agent initialized with model: {model}")
    
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
        try:
            page_text = self.get_page_text()
            current_url = self.get_current_url()
            
            buttons = []
            for btn in self.driver.find_elements(By.TAG_NAME, "button"):
                if btn.is_displayed() and btn.text.strip():
                    buttons.append(btn.text.strip())
            
            for link in self.driver.find_elements(By.TAG_NAME, "a"):
                if link.is_displayed() and link.text.strip():
                    text = link.text.strip()
                    if text not in buttons:
                        buttons.append(text)
            
            inputs = {}
            for inp in self.driver.find_elements(By.TAG_NAME, "input"):
                if inp.is_displayed():
                    name = inp.get_attribute("name") or inp.get_attribute("placeholder") or "unknown"
                    inp_type = inp.get_attribute("type") or "text"
                    inputs[name] = inp_type
            
            selects = {}
            for sel in self.driver.find_elements(By.TAG_NAME, "select"):
                if sel.is_displayed():
                    name = sel.get_attribute("name") or "unknown"
                    options = [opt.text for opt in sel.find_elements(By.TAG_NAME, "option")]
                    selects[name] = options
            
            return {
                "url": current_url,
                "page_text": page_text[:1200],
                "buttons": buttons[:15],
                "inputs": inputs,
                "selects": selects,
                "visited": current_url in self.visited_pages
            }
        except Exception as e:
            return {"error": str(e), "url": self.get_current_url()}
    
    async def call_ollama(self, prompt):
        try:
            response = await self.ollama_client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": 0.2,
                    "num_predict": 180,
                    "top_p": 0.9,
                }
            )
            return response['response'].strip()
        except Exception as e:
            print(f"Ollama error: {e}")
            return "Error"
    
    def click_element(self, text):
        try:
            search_text = text.lower().strip()
            
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                btn_text = btn.text.lower().strip()
                if search_text in btn_text or btn_text in search_text:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.8)
                        return True
            
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                link_text = link.text.lower().strip()
                if search_text in link_text or link_text in search_text:
                    if link.is_displayed():
                        link.click()
                        time.sleep(0.8)
                        return True
            
            return False
        except Exception as e:
            print(f"Click error: {e}")
            return False
    
    def type_text(self, field_name, text):
        try:
            search_field = field_name.lower().strip()
            
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if not inp.is_displayed():
                    continue
                
                name = (inp.get_attribute("name") or "").lower()
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                label_text = ""
                
                try:
                    parent = inp.find_element(By.XPATH, "./ancestor::div")
                    label = parent.find_element(By.TAG_NAME, "label")
                    label_text = label.text.lower()
                except:
                    pass
                
                if (search_field in name or search_field in placeholder or 
                    search_field in label_text or name.startswith(search_field[:3])):
                    inp.clear()
                    inp.send_keys(text)
                    time.sleep(0.3)
                    return True
            
            return False
        except Exception as e:
            print(f"Type error: {e}")
            return False
    
    def select_dropdown(self, field_name, value):
        try:
            search_field = field_name.lower().strip()
            search_value = value.lower().strip()
            
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for sel in selects:
                if not sel.is_displayed():
                    continue
                
                name = (sel.get_attribute("name") or "").lower()
                
                if search_field in name or name in search_field:
                    select = Select(sel)
                    
                    try:
                        select.select_by_value(value)
                        time.sleep(0.3)
                        return True
                    except:
                        pass
                    
                    try:
                        for option in select.options:
                            if search_value in option.text.lower():
                                select.select_by_value(option.get_attribute("value"))
                                time.sleep(0.3)
                                return True
                    except:
                        pass
            
            return False
        except Exception as e:
            print(f"Select error: {e}")
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
        time.sleep(2)
        
        system_prompt = """You are an IT admin assistant controlling a web panel.
Complete tasks by navigating and interacting with the web interface.

Rules:
1. Read the current page carefully
2. Respond with EXACTLY ONE action per turn
3. Do NOT repeat the same action twice in a row
4. When task is complete, respond: TASK_COMPLETE: [summary]
5. If failed, respond: TASK_FAILED: [reason]

Available actions:
- click: [button/link name]
- type: [field_name]:[value]
- select: [dropdown_name]:[option_value]
- navigate: [/url/path]
- wait: [seconds]
- TASK_COMPLETE: [summary]
- TASK_FAILED: [reason]

Guidelines:
- Only click buttons/links that exist
- Fill forms completely before submitting
- Look for user emails in page content
- If redirected, adapt and continue
- Track visited pages
- If stuck for 3+ steps, fail the task"""
        
        step_count = 0
        last_actions = []
        
        for step in range(20):
            step_count += 1
            
            page_info = self.get_page_structure()
            
            if "error" in page_info:
                print(f"Page error: {page_info['error']}")
                time.sleep(1)
                continue
            
            self.visited_pages.add(page_info['url'])
            
            prompt = f"""{system_prompt}

Current page:
URL: {page_info['url']}
Previously visited: {page_info['visited']}

Available buttons/links:
{', '.join(page_info['buttons'])}

Form fields:
{json.dumps(page_info['inputs'], indent=2)}

Dropdowns:
{json.dumps({k: v[:5] for k, v in page_info['selects'].items()}, indent=2)}

Page content:
{page_info['page_text']}

Task: {task_description}

Recent actions: {', '.join(last_actions[-3:])}

What is the NEXT action?"""
            
            print(f"Step {step_count}:")
            action = await self.call_ollama(prompt)
            print(f"   Decision: {action[:90].strip()}")
            
            last_actions.append(action[:50])
            if len(last_actions) > 5:
                last_actions.pop(0)
            
            if len(last_actions) >= 3:
                if last_actions[-1] == last_actions[-2] == last_actions[-3]:
                    print(f"   Agent stuck in loop. Exiting.")
                    break
            
            action_lower = action.lower()
            
            if "task_complete" in action_lower:
                print(f"\n   Task completed: {action}")
                break
            
            if "task_failed" in action_lower:
                print(f"\n   Task failed: {action}")
                break
            
            if "click:" in action_lower:
                text = action.split("click:")[-1].strip().split("\n")[0]
                if self.click_element(text):
                    print(f"   Clicked: {text[:50]}")
                else:
                    print(f"   Button not found: {text[:50]}")
            
            elif "type:" in action_lower:
                parts = action.split("type:")[-1].strip().split(":")
                if len(parts) >= 2:
                    field = parts[0].strip()
                    value = ":".join(parts[1:]).strip()
                    if self.type_text(field, value):
                        print(f"   Typed {field}: {value[:35]}")
                        self.form_data_filled[field] = value
                    else:
                        print(f"   Field not found: {field}")
            
            elif "select:" in action_lower:
                parts = action.split("select:")[-1].strip().split(":")
                if len(parts) >= 2:
                    field = parts[0].strip()
                    value = ":".join(parts[1:]).strip()
                    if self.select_dropdown(field, value):
                        print(f"   Selected {field}: {value}")
                        self.form_data_filled[field] = value
                    else:
                        print(f"   Dropdown not found: {field}={value}")
            
            elif "navigate:" in action_lower:
                url = action.split("navigate:")[-1].strip().split("\n")[0]
                full_url = url if url.startswith("http") else f"{self.base_url}{url}"
                self.driver.get(full_url)
                print(f"   Navigated to {url}")
                time.sleep(1)
            
            elif "wait:" in action_lower:
                try:
                    seconds = int(action.split("wait:")[-1].split()[0])
                    print(f"   Waiting {seconds}s...")
                    time.sleep(seconds)
                except:
                    time.sleep(2)
            
            time.sleep(0.5)
        
        self.stop_browser()
        print("\n" + "="*75 + "\n")


async def main():
    
    print("\n" + "="*75)
    print("IT ADMIN AGENT - DEMO")
    print("="*75)
    print("LLM: Llama3 (Local Ollama)")
    print("Browser: Selenium")
    print("="*75 + "\n")
    
    print("Task 1: CREATE NEW USER")
    print("-"*75)
    agent1 = LocalOllamaAgent(model="llama3")
    await agent1.run_task(
        "Login with admin/admin123. "
        "Navigate to Create User page. "
        "Fill form: username=john_doe, email=john@company.com, full_name=John Doe, department=Engineering, password=SecurePass123. "
        "Submit form."
    )
    
    await asyncio.sleep(3)
    
    print("\nTask 2: RESET PASSWORD FOR USER")
    print("-"*75)
    agent2 = LocalOllamaAgent(model="llama3")
    await agent2.run_task(
        "Login with admin/admin123. "
        "Go to Users page. "
        "Find user john@company.com. "
        "Click on that user. "
        "Reset password to NewPass456. "
        "Submit and confirm."
    )
    
    await asyncio.sleep(3)
    
    print("\nTask 3: ASSIGN LICENSE TO USER")
    print("-"*75)
    agent3 = LocalOllamaAgent(model="llama3")
    await agent3.run_task(
        "Login with admin/admin123. "
        "Go to Licenses page. "
        "Click Assign License. "
        "Select user john@company.com. "
        "Choose Office 365 license. "
        "Submit form."
    )


if __name__ == "__main__":
    asyncio.run(main())