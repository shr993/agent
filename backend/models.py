"""
Data Access Layer (Models & Database Queries).
Provides structured methods for users, trainings, access requests, and manager operations.
"""
import os
import sys
import smtplib
from email.message import EmailMessage
from psycopg2.extras import RealDictCursor

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from backend.database import get_db_connection, clean_val, is_yes
    from backend.config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, EMAIL_TEMPLATES
else:
    from .database import get_db_connection, clean_val, is_yes
    from .config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, EMAIL_TEMPLATES

def send_email_notification(to_email, name, template_key, **kwargs):
    """Sends an email notification via SMTP (falls back to simulation mode if password empty)."""
    if not EMAIL_PASSWORD:
        print(f"[SMTP SIMULATION] Email would be sent to {to_email} (Template: {template_key})")
        return True
    template = EMAIL_TEMPLATES.get(template_key)
    if not template:
        return False
    body = template["body"].replace("{Name}", name)
    subject = template["subject"].replace("{Name}", name)
    for k, v in kwargs.items():
        body = body.replace(f"{{{k}}}", str(v))
        subject = subject.replace(f"{{{k}}}", str(v))
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"[SMTP SUCCESS] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[SMTP ERROR] Failed to send email to {to_email}: {e}")
        return False

def get_or_create_user(name, email, role="employee"):
    """Fetch an existing user or create a new user profile on login."""
    conn = get_db_connection()
    if not conn:
        return None, "Database connection failed"
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (email.strip().lower(),))
            user = cur.fetchone()
            if not user:
                cur.execute("""
                    INSERT INTO onboarding_users (name, email, role, profile_created, bgc_status, onboarding_status, welcome_sent)
                    VALUES (%s, %s, %s, 'Yes', 'Pending', 'In Progress', 'Yes')
                    RETURNING *;
                """, (name.strip(), email.strip().lower(), role))
                user = cur.fetchone()
                
                # Assign default mandatory compliance trainings
                cur.execute("""
                    INSERT INTO user_trainings (user_id, training_id, status)
                    SELECT %s, id, 'Pending' FROM trainings_catalog
                    ON CONFLICT DO NOTHING;
                """, (user["id"],))
                conn.commit()
                send_email_notification(email, name, "welcome")
            return user, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

def get_employee_data(email):
    """Retrieve full employee profile, assigned trainings, and access requests."""
    conn = get_db_connection()
    if not conn:
        return None, "Database connection failed"
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (email.strip().lower(),))
            u = cur.fetchone()
            if not u:
                return None, f"Employee '{email}' not found."
            user_id = u["id"]

            # Trainings
            cur.execute("""
                SELECT tc.training_name, ut.status, ut.completed_at
                FROM user_trainings ut
                JOIN trainings_catalog tc ON ut.training_id = tc.id
                WHERE ut.user_id = %s
                ORDER BY tc.id ASC;
            """, (user_id,))
            trainings = cur.fetchall()
            trainings_list = [{"name": t["training_name"], "status": t["status"]} for t in trainings]
            pending_trainings = [t["training_name"] for t in trainings if clean_val(t["status"]).lower() != "completed"]

            # Access Requests
            cur.execute("""
                SELECT id, tool_name, tool_category, status, requested_at, reviewed_at
                FROM access_requests
                WHERE user_id = %s
                ORDER BY requested_at DESC;
            """, (user_id,))
            req_rows = cur.fetchall()
            access_list = [{
                "id": r["id"],
                "tool_name": r["tool_name"],
                "tool_category": r["tool_category"],
                "status": r["status"]
            } for r in req_rows]

            record = {
                "id": u["id"],
                "name": u["name"],
                "email": u["email"],
                "role": u.get("role") or "employee",
                "manager_id": u.get("manager_id"),
                "profile_created": "Yes" if is_yes(u.get("profile_created")) else "Pending",
                "welcome_sent": "Yes" if is_yes(u.get("welcome_sent")) else "Pending",
                "bgc_status": clean_val(u.get("bgc_status")) or "Pending",
                "onboarding_status": clean_val(u.get("onboarding_status")) or "In Progress",
                "credentials_sent": "Yes" if is_yes(u.get("credentials_sent")) else "Pending",
                "trainings": trainings_list,
                "pending_trainings": pending_trainings,
                "access_requests": access_list
            }
            return record, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

def get_manager_data(manager_email):
    """Retrieve full manager dashboard data: manager profile, team roster, approvals queue, and metrics."""
    conn = get_db_connection()
    if not conn:
        return None, "Database connection failed"
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (manager_email.strip().lower(),))
            mgr = cur.fetchone()
            if not mgr:
                cur.execute("""
                    INSERT INTO onboarding_users (name, email, role, profile_created, bgc_status, onboarding_status, welcome_sent)
                    VALUES ('Sarah Jenkins', %s, 'manager', 'Yes', 'Verified', 'Completed', 'Yes')
                    RETURNING *;
                """, (manager_email.strip().lower(),))
                mgr = cur.fetchone()
                conn.commit()

            cur.execute("""
                SELECT u.id, u.name, u.email, u.profile_created, u.bgc_status, u.onboarding_status, u.credentials_sent,
                       COUNT(ut.id) AS total_trainings,
                       COUNT(CASE WHEN LOWER(ut.status) = 'completed' THEN 1 END) AS completed_trainings
                FROM onboarding_users u
                LEFT JOIN user_trainings ut ON u.id = ut.user_id
                WHERE u.role = 'employee' OR u.id != %s
                GROUP BY u.id, u.name, u.email, u.profile_created, u.bgc_status, u.onboarding_status, u.credentials_sent
                ORDER BY u.id ASC;
            """, (mgr["id"],))
            emp_rows = cur.fetchall()

            employees = []
            pending_bgc_count = 0
            total_trainings_all = 0
            completed_trainings_all = 0

            for emp in emp_rows:
                tot = int(emp["total_trainings"] or 0)
                comp = int(emp["completed_trainings"] or 0)
                total_trainings_all += tot
                completed_trainings_all += comp
                if (emp["bgc_status"] or "").lower() == "pending":
                    pending_bgc_count += 1
                pct = int((comp / tot * 100)) if tot > 0 else 0
                employees.append({
                    "id": emp["id"],
                    "name": emp["name"],
                    "email": emp["email"],
                    "profile_created": emp["profile_created"],
                    "bgc_status": emp["bgc_status"],
                    "onboarding_status": emp["onboarding_status"],
                    "credentials_sent": emp["credentials_sent"],
                    "trainings_completed": comp,
                    "trainings_total": tot,
                    "progress_pct": pct
                })

            cur.execute("""
                SELECT ar.id, ar.user_id, u.name AS employee_name, u.email AS employee_email,
                       ar.tool_name, ar.tool_category, ar.status, ar.requested_at, ar.reviewed_at
                FROM access_requests ar
                JOIN onboarding_users u ON ar.user_id = u.id
                ORDER BY CASE WHEN ar.status = 'Pending' THEN 0 ELSE 1 END, ar.requested_at DESC;
            """)
            req_rows = cur.fetchall()
            access_requests = []
            pending_access_count = 0
            for r in req_rows:
                if (r["status"] or "").lower() == "pending":
                    pending_access_count += 1
                access_requests.append({
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "employee_name": r["employee_name"],
                    "employee_email": r["employee_email"],
                    "tool_name": r["tool_name"],
                    "tool_category": r["tool_category"],
                    "status": r["status"],
                    "requested_at": str(r["requested_at"]) if r.get("requested_at") else None,
                    "reviewed_at": str(r["reviewed_at"]) if r.get("reviewed_at") else None
                })

            avg_progress = int((completed_trainings_all / total_trainings_all * 100)) if total_trainings_all > 0 else 0

            return {
                "manager": {
                    "id": mgr["id"],
                    "name": mgr["name"],
                    "email": mgr["email"],
                    "role": "manager"
                },
                "employees": employees,
                "access_requests": access_requests,
                "stats": {
                    "total_employees": len(employees),
                    "pending_access_requests": pending_access_count,
                    "pending_bgc": pending_bgc_count,
                    "avg_training_progress": avg_progress
                }
            }, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

def create_tool_request(email, tool_name, tool_category="Development"):
    """Submits a new tool access request for an employee."""
    conn = get_db_connection()
    if not conn:
        return None, "Database connection failed"
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (email.strip().lower(),))
            u = cur.fetchone()
            if not u:
                return None, f"User '{email}' not found."
            cur.execute("""
                INSERT INTO access_requests (user_id, tool_name, tool_category, status, requested_at)
                VALUES (%s, %s, %s, 'Pending', NOW())
                RETURNING id, tool_name, status, requested_at;
            """, (u["id"], tool_name, tool_category))
            req = cur.fetchone()
            conn.commit()
            return req, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

def process_tool_approval(request_id, manager_email, action="approve"):
    """Approves or rejects a tool access request."""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (manager_email.strip().lower(),))
            mgr = cur.fetchone()
            mgr_id = mgr["id"] if mgr else None
            new_status = "Approved" if action.lower() == "approve" else "Rejected"
            cur.execute("""
                UPDATE access_requests
                SET status = %s, reviewed_by = %s, reviewed_at = NOW()
                WHERE id = %s
                RETURNING tool_name, user_id;
            """, (new_status, mgr_id, request_id))
            updated = cur.fetchone()
            if not updated:
                return False, f"Access request ID {request_id} not found."
            conn.commit()

            cur.execute("SELECT name, email FROM onboarding_users WHERE id = %s;", (updated["user_id"],))
            emp = cur.fetchone()
            if emp and new_status == "Approved":
                send_email_notification(emp["email"], emp["name"], "access_approved", ToolName=updated["tool_name"])
            return True, f"Request for '{updated['tool_name']}' has been {new_status}."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def bulk_approve_all_pending(manager_email):
    """Bulk approves all pending access requests."""
    conn = get_db_connection()
    if not conn:
        return 0, "Database connection failed"
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (manager_email.strip().lower(),))
            mgr = cur.fetchone()
            mgr_id = mgr["id"] if mgr else None
            cur.execute("""
                UPDATE access_requests
                SET status = 'Approved', reviewed_by = %s, reviewed_at = NOW()
                WHERE status = 'Pending'
                RETURNING id;
            """, (mgr_id,))
            rows = cur.fetchall()
            conn.commit()
            return len(rows), None
    except Exception as e:
        return 0, str(e)
    finally:
        conn.close()

def bulk_nudge_incomplete_trainings():
    """Sends training reminders to all employees with incomplete compliance trainings."""
    conn = get_db_connection()
    if not conn:
        return 0, "Database connection failed"
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT u.name, u.email, STRING_AGG(tc.training_name, ', ') AS pending_list
                FROM onboarding_users u
                JOIN user_trainings ut ON u.id = ut.user_id
                JOIN trainings_catalog tc ON ut.training_id = tc.id
                WHERE LOWER(ut.status) != 'completed' AND u.role = 'employee'
                GROUP BY u.id, u.name, u.email;
            """)
            nudges = cur.fetchall()
            count = 0
            for n in nudges:
                send_email_notification(n["email"], n["name"], "training_reminder", PendingList=n["pending_list"])
                count += 1
            return count, None
    except Exception as e:
        return 0, str(e)
    finally:
        conn.close()
