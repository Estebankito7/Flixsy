# Saved Watchlist — Design Spec

## Overview

A localStorage-backed watchlist that lets users save movies/series from the detail page and browse them on a dedicated "Saved" page. No backend changes needed — the existing `Item` model and TMDB API are untouched.

## Storage

### Schema (per item, stored in `localStorage` under key `flixsy_saved`)
```json
{
  "id": "tmdb_numeric_id",
  "imdb_id": "tt1234567",
  "title": "Breaking Bad",
  "type": "series",
  "primaryImage": "https://image.tmdb.org/t/p/w500/...",
  "startYear": "2008",
  "averageRating": 8.9,
  "savedAt": "2026-05-30T12:00:00Z"
}
```

**Store full detail data on save** so the Saved page can render cards without fetching the API again. Max practical limit: ~50 items before UI pagination is needed.

---

## Feature 1: Detail Page — Save/Unsave Toggle

### Button
Replace the existing "More Info" button in `detail.html` with a save toggle.

- **Same `btn-stadium secondary` style** — preserves visual consistency
- **Bookmark icon** — outline when unsaved, filled when saved
- All other visuals stay: same padding, same font, same hover/active states

### Behaviour (`detail.js`)
1. On `renderMovie()`: check `localStorage` for this movie's ID. If found, mark button as "saved" (filled icon).
2. On click:
   - **Unsaved → Saved:** store movie data (id, imdb_id, title, type, primaryImage, startYear, averageRating, savedAt) to localStorage. Switch icon to filled.
   - **Saved → Unsaved:** remove from localStorage. Switch icon to outline.
3. The save state is independent of the player — no side effects on Play or episode selector.

### Icon SVG
Bookmark outline (unsaved):
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
  <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2v16z"/>
</svg>
```

Bookmark filled (saved):
```html
<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.8">
  <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2v16z"/>
</svg>
```

---

## Feature 2: Saved Page — `/saved/`

### Nav
The existing `<button class="nav-rail-item">Saved</button>` (and its bottom-nav counterpart) becomes:
```html
<a href="{% url 'core:saved' %}" class="nav-rail-item">
```

Active state highlights the Saved nav item when on the saved page.

### View (`views.py`)
New function:
```python
@require_GET
def saved_list(request: HttpRequest) -> HttpResponse:
    return render(request, "core/saved.html")
```

Minimal — just renders the template. All data comes from localStorage on the client.

### URL (`urls.py`)
```python
path("saved/", views.saved_list, name="saved"),
```

### Template (`saved.html`)
Follows the same structure as `home.html`:
- Same `<nav>`, `<topbar>`, `<main>` wrapper
- Same `page-wrapper` layout with nav-rail offset
- Title: "Saved" heading
- **State 1 — Has items:** CSS grid of cards matching the home-page card style. Each card shows poster, title, type badge, year. Click navigates to `{% url 'core:movie-detail-imdb' item.imdb_id %}`.
- **State 2 — Empty:** Centered empty state with a message and a link to browse/search. Uses the same muted colors (`--fg-secondary`, `--muted`).

### JS (`saved.js`)
Inline in `saved.html`:
1. Read `flixsy_saved` from localStorage
2. If empty → show empty state, hide grid
3. If has items → render cards into the grid
4. Each card is an `<a>` linking to the detail page

### CSS
Minimal additions to `detail.css` or a new `saved.css`:
- `.saved-grid` — CSS grid matching the home page card grid
- `.saved-empty` — centered empty state block

---

## Files Changed

| File | Change |
|------|--------|
| `core/templates/core/detail.html` | Replace More Info button with save toggle; update nav link |
| `core/templates/core/home.html` | Update Saved nav from `<button>` to `<a>` |
| `core/templates/core/search_results.html` | Update Saved nav from `<button>` to `<a>` |
| `core/templates/core/saved.html` | **New file** — saved list page |
| `core/static/core/js/detail.js` | Add save/unsave logic in `renderMovie()` |
| `core/static/core/js/saved.js` | **New file** — localStorage reader + card renderer |
| `core/static/core/css/detail.css` | Add `.btn-stadium .icon-only` style if needed |
| `core/static/core/css/saved.css` | **New file** — saved page grid + empty state |
| `core/views.py` | Add `saved_list` view |
| `core/urls.py` | Add `/saved/` route |

---

## Non-Goals (YAGNI)

- No user authentication
- No syncing across devices
- No backend API for saves
- No DB migrations
- No collections/folders/tags
- No search/filter within saved list
