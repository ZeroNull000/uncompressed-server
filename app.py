from flask import Flask, request, jsonify
import time
import random
import json
import os

app = Flask(__name__)

# DATA FILES
DB_FILE = "database.json"

# GLOBAL MEMORY
directory = {}   # Maps Hardware_ID -> User Data
handle_map = {}  # Maps "John#1234" -> Hardware_ID
mailbox = {}     # Maps Hardware_ID -> [Messages]

# --- PERSISTENCE HELPER FUNCTIONS ---
def save_data():
    """Write memory to disk"""
    try:
        data = {
            "directory": directory,
            "handle_map": handle_map
        }
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    """Load memory from disk on startup"""
    global directory, handle_map
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                directory = data.get("directory", {})
                handle_map = data.get("handle_map", {})
            print("Data loaded successfully.")
        except Exception as e:
            print(f"Error loading data: {e}")

# LOAD DATA AT STARTUP
load_data()

# --- ENDPOINTS ---

@app.route('/recover', methods=['POST'])
def recover():
    data = request.json
    device_id = data.get('device_id')
    
    if device_id in directory:
        return jsonify({
            "status": "found",
            "handle": directory[device_id]['handle'],
            "public_key": directory[device_id]['public_key']
        })
    else:
        return jsonify({"status": "new_user"}), 404

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    device_id = data.get('device_id')
    raw_name = data.get('name')
    public_key = data.get('public_key')
    
    # CASE 1: USER EXISTS -> UPDATE KEY & SAVE
    if device_id in directory:
        directory[device_id]['public_key'] = public_key
        save_data() # <--- SAVE TO FILE
        return jsonify({
            "status": "exists", 
            "handle": directory[device_id]['handle']
        })

    # CASE 2: NEW USER
    full_handle = ""
    
    # Try 4-Digit Tags
    for _ in range(50):
        rand_tag = str(random.randint(1000, 9999))
        candidate = f"{raw_name}#{rand_tag}"
        if candidate not in handle_map:
            full_handle = candidate
            break
            
    # Try 6-Digit Tags
    if full_handle == "":
        for _ in range(50):
            rand_tag = str(random.randint(100000, 999999))
            candidate = f"{raw_name}#{rand_tag}"
            if candidate not in handle_map:
                full_handle = candidate
                break
    
    if full_handle == "":
        return jsonify({"status": "error", "message": "Name unavailable."}), 400

    # SAVE TO MEMORY & DISK
    directory[device_id] = {
        "handle": full_handle,
        "public_key": public_key,
        "last_seen": time.time()
    }
    handle_map[full_handle] = device_id
    save_data() # <--- SAVE TO FILE
    
    return jsonify({"status": "success", "handle": full_handle})

@app.route('/lookup', methods=['POST'])
def lookup():
    data = request.json
    target_handle = data.get('handle')
    target_uuid = handle_map.get(target_handle)
    
    if target_uuid and target_uuid in directory:
        return jsonify({
            "status": "found",
            "public_key": directory[target_uuid]['public_key']
        })
    else:
        return jsonify({"status": "not_found"}), 404

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    target_handle = data.get('recipient_id')
    sender_handle = data.get('sender_name')
    
    recipient_uuid = handle_map.get(target_handle)
    
    if not recipient_uuid:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    if recipient_uuid not in mailbox:
        mailbox[recipient_uuid] = []
    
    mailbox[recipient_uuid].append({
        "from": sender_handle,
        "text": data.get('message'),
        "aes_key": data.get('aes_key'),
        "timestamp": time.time()
    })
    return jsonify({"status": "sent"})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    my_uuid = request.args.get('device_id')
    if my_uuid in mailbox:
        messages = mailbox[my_uuid]
        mailbox[my_uuid] = [] 
        return jsonify({"messages": messages})
    else:
        return jsonify({"messages": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
