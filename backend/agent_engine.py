"""
Agentic Copilot Engine.
Autonomous tool registry, intent classification, multi-step action execution,
and interactive action card generation.
"""
import os
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from backend.models import (
        create_tool_request, process_tool_approval,
        bulk_approve_all_pending, bulk_nudge_incomplete_trainings,
        get_employee_data, get_manager_data, send_email_notification
    )
    from backend.database import get_db_connection
else:
    from .models import (
        create_tool_request, process_tool_approval,
        bulk_approve_all_pending, bulk_nudge_incomplete_trainings,
        get_employee_data, get_manager_data, send_email_notification
    )
    from .database import get_db_connection

from psycopg2.extras import RealDictCursor

class AgentEngine:
    """Enterprise Onboarding Autonomous Agent Engine."""

    def __init__(self):
        self.name = "OnboardAI Copilot"
        self.version = "2.0 (Agentic Execution)"

    def execute_tool(self, tool_name, params):
        """Directly executes a registered agent tool."""
        try:
            if tool_name == "approve_access":
                req_id = params.get("request_id")
                mgr_email = params.get("manager_email", "sjenkins@company.com")
                success, msg = process_tool_approval(req_id, mgr_email, "approve")
                return {"success": success, "message": msg, "tool": tool_name}

            elif tool_name == "reject_access":
                req_id = params.get("request_id")
                mgr_email = params.get("manager_email", "sjenkins@company.com")
                success, msg = process_tool_approval(req_id, mgr_email, "reject")
                return {"success": success, "message": msg, "tool": tool_name}

            elif tool_name == "bulk_approve_standard":
                mgr_email = params.get("manager_email", "sjenkins@company.com")
                count, err = bulk_approve_all_pending(mgr_email)
                if err:
                    return {"success": False, "message": err, "tool": tool_name}
                return {"success": True, "message": f"Successfully approved all {count} pending access requests!", "count": count, "tool": tool_name}

            elif tool_name == "request_access":
                email = params.get("email")
                tool = params.get("tool_name")
                cat = params.get("tool_category", "Development")
                req, err = create_tool_request(email, tool, cat)
                if err:
                    return {"success": False, "message": err, "tool": tool_name}
                return {"success": True, "message": f"Access request for '{tool}' submitted to your manager!", "request": req, "tool": tool_name}

            elif tool_name == "bulk_training_nudge":
                count, err = bulk_nudge_incomplete_trainings()
                if err:
                    return {"success": False, "message": err, "tool": tool_name}
                return {"success": True, "message": f"Sent compliance reminders to {count} employees with pending trainings.", "count": count, "tool": tool_name}

            elif tool_name == "verify_bgc":
                target_email = params.get("email")
                conn = get_db_connection()
                if not conn:
                    return {"success": False, "message": "Database unavailable", "tool": tool_name}
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("UPDATE onboarding_users SET bgc_status = 'Verified' WHERE LOWER(email) = %s RETURNING name;", (target_email.strip().lower(),))
                    res = cur.fetchone()
                    conn.commit()
                conn.close()
                if res:
                    return {"success": True, "message": f"BGC verified for {res['name']} ({target_email}).", "tool": tool_name}
                return {"success": False, "message": f"User {target_email} not found.", "tool": tool_name}

            elif tool_name == "schedule_checkin":
                emp_email = params.get("email")
                date_time = params.get("date_time", "Tomorrow at 10:00 AM")
                return {
                    "success": True,
                    "message": f"Day 1 Check-in invite scheduled with {emp_email} for {date_time}.",
                    "tool": tool_name
                }

            elif tool_name == "generate_team_insights":
                mgr_email = params.get("manager_email", "sjenkins@company.com")
                insights = self.calculate_team_insights(mgr_email)
                return {"success": True, "insights": insights, "tool": tool_name}

            else:
                return {"success": False, "message": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "message": f"Tool execution failed: {str(e)}", "tool": tool_name}

    def calculate_team_insights(self, manager_email):
        """Autonomous analysis of bottlenecks, SLA risks, and recommended actions."""
        mgr_data, err = get_manager_data(manager_email)
        if err or not mgr_data:
            return {"bottlenecks": [], "sla_status": "Normal", "action_items": []}

        employees = mgr_data.get("employees", [])
        access_requests = mgr_data.get("access_requests", [])
        pending_access = [r for r in access_requests if (r.get("status") or "").lower() == "pending"]

        bottlenecks = []
        action_cards = []

        if pending_access:
            tools_str = ", ".join([f"{r['tool_name']} ({r['employee_name']})" for r in pending_access[:3]])
            bottlenecks.append({
                "severity": "high",
                "title": f"{len(pending_access)} Pending Tool Approvals",
                "description": f"Blocked requests: {tools_str}",
                "action": "bulk_approve_standard",
                "action_label": "⚡ Approve All Standard Tools"
            })
            action_cards.append({
                "title": "Bulk Approve Pending Access",
                "desc": f"Unblock {len(pending_access)} tool access requests across your team.",
                "action": "bulk_approve_standard",
                "payload": {"manager_email": manager_email},
                "btn_text": "⚡ 1-Click Approve All",
                "color": "emerald"
            })

        pending_bgc = [e for e in employees if (e.get("bgc_status") or "").lower() == "pending"]
        if pending_bgc:
            bottlenecks.append({
                "severity": "medium",
                "title": f"{len(pending_bgc)} Pending Background Checks",
                "description": f"Employees awaiting document verification: {', '.join([e['name'] for e in pending_bgc])}",
                "action": "view_pipeline",
                "action_label": "Review Roster"
            })

        low_trainings = [e for e in employees if e.get("trainings_completed", 0) < e.get("trainings_total", 4)]
        if low_trainings:
            bottlenecks.append({
                "severity": "info",
                "title": f"{len(low_trainings)} Incomplete Compliance Trainings",
                "description": "Compliance modules pending for team members.",
                "action": "bulk_training_nudge",
                "action_label": "📩 Send Batch Reminders"
            })
            action_cards.append({
                "title": "Send Compliance Reminders",
                "desc": f"Notify {len(low_trainings)} joiners with remaining mandatory trainings.",
                "action": "bulk_training_nudge",
                "payload": {},
                "btn_text": "📩 Send Batch Nudge",
                "color": "blue"
            })

        avg_progress = mgr_data.get("stats", {}).get("avg_training_progress", 0)
        sla_health = "On Track (2.4 Days Avg)" if avg_progress >= 50 else "Attention Required (SLA 3.8 Days)"

        return {
            "bottlenecks": bottlenecks,
            "sla_health": sla_health,
            "action_cards": action_cards,
            "summary": f"Team Velocity: {sla_health}. {len(pending_access)} approval blockers, {len(pending_bgc)} pending BGCs."
        }

    def process_chat(self, user_msg, context):
        msg_lower = user_msg.lower().strip()
        role = context.get("role", "employee")
        user_email = context.get("email", "")
        user_name = context.get("name", "there")

        action_cards = []
        tool_executed = None
        tool_result = None

        if role == "manager":
            if any(k in msg_lower for k in ["approve all", "bulk approve", "approve pending", "unblock all"]):
                res = self.execute_tool("bulk_approve_standard", {"manager_email": user_email})
                tool_executed = "bulk_approve_standard"
                return {
                    "reply": f"🤖 **Agent Tool Executed:** {res.get('message')}\nAll team access requests have been approved and employees have been notified.",
                    "tool_executed": tool_executed,
                    "action_cards": [],
                    "suggestions": ["Show team bottlenecks", "Send training reminders", "View team SLA"]
                }

            if "approve" in msg_lower and any(w in msg_lower for w in ["aws", "github", "vpn", "jira", "sandbox", "request"]):
                mgr_data, _ = get_manager_data(user_email)
                reqs = (mgr_data or {}).get("access_requests", [])
                pending = [r for r in reqs if (r.get("status") or "").lower() == "pending"]
                matched_req = None
                for r in pending:
                    if r["tool_name"].lower() in msg_lower or (r["employee_name"] or "").lower() in msg_lower:
                        matched_req = r
                        break
                if matched_req:
                    res = self.execute_tool("approve_access", {"request_id": matched_req["id"], "manager_email": user_email})
                    tool_executed = "approve_access"
                    return {
                        "reply": f"🤖 **Agent Action:** Approved **{matched_req['tool_name']}** for **{matched_req['employee_name']}**! Updated in database.",
                        "tool_executed": tool_executed,
                        "action_cards": [],
                        "suggestions": ["Approve remaining requests", "Check team progress"]
                    }
                elif pending:
                    for r in pending[:2]:
                        action_cards.append({
                            "title": f"Approve {r['tool_name']}",
                            "desc": f"Requested by {r['employee_name']}",
                            "action": "approve_access",
                            "payload": {"request_id": r["id"], "manager_email": user_email},
                            "btn_text": f"✓ Approve {r['tool_name']}",
                            "color": "emerald"
                        })
                    return {
                        "reply": f"I found {len(pending)} pending access requests. Would you like me to approve one of these?",
                        "tool_executed": None,
                        "action_cards": action_cards,
                        "suggestions": ["Approve all pending requests", "Show team roster"]
                    }

            if any(k in msg_lower for k in ["nudge", "remind", "reminder", "training reminder", "incomplete"]):
                res = self.execute_tool("bulk_training_nudge", {})
                tool_executed = "bulk_training_nudge"
                return {
                    "reply": f"🤖 **Agent Action:** {res.get('message')}\nAutomated reminder emails have been dispatched.",
                    "tool_executed": tool_executed,
                    "action_cards": [],
                    "suggestions": ["Show team bottlenecks", "Review team SLA"]
                }

            if any(k in msg_lower for k in ["bottleneck", "insight", "status", "overview", "what needs", "attention", "blocker"]):
                insights = self.calculate_team_insights(user_email)
                b_lines = [f"• **{b['title']}**: {b['description']}" for b in insights.get("bottlenecks", [])]
                text = f"📊 **Team Onboarding Intelligence Report:**\n\n**Velocity Health:** {insights.get('sla_health')}\n\n" + "\n".join(b_lines or ["• All systems operating smoothly. No critical blockers detected."])
                return {
                    "reply": text,
                    "tool_executed": "generate_team_insights",
                    "action_cards": insights.get("action_cards", []),
                    "suggestions": ["Approve all pending requests", "Send training reminders"]
                }

            insights = self.calculate_team_insights(user_email)
            return {
                "reply": f"Hello Manager {user_name}! I am your Autonomous Onboarding Copilot.\n\n{insights.get('summary')}\n\nYou can ask me to: *'Approve all requests'*, *'Send training reminders'*, or *'Show bottlenecks'*.",
                "tool_executed": None,
                "action_cards": insights.get("action_cards", [])[:2],
                "suggestions": ["Approve all pending requests", "Show team bottlenecks", "Send training reminders"]
            }

        else:
            emp_data, _ = get_employee_data(user_email)
            if not emp_data:
                emp_data = {"name": user_name, "email": user_email, "trainings": [], "access_requests": []}

            if any(k in msg_lower for k in ["request", "give me access", "need access", "want access", "sandbox"]):
                tool_target = "AWS Dev Sandbox"
                if "git" in msg_lower: tool_target = "GitHub Enterprise"
                elif "vpn" in msg_lower: tool_target = "Corporate VPN Gateway"
                elif "jira" in msg_lower: tool_target = "Jira & Confluence Suite"

                res = self.execute_tool("request_access", {"email": user_email, "tool_name": tool_target, "tool_category": "Development"})
                tool_executed = "request_access"
                return {
                    "reply": f"🤖 **Agent Action:** I have submitted a formal access request for **{tool_target}** to your reporting manager (Sarah Jenkins). You will receive an email once approved!",
                    "tool_executed": tool_executed,
                    "action_cards": [],
                    "suggestions": ["Check my status", "Show my trainings", "Who is my manager?"]
                }

            if any(k in msg_lower for k in ["next", "step", "what should i do", "status", "progress"]):
                bgc = emp_data.get("bgc_status", "Pending")
                pending_tr = emp_data.get("pending_trainings", [])
                if bgc == "Pending":
                    action_cards.append({
                        "title": "BGC Document Submission",
                        "desc": "Upload verification documents to proceed.",
                        "action": "nudge_bgc",
                        "payload": {"email": user_email},
                        "btn_text": "📄 Upload BGC Documents",
                        "color": "amber"
                    })
                    return {
                        "reply": f"Hi {user_name}, your immediate next step is **Background Verification (BGC)**. Once submitted, compliance modules will unlock.",
                        "tool_executed": None,
                        "action_cards": action_cards,
                        "suggestions": ["Show my trainings", "Request tool access"]
                    }
                elif pending_tr:
                    next_tr = pending_tr[0]
                    return {
                        "reply": f"Hi {user_name}, your BGC is verified! Your next priority is to complete **{next_tr}** ({len(pending_tr)} compliance modules remaining).",
                        "tool_executed": None,
                        "action_cards": [{
                            "title": f"Start {next_tr}",
                            "desc": "Required mandatory compliance training.",
                            "action": "open_training",
                            "payload": {"training": next_tr},
                            "btn_text": f"🚀 Launch {next_tr}",
                            "color": "blue"
                        }],
                        "suggestions": ["Show all trainings", "Request tool access"]
                    }
                else:
                    return {
                        "reply": f"🎉 Congratulations {user_name}! All onboarding requirements and compliance trainings are complete. Your IT credentials will be dispatched to `{user_email}`.",
                        "tool_executed": None,
                        "action_cards": [],
                        "suggestions": ["Request additional tools", "Who is my manager?"]
                    }

            if any(k in msg_lower for k in ["training", "course", "compliance", "module", "posh", "infosec"]):
                tr_list = emp_data.get("trainings", [])
                completed = len([t for t in tr_list if t.get("status") == "Completed"])
                return {
                    "reply": f"📚 **Compliance Overview ({completed}/{len(tr_list)} Completed):**\n" + "\n".join([f"• **{t['name']}**: {t['status']}" for t in tr_list]),
                    "tool_executed": None,
                    "action_cards": [],
                    "suggestions": ["What is my next step?", "Request tool access"]
                }

            if any(k in msg_lower for k in ["manager", "lead", "boss", "supervisor", "sarah"]):
                return {
                    "reply": "👤 **Your Reporting Manager:**\n• **Name:** Sarah Jenkins (Engineering & Onboarding Lead)\n• **Email:** `sjenkins@company.com`\n• **Office:** 4th Floor, Tech Hub",
                    "tool_executed": None,
                    "action_cards": [{
                        "title": "Schedule Day 1 Sync",
                        "desc": "Book a 15-min welcome chat with Sarah Jenkins.",
                        "action": "schedule_sync",
                        "payload": {"email": user_email},
                        "btn_text": "📅 Book 1-on-1 Sync",
                        "color": "indigo"
                    }],
                    "suggestions": ["What is my next step?", "Show my trainings"]
                }

            return {
                "reply": f"Hi {user_name}! I am your OnboardAI Assistant. How can I assist your Day 1 journey today?\n\nTry asking: *'What is my next step?'*, *'Request AWS Sandbox'*, or *'Show my trainings'*.",
                "tool_executed": None,
                "action_cards": [{
                    "title": "Request AWS Dev Sandbox",
                    "desc": "Provision cloud development workspace.",
                    "action": "request_access",
                    "payload": {"email": user_email, "tool_name": "AWS Dev Sandbox"},
                    "btn_text": "⚡ Request AWS Access",
                    "color": "blue"
                }],
                "suggestions": ["What is my next step?", "Request AWS Dev Sandbox", "Show my trainings"]
            }

agent_engine = AgentEngine()
