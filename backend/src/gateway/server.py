# combined_server.py
from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
import certifi
import os
import gridfs
import logging
import pika
from dotenv import load_dotenv
from bson.objectid import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, IndexModel, ASCENDING
from contextlib import contextmanager
import json
from werkzeug.utils import secure_filename
import datetime

from auth_svc import access
from auth import validate
from tts.producer import submit_tts

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('pika').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# This will look for .env in backend/python/
load_dotenv()

# Update MongoDB Configuration
try:
    mongo_uri = os.environ.get("MONGO_URI")
    if "?" in mongo_uri:
        app.config["MONGO_URI"] = f"{mongo_uri}&tlsCAFile={certifi.where()}"
    else:
        app.config["MONGO_URI"] = f"{mongo_uri}?tlsCAFile={certifi.where()}"

    # Initialize MongoDB and GridFS
    mongo = PyMongo(app)
    mongo.db.command('ping')
    logger.info("MongoDB connection successful")
    fs = gridfs.GridFS(mongo.db)
    
    # Create index safely using the correct collection access method
    try:
        # Access fs.files collection correctly through mongo.db
        fs_files_collection = mongo.db['fs.files']
        
        # Check if index exists
        existing_indexes = fs_files_collection.index_information()
        index_name = "metadata.task_id_1_metadata.user_id_1"
        
        if index_name not in existing_indexes:
            fs_files_collection.create_index(
                [
                    ("metadata.task_id", 1), 
                    ("metadata.user_id", 1)
                ],
                name=index_name
            )
            logger.info("Created index on fs.files collection")
        else:
            logger.info("Index already exists on fs.files collection")
            
    except Exception as e:
        logger.warning(f"Index creation warning (non-fatal): {str(e)}")
        # Continue even if index creation fails
        pass

except Exception as e:
    logger.error(f"MongoDB initialization error: {str(e)}")
    raise

# Collections will be:
# - users: user information and authentication
# - audio_files: metadata about audio files (actual files in GridFS)

# Add RabbitMQ connection management
@contextmanager
def get_rabbitmq_channel():
    try:
        # Initialize RabbitMQ connection
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=os.environ.get("RABBITMQ_HOST", "localhost"),
                port=5672,
                credentials=pika.PlainCredentials('guest', 'guest'),
                connection_attempts=3,
                retry_delay=5
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue="tts_queue", durable=True)
        logger.info("RabbitMQ connection established")
        yield channel
    except Exception as e:
        logger.error(f"RabbitMQ connection error: {str(e)}")
        raise
    finally:
        try:
            connection.close()
        except Exception:
            pass

@app.route('/register', methods=['POST'])
def register():
    return access.register_user(mongo, request.json)

@app.route('/login', methods=['POST'])
def login():
    return access.login_user(mongo, request.json)

@app.route('/tts/audio/<file_id>', methods=['GET'])
def get_audio(file_id):
    try:
        # Convert string ID to ObjectId
        file_id = ObjectId(file_id)
        
        # Get file from GridFS
        audio_data = fs.get(file_id)
        
        return send_file(
            audio_data,
            mimetype='audio/mp3',
            as_attachment=True,
            download_name=f'audio_{file_id}.mp3'
        )
        
    except Exception as e:
        logger.error(f"Audio retrieval error: {str(e)}")
        return jsonify({"success": False, "error": "Failed to retrieve audio"}), 500

@app.route('/tts/submit', methods=['POST'])
def submit_tts():
    try:
        # Token verification
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = validate.token(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        data = request.json
        doc_id = data.get('doc_id')
        text = data.get('text')
        logger.info(f"Received data: {data}")

        if doc_id:
            # Get document content
            document = mongo.db.documents.find_one({
                "_id": ObjectId(doc_id),
                "user_id": user_id
            })

            
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            if not document.get('content'):
                logger.info(f"Document content not available: {document}")
                return jsonify({"success": False, "error": "Document content not available"}), 400
            
            logger.info(f"Document content: {document.get('content')}")
            text = document['content']
            logger.info(f"Document content: {text}")

        if not text:
            return jsonify({"success": False, "error": "No text provided"}), 400

        # Generate task ID
        task_id = str(ObjectId())

        # Send to RabbitMQ for processing
        with get_rabbitmq_channel() as channel:
            channel.basic_publish(
                exchange='',
                routing_key='tts_queue',
                body=json.dumps({
                    'task_id': task_id,
                    'user_id': user_id,
                    'text': text,
                    'doc_id': str(doc_id) if doc_id else None,
                    'type': 'document' if doc_id else 'text'
                }),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                )
            )

        return jsonify({
            "success": True,
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"TTS submission error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to submit text"
        }), 500

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

        logger.debug(f"Checking status for task_id: {task_id}, user_id: {user_id}")

        # Fix: Use proper GridFS file lookup
        file_exists = mongo.db['fs.files'].find_one({
            "metadata.task_id": task_id,
            "metadata.user_id": user_id
        })
        
        if file_exists:
            logger.info(f"Found audio file with id: {file_exists['_id']}")
            return jsonify({
                "status": "completed",
                "file_id": str(file_exists['_id'])
            })
        
        logger.info(f"No audio file found for task_id: {task_id}")
        return jsonify({"status": "processing"})

    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({"status": "failed"}), 500

@app.route('/documents/upload', methods=['POST'])
def upload_document():
    try:
        # Verify token
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = validate.token(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        # Check if PDF file is present
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
            
        if not file.filename.endswith('.pdf'):
            return jsonify({"success": False, "error": "Only PDF files are allowed"}), 400

        # Create document record with initial status
        doc_id = str(ObjectId())
        mongo.db.documents.insert_one({
            "_id": ObjectId(doc_id),
            "user_id": user_id,
            "type": "pdf",
            "status": "processing",
            "filename": secure_filename(file.filename),
            "created_at": datetime.datetime.utcnow(),
            "content": "",  # Will be updated after processing
        })

        # Save PDF to GridFS for processing
        pdf_id = fs.put(file, 
                       filename=secure_filename(file.filename),
                       metadata={"doc_id": doc_id, "user_id": user_id})

        # Queue PDF for processing
        with get_rabbitmq_channel() as channel:
            channel.queue_declare(queue="pdf_queue", durable=True)
            message = {
                "doc_id": doc_id,
                "pdf_id": str(pdf_id),
                "user_id": user_id
            }
            
            channel.basic_publish(
                exchange="",
                routing_key="pdf_queue",
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ),
            )

        return jsonify({
            "success": True,
            "document_id": doc_id,
            "status": "processing"
        })

    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to process document"
        }), 500

@app.route('/documents', methods=['GET'])
def get_documents():
    try:
        # Verify token
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = validate.token(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        # Fetch documents for the user
        documents = list(mongo.db.documents.find(
            {"user_id": user_id}
        ).sort("created_at", -1))  # Most recent first

        # Convert ObjectId and datetime to string for JSON serialization
        for doc in documents:
            doc['_id'] = str(doc['_id'])
            doc['created_at'] = doc['created_at'].isoformat()

        return jsonify({
            "success": True,
            "documents": documents
        })

    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch documents"
        }), 500

@app.route('/tts/convert', methods=['POST'])
def convert_text():
    try:
        # Token verification
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = validate.token(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        data = request.json
        doc_id = data.get('doc_id')
        chunk_id = data.get('chunk_id')

        # Get document chunk
        vector = mongo.db.vectors.find_one({
            "document_id": ObjectId(doc_id),
            "chunk_id": chunk_id
        })

        if not vector:
            return jsonify({"success": False, "error": "Chunk not found"}), 404

        # Generate task ID
        task_id = str(ObjectId())

        # Send to RabbitMQ for processing
        with get_rabbitmq_channel() as channel:
            channel.basic_publish(
                exchange='',
                routing_key='tts_queue',
                body=json.dumps({
                    'task_id': task_id,
                    'user_id': user_id,
                    'text': vector['content'],
                    'type': 'chunk',
                    'doc_id': str(doc_id),
                    'chunk_id': chunk_id
                }),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                )
            )

        return jsonify({
            "success": True,
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"TTS conversion error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to convert text"
        }), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)