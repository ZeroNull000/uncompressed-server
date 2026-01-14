from flask import Flask, request, jsonify
import time
import random

app = Flask(__name__)

# 1. The Phonebook: Stores UUID -> User Data
directory = {} 

# 2. The Reverse Lookup: Stores "John#1234" -> UUID
# This helps us find people quickly without scanning the whole list
handle_map = {}

# 3. The Mailbox
mailbox = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    device_id = data.get('device_id')
    raw_name = data.get('name', 'Unknown')
    public_key = data.get('public_key')
    
    # If this device is already registered, just return existing data
    if device_id in directory:
        return jsonify({
            "status": "exists", 
            "handle": directory[device_id]['handle']
        })

    # GENERATE UNIQUE TAG
    # We try up to 100 times to find a free tag for this name
    tag = "0000"
    full_handle = ""
    
    for _ in range(100):
        # Generate random number between 1000 and 9999
        rand_tag = str(random.randint(1000, 9999))
        candidate_handle = f"{raw_name}#{rand_tag}"
        
        # Check if "John#1234" is already taken
        if candidate_handle not in handle_map:
            tag = rand_tag
            full_handle = candidate_handle
            break
    
    if full_handle == "":
        return jsonify({"status": "error", "message": "Name is too popular!"}), 400

    # SAVE USER
    directory[device_id] = {
        "handle": full_handle, # Store "John#1234"
        "public_key": public_key,
        "last_seen": time.time()
    }
    
    # Map the handle back to the ID for easy lookup
    handle_map[full_handle] = device_id
    
    return jsonify({
        "status": "success", 
        "handle": full_handle
    })

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    target_handle = data.get('recipient_id') # User types "John#1234"
    sender_handle = data.get('sender_name')  # "Me#5555"
    
    # 1. Resolve Handle -> UUID
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

@app.route('/lookup', methods=['POST']) # Changed to POST to search safely
def lookup():
    # Allow looking up a specific handle to get their Public Key
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

# Debug endpoint to see who is online (optional)
@app.route('/debug_users', methods=['GET'])
def debug_users():
    return jsonify(handle_map)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
