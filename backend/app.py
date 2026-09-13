"""
Main Flask Server Entrypoint.
Serves API routes and frontend single-page application.
"""
import os
import sys

# Ensure UTF-8 output encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Universal import support
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from backend.routes.employee_routes import employee_bp
    from backend.routes.manager_routes import manager_bp
    from backend.routes.agent_routes import agent_bp
    from backend.setup_db import init_db
else:
    from .routes.employee_routes import employee_bp
    from .routes.manager_routes import manager_bp
    from .routes.agent_routes import agent_bp
    from .setup_db import init_db

from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

# Enable CORS
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

# Register Blueprints
app.register_blueprint(employee_bp)
app.register_blueprint(manager_bp)
app.register_blueprint(agent_bp)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Serve Frontend SPA
@app.route("/")
@app.route("/agent")
def serve_index():
    if os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
        return send_from_directory(FRONTEND_DIR, "index.html")
    # Fallback to root agent.html
    return send_from_directory(ROOT_DIR, "agent.html")

@app.route("/frontend/<path:path>")
def serve_frontend_assets(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route("/css/<path:path>")
def serve_css(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), path)

@app.route("/js/<path:path>")
def serve_js(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), path)

@app.route("/api/health")
def health_check():
    return jsonify({"status": "healthy", "service": "OnboardAI Platform", "version": "2.0.0"})

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 OnboardAI Backend Server running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
