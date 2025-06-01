from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import httpx
from app.core.config import settings
from app.core.auth import get_current_active_session
from app.core.redis import set_user_tracks_cache, get_user_tracks_cache
import asyncio

router = APIRouter()

@router.get("/liked")
async def get_liked_tracks(current_session: dict = Depends(get_current_active_session)):
    """Get user's liked tracks"""

    app_session_token = current_session.get("app_session_token")
    if not app_session_token:
        raise HTTPException(status_code=401, detail="No app session token found in session")
    
    spotify_access_token = current_session.get("spotify_access_token")
    if not spotify_access_token:
        raise HTTPException(status_code=401, detail="No access token found in session")
    
    # 1. Check if tracks are cached
    cached_tracks = get_user_tracks_cache(app_session_token)
    if cached_tracks:
        return cached_tracks
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {spotify_access_token}"}
            limit_per_request = settings.SAVED_TRACKS_LIMIT_PER_REQUEST
            
            # 2. Initial request to get total number of liked songs
            initial_response = await client.get(
                f"{settings.API_BASE_URL}/me/tracks",
                headers=headers,
                params={"limit": limit_per_request}
            )
            initial_response.raise_for_status() # Raise an exception for bad status codes
            initial_response_data = initial_response.json()
            
            total_from_spotify = initial_response_data.get('total', 0)

            # 3. Figure out effective total to fetch
            effective_total_to_fetch = min(total_from_spotify, settings.SAVED_TRACKS_LIMIT)

            initial_items = initial_response_data.get('items', [])
            all_tracks = list(initial_items)

            # 4. If first batch is sufficient, return
            if len(initial_items) >= total_from_spotify:
                return all_tracks[:effective_total_to_fetch]

            # 5. Calculate offsets for remaining pages
            tasks = []
            current_offset = limit_per_request # Start offset for the second page

            # 6. Create helper to fetch a page of liked songs
            async def fetch_page(offset_val: int, page_limit: int):
                page_params = {"limit": page_limit, "offset": offset_val}
                page_response = await client.get(
                    f"{settings.API_BASE_URL}/me/tracks",
                    headers=headers, # from outer scope
                    params=page_params
                )
                page_response.raise_for_status()
                return page_response.json().get('items', [])

            offsets_to_fetch = []
            while current_offset < effective_total_to_fetch:
                offsets_to_fetch.append(current_offset)
                current_offset += limit_per_request
            
            if offsets_to_fetch:
                for offset_val in offsets_to_fetch:
                    tasks.append(fetch_page(offset_val, limit_per_request))
                
                # 7. Execute tasks concurrently
                results_from_other_pages = await asyncio.gather(*tasks)
                
                # 8. Combine results
                for page_items in results_from_other_pages:
                    all_tracks.extend(page_items)
            
            # 9. Cache the results
            set_user_tracks_cache(app_session_token, all_tracks, settings.SAVED_TRACKS_CACHE_TTL)

            # 10. Return combined list
            return all_tracks[:effective_total_to_fetch]
            
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error fetching liked tracks: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error from Spotify API")
    except Exception as e:
        print(f"Unexpected error fetching liked tracks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred") 