import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Use home directory for data storage
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, '.streamlit_app_data')
DB_PATH = os.path.join(DATA_DIR, 'users.db')

def init_db():
    try:
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Set proper permissions
        os.chmod(DATA_DIR, 0o755)
        
        # Create or connect to database
        conn = sqlite3.connect(DB_PATH)
        
        # Set proper permissions for the database file
        if os.path.exists(DB_PATH):
            os.chmod(DB_PATH, 0o644)
            
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (username TEXT PRIMARY KEY, password TEXT)''')
        conn.commit()
        conn.close()
        
        # Ensure the database file has correct permissions
        os.chmod(DB_PATH, 0o644)
        
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        raise

def add_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        hashed_password = generate_password_hash(password)
        c.execute("INSERT INTO users VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return check_password_hash(result[0], password)
        return False
    except Exception:
        return False 
