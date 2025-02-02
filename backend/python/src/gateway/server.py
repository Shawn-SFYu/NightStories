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
import pika
from dotenv import load_dotenv

from auth_svc import access
from auth import validate
from tts.producer import submit_tts

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

load_dotenv() 

# Update MongoDB Configuration
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")

try:
    mongo = PyMongo(app)
    mongo.db.command('ping')
    logger.info("MongoDB connection successful")
    fs = gridfs.GridFS(mongo.db)  # For storing audio files
    collections = mongo.db.list_collection_names()

    if "users" not in collections or "audio" not in collections:
        raise Exception("Database not initialized")

    # Update RabbitMQ connection
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.environ.get("RABBITMQ_HOST", "rabbitmq"))
    )
    channel = connection.channel()
    channel.queue_declare(queue="tts_queue", durable=True)
    
except Exception as e:
    logger.error(f"Initialization error: {str(e)}")


# Collections will be:
# - users: user information and authentication
# - audio_files: metadata about audio files (actual files in GridFS)

@app.route('/register', methods=['POST'])
def register():
    return access.register_user(mongo, request.json)

@app.route('/login', methods=['POST'])
def login():
    return access.login_user(mongo, request.json)

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

@app.route('/tts/submit', methods=['POST'])
def handle_tts_submit():
    return submit_tts(channel, validate.token)

@app.route('/tts/status/<task_id>', methods=['GET'])
def get_tts_status(task_id):
    try:
        # Verify token
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = validate.token(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        # Check if audio file exists with this task_id
        audio_file = mongo.db.fs.files.find_one({"task_id": task_id})
        if audio_file:
            return jsonify({
                "status": "completed",
                "file_id": str(audio_file._id)
            })
        
        return jsonify({"status": "processing"})

    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({"status": "failed"}), 500
'''
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
'''
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)