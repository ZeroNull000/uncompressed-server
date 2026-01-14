from flask import Flask, request, jsonify
import time
import random

app = Flask(__name__)

# directory: Maps Hardware_ID -> User Data
directory = {} 

# handle_map: Maps "John#1234" -> Hardware_ID
handle_map = {}

# mailbox: Maps Hardware_ID -> Messages
mailbox = {}

@app.route('/recover', methods=['POST'])
def recover():
    # 1. Check if this hardware ID is already registered
    data = request.json
    device_id = data.get('device_id')
    
    if device_id in directory:
        # User exists! Send back their handle and key
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
    
    # Double check: Is this device already registered?
    if device_id in directory:
        return jsonify({
            "status": "exists", 
            "handle": directory[device_id]['handle']
        })

    # GENERATE UNIQUE TAG
    tag = ""
    full_handle = ""
    
    # Phase 1: Try 4-Digit Tags (1000-9999)
    # We attempt 50 random tries. If all collide, we move to Phase 2.
    for _ in range(50):
        rand_tag = str(random.randint(1000, 9999))
        candidate = f"{raw_name}#{rand_tag}"
        if candidate not in handle_map:
            full_handle = candidate
            break
            
    # Phase 2: If 4-digits failed, try 6-Digit Tags (100000-999999)
    if full_handle == "":
        for _ in range(50):
            rand_tag = str(random.randint(100000, 999999))
            candidate = f"{raw_name}#{rand_tag}"
            if candidate not in handle_map:
                full_handle = candidate
                break
    
    # If still failed (Millions of Johns?), return error
    if full_handle == "":
        return jsonify({"status": "error", "message": "Name unavailable. Try another."}), 400

    # SAVE NEW USER
    directory[device_id] = {
        "handle": full_handle,
        "public_key": public_key,
        "last_seen": time.time()
    }
    handle_map[full_handle] = device_id
    
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
