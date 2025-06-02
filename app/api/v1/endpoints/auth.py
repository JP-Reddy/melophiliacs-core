import httpx
import json
import time
import uuid
from app.core.config import settings
from app.core.redis import set_session_data
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, JSONResponse, RedirectResponse
from app.core.auth import get_current_active_session
from app.core.redis import delete_session_data
from typing import Dict
from fastapi import Depends

router = APIRouter()

@router.get("/login")
async def login(response: Response, request: Request, final_redirect_uri: str = None):
    """Initialize Spotify login flow"""
    
    scope = settings.SPOTIFY_SCOPE

    # 1. Determine and validate the final redirect URI
    target_final_redirect_uri = settings.DEFAULT_FINAL_REDIRECT_URI
    
    if final_redirect_uri:
        is_allowed = False
        # Validate the provided final_redirect_uri against the whitelist
        # TODO: add more robust validation
        for allowed_uri_prefix in settings.ALLOWED_FINAL_REDIRECT_URIS:
            if final_redirect_uri.startswith(allowed_uri_prefix):
                target_final_redirect_uri = final_redirect_uri
                is_allowed = True
                break
        
        if not is_allowed:
            print(f"Warning: Client from IP {request.client.host} provided a non-whitelisted final_redirect_uri: {final_redirect_uri}. Using default.")
        
    # 2. Create CSRF nonce and payload for the state cookie
    csrf_nonce = str(uuid.uuid4())
    state_cookie_payload = json.dumps({
        "nonce": csrf_nonce,
        "final_redirect_uri": target_final_redirect_uri
    })

    # 3. Construct the Spotify OAuth URL (state parameter is the CSRF nonce)
    auth_url = f"{settings.AUTH_URL}?client_id={settings.SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={settings.REDIRECT_URI}&scope={scope}&state={csrf_nonce}"

    response = RedirectResponse(url=auth_url)
    
    # 4. Store state in a cookie before returning the auth_url
    response.set_cookie(
        key="spotify_oauth_state",
        value=state_cookie_payload,
        httponly=True,
        max_age=300, # 5 minutes
        samesite="lax",
        path="/",
        secure=settings.API_ENV != "development"
    )

    return response

@router.get("/callback")
async def callback(request: Request, response: Response, code: str, state: str, error: str = None):
    """Handle Spotify OAuth callback"""

    if error:
        raise HTTPException(status_code=400, detail=f"Spotify OAuth error: {error}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state from Spotify OAuth callback")

    # 1. Retrieve and parse the state cookie
    stored_state_from_cookie = request.cookies.get("spotify_oauth_state")

    try:
        state_cookie_payload = json.loads(stored_state_from_cookie)
        csrf_nonce = state_cookie_payload.get("nonce")
        target_final_redirect_uri = state_cookie_payload.get("final_redirect_uri")
    except json.JSONDecodeError:
        raise HTTPException(status_code=403, detail="Invalid state cookie format")
    
    if not csrf_nonce or not target_final_redirect_uri:
        raise HTTPException(status_code=403, detail="State cookie missing required fields")
    
    # 2. Validate the CSRF nonce 
    # 'state' from spotify callback should match csrf_nonce from state cookie
    if csrf_nonce != state:
        raise HTTPException(status_code=403, detail="State parameter mismatch. Possible CSRF attack.")
    
    # 3. Exchange the authorization code for an access token
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
                    "client_secret": settings.SPOTIFY_CLIENT_SECRET
                }
            )
            token_data = token_response.json()

            spotify_access_token = token_data.get("access_token")
            spotify_refresh_token = token_data.get("refresh_token")
            spotify_expires_in = token_data.get("expires_in")

            if not all([spotify_access_token, spotify_refresh_token, spotify_expires_in]):
                raise HTTPException(status_code=500, detail="Incomplete token data from Spotify")
            

            app_session_token = str(uuid.uuid4())

            spotify_access_token_expires_at = int(time.time()) + spotify_expires_in

            session_payload = {
                "spotify_access_token": spotify_access_token,
                "spotify_refresh_token": spotify_refresh_token,
                "spotify_access_token_expires_at": spotify_access_token_expires_at
            }

            if not set_session_data(app_session_token, session_payload):
                print(f"Failed to set session data for app_session_token: {app_session_token}")
                raise HTTPException(status_code=500, detail="Could not save session data")


            response = RedirectResponse(url=target_final_redirect_uri)

            # 4. Set the app_session_token cookie
            response.set_cookie(
                key = "app_session_token",
                value = app_session_token,
                httponly = True,
                secure = settings.API_ENV != "development", 
                samesite= "lax",
                max_age = settings.SESSION_TIMEOUT,
                path = "/"
            )
            response.delete_cookie(
                "spotify_oauth_state",
                path="/",             # Match path from set_cookie
                secure=settings.API_ENV != "development",       
                httponly=True,      
                samesite="lax"      
            )

            # 5. Redirect to the final redirect URI
            return response
    except httpx.RequestError as exc:
        print(f"HTTP request error: {exc}")
        raise HTTPException(status_code=502, detail="Error communicating with Spotify")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Could not exchange code for access token")

@router.get("/me", response_model=Dict[str, str])
async def read_users_me(current_session: dict = Depends(get_current_active_session)):
    """Fetch current authenticated user's session status."""
    return {"status": "authenticated", "app_session_token_suffix": current_session.get("app_session_token", "")[-4:]}

@router.post("/logout") 
async def logout_user(response: Response, current_session: dict = Depends(get_current_active_session)):
    """Logout user by deleting session from Redis and clearing the cookie."""
    app_session_token = current_session.get("app_session_token")
    
    if app_session_token:
        deleted_count = delete_session_data(app_session_token)
        if deleted_count > 0:
            print(f"Session {app_session_token[:4]}...{app_session_token[-4:]} deleted from Redis.")
        else:
            print(f"Warning: Logout attempt for session {app_session_token[:4]}...{app_session_token[-4:]}, but no session found in Redis to delete.")
    else:
        # This case should ideally not be reached if get_current_active_session works correctly
        print("Warning: app_session_token not found in current_session during logout.")

    response = JSONResponse(content={"message": "Logout successful"}, status_code=200)

    # Clear the app_session_token cookie from the browser
    response.delete_cookie(
        key="app_session_token",
        path="/", 
        secure=settings.API_ENV != "development", 
        httponly=True, 
        samesite="lax" 
    )

    return response