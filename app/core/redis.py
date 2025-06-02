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
    print(f"DEBUG: Fetching user tracks from Redis for session {app_session_token[:4]}...{app_session_token[-4:]}") # Mask the session token
    return json.loads(data)

def delete_user_tracks_cache(app_session_token: str):
    """Delete user saved songs from Redis cache"""
    redis_client = get_redis()
    redis_client.delete(f"user_tracks:{app_session_token}")
    return True 

def set_top_artists_cache(app_session_token: str, top_artists: list, ttl: int):
    """Store user's top artists in Redis"""
    if not app_session_token:
        return False
    redis_client = get_redis()
    redis_client.setex(
        f"top_artists:{app_session_token}",
        ttl,
        json.dumps(top_artists)
    )
    return True

def get_top_artists_cache(app_session_token: str) -> Optional[list]:
    """Fetch user's top artists from Redis"""
    if not app_session_token:
        return None
    redis_client = get_redis()
    data = redis_client.get(f"top_artists:{app_session_token}")
    if not data:
        print(f"DEBUG: No top artists found in Redis cache for session {app_session_token[:4]}...{app_session_token[-4:]}")
        return None
    print(f"DEBUG: Top artists found in Redis cache for session {app_session_token[:4]}...{app_session_token[-4:]}")
    return json.loads(data)

def delete_top_artists_cache(app_session_token: str):
    """Delete user's top artists from Redis"""
    if not app_session_token:
        return False
    redis_client = get_redis()
    redis_client.delete(f"top_artists:{app_session_token}")
    return True 

# Functions for Top Albums Cache
def set_top_albums_cache(app_session_token: str, top_albums: list, ttl: int):
    """Store user's top albums in Redis"""
    if not app_session_token:
        return False
    redis_client = get_redis()
    redis_client.setex(
        f"top_albums:{app_session_token}",
        ttl,
        json.dumps(top_albums)
    )
    return True

def get_top_albums_cache(app_session_token: str) -> Optional[list]:
    """Fetch user's top albums from Redis"""
    if not app_session_token:
        return None
    redis_client = get_redis()
    data = redis_client.get(f"top_albums:{app_session_token}")
    if not data:
        print(f"DEBUG: No top albums found in Redis cache for session {app_session_token[:4]}...{app_session_token[-4:]}")
        return None
    print(f"DEBUG: Top albums found in Redis cache for session {app_session_token[:4]}...{app_session_token[-4:]}")
    return json.loads(data)

def delete_top_albums_cache(app_session_token: str):
    """Delete user's top albums from Redis"""
    if not app_session_token:
        return False
    redis_client = get_redis()
    redis_client.delete(f"top_albums:{app_session_token}")
    return True 

def delete_session_data(app_session_token: str):
    """Delete session data from Redis"""
    if not app_session_token:
        return False
    redis_client = get_redis()
    redis_client.delete(f"session:{app_session_token}")
    redis_client.delete(f"user_tracks:{app_session_token}")
    redis_client.delete(f"top_artists:{app_session_token}")
    redis_client.delete(f"top_albums:{app_session_token}")
    return True 