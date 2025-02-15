import pika
import json
import os
import gridfs
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
import certifi
from dotenv import load_dotenv
import logging
from processor import ChatProcessor
from bson.objectid import ObjectId

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
load_dotenv()

# MongoDB setup
mongo_uri = os.environ.get("MONGO_URI")
if "?" in mongo_uri:
    app.config["MONGO_URI"] = f"{mongo_uri}&tlsCAFile={certifi.where()}"
else:
    app.config["MONGO_URI"] = f"{mongo_uri}?tlsCAFile={certifi.where()}"

try:
    mongo = PyMongo(app)
    mongo.db.command('ping')
    logger.info("MongoDB connection successful")
    fs = gridfs.GridFS(mongo.db)
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")
    raise

# Initialize chat processor
chat_processor = ChatProcessor(mongo.db)

@app.route('/chat', methods=['POST', 'OPTIONS'])
def process_chat():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.json
        doc_ids = data.get('doc_ids', [])
        message = data.get('message')
        user_id = data.get('user_id')
        logger.info(f"Processing chat with message: {message}")
        logger.info(f"User ID: {user_id}")
        # Verify document access
        logger.info(f"Doc IDs: {doc_ids}")
        for doc_id in doc_ids:
            doc = mongo.db.documents.find_one({
                "_id": ObjectId(doc_id),
                "user_id": user_id
            })
            logger.info(f"Doc: {doc}")
            if not doc:
                return jsonify({"success": False, "error": "Document not found or access denied"}), 404

        # Process chat with document IDs
        response = chat_processor.process_chat(message, doc_ids)
        logger.info(f"Chat response: {response}")
        return jsonify({
            "success": True,
            "response": response
        })

    except Exception as e:
        logger.error(f"Chat processing error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to process chat message"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True) 