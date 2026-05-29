from __future__ import annotations

import os

import requests
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.generic import ListView

from .models import Item

CACHE_TIMEOUT = 900  # 15 minutes
CACHE_KEY = "peliculas_cache"

IMDB_API_BASE = "https://imdb236.p.rapidapi.com/api/imdb"

RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

if not RAPIDAPI_HOST or not RAPIDAPI_KEY:
    raise RuntimeError(
        "Missing RAPIDAPI_HOST or RAPIDAPI_KEY in environment. "
        "Create a .env file at the project root with:\n"
        "  RAPIDAPI_HOST=imdb236.p.rapidapi.com\n"
        "  RAPIDAPI_KEY=your_key_here"
    )

HEADERS = {
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY,
}


def _raise_for_auth(response: requests.Response) -> None:
    """Raise a clear error on 401/403 so the developer knows credentials are wrong."""
    if response.status_code in (401, 403):
        raise PermissionError(
            f"RapidAPI returned {response.status_code}. "
            "Check that RAPIDAPI_KEY in your .env file is valid and active."
        )


def _fetch_movies() -> list[dict]:
    response = requests.get(
        f"{IMDB_API_BASE}/cast/nm0000190/titles",
        headers=HEADERS,
        timeout=10,
    )
    _raise_for_auth(response)
    response.raise_for_status()

    raw = response.json()
    return [
        {
            **m,
            "title": m["primaryTitle"],
            "pk": int(m["id"][2:])
            if m["id"][:2] == "tt" and m["id"][2:].isdigit()
            else i,
        }
        for i, m in enumerate(raw)
    ]


def _fetch_movie_by_id(imdb_id: str) -> dict | None:
    """Fetch a single movie from the IMDB API by ID (with or without 'tt' prefix).

    Raises PermissionError on 401/403 so auth failures are never silent.
    """
    candidates = (imdb_id, imdb_id.replace("tt", "", 1))
    for candidate in candidates:
        try:
            r = requests.get(
                f"{IMDB_API_BASE}/{candidate}",
                headers=HEADERS,
                timeout=10,
            )
            _raise_for_auth(r)
            if r.ok:
                movie = r.json()
                movie["title"] = movie.get("primaryTitle", "")
                return movie
        except requests.RequestException:
            continue
    return None


def _get_cached_movies() -> list[dict]:
    movies = cache.get(CACHE_KEY)
    if movies is not None:
        return movies
    try:
        movies = _fetch_movies()
    except Exception:
        movies = []
    cache.set(CACHE_KEY, movies, CACHE_TIMEOUT)
    return movies


class HomeView(ListView):
    model = Item
    template_name = "core/home.html"
    context_object_name = "items"

    def get_context_data(self, **kwargs) -> dict:
        ctx = super().get_context_data(**kwargs)
        ctx["peliculas"] = _get_cached_movies()
        ctx["rapidapi_host"] = RAPIDAPI_HOST
        ctx["rapidapi_key"] = RAPIDAPI_KEY
        return ctx


def movie_detail(request: HttpRequest, pk: int) -> HttpResponse:
    peliculas = _get_cached_movies()
    movie = next((m for m in peliculas if m["pk"] == pk), None)
    if not movie:
        raise Http404("Movie not found")
    return render(request, "core/detail.html", {"movie": movie})


def movie_detail_imdb(request: HttpRequest, imdb_id: str) -> HttpResponse:
    if not imdb_id.startswith("tt"):
        imdb_id = "tt" + imdb_id

    # Try cache first
    peliculas = cache.get(CACHE_KEY)
    movie = next(
        (m for m in peliculas if m["id"] == imdb_id), None
    ) if peliculas else None

    # Fallback: real-time API fetch
    if not movie:
        movie = _fetch_movie_by_id(imdb_id)

    if not movie:
        raise Http404("Movie not found")

    is_series = any(
        tag in (movie.get("type") or "").lower() for tag in ("tv", "series")
    )

    return render(request, "core/detail.html", {
        "movie": movie,
        "season": 1 if is_series else None,
        "episode": 1 if is_series else None,
    })


@require_GET
def movie_api_json(request: HttpRequest, imdb_id: str) -> JsonResponse:
    """JSON endpoint for movie detail data, consumed by detail.js."""
    if not imdb_id.startswith("tt"):
        imdb_id = "tt" + imdb_id

    # Try cache first
    peliculas = cache.get(CACHE_KEY)
    movie = next(
        (m for m in peliculas if m["id"] == imdb_id), None
    ) if peliculas else None

    # Fallback: real-time API fetch
    if not movie:
        movie = _fetch_movie_by_id(imdb_id)

    if not movie:
        return JsonResponse({"error": "Movie not found"}, status=404)

    is_series = any(
        tag in (movie.get("type") or "").lower() for tag in ("tv", "series")
    )

    movie["isSeries"] = is_series
    movie["season"] = 1 if is_series else None
    movie["episode"] = 1 if is_series else None
    movie["title"] = movie.get("primaryTitle", movie.get("title", ""))

    return JsonResponse(movie)


SEARCH_CATALOG_CACHE_KEY = "search_catalog"


def _get_search_catalog() -> list[dict]:
    cached = cache.get(SEARCH_CATALOG_CACHE_KEY)
    if cached is not None:
        return cached

    catalog: list[dict] = []
    urls = [
        f"{IMDB_API_BASE}/most-popular-movies",
        f"{IMDB_API_BASE}/most-popular-tv",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            _raise_for_auth(r)
            if r.ok:
                raw = r.json()
                items = raw if isinstance(raw, list) else raw.get("results", raw.get("rows", []))
                catalog.extend(items)
        except requests.RequestException:
            pass

    seen: set[str] = set()
    unique: list[dict] = []
    for item in catalog:
        item_id = item.get("id", "")
        if item_id and item_id not in seen:
            seen.add(item_id)
            item["title"] = item.get("primaryTitle", item.get("title", ""))
            unique.append(item)

    cache.set(SEARCH_CATALOG_CACHE_KEY, unique, CACHE_TIMEOUT)
    return unique


def _search_rapidapi(q: str) -> list[dict]:
    ql = q.lower()
    catalog = _get_search_catalog()

    results = [
        item
        for item in catalog
        if ql in (item.get("title") or "").lower()
    ]

    try:
        r = requests.get(
            f"{IMDB_API_BASE}/search?query={requests.utils.quote(q)}",
            headers=HEADERS,
            timeout=10,
        )
        _raise_for_auth(r)
        if r.ok:
            raw = r.json()
            extras = raw if isinstance(raw, list) else raw.get("results", [])
            seen_ids = {item.get("id", "") for item in results}
            for item in extras:
                item["title"] = item.get("primaryTitle", item.get("title", ""))
                if (
                    item.get("id", "") not in seen_ids
                    and ql in (item["title"] or "").lower()
                ):
                    results.append(item)
    except requests.RequestException:
        pass

    results.sort(key=lambda x: x.get("averageRating") or 0, reverse=True)

    return [
        {
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "primaryImage": item.get("primaryImage", ""),
            "averageRating": item.get("averageRating"),
            "genres": item.get("genres", []),
            "startYear": item.get("startYear"),
            "description": item.get("description", ""),
        }
        for item in results
    ][:50]


@require_GET
def search_results(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    results = _search_rapidapi(q) if q else []
    return render(request, "core/search_results.html", {
        "query": q,
        "results": results,
    })


@require_GET
def search_api(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q", "").strip()
    results = _search_rapidapi(q) if q else []
    return JsonResponse({"results": results, "query": q})
