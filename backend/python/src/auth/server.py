import jwt, datetime, os
from flask import Flask, request, jsonify
from functools import wraps
from flask_mysqldb import MySQL

server = Flask(__name__)
mysql = MySQL(server)

server.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
server.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
server.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
server.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')
server.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT'))


@server.route('/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth:
        return "Missing credentials", 401
    
    # check db for username and password
    cursor = mysql.connection.cursor()
    query = f"SELECT email, password FROM users WHERE email='{auth.username}' AND password='{auth.password}'"
    cursor.execute(query)
    result = cursor.fetchone()
    if not result:
        return "Invalid credentials", 401
    email, password = result
    return createJWT(email, os.environ.get('JWT_SECRET'), True)

@server.route('/validate', methods=['POST'])
def validateJWT(request):
    encoded_jwt = request.headers['Authorization']
    if not encoded_jwt:
        return "Missing credentials", 401
    encoded_jwt = encoded_jwt.split(" ")[1]
    try:
        decoded = jwt.decode(encoded_jwt, os.environ.get('JWT_SECRET'), algorithms=["HS256"])
    except:
        return "Not authorized", 403 
    return decoded, 200

def createJWT(email, secret, authz):
    return jwt.encode(
        {
            "email": email,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1),
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "authz": authz
        },
        secret,
        algorithm="HS256"
    )

if __name__ == '__main__':
    server.run(host="0.0.0.0", port=5000)