"""
Database Connection and Initialization for MediFriend
"""
import sqlite3
import os
from models import ALL_MODELS


DB_PATH = os.path.join(os.path.dirname(__file__), 'hms.db')


def get_db_connection():
    """
    Get a new database connection with row factory for dictionary-like access
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Initialize the database by creating all tables from models.
    Only creates database if it doesn't exist.
    """
    # Check if database already exists
    if os.path.exists(DB_PATH):
        print(f"✅ Database already exists at: {DB_PATH}")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🏥 Initializing MediFriend Database...")
    
    try:
        # Create all tables
        for model in ALL_MODELS:
            print(f"   Creating table: {model.TABLE_NAME}")
            cursor.execute(model.create_table_sql())
            
            # Create indexes if available
            if hasattr(model, 'create_indexes_sql'):
                for index_sql in model.create_indexes_sql():
                    cursor.execute(index_sql)
        
        conn.commit()
        print("✅ Database initialized successfully!")
        print(f"📁 Database location: {DB_PATH}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Helper function to execute SQL queries
    
    Args:
        query: SQL query string
        params: Query parameters (tuple)
        fetchone: Return single row
        fetchall: Return all rows
        commit: Commit changes (for INSERT/UPDATE/DELETE)
    
    Returns:
        Query results or lastrowid for INSERT operations
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        
        if commit:
            conn.commit()
            return cursor.lastrowid
        
        if fetchone:
            result = cursor.fetchone()
            return dict(result) if result else None
        
        if fetchall:
            results = cursor.fetchall()
            return [dict(row) for row in results]
        
        return None
        
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        conn.close()


def insert_user(full_name, email, password_hash, role, phone=None, gender=None, dob=None):
    """
    Insert a new user into the database
    """
    query = """
        INSERT INTO users (full_name, email, password_hash, role, phone, gender, dob)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return execute_query(query, (full_name, email, password_hash, role, phone, gender, dob), commit=True)


def get_user_by_email(email):
    """
    Get user by email
    """
    query = "SELECT * FROM users WHERE email = ?"
    return execute_query(query, (email,), fetchone=True)


def get_user_by_id(user_id):
    """
    Get user by ID
    """
    query = "SELECT * FROM users WHERE id = ?"
    return execute_query(query, (user_id,), fetchone=True)


def insert_patient_details(user_id, blood_group=None, allergies=None, chronic_conditions=None, emergency_contact=None):
    """
    Insert patient-specific details
    """
    query = """
        INSERT INTO patient_details (user_id, blood_group, allergies, chronic_conditions, emergency_contact)
        VALUES (?, ?, ?, ?, ?)
    """
    return execute_query(query, (user_id, blood_group, allergies, chronic_conditions, emergency_contact), commit=True)


def insert_doctor_details(user_id, specialization, qualification=None, experience_years=0, consultation_fee=0.0, schedule_json=None):
    """
    Insert doctor-specific details
    """
    query = """
        INSERT INTO doctor_details (user_id, specialization, qualification, experience_years, consultation_fee, schedule_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    return execute_query(query, (user_id, specialization, qualification, experience_years, consultation_fee, schedule_json), commit=True)


def get_all_doctors():
    """
    Get all doctors with their details
    """
    query = """
        SELECT u.*, d.specialization, d.experience_years, d.consultation_fee
        FROM users u
        JOIN doctor_details d ON u.id = d.user_id
        WHERE u.role = 'DOCTOR'
        ORDER BY u.full_name
    """
    return execute_query(query, fetchall=True)


def get_doctor_details(doctor_id):
    """
    Get doctor details by user ID
    """
    query = """
        SELECT u.*, d.specialization, d.experience_years, d.consultation_fee, d.schedule_json
        FROM users u
        JOIN doctor_details d ON u.id = d.user_id
        WHERE u.id = ?
    """
    return execute_query(query, (doctor_id,), fetchone=True)


def get_patient_details(patient_id):
    """
    Get patient details by user ID
    """
    query = """
        SELECT u.*, p.blood_group, p.allergies, p.chronic_conditions, p.emergency_contact
        FROM users u
        LEFT JOIN patient_details p ON u.id = p.user_id
        WHERE u.id = ?
    """
    return execute_query(query, (patient_id,), fetchone=True)


# Run initialization if executed directly
if __name__ == "__main__":
    init_db()
