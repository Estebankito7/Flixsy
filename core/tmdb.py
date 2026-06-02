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
        self._genre_cache: dict[str, dict[int, str]] | None = None

    def _load_genre_map(self, media_type: str = "movie") -> dict[int, str]:
        if self._genre_cache is None:
            self._genre_cache = {}
        if media_type in self._genre_cache:
            return self._genre_cache[media_type]
        mapping: dict[int, str] = {}
        try:
            resp = self._get(f"genre/{media_type}/list", {"language": "en"})
            for g in resp.json().get("genres", []):
                mapping[g["id"]] = g["name"]
        except requests.RequestException:
            pass
        self._genre_cache[media_type] = mapping
        return mapping

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
        genre_ids = item.get("genre_ids", [])
        mtype = item.get("media_type", "movie")
        genre_map = self._load_genre_map(mtype)
        return {
            "id": item.get("id"),
            "media_type": mtype,
            "primaryImage": (
                f"{POSTER_BASE_URL}{item['poster_path']}"
                if item.get("poster_path") else None
            ),
            "title": item.get("title") or item.get("name") or "",
            "averageRating": item.get("vote_average"),
            "startYear": (
                item["release_date"][:4]
                if item.get("release_date") else None
            ),
            "genres": [genre_map.get(gid) for gid in genre_ids if genre_map.get(gid)],
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

    def fetch_by_genre(self, media_type: str, genre_name: str, page: int = 1, enrich: bool = True) -> list[dict]:
        tmdb_type = "movie" if media_type == "movie" else "tv"
        genre_map = self._load_genre_map(tmdb_type)
        genre_aliases = {
            "sci-fi": "Science Fiction" if tmdb_type == "movie" else "Sci-Fi & Fantasy",
            "action": "Action" if tmdb_type == "movie" else "Action & Adventure",
            "thriller": "Thriller" if tmdb_type == "movie" else "Thriller",
        }
        search_name = genre_aliases.get(genre_name.lower(), genre_name)
        genre_id = None
        for gid, gname in genre_map.items():
            if gname.lower() == search_name.lower():
                genre_id = gid
                break
        if not genre_id:
            return []
        try:
            response = self._get(f"discover/{tmdb_type}", {
                "with_genres": str(genre_id),
                "sort_by": "popularity.desc",
                "page": str(page),
            })
            data = response.json()
            items = []
            for item in data.get("results", []):
                item["media_type"] = tmdb_type
                items.append(self._normalize_trending(item))
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

    def _normalize_search_result(self, item: dict, media_type: str = "movie") -> dict:
        return {
            "id": item.get("id"),
            "titulo": item.get("title") or item.get("name") or "",
            "imagen": (
                f"{POSTER_BASE_URL}{item['poster_path']}"
                if item.get("poster_path") else None
            ),
            "calificacion": item.get("vote_average"),
            "año": (
                (item.get("release_date") or item.get("first_air_date") or "")[:4]
                if (item.get("release_date") or item.get("first_air_date")) else None
            ),
            "generos": [],
            "resumen": item.get("overview", ""),
            "media_type": media_type,
        }

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
            return [self._normalize_search_result(item, "movie") for item in results]
        except requests.RequestException:
            return []

    def search_tv(self, query: str, page: int = 1) -> list[dict]:
        cleaned = self._clean_query(query)
        if not cleaned:
            return []
        try:
            response = self._get("search/tv", {"query": cleaned, "page": str(page)})
            data = response.json()
            results = data.get("results", [])
            if not results:
                return []
            return [self._normalize_search_result(item, "tv") for item in results]
        except requests.RequestException:
            return []

    def search_all(self, query: str, page: int = 1) -> list[dict]:
        import concurrent.futures
        cleaned = self._clean_query(query)
        if not cleaned:
            return []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            movie_future = pool.submit(self.search_movies, cleaned, page)
            tv_future = pool.submit(self.search_tv, cleaned, page)
            movies = movie_future.result()
            tv = tv_future.result()
        merged = (movies or []) + (tv or [])
        merged.sort(key=lambda x: x.get("calificacion", 0) or 0, reverse=True)
        return merged
