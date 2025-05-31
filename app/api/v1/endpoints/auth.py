import httpx
import json
import time
import uuid
from app.core.config import settings
from app.core.redis import set_session_data
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, JSONResponse, RedirectResponse

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

    # 3. Store state in a cookie before returning the auth_url
    response.set_cookie(
        key="spotify_oauth_state",
        value=state_cookie_payload,
        httponly=True,
        max_age=300, # 5 minutes
        samesite="lax",
        secure=settings.API_ENV != "development"
    )

    # 4. Construct the Spotify OAuth URL (state parameter is the CSRF nonce)
    auth_url = f"{settings.AUTH_URL}?client_id={settings.SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={settings.REDIRECT_URI}&scope={scope}&state={csrf_nonce}"
    return {"auth_url": auth_url}

@router.get("/callback")
async def callback(request: Request, response: Response, code: str, state: str, error: str = None):
    """Handle Spotify OAuth callback"""

    if error:
        raise HTTPException(status_code=400, detail=f"Spotify OAuth error: {error}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state from Spotify OAuth callback")

    # 1. Retrieve and parse the state cookie
    stored_state_from_cookie = request.cookies.get("spotify_oauth_state")

    # Delete the state cookie to prevent reuse
    response.delete_cookie(
        "spotify_oauth_state",
        path="/",             # Match path from set_cookie
        secure=settings.API_ENV != "development",       
        httponly=True,      # Match httponly flag
        samesite="lax"      # Match samesite flag
    )

    if not stored_state_from_cookie:
        raise HTTPException(status_code=403, detail="State cookie not found. Possible CSRF attempt or cookie issue.")

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

            # 5. Redirect to the final redirect URI
            return RedirectResponse(url=target_final_redirect_uri)
        
    except httpx.RequestError as exc:
        print(f"HTTP request error: {exc}")
        raise HTTPException(status_code=502, detail="Error communicating with Spotify")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Could not exchange code for access token")