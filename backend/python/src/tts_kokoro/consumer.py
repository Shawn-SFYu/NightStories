import io
import numpy as np
import pika, json, sys, os
from flask import Flask
from flask_cors import CORS
import certifi
import time

import logging
import gridfs
from flask_pymongo import PyMongo
import soundfile as sf
from kokoro import KPipeline
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

load_dotenv()

# Update MongoDB Configuration
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

# Initialize TTS pipeline
pipeline = KPipeline(lang_code='a')

def generate_audio(generator):
    audio_segments = []
    
    for i, (gs, ps, audio) in enumerate(generator):
        audio_segments.append(audio)
    # Concatenate all audio segments
    combined_audio = np.concatenate(audio_segments)
    # Save to BytesIO instead of file
    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, combined_audio, 24000, format='MP3')
    audio_buffer.seek(0)
    
    return audio_buffer

def process_tts(message):
    try:
        data = json.loads(message)
        
        generator = pipeline(
            data['text'],
            voice='af_heart',
            speed=1,
            split_pattern=r'\n+'
        )
        
        audio_buffer = generate_audio(generator)
        
        file_id = fs.put(
            audio_buffer.getvalue(),
            filename=f'tts_{data["task_id"]}.mp3',
            content_type='audio/mp3',
            metadata={
                'task_id': data['task_id'],
                'user_id': data['user_id']
            }
        )
        return str(file_id)
    except Exception as e:
        logger.error(f"TTS processing error: {str(e)}")
        return None

def main():
    # Add retry logic and explicit connection parameters
    max_retries = 5
    retry_count = 0
    
    # Get host from environment or default to localhost if using port-forward
    rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
    logger.info(f"Attempting to connect to RabbitMQ at {rabbitmq_host}")
    
    while retry_count < max_retries:
        try:
            # More explicit connection parameters
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
            
            # Declare the queue
            channel.queue_declare(queue="tts_queue", durable=True)
            logger.info("Successfully connected to RabbitMQ")
            
            def callback(ch, method, properties, body):
                try:
                    logger.info("Received message")
                    file_id = process_tts(body)
                    if file_id:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        ch.basic_nack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    ch.basic_nack(delivery_tag=method.delivery_tag)
            
            channel.basic_consume(
                queue="tts_queue",
                on_message_callback=callback
            )
            
            logger.info("Starting to consume messages...")
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            retry_count += 1
            logger.error(f"Failed to connect to RabbitMQ (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count == max_retries:
                raise
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")