"""
Agentic Execution & Chat Routes.
Handles conversational AI queries, autonomous intent parsing, and tool execution.
"""
import os
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from backend.agent_engine import agent_engine
else:
    from ..agent_engine import agent_engine

from flask import Blueprint, request, jsonify

agent_bp = Blueprint("agent_bp", __name__)

@agent_bp.route("/api/agent/chat", methods=["POST"])
@agent_bp.route("/api/chat", methods=["POST"])
def chat_with_agent():
    payload = request.get_json() or {}
    message = (payload.get("prompt") or payload.get("message") or "").strip()
    context = payload.get("context") or {}
    role = (payload.get("role") or context.get("role") or "employee").strip().lower()
    context["role"] = role
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400

    result = agent_engine.process_chat(message, context)
    return jsonify({
        "success": True,
        "reply": result["reply"],
        "tool_executed": result.get("tool_executed"),
        "action_cards": result.get("action_cards", []),
        "suggestions": result.get("suggestions", [])
    })

@agent_bp.route("/api/agent/execute_tool", methods=["POST"])
def execute_tool_endpoint():
    payload = request.get_json() or {}
    tool_name = payload.get("tool_name")
    params = payload.get("params") or {}
    if not tool_name:
        return jsonify({"success": False, "error": "tool_name is required"}), 400
    result = agent_engine.execute_tool(tool_name, params)
    return jsonify(result)
