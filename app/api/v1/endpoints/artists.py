from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Tuple
from collections import OrderedDict
import httpx
from app.core.config import settings
from app.core.auth import get_current_active_session
from app.utils.spotify_utils import fetch_all_liked_tracks
from app.core.redis import get_top_artists_cache, set_top_artists_cache

router = APIRouter()

def _organize_tracks_by_artist(tracks_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Helper to organize tracks by artist and count songs"""
    
    artist_songs = {}
    for track_obj in tracks_data:
        track = track_obj.get('track') 
        if not track or not isinstance(track, dict): 
            continue
        
        for artist in track.get('artists', []):
            artist_name = artist.get('name')
            if not artist_name:
                continue

            song_info = {
                'name': track.get('name'),
                'album': track.get('album', {}).get('name'),
            }
            
            if artist_name not in artist_songs:
                artist_songs[artist_name] = {
                    'tracks': [],
                    'count': 0
                }
            artist_songs[artist_name]['tracks'].append(song_info)
            artist_songs[artist_name]['count'] += 1
    
    return artist_songs

@router.get("/top", response_model=List[Tuple[str, int]])
async def get_top_artists_from_liked_songs(
    current_session: dict = Depends(get_current_active_session)
):
    """Get user's top artists from their liked/saved songs"""
    app_session_token = current_session.get("app_session_token")
    spotify_access_token = current_session.get("spotify_access_token")

    if not app_session_token or not spotify_access_token:
        raise HTTPException(status_code=401, detail="Invalid session data")

    # 1. Check cache for top artists
    cached_top_artists = get_top_artists_cache(app_session_token)
    if cached_top_artists is not None:
        return cached_top_artists

    # 2. If not cached, fetch liked tracks
    try:
        liked_tracks = await fetch_all_liked_tracks(spotify_access_token, app_session_token)
        if not liked_tracks:
            return [] 

        # 3. Organize tracks by artist
        artist_tracks_aggregation = _organize_tracks_by_artist(liked_tracks)
        if not artist_tracks_aggregation:
            return []

        # 4. Sort artists by song count and name, then limit
        # Create a list of (artist_name, song_count)
        artist_song_counts = [
            (artist, data['count']) 
            for artist, data in artist_tracks_aggregation.items()
        ]
        
        # Sort: primary key is count (desc), secondary is artist name (asc)
        sorted_artists = sorted(artist_song_counts, key=lambda x: (-x[1], x[0]))
        
        top_n_artists = sorted_artists[:settings.TOP_ARTISTS_COUNT]

        # 5. Cache the result
        set_top_artists_cache(app_session_token, top_n_artists, settings.USER_CACHE_TTL_SECONDS)
        
        return top_n_artists

    except HTTPException as http_exc: # Re-raise if fetch_all_liked_tracks raised one
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_top_artists_from_liked_songs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing top artists from liked songs.")