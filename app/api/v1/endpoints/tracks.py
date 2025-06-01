from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.core.config import settings
from app.core.auth import get_current_active_session
from app.utils.spotify_utils import fetch_all_liked_tracks

router = APIRouter()

@router.get("/liked", response_model=List[Dict[str, Any]])
async def get_liked_tracks(current_session: dict = Depends(get_current_active_session)):
    """Get user's liked tracks"""
    try:
        app_session_token = current_session.get("app_session_token")
        spotify_access_token = current_session.get("spotify_access_token")

        if not app_session_token or not spotify_access_token:
            raise HTTPException(status_code=401, detail="Invalid session data")

        liked_tracks = await fetch_all_liked_tracks(spotify_access_token, app_session_token)
        return liked_tracks
    except HTTPException as http_exc:
        print(f"HTTP error in get_liked_tracks endpoint: {str(http_exc)}")
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_liked_tracks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching liked tracks.") 