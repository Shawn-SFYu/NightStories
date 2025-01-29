import jwt, datetime, os
from flask import Flask, request, jsonify
from functools import wraps
from flask_mysqldb import MySQL

server = Flask(__name__)

# MySQL Configuration
server.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST", "mysql")
server.config["MYSQL_USER"] = os.environ.get("MYSQL_USER", "auth_user")
server.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "Auth123")
server.config["MYSQL_DB"] = os.environ.get("MYSQL_DB", "auth")
server.config["MYSQL_PORT"] = int(os.environ.get("MYSQL_PORT", 3306))  # Convert port to integer

mysql = MySQL(server)

@server.route('/login', methods=['POST'])
def login():
    try:
        auth = request.authorization
        if not auth:
            return "Missing credentials", 401
        
        # Use parameterized query to prevent SQL injection
        cursor = mysql.connection.cursor()
        query = "SELECT email, password FROM users WHERE email=%s AND password=%s"
        cursor.execute(query, (auth.username, auth.password))
        result = cursor.fetchone()
        email, _ = result        
        if not result:
            return "Invalid credentials", 401
        
        return createJWT(email, os.environ.get('JWT_SECRET'), True), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")  # For debugging
        return "Internal server error", 500
    finally:
        cursor.close()  # Always close the cursor

@server.route('/validate', methods=['POST'])
def validate():
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
            "admin": authz
        },
        secret,
        algorithm="HS256"
    )

if __name__ == '__main__':
    server.run(host="0.0.0.0", port=5000)