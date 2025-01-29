import os, requests

def token(request):
    if not "Authorization" in request.headers:
        return False, ("Missing credentials", 401)
    
    token = request.headers["Authorization"]

    if not token:
        return False, ("Missing credentials", 401)
    
    res = requests.post(
        f"http://{os.environ.get('AUTH_SVC_ADDRESS')}/validate",
        headers={"Authorization": token}
    )

    if res.status_code == 200:
        return True
    else:
        return False, (res.text, res.status_code)