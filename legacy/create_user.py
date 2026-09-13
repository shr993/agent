import sys
import psycopg2

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "2002"  # PostgreSQL password

def register_user(name, email):
    print(f"[*] Registering employee profile for '{name}' ({email})...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # 1. Insert into onboarding_users
        cur.execute("""
            INSERT INTO onboarding_users (name, email, profile_created, bgc_status, onboarding_status)
            VALUES (%s, %s, 'Yes', 'Pending', 'In Progress')
            ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
            RETURNING id;
        """, (name, email))
        user_row = cur.fetchone()
        user_id = user_row[0] if user_row else None
        
        # 2. Assign trainings
        if user_id:
            cur.execute("""
                INSERT INTO user_trainings (user_id, training_id, status)
                SELECT 
                    %s, 
                    t.id, 
                    CASE 
                        WHEN t.training_name = 'Information Security' THEN 'Completed'
                        WHEN t.training_name = 'Code of Conduct' THEN 'In Progress'
                        ELSE 'Pending'
                    END
                FROM trainings_catalog t
                ON CONFLICT DO NOTHING;
            """, (user_id,))
            
        conn.commit()
        cur.close()
        conn.close()
        print(f"[SUCCESS] Profile for '{name}' ({email}) successfully created with mandatory trainings!")
    except Exception as e:
        print(f"[ERROR] Could not connect to PostgreSQL: {e}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        name = sys.argv[1]
        email = sys.argv[2]
    else:
        name = input("Enter Full Name [default: Shraddha Warade]: ").strip() or "Shraddha Warade"
        email = input("Enter Email [default: shraddhawarade85@gmail.com]: ").strip() or "shraddhawarade85@gmail.com"
        
    register_user(name, email)
