# IT Admin Panel - AI Agent Automation

An intelligent AI agent that automates IT admin tasks on a mock admin panel using natural language commands.

## Features

- **AI-Powered Automation**: Uses Llama3 (local Ollama) to understand and execute tasks
- **Browser Automation**: Selenium WebDriver for realistic UI interaction
- **No API Shortcuts**: Agent navigates UI like a human would
- **100% Local**: No cloud services, complete privacy
- **Multi-Step Tasks**: Handles complex workflows with conditional logic

##  Tasks Supported

1. **Create New User** - Add users with email, name, department, password
2. **Reset Password** - Change user passwords securely
3. **Assign License** - Allocate licenses to users

##  Quick Start

### Prerequisites
- Python 3.8+
- Chrome browser
- Ollama installed (https://ollama.ai)
- ChromeDriver (auto-installed via webdriver-manager)

### Installation

1. **Clone repository**
```bash
git clone https://github.com/harshityadav802/IT-admin-panel
cd IT-admin-panel
