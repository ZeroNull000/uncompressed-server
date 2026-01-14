@app.route('/register', methods=['POST'])
def register():
    data = request.json
    device_id = data.get('device_id')
    raw_name = data.get('name')
    public_key = data.get('public_key') # <--- The New Key
    
    # CASE 1: USER EXISTS -> UPDATE KEY
    if device_id in directory:
        # CRITICAL FIX: Update the key to the new one!
        directory[device_id]['public_key'] = public_key
        
        return jsonify({
            "status": "exists", 
            "handle": directory[device_id]['handle']
        })

    # CASE 2: NEW USER -> GENERATE TAG (Logic remains the same)
    tag = ""
    full_handle = ""
    
    # Phase 1: Try 4-Digit Tags
    for _ in range(50):
        rand_tag = str(random.randint(1000, 9999))
        candidate = f"{raw_name}#{rand_tag}"
        if candidate not in handle_map:
            full_handle = candidate
            break
            
    # Phase 2: Try 6-Digit Tags
    if full_handle == "":
        for _ in range(50):
            rand_tag = str(random.randint(100000, 999999))
            candidate = f"{raw_name}#{rand_tag}"
            if candidate not in handle_map:
                full_handle = candidate
                break
    
    if full_handle == "":
        return jsonify({"status": "error", "message": "Name unavailable."}), 400

    # SAVE NEW USER
    directory[device_id] = {
        "handle": full_handle,
        "public_key": public_key,
        "last_seen": time.time()
    }
    handle_map[full_handle] = device_id
    
    return jsonify({"status": "success", "handle": full_handle})
