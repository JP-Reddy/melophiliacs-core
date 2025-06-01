import httpx
import asyncio
from app.core.config import settings
from app.core.redis import get_user_tracks_cache, set_user_tracks_cache
from typing import List, Dict, Any

async def fetch_all_liked_tracks(
    spotify_access_token: str, 
    app_session_token: str 
) -> List[Dict[str, Any]]:
    """Fetch all liked tracks for a user. Also cache the results."""
    
    # 1. Check if tracks are cached
    cached_tracks = get_user_tracks_cache(app_session_token)
    if cached_tracks is not None:
        # print(f"DEBUG: Liked tracks for session {app_session_token[:4]}... found in cache.")
        return cached_tracks

    # print(f"DEBUG: Liked tracks for session {app_session_token[:4]}... not in cache. Fetching from Spotify.")
    all_tracks_items = [] 
    limit_per_request = settings.SAVED_TRACKS_LIMIT_PER_REQUEST
    current_offset = 0
    
    # Initialize with max limit, will be refined after first API call
    effective_total_to_fetch = settings.SAVED_TRACKS_LIMIT 

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {spotify_access_token}"}
        
        # 2. Make initial call to get total and first page
        initial_response = await client.get(
            f"{settings.API_BASE_URL}/me/tracks",
            headers=headers,
            params={"limit": limit_per_request, "offset": 0}
        )
        initial_response.raise_for_status()
        initial_data = initial_response.json()
        
        total_from_spotify = initial_data.get("total", 0)

        # 3. Calculate effective_total_to_fetch based on actual total from Spotify
        effective_total_to_fetch = min(total_from_spotify, settings.SAVED_TRACKS_LIMIT)
        
        current_page_items = initial_data.get("items", [])
        all_tracks_items.extend(current_page_items)
        current_offset = len(all_tracks_items)

        # 4. Return if first page already covers all tracks to fetch
        if current_offset >= effective_total_to_fetch:
            tracks_to_cache = all_tracks_items[:effective_total_to_fetch]
            set_user_tracks_cache(app_session_token, tracks_to_cache, settings.USER_CACHE_TTL_SECONDS)
            return tracks_to_cache

        tasks = []
        async def fetch_page(offset_val: int, page_limit: int):
            page_params = {"limit": page_limit, "offset": offset_val}
            page_response = await client.get(
                f"{settings.API_BASE_URL}/me/tracks", headers=headers, params=page_params
            )
            page_response.raise_for_status()
            return page_response.json().get("items", [])

        # 5. Calculate offsets for remaining pages
        offsets_to_fetch = []
        temp_offset = current_offset
        while temp_offset < effective_total_to_fetch:
            offsets_to_fetch.append(temp_offset)
            temp_offset += limit_per_request
        
        # 6. Fetch remaining pages concurrently
        if offsets_to_fetch:
            for offset_val in offsets_to_fetch:
                tasks.append(fetch_page(offset_val, limit_per_request))
            
            results_from_other_pages = await asyncio.gather(*tasks)
            for page_items in results_from_other_pages:
                all_tracks_items.extend(page_items)

    # 7. Cache the results
    final_tracks_to_cache = all_tracks_items[:effective_total_to_fetch]
    set_user_tracks_cache(app_session_token, final_tracks_to_cache, settings.USER_CACHE_TTL_SECONDS)

    return final_tracks_to_cache 