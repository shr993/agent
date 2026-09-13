"""
Database Connection Manager.
Handles PostgreSQL connection creation, cursor helpers, and safe closing.
"""
import os
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from backend.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
else:
    from .config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Establish and return a connection to PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        return conn
    except Exception as e:
        print(f"[DB ERROR] PostgreSQL Connection Error: {e}")
        return None

def clean_val(v):
    return str(v).strip() if v is not None else ""

def is_yes(v):
    return clean_val(v).lower() == "yes"
