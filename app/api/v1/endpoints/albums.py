from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("/top")
async def get_top_albums(access_token: str):
    """Get user's top albums"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(
                f"{settings.API_BASE_URL}/me/top/albums",
                headers=headers,
                params={"limit": settings.TOP_ALBUMS_COUNT}
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 