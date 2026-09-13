"""
Configuration Module for OnboardAI Platform.
Manages database, SMTP credentials, and agent configurations.
"""
import os

# 1. PostgreSQL Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2002")

# 2. Email Notifications (SMTP)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "shraddhawarade85@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")  # Google App Password if active
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to the Team, {Name}! Action Required",
        "body": "Hi {Name},\n\nWelcome to the team! Your account profile has been created.\n\nPlease upload your BGC documents.\n\nBest,\nHR Onboarding Team"
    },
    "training_reminder": {
        "subject": "Action Required: Complete Mandatory Onboarding Trainings, {Name}",
        "body": "Hi {Name},\n\nThis is a reminder to complete your mandatory compliance modules ({PendingList}).\n\nPlease log into the Onboarding Portal to finish these.\n\nBest,\nHR Onboarding Team"
    },
    "access_approved": {
        "subject": "Access Granted: {ToolName}",
        "body": "Hi {Name},\n\nYour manager has approved access to {ToolName}. Your credentials and sandbox access are now active.\n\nBest,\nIT Provisioning Team"
    }
}

# 3. Agent Engine Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AGENT_NAME = "OnboardAI Copilot"
AGENT_VERSION = "2.0.0 (Agentic Execution Engine)"
