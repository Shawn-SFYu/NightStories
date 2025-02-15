from flask import Flask
from flask_pymongo import PyMongo
import certifi
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

# MongoDB Configuration
mongo_uri = os.environ.get("MONGO_URI")
if "?" in mongo_uri:
    app.config["MONGO_URI"] = f"{mongo_uri}&tlsCAFile={certifi.where()}"
else:
    app.config["MONGO_URI"] = f"{mongo_uri}?tlsCAFile={certifi.where()}"

mongo = PyMongo(app)

def init_db():
    try:
        # Test connection
        mongo.db.command('ping')
        logger.info("MongoDB connection successful")

        # Create collections
        if "users" not in mongo.db.list_collection_names():
            mongo.db.create_collection("users")
            logger.info("Created users collection")

        if "fs.files" not in mongo.db.list_collection_names():
            mongo.db.create_collection("fs.files")
            mongo.db.create_collection("fs.chunks")
            logger.info("Created GridFS collections")

        # Create test user if none exists
        if mongo.db.users.count_documents({}) == 0:
            mongo.db.users.insert_one({
                "email": "test@example.com",
                "password": "test123"  # In production, use hashed password
            })
            logger.info("Created test user")

        # Existing collections
        if "documents" not in mongo.db.list_collection_names():
            mongo.db.create_collection("documents")
            mongo.db.documents.create_index([
                ("user_id", 1),
                ("type", 1)
            ])
            logger.info("Created documents collection")
            
        # Create vector store collection
        if "vectors" not in mongo.db.list_collection_names():
            mongo.db.create_collection("vectors")
            mongo.db.vectors.create_index([
                ("document_id", 1),
                ("chunk_id", 1)
            ])
            mongo.db.vectors.create_index([
                ("embedding", "2dsphere")
            ])
            logger.info("Created vectors collection")

        logger.info("Database initialization complete")

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    init_db() 