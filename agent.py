import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
ADMIN_URL = 'http://localhost:5000'

groq_client = Groq(api_key=GROQ_API_KEY)

def get_page_text(driver):
    try:
        text = driver.find_element(By.TAG_NAME, 'body').text
        return text[:2000]
    except:
        return "Page loading..."

def find_button_by_text(driver, text):
    buttons = driver.find_elements(By.TAG_NAME, 'button')
    for btn in buttons:
        if text.lower() in btn.text.lower():
            return btn
    return None

def find_link_by_text(driver, text):
    links = driver.find_elements(By.TAG_NAME, 'a')
    for link in links:
        if text.lower() in link.text.lower():
            return link
    return None

def find_input_by_name(driver, name):
    try:
        inputs = driver.find_elements(By.TAG_NAME, 'input')
        for inp in inputs:
            input_name = inp.get_attribute('name')
            if input_name and name.lower() in input_name.lower():
                return inp
    except:
        pass
    return None

def execute_action(driver, action):
    action = action.lower()
    time.sleep(0.3)
    
    try:
        if 'click' in action and 'login' in action and 'button' in action:
            btn = find_button_by_text(driver, 'login')
            if btn:
                btn.click()
                time.sleep(2)
                return "Clicked login button"
        
        elif 'click' in action and 'create' in action:
            link = find_link_by_text(driver, 'create')
            if link:
                link.click()
                time.sleep(2)
                return "Clicked create user link"
        
        elif 'click' in action and 'users' in action:
            link = find_link_by_text(driver, 'users')
            if link:
                link.click()
                time.sleep(2)
                return "Clicked users link"
        
        elif 'click' in action and 'reset' in action:
            link = find_link_by_text(driver, 'reset')
            if link:
                link.click()
                time.sleep(2)
                return "Clicked reset password"
        
        elif 'click' in action and ('submit' in action or 'button' in action):
            btn = find_button_by_text(driver, 'submit')
            if not btn:
                btn = find_button_by_text(driver, 'create')
            if not btn:
                btn = find_button_by_text(driver, 'reset')
            if btn:
                btn.click()
                time.sleep(2)
                return "Clicked submit button"
        
        elif 'type' in action or 'enter' in action:
            if 'username' in action:
                inp = find_input_by_name(driver, 'username')
                if inp:
                    inp.clear()
                    inp.send_keys('alice')
                    time.sleep(0.5)
                    return "Entered username: alice"
            
            elif 'password' in action and 'new' not in action and 'reset' not in action:
                inp = find_input_by_name(driver, 'password')
                if inp:
                    inp.clear()
                    inp.send_keys('alice123')
                    time.sleep(0.5)
                    return "Entered password"
            
            elif 'new_password' in action or ('password' in action and 'new' in action):
                inp = find_input_by_name(driver, 'new_password')
                if inp:
                    inp.clear()
                    inp.send_keys('NewPassword123')
                    time.sleep(0.5)
                    return "Entered new password: NewPassword123"
            
            elif 'email' in action:
                inp = find_input_by_name(driver, 'email')
                if inp:
                    inp.clear()
                    inp.send_keys('alice@company.com')
                    time.sleep(0.5)
                    return "Entered email: alice@company.com"
            
            elif 'full_name' in action or 'name' in action:
                inp = find_input_by_name(driver, 'full_name')
                if inp:
                    inp.clear()
                    inp.send_keys('Alice Johnson')
                    time.sleep(0.5)
                    return "Entered full name: Alice Johnson"
        
        elif 'select' in action or 'department' in action:
            selects = driver.find_elements(By.TAG_NAME, 'select')
            for sel in selects:
                sel_name = sel.get_attribute('name')
                if sel_name and 'department' in sel_name.lower():
                    select_obj = Select(sel)
                    options = select_obj.options
                    for opt in options:
                        if 'engineering' in opt.text.lower():
                            select_obj.select_by_value(opt.get_attribute('value'))
                            time.sleep(0.5)
                            return "Selected Engineering department"
        
        elif 'wait' in action:
            time.sleep(2)
            return "Waited for page load"
        
        return "Action executed"
    
    except Exception as e:
        return f"Action error: {str(e)[:50]}"

def run_agent(task_description, is_first_task=True):
    driver = None
    try:
        driver = webdriver.Chrome()
        driver.set_page_load_timeout(15)
        
        print(f"\nTask: {task_description}\n")
        print("=" * 60)
        
        if is_first_task:
            driver.get(f'{ADMIN_URL}/login')
            time.sleep(2)
            
            try:
                username_input = driver.find_element(By.NAME, 'username')
                password_input = driver.find_element(By.NAME, 'password')
                username_input.send_keys('admin')
                password_input.send_keys('admin123')
                
                buttons = driver.find_elements(By.TAG_NAME, 'button')
                buttons[0].click()
                time.sleep(3)
            except:
                print("Already logged in")
        else:
            driver.get(f'{ADMIN_URL}/dashboard')
            time.sleep(2)
        
        system_prompt = """You are an IT automation agent. Look at the page and suggest ONE action.

Available actions:
- Type username
- Type password
- Type email
- Type full_name
- Type new_password
- Select department
- Click login button
- Click create user
- Click users
- Click reset password
- Click submit button
- Wait

Be specific. When task is done, say 'TASK COMPLETE'."""

        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task_description}"}
        ]
        
        step = 0
        max_steps = 10
        
        while step < max_steps:
            step += 1
            print(f"\nStep {step}:")
            
            page_content = f"Page:\n{get_page_text(driver)}"
            conversation.append({"role": "user", "content": page_content})
            
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=conversation,
                max_tokens=100
            )
            
            agent_message = response.choices[0].message.content
            print(f"Agent: {agent_message}")
            
            conversation.append({"role": "assistant", "content": agent_message})
            
            if "TASK COMPLETE" in agent_message.upper():
                print("\nTask completed!")
                break
            
            result = execute_action(driver, agent_message)
            print(f"Result: {result}")
            
            time.sleep(0.5)
        
        print("=" * 60)
        return driver
        
    except Exception as e:
        print(f"Error: {e}")
        if driver:
            driver.quit()
        return None

def main():
    driver = None
    try:
        driver = run_agent("Create a new user named Alice Johnson with email alice@company.com in Engineering department", is_first_task=True)
        
        if driver:
            time.sleep(2)
            driver.get(f'{ADMIN_URL}/dashboard')
            time.sleep(2)
            run_agent("Reset password for alice@company.com to NewPassword123", is_first_task=False)
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()