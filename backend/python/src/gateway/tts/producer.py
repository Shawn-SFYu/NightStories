from flask import request, jsonify
from bson.objectid import ObjectId
import datetime
import json
import pika
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def submit_tts(channel, verify_jwt):
    try:
        # Verify token
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "errors": "No token provided"}), 401

        user_id = verify_jwt(token.split(' ')[1])
        if not user_id:
            return jsonify({"success": False, "errors": "Invalid token"}), 401

        data = request.json
        text = data.get('text')
        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400

        # Generate task ID
        task_id = str(ObjectId())

        # Create message for queue
        message = {
            "task_id": task_id,
            "user_id": user_id,
            "text": text,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        # Send to RabbitMQ
        channel.basic_publish(
            exchange="",
            routing_key="tts_queue",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )

        return jsonify({
            "success": True,
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"TTS submission error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to submit TTS task"
        }), 500
