import io
import numpy as np
import pika, json, sys, os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from bson.objectid import ObjectId

import datetime
import logging
import gridfs
from flask_pymongo import PyMongo
import certifi
import soundfile as sf
from kokoro import KPipeline
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
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
    sf.write(audio_buffer, combined_audio, 24000, format='WAV')
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
            filename=f'tts_{data["task_id"]}.wav',
            content_type='audio/wav',
            task_id=data['task_id'],
            user_id=data['user_id']
        )
        return str(file_id)
    except Exception as e:
        logger.error(f"TTS processing error: {str(e)}")
        return None

def main():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.environ.get("RABBITMQ_HOST", "rabbitmq"))
    )
    channel = connection.channel()
    
    channel.queue_declare(queue="tts_queue", durable=True)
    
    def callback(ch, method, properties, body):
        file_id = process_tts(body)
        if file_id:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(
        queue="tts_queue",
        on_message_callback=callback
    )
    
    print("TTS Consumer waiting for messages...")
    channel.start_consuming()


'''
@app.route("/tts/generate", methods=["POST"])
def generate_tts():
    try:
        data = request.json
        text = data.get("text")
        voice = data.get("voice", "af_heart")
        speed = data.get("speed", 1)
        split_pattern = data.get("split_pattern", r'\n+')
        generator = pipeline(
            text, voice, 
            speed, split_pattern)
        audio_buffer = generate_audio(generator)

        file_id = fs.put(
            audio_buffer.getvalue(), 
            filename=f'tts_{datetime.datetime.utcnow().timestamp()}.wav',
            content_type='audio/wav'
        )
        
        return jsonify({
            "success": True,
            "file_id": str(file_id)
        }), 200
        
    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to generate audio"
        }), 500

@app.route('/tts/audio/<file_id>', methods=['GET'])
def get_audio(file_id):
    try:
        # Retrieve from GridFS
        audio_file = fs.get(ObjectId(file_id))
        
        return send_file(
            io.BytesIO(audio_file.read()),
            mimetype='audio/wav',
            as_attachment=True,
            download_name=f'tts_audio_{file_id}.wav'
        )
        
    except Exception as e:
        logger.error(f"Audio retrieval error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve audio"
        }), 500
    '''

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)