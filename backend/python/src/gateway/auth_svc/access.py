import requests
import os 
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def login(request):
    try:
        # Check if authorization exists
        auth = request.authorization
        if not auth:
            logger.warning("No authorization credentials provided")
            return False, ("Missing credentials", 401)
        
        # Log attempt (sanitized)
        logger.debug(f"Login attempt for user: {auth.username}")
        
        # Prepare request
        basicAuth = (auth.username, auth.password)
        auth_svc_address = os.environ.get('AUTH_SVC_ADDRESS')
        
        if not auth_svc_address:
            logger.error("AUTH_SVC_ADDRESS environment variable not set")
            return False, ("Server configuration error", 500)

        # Make request to auth service
        try:
            res = requests.post(
                f"http://{auth_svc_address}/login",
                auth=basicAuth,
                timeout=5  # Add timeout
            )
            logger.debug(f"Auth service response status: {res.status_code}")
            
            if res.status_code == 200:
                return res.text, None
            else:
                logger.error(f"Auth service error: {res.text}")
                return False, (res.text, res.status_code)
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to auth service at {auth_svc_address}")
            return False, ("Authentication service unavailable", 503)
        except requests.exceptions.Timeout:
            logger.error("Auth service request timed out")
            return False, ("Authentication service timeout", 504)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to auth service failed: {str(e)}")
            return False, ("Authentication failed", 500)
            
    except Exception as e:
        logger.exception("Unexpected error during login")
        return False, (f"Internal server error: {str(e)}", 500)