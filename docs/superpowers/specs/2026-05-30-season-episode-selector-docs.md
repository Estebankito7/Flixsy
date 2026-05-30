# Season/Episode Selector — Architecture & Reference

## Overview

The season/episode selector lets users browse and switch between TV series episodes before clicking Play. It is rendered only for series-type content and appears between the media info and the video player on the detail page.

## Data Flow

```
TMDB API (/tv/{id})
  → TMDBClient._normalize_detail(data, is_tv=True)
    → returns dict with `seasons` array
      → movie_api_json() adds isSeries, season, episode
        → detail.js fetch → renderMovie → setupEpisodeSelector
```

### 1. Backend: TMDB Data Enrichment

**File:** `core/tmdb.py:243-249` — `TMDBClient._normalize_detail()`

When `is_tv=True`, the method appends two fields to the result dict:

```python
result["number_of_seasons"] = data.get("number_of_seasons", 0)
result["seasons"] = [
    {"seasonNumber": s["season_number"], "episodeCount": s["episode_count"]}
    for s in data.get("seasons", [])
    if s.get("season_number", 0) > 0  # skip Season 0 (Specials)
]
```

- `number_of_seasons`: integer, total seasons from TMDB
- `seasons`: filtered list excluding specials (season 0), each entry has `seasonNumber` and `episodeCount`

### 2. Backend: API Response Enrichment

**File:** `core/views.py:34-42` — `_resolve_movie()` helper

Extracts the common ID-resolution pattern shared by `movie_detail_imdb` and `movie_api_json`:

- If identifier starts with `tt`, resolves via TMDB's external ID lookup
- Otherwise parses as a numeric TMDB ID, trying movie then TV

**File:** `core/views.py:61-69` — `movie_api_json()`

Adds frontend-facing metadata before returning JSON:

```python
movie["isSeries"] = movie.get("type", "") in ("series", "tv")
movie["season"] = 1  # default
movie["episode"] = 1  # default
```

- `isSeries`: boolean flag that controls selector visibility on the frontend
- `season`/`episode`: initial values (1/1), overridden by selector interaction

### 3. Frontend: Selector Rendering

**File:** `core/static/core/js/detail.js`

#### `setupEpisodeSelector(data)` (line 131)

Entry point called from `renderMovie`. Decision tree:

1. If `episodeSelector` element is missing → return
2. If `data.isSeries` is falsy → hide selector, return
3. If `data.seasons` is empty → hide selector, return
4. Otherwise → clear and show selector, build DOM

Builds two `<select>` elements with labels:

```
[Season] [▼ Season 1] [Episode] [▼ Episode 1]
```

#### `populateEpisodeSelect(selectEl, seasons, seasonNumber)` (line 106)

Given a season number, finds the matching `episodeCount` from the seasons array and populates the episode `<select>` with `<option>` elements (1-based).

#### `syncPlayButton(seasonEl, episodeEl)` (line 119)

Reads the current values from both selects and writes them to the Play button's `data-season` and `data-episode` attributes. Called on every change.

#### `reloadPlayerIfActive()` (line 126)

Conditionally destroys and recreates the player iframe when a player is already active — handles the case where the user switches season/episode while watching.

### 4. Event Handlers

#### Season change (`seasonSelect` `change` event)

```javascript
populateEpisodeSelect(episodeSelect, seasons, parseInt(seasonSelect.value, 10));
syncPlayButton(seasonSelect, episodeSelect);
reloadPlayerIfActive();
```

1. Rebuild episode options for the new season
2. Sync data attributes to Play button
3. If player is active, reload with new season/episode

#### Episode change (`episodeSelect` `change` event)

```javascript
syncPlayButton(seasonSelect, episodeSelect);
reloadPlayerIfActive();
```

1. Sync data attributes to Play button
2. If player is active, reload with new season/episode

### 5. Player Integration

The Play button carries three data attributes that the player builder reads:

| Attribute | Source | Example |
|-----------|--------|---------|
| `data-imdb-id` | movie.id (TMDB numeric or IMDB string) | `12345` or `tt1234567` |
| `data-season` | selector or default (1) | `1` |
| `data-episode` | selector or default (1) | `1` |

`createPlayerElement` uses `isTVType(type)` to determine server URL structure. TV URLs embed season/episode; movie URLs don't.

## CSS Architecture

**File:** `core/static/core/css/detail.css:80-95`

| Class | Role |
|-------|------|
| `.episode-selector` | Flex row container, wraps on small screens |
| `.episode-label` | Uppercase label for each select |
| `.episode-select` | Pill-shaped `<select>` matching the design system |

Uses design tokens from `base.css`:
- `--gap-sm`, `--gap-xs` for spacing
- `--radius-pill` for border radius
- `--fs-small` for type scale
- `--fg`, `--fg-secondary`, `--border`, `--surface`, `--accent` for colors
- `--font-body` for typography

## Template Integration

**File:** `core/templates/core/detail.html:99`

```html
<div id="episodeSelector" class="episode-selector" hidden></div>
```

Placed inside `#mediaColumn`, before the player container. Initially hidden; visibility is controlled by JavaScript after the API response is parsed.

## Refactoring Summary (2026-05-30)

### detail.js
- **Extracted** `SERVERS` constant — URL definitions centralized, not inline
- **Extracted** `getPlayButton()` helper — repeated DOM queries replaced with single getter
- **Extracted** `isTVType()` — type checking logic reusable and testable
- **Extracted** `populateEpisodeSelect()` — no longer a closure inside `setupEpisodeSelector`
- **Extracted** `syncPlayButton()` and `reloadPlayerIfActive()` — event handlers become one-liners
- **Removed** module-level mutable `seasonSelect`/`episodeSelect` vars — scoped inside `setupEpisodeSelector`

### views.py
- **Extracted** `_resolve_movie()` — eliminates 12 lines of duplicated ID-resolution logic between `movie_detail_imdb` and `movie_api_json`
