from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.generic import ListView

from .models import Item
from .tmdb import TMDBClient

tmdb = TMDBClient()


class HomeView(ListView):
    model = Item
    template_name = "core/home.html"
    context_object_name = "items"

    def get_context_data(self, **kwargs) -> dict:
        ctx = super().get_context_data(**kwargs)
        ctx["peliculas"] = tmdb.fetch_trending()
        return ctx


@require_GET
def trending_api(request: HttpRequest) -> JsonResponse:
    media_type = request.GET.get("media_type", "movie")
    time_window = request.GET.get("time_window", "day")
    page = int(request.GET.get("page", "1"))
    results = tmdb.fetch_trending(media_type, time_window, page)
    return JsonResponse({"results": results})


def _resolve_movie(identifier: str) -> dict | None:
    if identifier.startswith("tt"):
        return tmdb.find_by_external_id(identifier)
    try:
        pk = int(identifier)
        movie = tmdb.fetch_movie_by_id(pk)
        return movie if movie else tmdb.fetch_tv_by_id(pk)
    except ValueError:
        return None


def movie_detail(request: HttpRequest, pk: int) -> HttpResponse:
    movie = tmdb.fetch_movie_by_id(pk)
    if not movie:
        movie = tmdb.fetch_tv_by_id(pk)
    if not movie:
        raise Http404("Movie not found")
    return render(request, "core/detail.html", {"movie": movie})


def movie_detail_imdb(request: HttpRequest, imdb_id: str) -> HttpResponse:
    movie = _resolve_movie(imdb_id)
    if not movie:
        raise Http404("Movie not found")
    return render(request, "core/detail.html", {"movie": movie})


@require_GET
def movie_api_json(request: HttpRequest, imdb_id: str) -> JsonResponse:
    movie = _resolve_movie(imdb_id)
    if not movie:
        return JsonResponse({"error": "Movie not found"}, status=404)
    movie["isSeries"] = movie.get("type", "") in ("series", "tv")
    movie["season"] = 1
    movie["episode"] = 1
    return JsonResponse(movie)


@require_GET
def search_results(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    results = tmdb.search_movies(q) if q else []
    return render(request, "core/search_results.html", {
        "query": q,
        "results": results,
    })


@require_GET
def search_api(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q", "").strip()
    results = tmdb.search_movies(q) if q else []
    return JsonResponse({"results": results, "query": q})


@require_GET
def saved_list(request: HttpRequest) -> HttpResponse:
    """Renders the saved watchlist page (data loaded client-side from localStorage)."""
    return render(request, "core/saved.html")
