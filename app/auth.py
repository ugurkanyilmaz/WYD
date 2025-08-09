import os
from jose import jwt, JWTError
from datetime import datetime, timedelta

# Prefer JWT_SECRET but support legacy JWT_SECRET_KEY for compatibility
SECRET = os.getenv('JWT_SECRET') or os.getenv('JWT_SECRET_KEY', 'devsecret')
ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', str(60 * 24 * 7)))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded = jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)
    return encoded

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# OAuth placeholders (Google/Facebook)
# In production, use libraries like authlib to perform full OAuth flows.
def get_oauth_redirect(provider: str, redirect_uri: str):
    return f"https://oauth.{provider}/authorize?redirect_uri={redirect_uri}&client_id=REPLACE"
