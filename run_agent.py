"""Main AI Agent using OpenAI LLM"""
import os
from openai import OpenAI
from agent.prompts import TASK_ANALYSIS_PROMPT
from agent.tools import ScreenCapture
from agent.state import AgentState
import time
import re
import base64

class ITAdminAgent:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Cheaper than gpt-4o
        self.screen = ScreenCapture()
        self.max_retries = 15
        self.state = None
    
    def execute_task(self, task: str) -> dict:
        print(f"\n{'='*60}")
        print(f"🤖 STARTING TASK: {task}")
        print(f"{'='*60}\n")
        
        self.state = AgentState(task=task)
        
        try:
            self.screen.start_browser()
            
            analysis = self._analyze_task(task)
            self.state.log_action("Task analysis completed")
            print(f"📋 Analysis:\n{analysis}\n")
            
            screenshot = self.screen.navigate("/")
            self.state.add_screenshot(screenshot)
            self.state.log_action("Navigated to home page")
            print("✓ Navigated to admin panel\n")
            
            for attempt in range(self.max_retries):
                print(f"→ Iteration {attempt + 1}/{self.max_retries}")
                
                page_text = self.screen.get_page_text()
                next_action = self._get_next_action(task, page_text)
                
                if next_action.get('type') == 'TASK_COMPLETE':
                    self.state.status = "completed"
                    self.state.log_action("✅ TASK COMPLETED")
                    print(f"✅ {next_action.get('summary', 'Task completed')}")
                    break
                
                if next_action.get('type') == 'TASK_FAILED':
                    self.state.status = "failed"
                    self.state.error = next_action.get('reason', 'Unknown error')
                    self.state.log_action(f"❌ TASK FAILED")
                    print(f"❌ {self.state.error}")
                    break
                
                action_type = next_action.get('action')
                
                if action_type == 'click':
                    x, y = next_action.get('coordinates', [960, 540])
                    screenshot = self.screen.click(x, y)
                    self.state.log_action(f"Clicked at ({x}, {y})")
                    print(f"  🖱️  Clicked at ({x}, {y})")
                    
                elif action_type == 'type':
                    text = next_action.get('text', '')
                    screenshot = self.screen.type_text(text)
                    self.state.log_action(f"Typed: {text[:30]}...")
                    print(f"  ⌨️  Typed: {text[:30]}...")
                    
                elif action_type == 'scroll':
                    direction = next_action.get('direction', 'down')
                    screenshot = self.screen.scroll(direction)
                    self.state.log_action(f"Scrolled {direction}")
                    print(f"  📜 Scrolled {direction}")
                    
                elif action_type == 'wait':
                    seconds = next_action.get('seconds', 2)
                    time.sleep(seconds)
                    screenshot = self.screen.get_screenshot()
                    self.state.log_action(f"Waited {seconds}s")
                    print(f"  ⏳ Waited {seconds}s")
                
                self.state.add_screenshot(screenshot)
            
            self.state.completed_at = time.time()
            
        except Exception as e:
            self.state.status = "failed"
            self.state.error = str(e)
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.screen.close()
        
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY: {self.state.status.upper()}")
        print(f"{'='*60}\n")
        
        return self.state.to_dict()
    
    def _analyze_task(self, task: str) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": TASK_ANALYSIS_PROMPT.format(task=task)}]
            )
            return response.content[0].text
        except Exception as e:
            return "Unable to analyze task"
    
    def _get_next_action(self, task: str, page_text: str) -> dict:
        screenshot = self.state.screenshots[-1] if self.state.screenshots else None
        
        prompt = f"""You are controlling an IT admin panel through a browser.

TASK: {task}

RECENT ACTIONS:
{chr(10).join(self.state.actions[-3:])}

CURRENT PAGE TEXT:
{page_text[:1500]}

Look at the screenshot and decide your NEXT ACTION.

Respond with ONLY ONE of these formats:

1. TASK_COMPLETE: [summary]
2. TASK_FAILED: [reason]
3. click:[name]:[x,y]
4. type:[text]
5. scroll:[up/down]
6. wait:[seconds]

EXAMPLES:
- click:Reset Password:1100,250
- type:alice@company.com
- scroll:down
- wait:2
"""
        
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # Add screenshot if available
            if screenshot:
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot}",
                        "detail": "low"  # Use low detail to save tokens
                    }
                })
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=messages
            )
            
            text = response.choices[0].message.content.strip()
            print(f"  LLM: {text[:60]}")
            
            return self._parse_action_response(text)
            
        except Exception as e:
            print(f"LLM error: {e}")
            return {"action": "wait", "seconds": 1}
    
    def _parse_action_response(self, response: str) -> dict:
        response = response.strip()
        
        if response.startswith("TASK_COMPLETE"):
            summary = response.replace("TASK_COMPLETE:", "").strip()
            return {"type": "TASK_COMPLETE", "summary": summary}
        
        if response.startswith("TASK_FAILED"):
            reason = response.replace("TASK_FAILED:", "").strip()
            return {"type": "TASK_FAILED", "reason": reason}
        
        if response.startswith("click"):
            coords = re.findall(r'(\d+),(\d+)', response)
            if coords:
                return {"action": "click", "coordinates": [int(coords[0][0]), int(coords[0][1])]}
        
        if response.startswith("type"):
            parts = response.split(":", 1)
            if len(parts) >= 2:
                return {"action": "type", "text": parts[1].strip()}
        
        if response.startswith("scroll"):
            direction = "down" if "down" in response.lower() else "up"
            return {"action": "scroll", "direction": direction}
        
        if response.startswith("wait"):
            try:
                seconds = int(re.search(r'\d+', response).group())
            except:
                seconds = 2
            return {"action": "wait", "seconds": seconds}
        
        return {"action": "wait", "seconds": 1}