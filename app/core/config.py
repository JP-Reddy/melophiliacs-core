from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Configuration
    API_ENV: str = os.getenv("API_ENV", "development")
    DEBUG: bool = API_ENV == "development"
    
    # Spotify Configuration
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    REDIRECT_URI: str = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")
    FRONTEND_URI: str = os.getenv("FRONTEND_URI", "http://localhost:5173")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # Session Configuration
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "https://melophiliacs.com",
        "https://api.spotify.com",
        "https://accounts.spotify.com",
        "http://localhost:5173"  # For development
    ]
    
    # Spotify API URLs
    AUTH_URL: str = "https://accounts.spotify.com/authorize"
    TOKEN_URL: str = "https://accounts.spotify.com/api/token"
    API_BASE_URL: str = "https://api.spotify.com/v1"
    
    # API Limits
    SAVED_TRACKS_LIMIT: int = 3000
    SAVED_TRACKS_LIMIT_PER_REQUEST: int = 50
    TOP_ARTISTS_COUNT: int = 50
    TOP_ALBUMS_COUNT: int = 50

    class Config:
        case_sensitive = True

settings = Settings() 