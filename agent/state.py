"""
Track agent execution state and actions
"""
from dataclasses import dataclass, field
from typing import List
from datetime import datetime

@dataclass
class AgentState:
    """Track agent execution state"""
    task: str
    status: str = "running"
    actions: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    current_page: str = "home"
    error: str = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str = None
    
    def log_action(self, action: str):
        """Log an action"""
        self.actions.append(f"[{len(self.actions)+1}] {action}")
    
    def add_screenshot(self, screenshot: str):
        """Add screenshot to history"""
        self.screenshots.append(screenshot)
    
    def to_dict(self):
        return {
            'task': self.task,
            'status': self.status,
            'actions': self.actions,
            'current_page': self.current_page,
            'error': self.error,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'action_count': len(self.actions)
        }