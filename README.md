# Melophiliacs Core

[![CI Status](https://img.shields.io/badge/ci-passing-brightgreen.svg)](https://github.com/JP-Reddy/melophiliacs-core)

This is the backend API for **Melophiliacs**, a web application that integrates with Spotify to help users discover their music taste and organize their library.

This API is built with **FastAPI** and uses **Redis** for session and cache management. It handles all communication with the Spotify API, including authentication, data fetching, and processing.

## Features

-   **Spotify Authentication:** Implements OAuth 2.0 Authorization Code Flow to securely connect with a user's Spotify account.
-   **Session Management:** Uses Redis to manage user sessions with secure, HTTP-only cookies.
-   **Data Caching:** Caches API responses from Spotify (liked songs, top artists, etc.) in Redis to ensure fast response times and reduce redundant API calls.
-   **Data Processing:** Aggregates and processes raw data from Spotify to provide required insights, such as user's top artists and albums based on their liked songs.
-   **Decoupled Architecture:** Designed to be a standalone service that can be consumed by any frontend client.

## API Endpoints

A few key endpoints provided by the API:

-   `/api/v1/auth/login`: Initiates the Spotify login flow.
-   `/api/v1/auth/callback`: Handles the OAuth callback from Spotify.
-   `/api/v1/auth/me`: Checks if the current user has a valid session.
-   `/api/v1/auth/logout`: Logs the user out and clears their session.
-   `/api/v1/artists/top`: Returns a user's top artists from their liked songs.
-   `/api/v1/albums/top`: Returns a user's top albums from their liked songs.

## Getting Started

Follow these instructions to get the API server running on your local machine.

### Prerequisites

-   Python 3.8+
-   Redis
-   A Spotify Developer account and an application created on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

### Installation & Setup

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/JP-Reddy/melophiliacs-core.git
    cd melophiliacs-core
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**

    Create a file named `.env` in the root of the project. This is where you'll store your Spotify API credentials and other configuration settings.

    ```dotenv
    # Spotify Configuration
    SPOTIFY_CLIENT_ID="YOUR_SPOTIFY_CLIENT_ID"
    SPOTIFY_CLIENT_SECRET="YOUR_SPOTIFY_CLIENT_SECRET"

    # The full callback URL for your backend API
    REDIRECT_URI="http://127.0.0.1:8000/api/v1/auth/callback"

    # A comma-separated list of frontend URLs that are allowed to use the API
    # Used for both CORS and redirect validation.
    ALLOWED_FINAL_REDIRECT_URIS="http://127.0.0.1:5173"
    CORS_ORIGINS="http://127.0.0.1:5173"

    # Redis Configuration (defaults are for a local instance)
    REDIS_HOST="127.0.0.1"
    REDIS_PORT="6379"
    ```

    **Important:** You must add your `REDIRECT_URI` to the settings for your application in the Spotify Developer Dashboard.

5.  **Run the API server:**
    ```sh
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    The API will now be running at `http://127.0.0.1:8000`.

## Usage Examples

You can interact with the API using any HTTP client, like `curl`.

**Check if you are authenticated (requires a valid session cookie):**

```sh
curl -i --cookie "app_session_token=YOUR_TOKEN" http://127.0.0.1:8000/api/v1/auth/me
```

**Get top artists (requires a valid session cookie):**

```sh
curl --cookie "app_session_token=YOUR_TOKEN" http://127.0.0.1:8000/api/v1/artists/top
```

Expected Response:
```json
[
  [
    "Tame Impala",
    25
  ],
  [
    "Radiohead",
    22
  ]
]
```

## Contributing

Contributions are welcome! If you have a suggestion or find a bug, please open an issue to discuss it.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request
