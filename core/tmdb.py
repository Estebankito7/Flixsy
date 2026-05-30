from __future__ import annotations

import os
import re
from dataclasses import dataclass

import requests

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

if not TMDB_API_KEY:
    raise RuntimeError(
        "Missing TMDB_API_KEY in environment. "
        "Create a .env file at the project root with:\n"
        "  TMDB_API_KEY=your_tmdb_api_key_here"
    )


@dataclass
class TMDBConfig:
    base_url: str = "https://api.themoviedb.org/3"
    api_key: str = TMDB_API_KEY
    language: str = "es-ES"
    timeout: int = 10


class TMDBError(Exception):
    pass


class AuthError(TMDBError):
    pass


class NotFoundError(TMDBError):
    pass


POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"


class TMDBClient:
    """Cliente para la API de TMDB v3.

    Reemplaza al antiguo IMDBClient (RapidAPI). Maneja la autenticación
    mediante la clave TMDB_API_KEY del entorno y normaliza las respuestas
    de TMDB al formato que esperan las vistas y plantillas de Flixsy.

    Flujo de integración:
        views.py → instancia global ``tmdb = TMDBClient()`` y la usa en
        cada vista. Los datos normalizados se pasan al contexto de las
        plantillas como diccionarios con claves en español (``titulo``,
        ``imagen``, ``calificacion``) para búsqueda y en inglés
        (``title``, ``primaryImage``, ``averageRating``) para el home
        (compatibilidad con home.js).

    Mapeo de datos TMDB → Flixsy:
        - ``id`` → id numérico de TMDB (se reemplaza por ``imdb_id`` en
          trending para garantizar unicidad global entre movies y TV).
        - ``title``/``name`` → ``title`` (y ``titulo`` en búsqueda).
        - ``poster_path`` → ``primaryImage``/``imagen`` (URL completa).
        - ``vote_average`` → ``averageRating``/``calificacion``.
        - ``release_date``/``first_air_date`` → ``startYear`` y ``releaseDate``.
        - ``overview`` → ``description``/``resumen``.
        - ``credits.crew[].job`` → ``directors`` y ``writers``.
        - ``genres[].name`` → ``genres``.
        - ``imdb_id`` / ``external_ids.imdb_id`` → ``imdb_id``.
    """

    def __init__(self, config: TMDBConfig | None = None) -> None:
        self.config = config or TMDBConfig()
        self._session = requests.Session()

    def _raise_for_auth(self, response: requests.Response) -> None:
        if response.status_code in (401, 403):
            raise AuthError(
                f"TMDB returned {response.status_code}. "
                "Check that TMDB_API_KEY in your .env file is valid."
            )

    def _get(self, path: str, params: dict[str, str] | None = None) -> requests.Response:
        url = f"{self.config.base_url}/{path.lstrip('/')}"
        query_params = {"api_key": self.config.api_key, "language": self.config.language}
        if params:
            query_params.update(params)
        response = self._session.get(url, params=query_params, timeout=self.config.timeout)
        self._raise_for_auth(response)
        response.raise_for_status()
        return response

    def _normalize_movie(self, item: dict) -> dict:
        return {
            "id": item.get("id"),
            "titulo": item.get("title", ""),
            "imagen": (
                f"{POSTER_BASE_URL}{item['poster_path']}"
                if item.get("poster_path") else None
            ),
            "calificacion": item.get("vote_average"),
            "año": (
                item["release_date"][:4]
                if item.get("release_date") else None
            ),
            "generos": [],
            "resumen": item.get("overview", ""),
        }

    def _clean_query(self, query: str | None) -> str:
        if not query:
            return ""
        cleaned = re.sub(r"\s+", " ", query.strip())
        return cleaned

    def _normalize_trending(self, item: dict) -> dict:
        return {
            "id": item.get("id"),
            "media_type": item.get("media_type", "movie"),
            "primaryImage": (
                f"{POSTER_BASE_URL}{item['poster_path']}"
                if item.get("poster_path") else None
            ),
            "title": item.get("title", ""),
            "averageRating": item.get("vote_average"),
            "startYear": (
                item["release_date"][:4]
                if item.get("release_date") else None
            ),
            "genres": [],
            "description": item.get("overview", ""),
        }

    def _enrich_with_imdb_ids(self, items: list[dict]) -> list[dict]:
        import concurrent.futures

        def _fetch(item):
            tmdb_id = item.get("id")
            media_type = item.get("media_type")
            if not tmdb_id or media_type == "person":
                return item
            try:
                if media_type == "tv":
                    resp = self._get(f"tv/{tmdb_id}", {"append_to_response": "external_ids"})
                    data = resp.json()
                    imdb_id = (data.get("external_ids") or {}).get("imdb_id")
                else:
                    resp = self._get(f"movie/{tmdb_id}")
                    data = resp.json()
                    imdb_id = data.get("imdb_id")
                if imdb_id:
                    item["id"] = imdb_id
                    item["imdb_id"] = imdb_id
            except requests.RequestException:
                pass
            return item

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            return list(pool.map(_fetch, items))

    def fetch_trending(self, media_type: str = "movie", time_window: str = "day", page: int = 1, enrich: bool = True) -> list[dict]:
        try:
            response = self._get(f"trending/{media_type}/{time_window}", {"page": str(page)})
            data = response.json()
            items = [self._normalize_trending(item) for item in data.get("results", [])]
            if enrich:
                items = self._enrich_with_imdb_ids(items)
            return items
        except requests.RequestException:
            return []

    def fetch_movie_by_id(self, movie_id: int) -> dict | None:
        try:
            response = self._get(f"movie/{movie_id}", {"append_to_response": "credits"})
            data = response.json()
            return self._normalize_detail(data)
        except requests.RequestException:
            return None

    def fetch_tv_by_id(self, tv_id: int) -> dict | None:
        try:
            response = self._get(f"tv/{tv_id}", {"append_to_response": "credits,external_ids"})
            data = response.json()
            return self._normalize_detail(data, is_tv=True)
        except requests.RequestException:
            return None

    def find_by_external_id(self, external_id: str) -> dict | None:
        if not external_id.startswith("tt"):
            return None
        try:
            response = self._get(f"find/{external_id}", {"external_source": "imdb_id"})
            data = response.json()
            movie_results = data.get("movie_results", [])
            if movie_results:
                return self.fetch_movie_by_id(movie_results[0]["id"])
            tv_results = data.get("tv_results", [])
            if tv_results:
                return self.fetch_tv_by_id(tv_results[0]["id"])
            return None
        except requests.RequestException:
            return None

    def _normalize_detail(self, data: dict, is_tv: bool = False) -> dict:
        genres = [g["name"] for g in data.get("genres", [])]
        directors = []
        writers = []
        for person in (data.get("credits") or {}).get("crew", []):
            job = (person.get("job") or "").lower()
            if job == "director":
                directors.append({"fullName": person.get("name", "")})
            elif job in ("writer", "screenplay", "story"):
                writers.append({"fullName": person.get("name", "")})
        if is_tv:
            title = data.get("name", "")
            date_key = "first_air_date"
            media_type = "series"
            imdb_id = (data.get("external_ids") or {}).get("imdb_id")
        else:
            title = data.get("title", "")
            date_key = "release_date"
            media_type = "movie"
            imdb_id = data.get("imdb_id")
        release_date = data.get(date_key, "")
        result = {
            "id": data.get("id"),
            "primaryImage": (
                f"{POSTER_BASE_URL}{data['poster_path']}"
                if data.get("poster_path") else None
            ),
            "title": title,
            "averageRating": data.get("vote_average"),
            "startYear": (
                release_date[:4]
                if release_date else None
            ),
            "genres": genres,
            "description": data.get("overview", ""),
            "directors": directors,
            "writers": writers,
            "releaseDate": release_date,
            "type": media_type,
            "imdb_id": imdb_id,
        }
        if is_tv:
            result["number_of_seasons"] = data.get("number_of_seasons", 0)
            result["seasons"] = [
                {"seasonNumber": s["season_number"], "episodeCount": s["episode_count"]}
                for s in data.get("seasons", [])
                if s.get("season_number", 0) > 0
            ]
        return result

    def search_movies(self, query: str, page: int = 1) -> list[dict]:
        cleaned = self._clean_query(query)
        if not cleaned:
            return []
        try:
            response = self._get("search/movie", {"query": cleaned, "page": str(page)})
            data = response.json()
            results = data.get("results", [])
            if not results:
                return []
            return [self._normalize_movie(item) for item in results]
        except requests.RequestException:
            return []
