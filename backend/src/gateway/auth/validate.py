import jwt
import os
from dotenv import load_dotenv

load_dotenv()

def token(token_str):
    try:
        decoded = jwt.decode(
            token_str,
            os.environ.get('JWT_SECRET'),
            algorithms=["HS256"]
        )
        return decoded['user_id']
    except:
        return None 