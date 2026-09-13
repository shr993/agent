import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.message import EmailMessage
from flask import Flask, jsonify, request, send_from_directory

# ==========================================
# 1. CONFIGURATION & DATABASE SETTINGS
# ==========================================
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"       # Database name
DB_USER = "postgres"
DB_PASSWORD = "2002"  # Password

EMAIL_ADDRESS = "shraddhawarade85@gmail.com"  # Sender email address
EMAIL_PASSWORD = "" # Gmail App Password if testing SMTP
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to the Team, {Name}! Action Required",
        "body": "Hi {Name},\n\nWelcome to the team! Your account profile has been created.\n\nPlease upload BGC documents.\n\nBest,\nHR Onboarding Team"
    }
}

app = Flask(__name__)

# Enable CORS for browser access
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

# ==========================================
# 2. DATABASE CONNECTION HELPER
# ==========================================
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"❌ PostgreSQL Connection Error: {e}")
        return None

def clean_val(v):
    return str(v).strip() if v is not None else ""

def is_yes(v):
    return clean_val(v).lower() == "yes"

# ==========================================
# 3. EMAIL AUTOMATION ENGINE
# ==========================================
def send_email(to_email, name, template_key):
    if not EMAIL_PASSWORD:
        print(f"⚠️ Simulation Mode: Email would be sent to {to_email} (App Password not configured).")
        return True

    template = EMAIL_TEMPLATES.get(template_key)
    if not template:
        return False

    msg = EmailMessage()
    msg.set_content(template["body"].replace("{Name}", name))
    msg['Subject'] = template["subject"].replace("{Name}", name)
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Welcome email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# ==========================================
# 4. POSTGRESQL DATA FETCH & UPDATE
# ==========================================
def get_user_data(target_user):
    target = target_user.strip().lower()
    conn = get_db_connection()
    if not conn:
        return None, "Database connection failed. Ensure PostgreSQL service is running."

    record = None
    event_msg = None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Query the User from onboarding_users table
            cur.execute("""
                SELECT * FROM onboarding_users 
                WHERE LOWER(email) = %s OR LOWER(name) = %s 
                LIMIT 1;
            """, (target, target))
            user_row = cur.fetchone()

            if not user_row:
                return None, f"User '{target_user}' not found in database."

            user_id = user_row["id"]
            name = clean_val(user_row["name"])
            email = clean_val(user_row["email"])
            role = clean_val(user_row.get("role")) or "employee"
            profile_created = user_row.get("profile_created")
            welcome_sent = user_row.get("welcome_sent")

            # 2. TRIGGER: If profile_created is 'Yes' & welcome email not sent yet
            if is_yes(profile_created) and not is_yes(welcome_sent):
                if send_email(email, name, "welcome"):
                    cur.execute("""
                        UPDATE onboarding_users 
                        SET welcome_sent = 'Yes', updated_at = NOW() 
                        WHERE id = %s;
                    """, (user_id,))
                    conn.commit()
                    welcome_sent = "Yes"
                    event_msg = f"Welcome email sent to {name} and recorded in database!"
                    print(f"💾 Updated PostgreSQL: welcome_sent='Yes' for user ID {user_id}")
            elif is_yes(welcome_sent):
                event_msg = f"Welcome email sent to {name} and recorded in database!"

            # 3. Query User's Assigned Trainings using SQL JOIN
            cur.execute("""
                SELECT 
                    t.training_name,
                    ut.status,
                    ut.completed_at
                FROM user_trainings ut
                JOIN trainings_catalog t ON ut.training_id = t.id
                WHERE ut.user_id = %s
                ORDER BY t.id;
            """, (user_id,))
            training_rows = cur.fetchall()

            trainings_list = []
            pending_trainings = []
            for t in training_rows:
                t_name = t["training_name"]
                t_status = clean_val(t["status"]) or "Pending"
                trainings_list.append({
                    "name": t_name,
                    "status": t_status
                })
                if t_status.lower() != "completed":
                    pending_trainings.append(t_name)

            # 4. Query User's Tool & Sandbox Access Requests
            cur.execute("""
                SELECT id, tool_name, tool_category, status, requested_at, reviewed_at
                FROM access_requests
                WHERE user_id = %s
                ORDER BY requested_at DESC;
            """, (user_id,))
            access_rows = cur.fetchall()
            access_list = []
            for ar in access_rows:
                access_list.append({
                    "id": ar["id"],
                    "tool_name": ar["tool_name"],
                    "tool_category": ar["tool_category"],
                    "status": ar["status"],
                    "requested_at": str(ar["requested_at"]) if ar.get("requested_at") else None,
                    "reviewed_at": str(ar["reviewed_at"]) if ar.get("reviewed_at") else None
                })

            record = {
                "id": user_id,
                "name": name,
                "email": email,
                "role": role,
                "manager_id": user_row.get("manager_id"),
                "profile_created": "Yes" if is_yes(profile_created) else "Pending",
                "welcome_sent": "Yes" if is_yes(welcome_sent) else "Pending",
                "bgc_status": clean_val(user_row.get("bgc_status")) or "Pending",
                "onboarding_status": clean_val(user_row.get("onboarding_status")) or "In Progress",
                "credentials_sent": "Yes" if is_yes(user_row.get("credentials_sent")) else "Pending",
                "trainings": trainings_list,
                "pending_trainings": pending_trainings,
                "access_requests": access_list
            }

    except Exception as e:
        print(f"❌ Error during database query: {e}")
        return None, f"Database error: {e}"
    finally:
        conn.close()

    return record, event_msg

def get_manager_dashboard_data(manager_email):
    conn = get_db_connection()
    if not conn:
        return None, "Database connection failed."

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch Manager record
            cur.execute("""
                SELECT * FROM onboarding_users 
                WHERE LOWER(email) = %s 
                LIMIT 1;
            """, (manager_email.strip().lower(),))
            mgr_row = cur.fetchone()

            if not mgr_row:
                return None, f"Manager '{manager_email}' not found."

            mgr_id = mgr_row["id"]

            # 2. Fetch all employees (reporting to this manager, or all users with role='employee')
            cur.execute("""
                SELECT u.id, u.name, u.email, u.profile_created, u.bgc_status, u.onboarding_status, u.credentials_sent,
                       COUNT(ut.id) AS total_trainings,
                       COUNT(CASE WHEN LOWER(ut.status) = 'completed' THEN 1 END) AS completed_trainings
                FROM onboarding_users u
                LEFT JOIN user_trainings ut ON u.id = ut.user_id
                WHERE u.role = 'employee' OR u.id != %s
                GROUP BY u.id, u.name, u.email, u.profile_created, u.bgc_status, u.onboarding_status, u.credentials_sent
                ORDER BY u.id;
            """, (mgr_id,))
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

            # 3. Fetch all tool access requests
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
                    "id": mgr_id,
                    "name": mgr_row["name"],
                    "email": mgr_row["email"],
                    "role": "manager"
                },
                "stats": {
                    "total_employees": len(employees),
                    "pending_bgc": pending_bgc_count,
                    "pending_access_requests": pending_access_count,
                    "avg_training_progress": avg_progress
                },
                "employees": employees,
                "access_requests": access_requests
            }, None

    except Exception as e:
        print(f"❌ Error fetching manager dashboard: {e}")
        return None, str(e)
    finally:
        conn.close()

# ==========================================
# 5. AI AGENT ENGINE (PROMPTS & SUGGESTIONS)
# ==========================================
def generate_agent_response(user_data, prompt):
    p = prompt.strip().lower()
    name = user_data["name"]
    role = user_data.get("role", "employee")

    # Manager Copilot responses
    if role == "manager":
        if any(k in p for k in ["hi", "hello", "hey"]):
            return (
                f"Hello Manager {name}! 👔 I am your Onboarding Operations Copilot. "
                f"I can help you monitor team onboarding progress, review pending BGC checks, "
                f"or approve tool and sandbox access permissions. How can I assist you today?"
            )
        if any(k in p for k in ["pending", "approval", "request", "tool", "sandbox"]):
            return (
                f"📋 **Pending Action Items:**\n"
                f"• Review pending developer tools & sandbox access requests in your Approvals queue.\n"
                f"• Verify pending background verification documents for newly onboarded team joiners.\n"
                f"You can approve or reject directly using the approval buttons above!"
            )
        if any(k in p for k in ["team", "employee", "joiner", "track", "progress"]):
            return (
                f"👥 **Team Onboarding Snapshot:**\n"
                f"You have team members progressing through compliance training and credentialing. "
                f"Click '👁️ View Journey' on any employee card to inspect their live workflow from their perspective!"
            )
        return (
            f"Hello {name}. You are currently logged in as a Manager. "
            f"Ask me about: *'Show pending approvals'*, *'Team progress summary'*, or *'Which employees have pending BGC?'*"
        )

    # Employee responses
    pending_tr = user_data.get("pending_trainings", [])
    bgc = user_data.get("bgc_status", "Pending")
    creds = user_data.get("credentials_sent", "Pending")
    total_tr = len(user_data.get("trainings", []))
    completed_tr = total_tr - len(pending_tr)

    # Greetings
    if any(k in p for k in ["hi", "hello", "hey", "good morning", "good afternoon"]):
        return (
            f"Hello {name}! 👋 I am your Onboarding Buddy. "
            f"I'm here to guide you through every milestone until your Day 1.\n\n"
            f"Currently, you have completed {completed_tr} of {total_tr} mandatory trainings, "
            f"and your Background Verification is '{bgc}'. How can I help you today?"
        )

    # Tool / Sandbox Access
    if any(k in p for k in ["tool", "sandbox", "aws", "github", "vpn", "access", "permission"]):
        return (
            f"🔑 **Tools & Sandbox Access:**\n"
            f"You can request access to developer tools (AWS Dev Sandbox, GitHub Enterprise, VPN, Jira) "
            f"directly from your 'Tools & Sandbox Permissions' dashboard card below. "
            f"Once submitted, your request is routed to your manager (Sarah Jenkins) for approval!"
        )

    # Next steps / Suggestions
    if any(k in p for k in ["suggest", "next", "what should i do", "priority"]):
        if bgc.lower() == "pending":
            return (
                f"💡 **Immediate Priority for {name}:**\n"
                f"Please upload your government-issued ID and address proof to complete your **Background Check (BGC)**. "
                f"Once verified, your work credentials can be generated."
            )
        elif pending_tr:
            return (
                f"💡 **Next Milestone:**\n"
                f"Your BGC is in good order! Please complete your **{len(pending_tr)} remaining training(s)**: "
                f"{', '.join(pending_tr)}."
            )
        elif creds != "Yes":
            return (
                f"💡 **Next Milestone:**\n"
                f"All compliance items are satisfied! The IT provisioning team is preparing your enterprise work credentials."
            )
        return f"🌟 Congratulations {name}! You have cleared all onboarding requirements and are 100% Day 1 ready!"

    # Checklist & Pending tasks
    if any(k in p for k in ["pending", "incomplete", "checklist", "remaining", "tasks"]):
        items = []
        if user_data["profile_created"] != "Yes":
            items.append("HR Profile Initialization")
        if bgc.lower() == "pending":
            items.append("Background Verification (Submit government ID & address proof)")
        if pending_tr:
            items.append(f"Mandatory Trainings ({len(pending_tr)} remaining): {', '.join(pending_tr)}")
        if creds != "Yes":
            items.append("IT Provisioning & Work Credentials issuance")
        
        if items:
            return f"📋 **Your Onboarding Checklist ({name}):**\n- " + "\n- ".join(items)
        return f"🎉 **All Done!** You have completed all required onboarding checklist items."

    # Background verification info
    if any(k in p for k in ["bgc", "background", "documents", "verification"]):
        if bgc.lower() == "pending":
            return (
                f"📄 **Background Check (BGC) Status: Pending Review**\n"
                f"Please ensure you have submitted:\n"
                f"1. Government-issued Photo ID (Passport, Driver's License, or National ID)\n"
                f"2. Current Address Proof (Utility bill or bank statement within 3 months)\n"
                f"3. Highest Educational Degree certificate\n\n"
                f"If you've already uploaded these, verification typically takes 24-48 business hours."
            )
        return f"✅ **Background Check (BGC) Status: Verified!** Your verification is complete."

    # Trainings details
    if any(k in p for k in ["training", "trainings", "course", "modules", "infosec", "posh", "conduct", "privacy"]):
        tr_lines = []
        for t in user_data["trainings"]:
            icon = "✅" if t["status"].lower() == "completed" else ("⏳" if t["status"].lower() == "in progress" else "⚪")
            tr_lines.append(f"{icon} **{t['name']}**: {t['status']}")
        return f"🎓 **Mandatory Compliance Modules ({completed_tr}/{total_tr} Completed):**\n" + "\n".join(tr_lines)

    # Manager / Leadership
    if any(k in p for k in ["manager", "lead", "supervisor", "reporting", "boss"]):
        return (
            f"👤 **Your Reporting Manager:**\n"
            f"• Name: Sarah Jenkins (Engineering & Onboarding Lead)\n"
            f"• Email: sjenkins@company.com\n"
            f"• Office Location: 4th Floor, Technology Center"
        )

    # IT Support / Credentials
    if any(k in p for k in ["it", "support", "laptop", "equipment", "credentials", "email", "access"]):
        return (
            f"💻 **IT & System Credentials:**\n"
            f"• Credentials Issued: **{creds}**\n"
            f"• IT Helpdesk: `itsupport@company.com`\n"
            f"• Helpdesk Phone: +1 (800) 555-0199\n\n"
            f"Credentials will be delivered to your registered email once BGC and Compliance Trainings are verified."
        )

    # Default summary
    return (
        f"Hi {name}! Here is a snapshot of your onboarding journey:\n"
        f"• Background Check (BGC): **{bgc}**\n"
        f"• Compliance Trainings: **{completed_tr}/{total_tr} Completed**\n"
        f"• Work Credentials: **{creds}**\n\n"
        f"Feel free to ask me: *'What is my next step?'*, *'Show my trainings'*, or *'Who is my manager?'*"
    )

# ==========================================
# 6. FLASK ROUTES
# ==========================================
@app.route("/")
@app.route("/agent")
def serve_dashboard():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "agent.html")

@app.route("/api/user")
def api_user():
    email = request.args.get("email")
    if not email:
        return jsonify({"success": False, "error": "Email is required"})
    record, event = get_user_data(email)
    if not record:
        return jsonify({"success": False, "error": event or f"User '{email}' not found"})
    return jsonify({"success": True, "user": record, "event": event})

@app.route("/api/manager/dashboard")
def api_manager_dashboard():
    manager_email = request.args.get("manager_email") or "sjenkins@company.com"
    data, err = get_manager_dashboard_data(manager_email)
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "data": data})

@app.route("/api/request_access", methods=["POST"])
def api_request_access():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    tool_name = (payload.get("tool_name") or "").strip()
    tool_category = (payload.get("tool_category") or "Development").strip()

    if not email or not tool_name:
        return jsonify({"success": False, "error": "Email and tool_name are required."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (email,))
            u = cur.fetchone()
            if not u:
                return jsonify({"success": False, "error": f"User '{email}' not found."}), 404

            user_id = u["id"]

            # Insert or update to Pending
            cur.execute("""
                INSERT INTO access_requests (user_id, tool_name, tool_category, status, requested_at)
                VALUES (%s, %s, %s, 'Pending', NOW())
                RETURNING id, tool_name, status, requested_at;
            """, (user_id, tool_name, tool_category))
            req_row = cur.fetchone()
            conn.commit()

            return jsonify({
                "success": True,
                "message": f"Access request for '{tool_name}' submitted to your manager for approval!",
                "request": {
                    "id": req_row["id"],
                    "tool_name": req_row["tool_name"],
                    "status": req_row["status"],
                    "requested_at": str(req_row["requested_at"])
                }
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/approve_access", methods=["POST"])
def api_approve_access():
    payload = request.get_json() or {}
    request_id = payload.get("request_id")
    manager_email = (payload.get("manager_email") or "sjenkins@company.com").strip().lower()
    action = (payload.get("action") or "approve").strip().lower() # 'approve' or 'reject'

    if not request_id:
        return jsonify({"success": False, "error": "request_id is required."}), 400

    new_status = "Approved" if action == "approve" else "Rejected"

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM onboarding_users WHERE LOWER(email) = %s LIMIT 1;", (manager_email,))
            mgr = cur.fetchone()
            mgr_id = mgr["id"] if mgr else None

            cur.execute("""
                UPDATE access_requests
                SET status = %s, reviewed_by = %s, reviewed_at = NOW()
                WHERE id = %s
                RETURNING id, tool_name, user_id, status;
            """, (new_status, mgr_id, request_id))
            updated_row = cur.fetchone()
            conn.commit()

            if not updated_row:
                return jsonify({"success": False, "error": f"Request ID {request_id} not found."}), 404

            return jsonify({
                "success": True,
                "message": f"Access request for '{updated_row['tool_name']}' has been {new_status}!",
                "updated": updated_row
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/update_employee_status", methods=["POST"])
def api_update_employee_status():
    payload = request.get_json() or {}
    email = (payload.get("email") or "").strip().lower()
    bgc_status = payload.get("bgc_status")
    credentials_sent = payload.get("credentials_sent")
    onboarding_status = payload.get("onboarding_status")

    if not email:
        return jsonify({"success": False, "error": "email is required."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database connection failed."}), 500

    try:
        with conn.cursor() as cur:
            updates = []
            vals = []
            if bgc_status:
                updates.append("bgc_status = %s")
                vals.append(bgc_status)
            if credentials_sent:
                updates.append("credentials_sent = %s")
                vals.append(credentials_sent)
            if onboarding_status:
                updates.append("onboarding_status = %s")
                vals.append(onboarding_status)

            if not updates:
                return jsonify({"success": False, "error": "No fields to update."}), 400

            updates.append("updated_at = NOW()")
            vals.append(email)

            sql = f"UPDATE onboarding_users SET {', '.join(updates)} WHERE LOWER(email) = %s RETURNING id, name;"
            cur.execute(sql, tuple(vals))
            row = cur.fetchone()
            conn.commit()

            if not row:
                return jsonify({"success": False, "error": f"Employee '{email}' not found."}), 404

            return jsonify({"success": True, "message": f"Status updated for {row[1]}!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    email = data.get("email")
    prompt = data.get("prompt")
    
    if not email or not prompt:
        return jsonify({"reply": "Missing email or prompt."})

    record, _ = get_user_data(email)
    if not record:
        return jsonify({"reply": "User not found in PostgreSQL database."})

    reply = generate_agent_response(record, prompt)
    return jsonify({"reply": reply})

@app.route("/api/create_user", methods=["POST"])
def api_create_user():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "employee").strip().lower()
    
    if not name or not email:
        return jsonify({"success": False, "error": "Name and email are required."})
        
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database connection failed."})
        
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO onboarding_users (name, email, role, profile_created, bgc_status, onboarding_status)
                VALUES (%s, %s, %s, 'Yes', 'Pending', 'In Progress')
                ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, role = EXCLUDED.role
                RETURNING id;
            """, (name, email, role))
            user_row = cur.fetchone()
            user_id = user_row[0] if user_row else None
            
            if user_id:
                cur.execute("""
                    INSERT INTO user_trainings (user_id, training_id, status)
                    SELECT %s, t.id, 'Pending'
                    FROM trainings_catalog t
                    ON CONFLICT DO NOTHING;
                """, (user_id,))
            conn.commit()
            
        record, event = get_user_data(email)
        return jsonify({"success": True, "user": record, "message": f"Profile created for {name}!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        conn.close()

def init_db():
    """Automatically ensures PostgreSQL tables, columns, and initial records exist when the server starts."""
    conn = get_db_connection()
    if not conn:
        print("[WARNING] Could not connect to PostgreSQL to initialize tables.")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
            -- 1. Base Users Table
            CREATE TABLE IF NOT EXISTS onboarding_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                role VARCHAR(50) DEFAULT 'employee',
                manager_id INT REFERENCES onboarding_users(id) NULL,
                profile_created VARCHAR(50) DEFAULT 'No',
                bgc_status VARCHAR(50) DEFAULT 'Pending',
                onboarding_status VARCHAR(50) DEFAULT 'In Progress',
                welcome_sent VARCHAR(50) DEFAULT 'No',
                reminder_sent VARCHAR(50) DEFAULT 'No',
                trainings_sent VARCHAR(50) DEFAULT 'No',
                credentials_sent VARCHAR(50) DEFAULT 'No',
                training_reminder_sent VARCHAR(50) DEFAULT 'No',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Ensure role and manager_id exist for older tables
            ALTER TABLE onboarding_users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'employee';
            ALTER TABLE onboarding_users ADD COLUMN IF NOT EXISTS manager_id INT REFERENCES onboarding_users(id) NULL;

            -- 2. Master Catalog of Trainings
            CREATE TABLE IF NOT EXISTS trainings_catalog (
                id SERIAL PRIMARY KEY,
                training_name VARCHAR(100) UNIQUE NOT NULL,
                is_mandatory BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 3. Junction Table: User Trainings
            CREATE TABLE IF NOT EXISTS user_trainings (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES onboarding_users(id) ON DELETE CASCADE,
                training_id INT REFERENCES trainings_catalog(id) ON DELETE CASCADE,
                status VARCHAR(50) DEFAULT 'Pending',
                completed_at TIMESTAMP NULL,
                UNIQUE(user_id, training_id)
            );

            -- 4. Access Requests Table
            CREATE TABLE IF NOT EXISTS access_requests (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES onboarding_users(id) ON DELETE CASCADE,
                tool_name VARCHAR(100) NOT NULL,
                tool_category VARCHAR(100) DEFAULT 'Development',
                status VARCHAR(50) DEFAULT 'Pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by INT REFERENCES onboarding_users(id) NULL,
                reviewed_at TIMESTAMP NULL,
                notes TEXT NULL
            );

            -- Seed Trainings Catalog
            INSERT INTO trainings_catalog (training_name) VALUES 
            ('Information Security'),
            ('Code of Conduct'),
            ('POSH'),
            ('Data Privacy')
            ON CONFLICT (training_name) DO NOTHING;

            -- Seed Manager Sarah Jenkins & Sample Employees
            INSERT INTO onboarding_users (name, email, role, profile_created, bgc_status, onboarding_status)
            VALUES 
            ('Sarah Jenkins', 'sjenkins@company.com', 'manager', 'Yes', 'Verified', 'Completed'),
            ('Shaik Baji', 'shaikbaji331@gmail.com', 'employee', 'Yes', 'Pending', 'In Progress'),
            ('Shraddha Warade', 'shraddhawarade85@gmail.com', 'employee', 'Yes', 'Pending', 'In Progress')
            ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role;

            -- Link employees to Sarah Jenkins
            UPDATE onboarding_users 
            SET manager_id = (SELECT id FROM onboarding_users WHERE email = 'sjenkins@company.com' LIMIT 1)
            WHERE email IN ('shaikbaji331@gmail.com', 'shraddhawarade85@gmail.com');

            -- Assign trainings to employees
            INSERT INTO user_trainings (user_id, training_id, status)
            SELECT 
                u.id, 
                t.id, 
                CASE 
                    WHEN t.training_name = 'Information Security' THEN 'Completed'
                    WHEN t.training_name = 'Code of Conduct' THEN 'In Progress'
                    ELSE 'Pending'
                END
            FROM onboarding_users u
            CROSS JOIN trainings_catalog t
            WHERE u.email IN ('shaikbaji331@gmail.com', 'shraddhawarade85@gmail.com')
            ON CONFLICT DO NOTHING;

            -- Sample Access Requests
            INSERT INTO access_requests (user_id, tool_name, tool_category, status)
            SELECT u.id, 'AWS Dev Sandbox', 'Cloud Infrastructure', 'Pending'
            FROM onboarding_users u
            WHERE u.email = 'shraddhawarade85@gmail.com'
            AND NOT EXISTS (SELECT 1 FROM access_requests ar WHERE ar.user_id = u.id AND ar.tool_name = 'AWS Dev Sandbox');

            INSERT INTO access_requests (user_id, tool_name, tool_category, status)
            SELECT u.id, 'GitHub Enterprise', 'Version Control', 'Approved'
            FROM onboarding_users u
            WHERE u.email = 'shraddhawarade85@gmail.com'
            AND NOT EXISTS (SELECT 1 FROM access_requests ar WHERE ar.user_id = u.id AND ar.tool_name = 'GitHub Enterprise');
            """)
            conn.commit()
            print("[SUCCESS] PostgreSQL tables, manager role, and access requests verified/ready.")
    except Exception as e:
        print(f"[WARNING] Table initialization notice: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
