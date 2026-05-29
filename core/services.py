from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests
from django.core.cache import cache

CACHE_TIMEOUT = 900

RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

if not RAPIDAPI_HOST or not RAPIDAPI_KEY:
    raise RuntimeError(
        "Missing RAPIDAPI_HOST or RAPIDAPI_KEY in environment. "
        "Create a .env file at the project root with:\n"
        "  RAPIDAPI_HOST=imdb236.p.rapidapi.com\n"
        "  RAPIDAPI_KEY=your_key_here"
    )


@dataclass
class IMDBConfig:
    base_url: str = "https://imdb236.p.rapidapi.com/api/imdb"
    host: str = RAPIDAPI_HOST
    key: str = RAPIDAPI_KEY
    timeout: int = 10

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-rapidapi-host": self.host,
            "x-rapidapi-key": self.key,
        }


class IMDBError(Exception):
    pass


class AuthError(IMDBError):
    pass


class NotFoundError(IMDBError):
    pass


class IMDBClient:
    def __init__(self, config: IMDBConfig | None = None) -> None:
        self.config = config or IMDBConfig()
        self._session = requests.Session()
        self._session.headers.update(self.config.headers)

    def _raise_for_auth(self, response: requests.Response) -> None:
        if response.status_code in (401, 403):
            raise AuthError(
                f"RapidAPI returned {response.status_code}. "
                "Check that RAPIDAPI_KEY in your .env file is valid and active."
            )

    def _get(self, path: str) -> requests.Response:
        url = f"{self.config.base_url}/{path.lstrip('/')}"
        response = self._session.get(url, timeout=self.config.timeout)
        self._raise_for_auth(response)
        response.raise_for_status()
        return response

    def _normalize_title(self, item: dict) -> dict:
        item["title"] = item.get("primaryTitle", item.get("title", ""))
        return item

    def fetch_movies(self) -> list[dict]:
        response = self._get("cast/nm0000190/titles")
        raw = response.json()
        return [
            {
                **self._normalize_title(m),
                "pk": int(m["id"][2:])
                if m["id"][:2] == "tt" and m["id"][2:].isdigit()
                else i,
            }
            for i, m in enumerate(raw)
        ]

    def fetch_movie_by_id(self, imdb_id: str) -> dict | None:
        candidates = (imdb_id, imdb_id.replace("tt", "", 1))
        for candidate in candidates:
            try:
                r = self._session.get(
                    f"{self.config.base_url}/{candidate}",
                    timeout=self.config.timeout,
                )
                self._raise_for_auth(r)
                if r.ok:
                    movie = r.json()
                    return self._normalize_title(movie)
            except requests.RequestException:
                continue
        return None

    def fetch_popular(self, media_type: str = "movies") -> list[dict]:
        endpoint = "most-popular-movies" if media_type == "movies" else "most-popular-tv"
        try:
            r = self._get(endpoint)
            raw = r.json()
            items = raw if isinstance(raw, list) else raw.get("results", raw.get("rows", []))
            return [self._normalize_title(item) for item in items]
        except requests.RequestException:
            return []

    def search(self, query: str) -> list[dict]:
        ql = query.lower()
        catalog = _get_search_catalog(self)

        results = [
            item for item in catalog
            if ql in (item.get("title") or "").lower()
        ]

        try:
            r = self._session.get(
                f"{self.config.base_url}/search?query={requests.utils.quote(query)}",
                timeout=self.config.timeout,
            )
            self._raise_for_auth(r)
            if r.ok:
                raw = r.json()
                extras = raw if isinstance(raw, list) else raw.get("results", [])
                seen_ids = {item.get("id", "") for item in results}
                for item in extras:
                    self._normalize_title(item)
                    if item.get("id", "") not in seen_ids and ql in (item["title"] or "").lower():
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


def _get_search_catalog(client: IMDBClient) -> list[dict]:
    key = "search_catalog"
    cached = cache.get(key)
    if cached is not None:
        return cached

    catalog: list[dict] = []
    for media_type in ("movies", "tv"):
        catalog.extend(client.fetch_popular(media_type))

    seen: set[str] = set()
    unique: list[dict] = []
    for item in catalog:
        item_id = item.get("id", "")
        if item_id and item_id not in seen:
            seen.add(item_id)
            unique.append(item)

    cache.set(key, unique, CACHE_TIMEOUT)
    return unique
