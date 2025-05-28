from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("/liked")
async def get_liked_tracks(access_token: str):
    """Get user's liked tracks"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(
                f"{settings.API_BASE_URL}/me/tracks",
                headers=headers,
                params={"limit": settings.SAVED_TRACKS_LIMIT_PER_REQUEST}
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 