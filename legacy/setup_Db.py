import psycopg2

# 🐘 Your PostgreSQL connection details
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"       # Make sure this database exists
DB_USER = "postgres"
DB_PASSWORD = "2002"  # Update with your password

SQL_SCRIPT = """
-- 1. Create Onboarding Users Table
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

-- 4. Access Requests & Approvals Table (Sandboxes, Tools, Environments)
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

-- 5. Insert Master Trainings
INSERT INTO trainings_catalog (training_name) VALUES 
('Information Security'),
('Code of Conduct'),
('POSH'),
('Data Privacy')
ON CONFLICT (training_name) DO NOTHING;

-- 6. Insert Manager & Employee Profiles
INSERT INTO onboarding_users (name, email, role, profile_created, bgc_status, onboarding_status)
VALUES 
('Sarah Jenkins', 'sjenkins@company.com', 'manager', 'Yes', 'Verified', 'Completed'),
('Shaik Baji', 'shaikbaji331@gmail.com', 'employee', 'Yes', 'Pending', 'In Progress'),
('Shraddha Warade', 'shraddhawarade85@gmail.com', 'employee', 'Yes', 'Pending', 'In Progress')
ON CONFLICT (email) DO NOTHING;

-- Link employees to Sarah Jenkins
UPDATE onboarding_users 
SET manager_id = (SELECT id FROM onboarding_users WHERE email = 'sjenkins@company.com' LIMIT 1)
WHERE email IN ('shaikbaji331@gmail.com', 'shraddhawarade85@gmail.com');

-- 7. Assign Trainings to the Users
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

-- 8. Sample Access Requests
INSERT INTO access_requests (user_id, tool_name, tool_category, status)
SELECT u.id, 'AWS Dev Sandbox', 'Cloud Infrastructure', 'Pending'
FROM onboarding_users u
WHERE u.email = 'shraddhawarade85@gmail.com'
ON CONFLICT DO NOTHING;

INSERT INTO access_requests (user_id, tool_name, tool_category, status)
SELECT u.id, 'GitHub Enterprise', 'Version Control', 'Approved'
FROM onboarding_users u
WHERE u.email = 'shraddhawarade85@gmail.com'
ON CONFLICT DO NOTHING;
"""

import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def create_tables():
    print("[*] Connecting to PostgreSQL and creating tables...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute(SQL_SCRIPT)
        conn.commit()
        cur.close()
        conn.close()
        print("[SUCCESS] All tables created and sample data inserted successfully!")
    except Exception as e:
        print(f"[ERROR] Database error: {e}")

if __name__ == "__main__":
    create_tables()