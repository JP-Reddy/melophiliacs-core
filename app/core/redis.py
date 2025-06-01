import redis
from app.core.config import settings
import json
from typing import Optional, Any

def get_redis():
    """Get Redis connection"""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )

def get_session_data(session_id: str, key: Optional[str] = None) -> Any:
    """Fetch session data from Redis"""
    if not session_id:
        return None

    redis_client = get_redis()
    data = redis_client.get(f"session:{session_id}")
    if not data:
        return None

    session_data = json.loads(data)
    return session_data.get(key) if key else session_data

def set_session_data(session_id: str, data: dict) -> bool:
    """Store session data in Redis"""
    if not session_id:
        return False

    redis_client = get_redis()
    
    # If updating existing session, merge with existing data
    existing_data = get_session_data(session_id)
    if existing_data:
        existing_data.update(data)
        data = existing_data

    redis_client.setex(
        f"session:{session_id}",
        settings.SESSION_TIMEOUT,
        json.dumps(data)
    )
    return True 

def set_user_tracks_cache(app_session_token: str, tracks: list, ttl: int):
    """Store user saved songs in Redis"""

    redis_client = get_redis()
    redis_client.setex(
        f"user_tracks:{app_session_token}",
        ttl,
        json.dumps(tracks)
    )
    return True 

def get_user_tracks_cache(app_session_token: str) -> Optional[list]:
    """Fetch user saved songs from Redis"""

    redis_client = get_redis()
    data = redis_client.get(f"user_tracks:{app_session_token}")
    if not data:
        return None
    print(f"Fetching user tracks from Redis for session {app_session_token[:4]}...{app_session_token[-4:]}") # Mask the session token
    return json.loads(data)

def delete_user_tracks_cache(app_session_token: str):
    """Delete user saved songs from Redis cache"""
    redis_client = get_redis()
    redis_client.delete(f"user_tracks:{app_session_token}")
    return True 