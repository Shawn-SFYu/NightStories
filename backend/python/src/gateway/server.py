import os, gridfs, pika, json
from flask import Flask, request
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util

import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

server = Flask(__name__)
server.config["MONGO_URI"] = "mongodb://host.minikube.internal:27017/videos"

mongo = PyMongo(server)

fs = gridfs.GridFS(mongo.db)

connection = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
channel = connection.channel()

@server.route("/login", methods=["POST"])
def login():
    token, err = access.login(request)
    if not err:
        return token
    else:
        return err

@server.route("/upload", methods=["POST"])
def upload():
    access, err = validate.token(request)
    if err:
        return err
    logger.debug(f"Access value: {access}")    
    access = json.loads(access)
    logger.debug(f"Access value: {access}")
    if access["admin"]:
        if len(request.files) > 1 or request.files["file"].filename == "":
            return "Exactly one file required, Invalid input", 400
        
        for _, file in request.files.items():
            err = util.upload(file, fs, channel, access)
            if err:
                return err
        return "Success", 200
    else:
        return "Not authorized", 401

@server.route("/download", methods=["GET"])
def download():
    pass

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8080) 