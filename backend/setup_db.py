"""
Database Migration and Seeding Module.
Ensures all tables, catalog items, and manager accounts exist.
"""
import os
import sys

# Support running directly
if __package__ is None or __package__ == '':
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from backend.database import get_db_connection
else:
    from .database import get_db_connection

def init_db():
    conn = get_db_connection()
    if not conn:
        print("[WARNING] Could not connect to PostgreSQL for auto-migration.")
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
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

            -- Mandatory Trainings Catalog
            INSERT INTO trainings_catalog (training_name) VALUES 
                ('Information Security'),
                ('Code of Conduct'),
                ('POSH'),
                ('Data Privacy')
            ON CONFLICT (training_name) DO NOTHING;

            -- Manager Sarah Jenkins
            INSERT INTO onboarding_users (name, email, role, profile_created, bgc_status, onboarding_status, welcome_sent)
            VALUES ('Sarah Jenkins', 'sjenkins@company.com', 'manager', 'Yes', 'Verified', 'Completed', 'Yes')
            ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role;
            """)
            conn.commit()
            print("[SUCCESS] PostgreSQL database verified and ready.")
            return True
    except Exception as e:
        print(f"[DB NOTICE] Table migration notice: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
