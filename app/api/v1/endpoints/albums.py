from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Tuple
import httpx
from app.core.config import settings
from app.core.auth import get_current_active_session
from app.utils.spotify_utils import fetch_all_liked_tracks
from app.core.redis import get_top_albums_cache, set_top_albums_cache

router = APIRouter()

def _organize_tracks_by_albums(tracks_data: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    """Helper to organize tracks by album"""
    
    album_dict = {}
    
    for track_obj in tracks_data:
        track = track_obj.get('track')
        if not track or not isinstance(track, dict):
            continue
        
        album = track.get('album')
        if not album or not isinstance(album, dict):
            continue

        album_id = album.get('id')
        album_name = album.get('name')
        if not album_id or not album_name:
            continue
            
        # Use a key for the album
        album_key = f"{album_name}____{album_id}"
        
        if album_key not in album_dict:
            album_artists = [artist.get('name') for artist in album.get('artists', []) if artist.get('name')]
            album_art_images = album.get('images', [])
            album_art_url = None
            if album_art_images:
                # Try to find a 300x300 image, otherwise take the first one
                album_art_url = next((img['url'] for img in album_art_images if img.get('height') == 300 and img.get('width') == 300), None)
                if not album_art_url and album_art_images:
                    album_art_url = album_art_images[0].get('url')

            album_dict[album_key] = {
                'album_id': album_id,
                'album_name': album_name,
                'artists': album_artists,
                'saved_tracks_details': [], # To store details of saved tracks from this album
                'total_tracks_in_album': album.get('total_tracks'),
                'saved_track_count': 0,
                'album_art_url': album_art_url,
                'release_date': album.get('release_date')
            }
        
        album_dict[album_key]['saved_tracks_details'].append({
            'track_id': track.get('id'),
            'track_name': track.get('name'),
            'spotify_url': track.get('external_urls', {}).get('spotify')
        })
        album_dict[album_key]['saved_track_count'] += 1
        
    # Convert to list of tuples
    return list(album_dict.items())

@router.get("/top", response_model=List[Dict[str, Any]])
async def get_top_albums_from_liked_songs(
    current_session: dict = Depends(get_current_active_session)
):
    """Get user's top albums derived from their liked/saved songs."""
    app_session_token = current_session.get("app_session_token")
    spotify_access_token = current_session.get("spotify_access_token")

    if not app_session_token or not spotify_access_token:
        raise HTTPException(status_code=401, detail="Invalid session data")

    # 1. Check cache for top albums
    cached_top_albums = get_top_albums_cache(app_session_token)
    if cached_top_albums is not None:
        return cached_top_albums

    # 2. If not cached, fetch liked tracks
    try:
        liked_tracks = await fetch_all_liked_tracks(spotify_access_token, app_session_token)
        if not liked_tracks:
            return [] 

        # 3. Organize tracks by album
        albums_organized_list = _organize_tracks_by_albums(liked_tracks)
        if not albums_organized_list:
            return []

        # 4. Sort albums by saved_track_count (desc) and then album_key (asc)
        sorted_albums_with_key = sorted(
            albums_organized_list, 
            key=lambda item_tuple: (-item_tuple[1]['saved_track_count'], item_tuple[0])
        )
        
        # Limit to TOP_ALBUMS_COUNT
        top_n_albums_data = [
            album_data_dict 
            for _album_key, album_data_dict in sorted_albums_with_key[:settings.TOP_ALBUMS_COUNT]
        ]

        # 5. Cache the result
        set_top_albums_cache(app_session_token, top_n_albums_data, settings.USER_CACHE_TTL_SECONDS)
        
        return top_n_albums_data

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_top_albums_from_liked_songs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing top albums from liked songs.")