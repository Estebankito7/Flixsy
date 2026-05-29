from __future__ import annotations

from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.generic import ListView

from .models import Item
from .services import IMDBClient, IMDBConfig

CACHE_KEY = "peliculas_cache"

client = IMDBClient()


def _get_cached_movies() -> list[dict]:
    movies = cache.get(CACHE_KEY)
    if movies is not None:
        return movies
    try:
        movies = client.fetch_movies()
    except Exception:
        movies = []
    cache.set(CACHE_KEY, movies, 900)
    return movies


class HomeView(ListView):
    model = Item
    template_name = "core/home.html"
    context_object_name = "items"

    def get_context_data(self, **kwargs) -> dict:
        ctx = super().get_context_data(**kwargs)
        ctx["peliculas"] = _get_cached_movies()
        ctx["rapidapi_host"] = client.config.host
        ctx["rapidapi_key"] = client.config.key
        return ctx


def movie_detail(request: HttpRequest, pk: int) -> HttpResponse:
    peliculas = _get_cached_movies()
    movie = next((m for m in peliculas if m["pk"] == pk), None)
    if not movie:
        raise Http404("Movie not found")
    return render(request, "core/detail.html", {"movie": movie})


def _lookup_movie(imdb_id: str) -> dict | None:
    cached = cache.get(CACHE_KEY)
    movie = next(
        (m for m in cached if m["id"] == imdb_id), None
    ) if cached else None
    return movie or client.fetch_movie_by_id(imdb_id)


def _enrich_series(movie: dict) -> tuple[bool, int | None, int | None]:
    is_series = any(
        tag in (movie.get("type") or "").lower() for tag in ("tv", "series")
    )
    return is_series, 1 if is_series else None, 1 if is_series else None


def movie_detail_imdb(request: HttpRequest, imdb_id: str) -> HttpResponse:
    if not imdb_id.startswith("tt"):
        imdb_id = "tt" + imdb_id

    movie = _lookup_movie(imdb_id)
    if not movie:
        raise Http404("Movie not found")

    _, season, episode = _enrich_series(movie)

    return render(request, "core/detail.html", {
        "movie": movie,
        "season": season,
        "episode": episode,
    })


@require_GET
def movie_api_json(request: HttpRequest, imdb_id: str) -> JsonResponse:
    if not imdb_id.startswith("tt"):
        imdb_id = "tt" + imdb_id

    movie = _lookup_movie(imdb_id)
    if not movie:
        return JsonResponse({"error": "Movie not found"}, status=404)

    is_series, season, episode = _enrich_series(movie)
    movie["isSeries"] = is_series
    movie["season"] = season
    movie["episode"] = episode
    movie["title"] = movie.get("primaryTitle", movie.get("title", ""))

    return JsonResponse(movie)


@require_GET
def search_results(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    results = client.search(q) if q else []
    return render(request, "core/search_results.html", {
        "query": q,
        "results": results,
    })


@require_GET
def search_api(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q", "").strip()
    results = client.search(q) if q else []
    return JsonResponse({"results": results, "query": q})
