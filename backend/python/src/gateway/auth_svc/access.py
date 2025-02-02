from flask import jsonify
import jwt
import datetime
import os

def create_jwt(user_id):
    return jwt.encode(
        {
            "user_id": user_id,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1),
            "iat": datetime.datetime.now(datetime.timezone.utc),
        },
        os.environ.get('JWT_SECRET', 'your-secret-key'),
        algorithm="HS256"
    )

def login_user(mongo, data):
    try:
        user = mongo.db.users.find_one({
            "email": data['email'],
            "password": data['password']  # In production, verify hash!
        })

        if not user:
            return jsonify({
                "success": False, 
                "errors": "Invalid credentials"
            }), 401
            
        token = create_jwt(str(user['_id']))
        return jsonify({
            "success": True, 
            "token": token
        })
    
    except Exception as e:
        return jsonify({
            "success": False, 
            "errors": "Login failed"
        }), 500

def register_user(mongo, data):
    try:
        if mongo.db.users.find_one({"email": data['email']}):
            return jsonify({
                "success": False, 
                "errors": "Email already registered"
            }), 409

        user = {
            "email": data['email'],
            "password": data['password'],  # In production, hash this!
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        mongo.db.users.insert_one(user)

        return jsonify({"success": True}), 201

    except Exception as e:
        return jsonify({
            "success": False, 
            "errors": "Registration failed"
        }), 500 