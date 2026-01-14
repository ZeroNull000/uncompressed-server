from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# 1. The Phonebook
directory = {} 

# 2. The Mailbox
mailbox = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    device_id = data.get('device_id')
    
    directory[device_id] = {
        "name": data.get('name'),
        "public_key": data.get('public_key'), # We store the public key
        "last_seen": time.time()
    }
    return jsonify({"status": "success", "message": "Registered"})

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    recipient_id = data.get('recipient_id')
    
    # We now accept THREE parts
    sender_name = data.get('sender_name')
    message_text = data.get('message')   # The "Safe" (Encrypted Data)
    aes_key = data.get('aes_key')        # <--- THE MISSING PIECE (The Key)
    
    if recipient_id not in mailbox:
        mailbox[recipient_id] = []
    
    mailbox[recipient_id].append({
        "from": sender_name,
        "text": message_text,
        "aes_key": aes_key,              # Store the key in the mailbox
        "timestamp": time.time()
    })
    
    return jsonify({"status": "sent"})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    my_id = request.args.get('device_id')
    
    if my_id in mailbox:
        messages = mailbox[my_id]
        mailbox[my_id] = [] # Clear mailbox
        return jsonify({"messages": messages})
    else:
        return jsonify({"messages": []})

@app.route('/lookup', methods=['GET'])
def lookup():
    return jsonify(directory)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
