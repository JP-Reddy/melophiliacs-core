from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("/top")
async def get_top_artists(access_token: str):
    """Get user's top artists"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(
                f"{settings.API_BASE_URL}/me/top/artists",
                headers=headers,
                params={"limit": settings.TOP_ARTISTS_COUNT}
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 