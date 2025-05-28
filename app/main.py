from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from typing import Optional
import os
from dotenv import load_dotenv

from app.core.config import settings
from app.core.redis import get_redis
from app.api.v1.router import api_router

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Melophiliacs API",
    description="API for Melophiliacs - Spotify Stats and Playlist Generator",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to Melophiliacs API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 