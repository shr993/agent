"""
Manager API Routes.
Manages team oversight, access approvals, batch operations, and SLA metrics.
"""
import os
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from backend.models import get_manager_data, process_tool_approval, bulk_approve_all_pending, bulk_nudge_incomplete_trainings
    from backend.agent_engine import agent_engine
else:
    from ..models import get_manager_data, process_tool_approval, bulk_approve_all_pending, bulk_nudge_incomplete_trainings
    from ..agent_engine import agent_engine

from flask import Blueprint, request, jsonify

manager_bp = Blueprint("manager_bp", __name__)

@manager_bp.route("/api/manager/dashboard", methods=["GET"])
def get_dashboard():
    manager_email = request.args.get("manager_email") or "sjenkins@company.com"
    data, err = get_manager_data(manager_email)
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "data": data})

@manager_bp.route("/api/manager/insights", methods=["GET"])
def get_insights():
    manager_email = request.args.get("manager_email") or "sjenkins@company.com"
    insights = agent_engine.calculate_team_insights(manager_email)
    return jsonify({"success": True, "insights": insights})

@manager_bp.route("/api/approve_access", methods=["POST"])
def approve_request():
    payload = request.get_json() or {}
    req_id = payload.get("request_id")
    mgr_email = (payload.get("manager_email") or "sjenkins@company.com").strip().lower()
    action = (payload.get("action") or "approve").strip().lower()
    if not req_id:
        return jsonify({"success": False, "error": "request_id is required"}), 400
    success, msg = process_tool_approval(req_id, mgr_email, action)
    if not success:
        return jsonify({"success": False, "error": msg}), 400
    return jsonify({"success": True, "message": msg})

@manager_bp.route("/api/manager/bulk_approve", methods=["POST"])
def bulk_approve():
    payload = request.get_json() or {}
    mgr_email = (payload.get("manager_email") or "sjenkins@company.com").strip().lower()
    count, err = bulk_approve_all_pending(mgr_email)
    if err:
        return jsonify({"success": False, "error": err}), 500
    return jsonify({"success": True, "message": f"Successfully approved all {count} pending requests!", "count": count})

@manager_bp.route("/api/manager/bulk_nudge", methods=["POST"])
def bulk_nudge():
    count, err = bulk_nudge_incomplete_trainings()
    if err:
        return jsonify({"success": False, "error": err}), 500
    return jsonify({"success": True, "message": f"Dispatched automated compliance reminders to {count} employees.", "count": count})

@manager_bp.route("/api/update_employee_status", methods=["POST"])
def update_status():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400
    res = agent_engine.execute_tool("verify_bgc", {"email": email})
    return jsonify(res)
