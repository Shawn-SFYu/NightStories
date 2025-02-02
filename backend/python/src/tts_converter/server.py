import io
import numpy as np

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from bson.objectid import ObjectId

import datetime
import logging
import gridfs
from flask_pymongo import PyMongo
import certifi

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# MongoDB Configuration
app.config["MONGO_URI"] = ("mongodb+srv://shawnsfyuan:oGXOr3OVoJ3v75xX@"
                          "cluster0.0gcau.mongodb.net/nightstories?"
                          "retryWrites=true&w=majority&"
                          "tlsCAFile=" + certifi.where())
try:
    mongo = PyMongo(app)
    mongo.db.command('ping')
    logger.info("MongoDB connection successful")
    fs = gridfs.GridFS(mongo.db)
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")


from kokoro import KPipeline
import soundfile as sf
# 🇺🇸 'a' => American English, 🇬🇧 'b' => British English
# 🇯🇵 'j' => Japanese: pip install misaki[ja]
# 🇨🇳 'z' => Mandarin Chinese: pip install misaki[zh]
pipeline = KPipeline(lang_code='a') # <= make sure lang_code matches voice


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
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6000, debug=True)