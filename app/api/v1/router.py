from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from typing import List, Dict, Any
import uuid
import time

from app.core.config import settings
from app.core.redis import get_session_data, set_session_data
from app.api.v1.endpoints import auth, tracks, artists, albums

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tracks.router, prefix="/tracks", tags=["Tracks"])
api_router.include_router(artists.router, prefix="/artists", tags=["Artists"])
api_router.include_router(albums.router, prefix="/albums", tags=["Albums"]) 