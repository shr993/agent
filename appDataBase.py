import os
import sys
import smtplib
import psycopg2
from psycopg2.extras import RealDictCursor
from email.message import EmailMessage
from flask import Flask, request, jsonify, render_template_string, send_from_directory

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==========================================
# 1. CONFIGURATION (UPDATE THESE!)
# ==========================================
# 🐘 PostgreSQL Settings
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "2002"  # 👈 Enter the password you set during installation

# 📧 Email Settings
EMAIL_ADDRESS = "shaikbaji860566@gmail.com"  # 👈 Your sender email
EMAIL_PASSWORD = "eycsrblsevdxzsjj"           # 👈 The App Password you generated
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to the Team, {Name}! Action Required",
        "body": "Hi {Name},\n\nWelcome to the team! Your account profile has been created.\n\nPlease upload BGC documents.\n\nBest,\nHR Onboarding Team"
    }
}

app = Flask(__name__)

# Enable CORS for browser access (e.g. running agent.html locally or via Live Server)
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
    """Establishes and returns a connection to PostgreSQL."""
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

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def is_yes(val):
    return str(val).strip().lower() == "yes" if val is not None else False

def clean_val(val):
    return str(val).strip() if val is not None else ""

def send_email(to_email, name, template_key):
    template = EMAIL_TEMPLATES.get(template_key)
    if not template: return False
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
            profile_created = user_row.get("profile_created")
            welcome_sent = user_row.get("welcome_sent")

            # 2. TRIGGER: If profile_created is 'Yes' & welcome email not sent yet
            if is_yes(profile_created) and not is_yes(welcome_sent):
                if send_email(email, name, "welcome"):
                    # 💾 UPDATE DATABASE: Set welcome_sent = 'Yes'
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

            record = {
                "name": name,
                "email": email,
                "profile_created": "Yes" if is_yes(profile_created) else "Pending",
                "welcome_sent": "Yes" if is_yes(welcome_sent) else "Pending",
                "bgc_status": clean_val(user_row.get("bgc_status")) or "Pending",
                "onboarding_status": clean_val(user_row.get("onboarding_status")) or "In Progress",
                "credentials_sent": "Yes" if is_yes(user_row.get("credentials_sent")) else "Pending",
                "trainings": trainings_list,
                "pending_trainings": pending_trainings
            }

    except Exception as e:
        print(f"❌ Error during database query: {e}")
        return None, f"Database error: {e}"
    finally:
        conn.close()

    return record, event_msg

# ==========================================
# 5. AI AGENT ENGINE (PROMPTS & SUGGESTIONS)
# ==========================================
def generate_agent_response(user_data, prompt):
    p = prompt.strip().lower()
    name = user_data["name"]
    pending_tr = user_data["pending_trainings"]
    bgc = user_data["bgc_status"]
    creds = user_data["credentials_sent"]
    total_tr = len(user_data["trainings"])
    completed_tr = total_tr - len(pending_tr)

    # Greetings
    if any(k in p for k in ["hi", "hello", "hey", "good morning", "good afternoon"]):
        return (
            f"Hello {name}! 👋 I am your Onboarding Buddy. "
            f"I'm here to guide you through every milestone until your Day 1.\n\n"
            f"Currently, you have completed {completed_tr} of {total_tr} mandatory trainings, "
            f"and your Background Verification is '{bgc}'. How can I help you today?"
        )

    # Next steps / Suggestions
    if any(k in p for k in ["suggest", "next", "what should i do", "priority"]):
        if bgc.lower() == "pending":
            return (
                f"💡 **Immediate Priority for {name}:**\n"
                f"Please upload your government-issued ID and address proof to complete your **Background Check (BGC)**. "
                f"Once verified, your IT credentials can be generated."
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
        f"• Account Setup: {user_data['profile_created']}\n"
        f"• Background Check: {user_data['bgc_status']}\n"
        f"• Compliance Trainings: {completed_tr} of {total_tr} completed\n"
        f"• IT System Credentials: {user_data['credentials_sent']}\n\n"
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
    
    if not name or not email:
        return jsonify({"success": False, "error": "Name and email are required."})
        
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database connection failed."})
        
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO onboarding_users (name, email, profile_created, bgc_status, onboarding_status)
                VALUES (%s, %s, 'Yes', 'Pending', 'In Progress')
                ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                RETURNING id;
            """, (name, email))
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
    """Automatically ensures PostgreSQL tables exist when the server starts."""
    conn = get_db_connection()
    if not conn:
        print("[WARNING] Could not connect to PostgreSQL to initialize tables.")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
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

            CREATE TABLE IF NOT EXISTS trainings_catalog (
                id SERIAL PRIMARY KEY,
                training_name VARCHAR(100) UNIQUE NOT NULL,
                is_mandatory BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_trainings (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES onboarding_users(id) ON DELETE CASCADE,
                training_id INT REFERENCES trainings_catalog(id) ON DELETE CASCADE,
                status VARCHAR(50) DEFAULT 'Pending',
                completed_at TIMESTAMP NULL,
                UNIQUE(user_id, training_id)
            );

            INSERT INTO trainings_catalog (training_name) VALUES 
            ('Information Security'),
            ('Code of Conduct'),
            ('POSH'),
            ('Data Privacy')
            ON CONFLICT (training_name) DO NOTHING;

            INSERT INTO onboarding_users (name, email, profile_created, bgc_status, onboarding_status)
            VALUES 
            ('Shaik Baji', 'shaikbaji331@gmail.com', 'Yes', 'Pending', 'In Progress'),
            ('Shraddha Warade', 'shraddhawarade85@gmail.com', 'Yes', 'Pending', 'In Progress')
            ON CONFLICT (email) DO NOTHING;

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
            """)
            conn.commit()
            print("[SUCCESS] PostgreSQL tables and initial users verified/ready.")
    except Exception as e:
        print(f"[WARNING] Table initialization notice: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
