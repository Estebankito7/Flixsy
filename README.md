# Flixsy

Movie & TV discovery platform with real-time data from TMDB and multi-server video playback.

## Tech Stack

- **Backend:** Django 6.0, Python 3.14
- **API Client:** `requests` with session reuse & error handling
- **External API:** [TMDB v3](https://developer.themoviedb.org/)
- **Frontend:** Vanilla JS, CSS custom properties, responsive layout

## Setup

```bash
# Clone & enter
cd flixsy

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install django requests python-dotenv

# Environment variables
cp .env.example .env       # then fill in your TMDB API key

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TMDB_API_KEY` | Yes | Your TMDB API v3 key |

## Architecture

### Service Layer (`core/tmdb.py`)

The `TMDBClient` class encapsulates all TMDB API communication:

- **`fetch_trending()`** — Trending movies/TV with IMDB ID enrichment
- **`fetch_by_genre()`** — Discover movies/TV by genre via `/discover`
- **`fetch_movie_by_id()`** — Single movie detail with credits
- **`fetch_tv_by_id()`** — Single TV show detail with seasons & credits
- **`find_by_external_id()`** — Resolve IMDB ID to TMDB data
- **`search_all()`** — Full-text search across movies and TV

Uses `requests.Session` for connection reuse, genre ID→name caching, and concurrent IMDB ID enrichment via `ThreadPoolExecutor`.

### Views (`core/views.py`)

Thin view layer delegating to `TMDBClient`:

| Route | View | Description |
|---|---|---|
| `/` | `HomeView` | Landing page with hero carousel + trending rows |
| `/api/trending/` | `trending_api` | JSON trending (supports `?genre=` for discover) |
| `/detail/<imdb_id>/` | `movie_detail_imdb` | Detail page with poster, meta, sidebar |
| `/api/detail/<imdb_id>/` | `movie_api_json` | JSON endpoint for detail.js |
| `/search/` | `search_results` | Search results page |
| `/search/api/` | `search_api` | Search JSON endpoint |
| `/saved/` | `saved_list` | Saved watchlist page (client-side localStorage) |

### Frontend — Home (`core/static/core/js/home.js`)

- **Hero carousel** — Auto-rotating slideshow with dots navigation
- **Trending rows** — Movies and TV series with horizontal scroll arrows
- **Genre filtering** — Chip-based filter using TMDB Discover API (movies + TV)

### Frontend — Detail (`core/static/core/js/detail.js`)

- **Video player** — iframe-based player with server selector bar
- **Streaming servers:** MoviesApi, VidSrc, VidLink, VidFast
- **Season/Episode selector** — Dynamic dropdown for TV series
- **Save/Unsave** — localStorage watchlist toggle

### Templates

| Template | Description |
|---|---|
| `core/home.html` | Landing with hero carousel, genre chips, movie/TV rows |
| `core/detail.html` | Detail page with poster, meta, sidebar, video player |
| `core/search_results.html` | Search query results grid |
| `core/saved.html` | Saved watchlist from localStorage |

## Project Structure

```
Flixsy/
├── config/                 # Django project configuration
│   └── settings.py
├── core/                   # Main application
│   ├── tmdb.py             # TMDBClient API service
│   ├── views.py            # All view functions/classes
│   ├── models.py           # Item model
│   ├── urls.py             # App URL routing
│   ├── static/core/
│   │   ├── css/
│   │   │   ├── base.css
│   │   │   └── detail.css
│   │   ├── js/
│   │   │   ├── home.js
│   │   │   ├── detail.js
│   │   │   └── saved.js
│   │   └── style.css
│   └── templates/core/
│       ├── home.html
│       ├── detail.html
│       ├── search_results.html
│       └── saved.html
├── manage.py
├── pyproject.toml
├── .env                    # (not tracked — add your key)
└── .gitignore
```
