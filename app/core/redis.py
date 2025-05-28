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
    """Retrieve session data from Redis"""
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