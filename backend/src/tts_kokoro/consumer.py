import io
import numpy as np
import pika, json, sys, os
from flask import Flask
from flask_cors import CORS
import certifi
import time
import threading
from queue import Queue, Empty

import logging
import gridfs
from flask_pymongo import PyMongo
import soundfile as sf
from kokoro import KPipeline
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
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
        logger.info(f"Generated audio segment {i}")
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
        logger.info("Starting TTS processing")
        data = json.loads(message)
        text = data['text']
        
        metadata = {
            'task_id': data['task_id'],
            'user_id': data['user_id'],
            'doc_id': data['doc_id'],
            'type': 'document'
        }
        
        logger.info("Initializing TTS pipeline")
        generator = pipeline(
            text,
            voice='af_heart',
            speed=1,
            split_pattern=r'\n+'
        )
        
        logger.info("Generating audio")
        audio_buffer = generate_audio(generator)
        
        logger.info("Saving to GridFS")
        file_id = fs.put(
            audio_buffer.getvalue(),
            filename=f'tts_{data["task_id"]}.mp3',
            content_type='audio/mp3',
            metadata=metadata
        )
        logger.info(f"Successfully saved audio with file_id: {file_id}")
        return str(file_id)
        
    except Exception as e:
        logger.error(f"TTS processing error: {str(e)}")
        logger.exception("Full traceback:")
        return None

def main():
    while True:
        try:
            # Get host from environment or default to localhost if using port-forward
            rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
            logger.info(f"Attempting to connect to RabbitMQ at {rabbitmq_host}")
            
            parameters = pika.ConnectionParameters(
                host=rabbitmq_host,
                port=5672,
                virtual_host='/',
                credentials=pika.PlainCredentials('guest', 'guest'),
                connection_attempts=3,
                retry_delay=5,
                socket_timeout=600,  # 10 minutes
                heartbeat=120  # 2 minutes
            )
            
            logger.info("Connecting to RabbitMQ...")
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Declare the queue
            channel.queue_declare(queue="tts_queue", durable=True)
            channel.basic_qos(prefetch_count=1)
            logger.info("Successfully connected to RabbitMQ")
            
            def callback(ch, method, properties, body):
                try:
                    logger.info("Received new message")
                    message = body.decode()
                    
                    # Create a queue to get the result from the thread
                    result_queue = Queue()
                    
                    # Create and start processing thread
                    def process_thread():
                        try:
                            file_id = process_tts(message)
                            result_queue.put(('success', file_id))
                        except Exception as e:
                            result_queue.put(('error', str(e)))
                    
                    thread = threading.Thread(target=process_thread)
                    thread.daemon = True  # Make thread daemon so it exits when main thread exits
                    thread.start()
                    
                    # Poll the queue instead of blocking with join()
                    while thread.is_alive():
                        try:
                            status, result = result_queue.get(timeout=1.0)  # Check every second
                            if status == 'success' and result:
                                logger.info("Successfully processed message")
                                ch.basic_ack(delivery_tag=method.delivery_tag)
                            else:
                                logger.error(f"Failed to process message: {result}")
                                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                            break
                        except Empty:
                            continue  # Keep polling if no result yet
                    
                except Exception as e:
                    logger.error(f"Error in callback: {str(e)}")
                    logger.exception("Full traceback:")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            channel.basic_consume(
                queue="tts_queue",
                on_message_callback=callback
            )
            
            logger.info("Starting to consume messages...")
            channel.start_consuming()
            
        except (pika.exceptions.ConnectionClosedByBroker,
                pika.exceptions.AMQPConnectionError) as e:
            logger.error(f"Connection lost: {str(e)}")
            logger.info("Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            continue

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")