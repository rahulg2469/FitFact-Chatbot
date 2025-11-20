"""
Centralized database connection handler
Ensures consistent connection across all modules
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_database_connection():
    """Get a fresh database connection"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'fitfact_db'),
            user=os.getenv('DB_USER', 'satya'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def test_connection():
    """Test if database is accessible"""
    conn = get_database_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return True
        except:
            return False
    return False