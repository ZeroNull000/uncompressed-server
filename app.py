import os
import time
import random
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

# 1. DATABASE CONFIGURATION
# We get the URL from Render's Environment Variables.
# If running locally for testing, you can hardcode a URL in the second string.
DB_URL = os.environ.get('DATABASE_URL', 'postgres://YOUR_LOCAL_URL_IF_NEEDED')

def get_db_connection():
    """Helper to connect to the database"""
    conn = psycopg2.connect(DB_URL)
    return conn

def init_db():
    """Create the necessary tables if they don't exist yet"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # TABLE 1: USERS
        # Stores the link between Hardware ID, Handle (Name#1234), and Public Key
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                device_id TEXT PRIMARY KEY,
                handle TEXT UNIQUE NOT NULL,
                public_key TEXT NOT NULL,
                last_seen REAL
            );
        """)
        
        # TABLE 2: MESSAGES
        # Stores encrypted messages until they are retrieved
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                recipient_device_id TEXT NOT NULL,
                sender_handle TEXT NOT NULL,
                message_text TEXT NOT NULL,
                aes_key TEXT,
                timestamp REAL
            );
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Run initialization once on startup
if DB_URL:
    init_db()

# --- API ENDPOINTS ---

@app.route('/recover', methods=['POST'])
def recover():
    """Checks if a Hardware ID is already registered"""
    data = request.json
    device_id = data.get('device_id')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT handle, public_key FROM users WHERE device_id = %s", (device_id,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user:
            return jsonify({
                "status": "found", 
                "handle": user[0], 
                "public_key": user[1]
            })
        else:
            return jsonify({"status": "new_user"}), 404
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    """Registers a new user or updates keys for an existing one"""
    data = request.json
    device_id = data.get('device_id')
    raw_name = data.get('name')
    public_key = data.get('public_key')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Check if user already exists
        cur.execute("SELECT handle FROM users WHERE device_id = %s", (device_id,))
        existing_user = cur.fetchone()
        
        if existing_user:
            # CRITICAL FIX: Update the Public Key!
            # This fixes the "Ghost Key" bug where re-installing broke encryption.
            cur.execute("UPDATE users SET public_key = %s WHERE device_id = %s", (public_key, device_id))
            conn.commit()
            
            cur.close()
            conn.close()
            return jsonify({"status": "exists", "handle": existing_user[0]})
        
        # 2. Generate a Unique Handle (Name#1234)
        full_handle = ""
        
        # Try 4-digit tags first
        for _ in range(50):
            rand_tag = str(random.randint(1000, 9999))
            candidate = f"{raw_name}#{rand_tag}"
            
            # Check if this handle is taken
            cur.execute("SELECT 1 FROM users WHERE handle = %s", (candidate,))
            if not cur.fetchone():
                full_handle = candidate
                break
        
        # Fallback to 6-digit tags if name is popular
        if not full_handle:
            for _ in range(50):
                rand_tag = str(random.randint(100000, 999999))
                candidate = f"{raw_name}#{rand_tag}"
                cur.execute("SELECT 1 FROM users WHERE handle = %s", (candidate,))
                if not cur.fetchone():
                    full_handle = candidate
                    break
        
        if not full_handle:
            return jsonify({"status": "error", "message": "Name unavailable"}), 400
            
        # 3. Save New User
        cur.execute(
            "INSERT INTO users (device_id, handle, public_key, last_seen) VALUES (%s, %s, %s, %s)",
            (device_id, full_handle, public_key, time.time())
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "handle": full_handle})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/lookup', methods=['POST'])
def lookup():
    """Finds the Public Key for a given Handle (e.g. John#1234)"""
    data = request.json
    target_handle = data.get('handle')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT public_key FROM users WHERE handle = %s", (target_handle,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result:
            return jsonify({"status": "found", "public_key": result[0]})
        else:
            return jsonify({"status": "not_found"}), 404
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/send', methods=['POST'])
def send_message():
    """Stores an encrypted message for a recipient"""
    data = request.json
    recipient_handle = data.get('recipient_id') # e.g. "John#1234"
    sender_handle = data.get('sender_name')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Resolve Handle -> Recipient's Device ID
        cur.execute("SELECT device_id FROM users WHERE handle = %s", (recipient_handle,))
        recipient = cur.fetchone()
        
        if not recipient:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        recipient_device_id = recipient[0]
        
        # 2. Insert Message into Database
        cur.execute("""
            INSERT INTO messages (recipient_device_id, sender_handle, message_text, aes_key, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (recipient_device_id, sender_handle, data.get('message'), data.get('aes_key'), time.time()))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "sent"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """Retrieves and deletes messages for a specific device"""
    my_device_id = request.args.get('device_id')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Get messages destined for this device
        cur.execute("""
            SELECT sender_handle, message_text, aes_key 
            FROM messages 
            WHERE recipient_device_id = %s
        """, (my_device_id,))
        
        rows = cur.fetchall()
        
        # 2. Delete them (so we don't download them twice)
        if rows:
            cur.execute("DELETE FROM messages WHERE recipient_device_id = %s", (my_device_id,))
            conn.commit()
        
        cur.close()
        conn.close()
        
        # Format for JSON
        messages = []
        for row in rows:
            messages.append({
                "from": row[0],
                "text": row[1],
                "aes_key": row[2]
            })
            
        return jsonify({"messages": messages})

    except Exception as e:
        return jsonify({"messages": []}) # Return empty list on error to keep app alive

# --- DEBUG ROUTE (Add this near the bottom) ---
@app.route('/', methods=['GET'])
def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return "✅ Database Connected! Server is running."
    except Exception as e:
        return f"❌ Database Error: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

