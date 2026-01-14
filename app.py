from flask import Flask, request, jsonify

app = Flask(__name__)
directory = {} # Our temporary phonebook

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user_id = data.get('device_id')
    directory[user_id] = {
        "name": data.get('name'),
        "ip": request.remote_addr,
        "public_key": data.get('public_key')
    }
    print(f"Registered: {data.get('name')} at {request.remote_addr}")
    return jsonify({"status": "success"})

@app.route('/lookup', methods=['GET'])
def lookup():
    return jsonify(directory)

if __name__ == '__main__':
    # This starts the server
    app.run(host='0.0.0.0', port=5000)