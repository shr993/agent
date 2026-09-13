"""
OnboardAI Platform - Main Application Launcher
Launches the Flask backend server and automatically opens the application.
"""
import os
import sys
import webbrowser
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app import app
from backend.setup_db import init_db

def open_browser(port):
    time.sleep(1.2)
    url = f"http://127.0.0.1:{port}"
    print(f"\n🌐 Opening OnboardAI in your browser: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting OnboardAI Enterprise Agentic Onboarding Platform")
    print("=" * 60)
    
    init_db()
    port = int(os.getenv("PORT", 5000))
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False)
