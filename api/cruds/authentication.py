import requests
from fastapi import HTTPException
from urllib.parse import urlencode
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from api.config.config import settings


CONFIG = settings

def get_google_login():
    params = {
        "client_id": CONFIG.GOOGLE_CLIENT_ID,
        "redirect_uri": CONFIG.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "prompt": "consent",
        "access_type": "offline"
    }

    url = CONFIG.GOOGLE_AUTH_URL + "?" + urlencode(params)
    return url

def get_google_callback(code: str):

    token_url = CONFIG.GOOGLE_TOKEN_URL

    data = {
        "client_id": CONFIG.GOOGLE_CLIENT_ID,
        "client_secret": CONFIG.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": CONFIG.GOOGLE_REDIRECT_URI,
    }

    token_response = requests.post(token_url, data=data).json()

    if "error" in token_response:
        raise HTTPException(status_code=400, detail=token_response)

    id_token = token_response["id_token"]

    try:
        user_info = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            CONFIG.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not get user info")
    
    return user_info