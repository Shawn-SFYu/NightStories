# combined_server.py
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
import jwt
import datetime
import os
import gridfs
import logging
import certifi

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# MongoDB Configuration
app.config["MONGO_URI"] = ("mongodb+srv://shawnsfyuan:oGXOr3OVoJ3v75xX@"
                           "cluster0.0gcau.mongodb.net/nightstories?"
                           "retryWrites=true&w=majority&"
                           "tlsCAFile=" + certifi.where() )

try:
    mongo = PyMongo(app)
    mongo.db.command('ping')
    logger.info("MongoDB connection successful")
    fs = gridfs.GridFS(mongo.db)  # For storing audio files
    collections = mongo.db.list_collection_names()

    if "users" not in collections or "audio" not in collections:
        raise Exception("Database not initialized")
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")


# Collections will be:
# - users: user information and authentication
# - audio_files: metadata about audio files (actual files in GridFS)

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        # Check if user already exists
        if mongo.db.users.find_one({"email": data['email']}):
            return jsonify({
                "success": False, 
                "errors": "Email already registered"
            }), 409

        # Create new user
        user = {
            "email": data['email'],
            "password": data['password'],  # In production, hash this!
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        mongo.db.users.insert_one(user)

        return jsonify({"success": True}), 201

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({
            "success": False, 
            "errors": "Registration failed"
        }), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        user = mongo.db.users.find_one({
            "email": data['email'],
            "password": data['password']  # In production, verify hash!
        })

        print(user, flush=True)
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
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            "success": False, 
            "errors": "Login failed"
        }), 500

@app.route('/tts/generate', methods=['POST'])
def generate_audio():
    try:
        # Verify token
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = verify_jwt(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        # Get text and generate audio (implement your TTS logic here)
        text = request.json.get('text')
        # audio_data = your_tts_function(text)

        # For now, let's simulate audio data
        audio_data = b"Simulated audio data"

        # Store audio file in GridFS
        file_id = fs.put(
            audio_data,
            filename=f"audio_{datetime.datetime.now(datetime.timezone.utc).timestamp()}.mp3",
            user_id=user_id,
            text=text
        )

        # Store metadata in audio_files collection
        mongo.db.audio_files.insert_one({
            "user_id": user_id,
            "file_id": file_id,
            "text": text,
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        })

        return jsonify({
            "success": True,
            "file_id": str(file_id)
        })

    except Exception as e:
        logger.error(f"Audio generation error: {str(e)}")
        return jsonify({
            "success": False,
            "errors": "Audio generation failed"
        }), 500

@app.route('/tts/audio/<file_id>', methods=['GET'])
def get_audio(file_id):
    try:
        # Verify token
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = verify_jwt(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        # Get audio file from GridFS
        audio_file = fs.get(file_id)
        return send_file(
            audio_file,
            mimetype='audio/mp3',
            as_attachment=True,
            download_name=f"audio_{file_id}.mp3"
        )

    except Exception as e:
        logger.error(f"Audio retrieval error: {str(e)}")
        return jsonify({
            "success": False,
            "errors": "Audio retrieval failed"
        }), 500

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

def verify_jwt(token):
    try:
        decoded = jwt.decode(
            token,
            os.environ.get('JWT_SECRET', 'your-secret-key'),
            algorithms=["HS256"]
        )
        return decoded['user_id']
    except:
        return None

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)