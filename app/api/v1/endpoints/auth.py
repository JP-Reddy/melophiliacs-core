from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("/login")
async def login():
    """Initialize Spotify login flow"""
    scope = "user-read-private user-read-email user-library-read user-top-read playlist-modify-public playlist-modify-private"
    auth_url = f"{settings.AUTH_URL}?client_id={settings.SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={settings.REDIRECT_URI}&scope={scope}"
    return {"auth_url": auth_url}

@router.get("/callback")
async def callback(code: str):
    """Handle Spotify OAuth callback"""
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            token_response = await client.post(
                settings.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.REDIRECT_URI,
                    "client_id": settings.SPOTIFY_CLIENT_ID,
                    "client_secret": settings.SPOTIFY_CLIENT_SECRET,
                }
            )
            token_data = token_response.json()
            
            if "error" in token_data:
                raise HTTPException(status_code=400, detail=token_data["error"])
            
            return JSONResponse(
                content={"access_token": token_data["access_token"]},
                headers={"Location": settings.FRONTEND_URI}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 