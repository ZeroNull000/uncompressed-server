from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# 1. The Phonebook (Who is online?)
directory = {} 

# 2. The Mailbox (Where messages wait)
# Structure: { "Recipient_ID": [ {from: "Sender", text: "Hello"} ] }
mailbox = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    device_id = data.get('device_id')
    
    directory[device_id] = {
        "name": data.get('name'),
        "public_key": data.get('public_key'), # <--- ADD THIS LINE
        "last_seen": time.time()
    }
    return jsonify({"status": "success", "message": "Registered"})

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    recipient_id = data.get('recipient_id')
    message_text = data.get('message')
    sender_name = data.get('sender_name')
    
    # Create a mailbox for this person if it doesn't exist
    if recipient_id not in mailbox:
        mailbox[recipient_id] = []
    
    # Drop the letter in the box
    mailbox[recipient_id].append({
        "from": sender_name,
        "text": message_text,
        "timestamp": time.time()
    })
    
    print(f"Message stored for {recipient_id}: {message_text}")
    return jsonify({"status": "sent"})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    # The phone asks: "Any mail for me?"
    my_id = request.args.get('device_id')
    
    if my_id in mailbox:
        # Give them their mail
        messages = mailbox[my_id]
        # Clear the mailbox (so they don't download it twice)
        mailbox[my_id] = [] 
        return jsonify({"messages": messages})
    else:
        return jsonify({"messages": []})

@app.route('/lookup', methods=['GET'])
def lookup():
    return jsonify(directory)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

