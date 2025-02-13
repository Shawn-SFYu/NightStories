import pika
import json
import os
import gridfs
from flask import Flask
from flask_pymongo import PyMongo
import certifi
from dotenv import load_dotenv
import logging
from processor import PDFProcessor
from bson.objectid import ObjectId
import datetime
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
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

# Initialize PDF processor
pdf_processor = PDFProcessor()

def process_pdf(ch, method, properties, body):
    try:
        data = json.loads(body)
        doc_id = data['doc_id']
        pdf_id = data['pdf_id']
        user_id = data['user_id']

        logger.info(f"Processing PDF document: {doc_id}")

        try:
            # Get PDF from GridFS
            pdf_file = fs.get(ObjectId(pdf_id))
        except Exception as e:
            logger.error(f"Failed to retrieve PDF from GridFS: {str(e)}")
            raise

        try:
            # Process PDF
            text = pdf_processor.extract_text(pdf_file)
            chapters = pdf_processor.segment_chapters(text)
        except Exception as e:
            logger.error(f"Failed to process PDF content: {str(e)}")
            raise

        try:
            # Update document with chapters
            mongo.db.documents.update_one(
                {"_id": ObjectId(doc_id)},
                {
                    "$set": {
                        "chapters": chapters,
                        "status": "completed",
                        "processed_at": datetime.datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")
            raise

        logger.info(f"Successfully processed document {doc_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        try:
            mongo.db.documents.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {"status": "failed", "error": str(e)}}
            )
        except Exception as update_error:
            logger.error(f"Error updating document status: {str(update_error)}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    max_retries = 5
    retry_count = 0
    rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
    logger.info(f"Attempting to connect to RabbitMQ at {rabbitmq_host}")
    
    while retry_count < max_retries:
        try:
            parameters = pika.ConnectionParameters(
                host=rabbitmq_host,
                port=5672,
                virtual_host='/',
                credentials=pika.PlainCredentials('guest', 'guest'),
                connection_attempts=3,
                retry_delay=5,
                socket_timeout=5
            )
            
            logger.info("Connecting to RabbitMQ...")
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            channel.queue_declare(queue="pdf_queue", durable=True)
            logger.info("Successfully connected to RabbitMQ")
            
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue='pdf_queue',
                on_message_callback=process_pdf
            )
            
            logger.info("PDF processor service started. Waiting for messages...")
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            retry_count += 1
            logger.error(f"Failed to connect to RabbitMQ (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count == max_retries:
                raise
            time.sleep(5)

if __name__ == "__main__":
    main() 