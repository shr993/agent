 OnboardAI - Enterprise Agentic Onboarding Platform

An autonomous, agentic employee onboarding and manager oversight platform built with **Python (Flask)**, **PostgreSQL**, and a modern, decluttered **Single-Page Application (SPA)** with in-browser screen recording capabilities.

---

## 🌟 Key Features

### 👤 1. Employee Onboarding Journey
- **Connected Circular Stepper Workflow**: Visual pipeline tracking (Profile Created ➔ BGC Verification ➔ Compliance Modules ➔ Work Credentials ➔ Day 1 Ready) with dynamic progress lines.
- **Tools & Sandbox Access Permissions**: Self-service access requests for development tools (*AWS Dev Sandbox*, *GitHub Enterprise*, *Corporate VPN*, *Jira Suite*) with real-time approval tracking.
- **Mandatory Compliance Checklist**: Integrated tracking for compliance modules (*InfoSec*, *Code of Conduct*, *POSH*, *Data Privacy*).

### 👔 2. Manager Operations & Approvals Hub
- **🤖 AI Agent Bottleneck Intelligence**: Autonomous risk analysis detecting SLA breaches, pending approvals, and unverified documents with 1-click batch actions.
- **⚡ Smart Batch Operations**:
  - `[⚡ 1-Click Approve All]`: Bulk approves pending developer tool and sandbox access.
  - `[📩 Send Group Nudge]`: Dispatches automated reminders to joiners with incomplete compliance trainings.
- **Executive KPI Bar**: Live metrics on team size, pending approvals, pending BGCs, and team training velocity.
- **Team Onboarding Master Pipeline**: Real-time roster table with one-click background check verification.
- **Perspective Switcher**: Managers can switch view to inspect any employee's onboarding journey with an override return banner.

### 🤖 3. Truly Agentic AI Copilot
- **Autonomous Tool Execution Engine**:
  - `approve_access(request_id)`
  - `bulk_approve_standard()`
  - `request_access(tool_name)`
  - `bulk_training_nudge()`
  - `verify_bgc(email)`
  - `schedule_checkin(email)`
  - `generate_team_insights()`
- **Interactive Action Cards in Chat**: The agent explains its reasoning and returns actionable UI triggers directly in chat bubbles.

### 🎥 4. In-Browser Screen Recorder (Starts from Login)
- Native screen capture (`MediaRecorder` + `getDisplayMedia`) requiring zero third-party extensions.
- Dedicated **Demo Screen Recording** trigger directly on the login card to capture full end-to-end demonstrations starting before sign-in.
- Synchronized live timers, floating bottom recording widget, and in-browser preview modal with instant `.webm` video download.

### 🔐 5. Clean, Uncluttered Authentication
- Simplified login with strictly **Full Name** and **Email Address** inputs.
- Quick role toggle between Employee and Manager.

---

## 📂 Project Architecture

```text
OnboardAI/
├── backend/
│   ├── app.py                     # Flask entrypoint & CORS configuration
│   ├── config.py                  # Database, SMTP & AI model settings
│   ├── database.py                # PostgreSQL connection helpers
│   ├── models.py                  # Data access layer & database queries
│   ├── agent_engine.py            # Agentic tool registry, reasoning & execution
│   ├── routes/
│   │   ├── employee_routes.py     # Employee profile & tool request APIs
│   │   ├── manager_routes.py      # Manager dashboard, approvals & SLA APIs
│   │   └── agent_routes.py        # Agent chat & tool execution APIs
│   ├── setup_db.py                # Database migrations & seeds
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Template environment configuration
│
├── frontend/
│   ├── index.html                 # Clean, decluttered SPA dashboard
│   ├── css/
│   │   └── styles.css             # Typography, animations & scrollbars
│   └── js/
│       ├── app.js                 # App state, role switcher & toasts
│       ├── agent.js               # Agentic copilot & interactive action cards
│       ├── manager.js             # Manager hub, batch operations & SLA metrics
│       ├── employee.js            # Stepper workflow, tool permissions & trainings
│       └── recorder.js            # Screen recording capture engine & preview
│
├── agent.html                     # Standalone dashboard (portable single-file mode)
├── .gitignore                     # Git ignore rules for Python & IDEs
├── README.md                      # Documentation & setup guide
└── run.py                         # Single-command launcher
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.9+**
- **PostgreSQL** running locally on port `5432`

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/onboard-ai.git
cd onboard-ai
pip install -r backend/requirements.txt
```

### 3. Database Configuration
Ensure PostgreSQL is running. Copy `.env.example` to `.env` (or configure `backend/config.py`):
```bash
cp backend/.env.example backend/.env
```
Run database setup and migrations:
```bash
python backend/setup_db.py
```

### 4. Run the Application
Launch both backend and frontend with a single command:
```bash
python run.py
```
Or run the Flask server directly:
```bash
python backend/app.py
```
Navigate to: **`http://127.0.0.1:5000`**

---

## 📡 API Reference

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `GET /api/user?email=...` | `GET` | Employee | Returns onboarding workflow state and tool requests |
| `POST /api/user/login` | `POST` | Public | Authenticates or registers user profile |
| `POST /api/request_access` | `POST` | Employee | Submits sandbox/tool request to manager |
| `GET /api/manager/dashboard` | `GET` | Manager | Returns team joiners, pending requests, and KPI stats |
| `GET /api/manager/insights` | `GET` | Manager | AI bottleneck insights and team SLA analysis |
| `POST /api/approve_access` | `POST` | Manager | Approves or rejects a tool request |
| `POST /api/manager/bulk_approve` | `POST` | Manager | 1-Click approval for all pending standard tools |
| `POST /api/manager/bulk_nudge` | `POST` | Manager | Sends compliance reminder to all pending employees |
| `POST /api/agent/chat` | `POST` | All | Conversational agent turn with intent parsing |
| `POST /api/agent/execute_tool` | `POST` | All | Direct tool execution endpoint for interactive UI action cards |
