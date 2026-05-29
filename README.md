# Flixsy

Movie discovery platform with real-time data from RapidAPI IMDB.

## Tech Stack

- **Backend:** Django 6.0, Python 3.14
- **API Client:** `requests` with session reuse & error handling
- **Caching:** Django cache framework (15 min TTL)
- **External API:** [RapidAPI IMDB236](https://rapidapi.com/Glavier/api/imdb236)
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
cp .env.example .env       # then fill in your RapidAPI key

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `RAPIDAPI_HOST` | Yes | IMDB API host (e.g. `imdb236.p.rapidapi.com`) |
| `RAPIDAPI_KEY` | Yes | Your RapidAPI subscription key |

## Architecture

### Service Layer (`core/services.py`)

The `IMDBClient` class encapsulates all RapidAPI communication:

- **`fetch_movies()`** — Gets titles for a specific cast member
- **`fetch_movie_by_id(imdb_id)`** — Single movie lookup with fallback
- **`fetch_popular(media_type)`** — Most-popular movies or TV
- **`search(query)`** — Full-text search against cached catalog + API

Uses `requests.Session` for connection reuse and has built-in auth error handling.

### Views (`core/views.py`)

Thin view layer that delegates to `IMDBClient` and Django cache:

| Route | View | Description |
|---|---|---|
| `/` | `HomeView` | Landing page with hero carousel + media rows |
| `/item/<pk>/` | `movie_detail` | Detail by internal primary key |
| `/detail/<imdb_id>/` | `movie_detail_imdb` | Detail by IMDB ID |
| `/api/detail/<imdb_id>/` | `movie_api_json` | JSON endpoint for detail.js |
| `/search/` | `search_results` | Search results page |
| `/search/api/` | `search_api` | Search JSON endpoint |

### Caching

- **Movies list** — 15 min TTL, key `peliculas_cache`
- **Search catalog** — 15 min TTL, key `search_catalog`
- Falls back to empty list on API failure

### Templates

| Template | Description |
|---|---|
| `core/home.html` | Landing with hero carousel, genre chips, movie/TV rows |
| `core/detail.html` | Movie/show detail with poster, meta, sidebar, video player |
| `core/search_results.html` | Search query results grid |

### Static Assets

| File | Description |
|---|---|
| `core/style.css` | Global styles, layout, navigation, hero, cards |
| `core/css/detail.css` | Detail page styles (backdrop, poster, player) |
| `core/js/detail.js` | Client-side: video player, server switching, API enrichment |

## Project Structure

```
Flixsy/
├── config/                 # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── core/                   # Main application
│   ├── services.py         # IMDBClient API service
│   ├── views.py            # All view functions/classes
│   ├── models.py           # Item model
│   ├── urls.py             # App URL routing
│   ├── admin.py            # Admin registration
│   ├── migrations/
│   ├── static/core/
│   │   ├── style.css
│   │   ├── css/detail.css
│   │   └── js/detail.js
│   └── templates/core/
│       ├── home.html
│       ├── detail.html
│       └── search_results.html
├── manage.py
├── pyproject.toml
├── .env                    # (not tracked — add your keys)
└── .gitignore
```
