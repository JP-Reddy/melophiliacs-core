from fastapi import Depends, HTTPException, status, Request
from app.core.config import settings
from app.core.redis import get_session_data, set_session_data 
import httpx
import time
import uuid
from typing import Optional

# Dependency 
async def get_current_active_session(request: Request) -> dict:
    app_session_token = request.cookies.get("app_session_token")
    if not app_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - missing session token",
            headers={"WWW-Authenticate": "Bearer"}, 
        )

    session_data = get_session_data(app_session_token)

    session_data["app_session_token"] = app_session_token
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    
    spotify_access_token_expires_at = session_data.get("spotify_access_token_expires_at", 0)
    current_time = int(time.time())
    
    # Buffer time before actual expiry to trigger refresh
    buffer_time_seconds = 300 

    if spotify_access_token_expires_at < (current_time + buffer_time_seconds):
        
        print(f"Spotify token for session {app_session_token[:4]}...{app_session_token[-4:]} expired or expiring soon. Refreshing...")
        new_spotify_tokens = await refresh_spotify_token(session_data.get("spotify_refresh_token"))
        
        if not new_spotify_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh Spotify token. Please log in again.",
            )

        # Update session with new tokens
        session_data["spotify_access_token"] = new_spotify_tokens["access_token"]
        session_data["spotify_access_token_expires_at"] = int(time.time()) + new_spotify_tokens["expires_in"]
        
        # Spotify may issue a new refresh token, though it's not always the case
        if "refresh_token" in new_spotify_tokens:
            session_data["spotify_refresh_token"] = new_spotify_tokens["refresh_token"]
        
        if not set_session_data(app_session_token, session_data):
            print(f"CRITICAL: Failed to update session data in Redis after token refresh for {app_session_token[:4]}...{app_session_token[-4:]}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not update session after token refresh.",
            )
        print(f"Spotify token refreshed successfully for session {app_session_token[:4]}...{app_session_token[-4:]}")

    return session_data 


async def refresh_spotify_token(spotify_refresh_token: str) -> Optional[dict]:
    if not spotify_refresh_token:
        return None
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": spotify_refresh_token,
                    "client_id": settings.SPOTIFY_CLIENT_ID,
                    "client_secret": settings.SPOTIFY_CLIENT_SECRET,
                },
            )
            response.raise_for_status() 
            token_data = response.json()

            if "error" in token_data:
                print(f"Error refreshing Spotify token: {token_data.get('error_description', token_data['error'])}")
                return None
            
            if not token_data.get("access_token") or "expires_in" not in token_data:
                print(f"Incomplete data from Spotify token refresh: {token_data}")
                return None

            return token_data
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error during Spotify token refresh: {exc.response.status_code} - {exc.response.text}")
            return None
        except Exception as e:
            print(f"Unexpected error during Spotify token refresh: {str(e)}")
            return None
