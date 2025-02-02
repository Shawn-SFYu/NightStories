import jwt
import os

def token(token_str):
    try:
        decoded = jwt.decode(
            token_str,
            os.environ.get('JWT_SECRET', 'your-secret-key'),
            algorithms=["HS256"]
        )
        return decoded['user_id']
    except:
        return None 