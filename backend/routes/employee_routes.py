"""
Employee API Routes.
Manages employee profiles, onboarding status retrieval, and tool access requests.
"""
import os
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from backend.models import get_or_create_user, get_employee_data, create_tool_request
else:
    from ..models import get_or_create_user, get_employee_data, create_tool_request

from flask import Blueprint, request, jsonify

employee_bp = Blueprint("employee_bp", __name__)

@employee_bp.route("/api/user", methods=["GET"])
def get_user_profile():
    email = request.args.get("email")
    if not email:
        return jsonify({"success": False, "error": "Email parameter is required"}), 400
    user, err = get_employee_data(email)
    if err:
        return jsonify({"success": False, "error": err}), 404
    return jsonify({"success": True, "user": user, "event": "Profile loaded from database."})

@employee_bp.route("/api/user/login", methods=["POST"])
def user_login():
    payload = request.get_json() or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    role = (payload.get("role") or "employee").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400
    user, err = get_or_create_user(name or email.split("@")[0].capitalize(), email, role)
    if err:
        return jsonify({"success": False, "error": err}), 500
    return jsonify({"success": True, "user": user})

@employee_bp.route("/api/request_access", methods=["POST"])
def submit_tool_request():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    tool_name = (payload.get("tool_name") or "").strip()
    tool_cat = (payload.get("tool_category") or "Development").strip()
    if not email or not tool_name:
        return jsonify({"success": False, "error": "Email and tool_name are required"}), 400
    req, err = create_tool_request(email, tool_name, tool_cat)
    if err:
        return jsonify({"success": False, "error": err}), 500
    return jsonify({"success": True, "message": f"Access request for '{tool_name}' submitted to your manager!", "request": req})
