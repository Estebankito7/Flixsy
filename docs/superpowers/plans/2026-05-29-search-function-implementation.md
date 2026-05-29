# Búsqueda Híbrida — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hybrid search (client-side fuzzy + server-side RapidAPI) to the existing Flixsy search bar.

**Architecture:** Client-side fuse.js filtering on cached data for instant results, plus a Django endpoint that proxies to RapidAPI for the full catalog. Graceful degradation if RapidAPI is down.

**Tech Stack:** Django 5.x, fuse.js v7 (CDN), RapidAPI IMDB236

---

### Task 1: Backend — Search view + URL route

**Files:**
- Modify: `core/views.py` — add `search_movies` view after `movie_api_json`
- Modify: `core/urls.py` — add search route

- [ ] **Step 1: Add `search_movies` view to `core/views.py`**

Append this function at the end of `views.py` (after `movie_api_json`):

```python
@require_GET
def search_movies(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": [], "query": q})

    cache_key = f"search_cache:{q.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse({"results": cached, "query": q})

    try:
        r = requests.get(
            f"{IMDB_API_BASE}/search/{requests.utils.quote(q)}",
            headers=HEADERS,
            timeout=10,
        )
        _raise_for_auth(r)
        if r.ok:
            raw = r.json()
            results = [
                {
                    "id": item.get("id", ""),
                    "title": item.get("primaryTitle", item.get("title", "")),
                    "primaryImage": item.get("primaryImage", ""),
                    "averageRating": item.get("averageRating"),
                    "genres": item.get("genres", []),
                    "startYear": item.get("startYear"),
                    "description": item.get("description", ""),
                }
                for item in (raw if isinstance(raw, list) else raw.get("results", []))
            ]
            cache.set(cache_key, results, 300)
            return JsonResponse({"results": results, "query": q})
    except requests.RequestException:
        pass

    return JsonResponse({"results": [], "query": q})
```

- [ ] **Step 2: Add search URL to `core/urls.py`**

Add this line before the closing bracket of `urlpatterns`:

```python
    path("search/", views.search_movies, name="search"),
```

- [ ] **Step 3: Verify no syntax errors**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
git add core/views.py core/urls.py
git commit -m "feat: add search API endpoint proxying to RapidAPI"
```

---

### Task 2: Template — fuse.js CDN + search bar markup

**Files:**
- Modify: `core/templates/core/home.html`

- [ ] **Step 1: Add fuse.js CDN to `<head>`**

Add after the existing `style.css` link (line 14):

```html
    <script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0"></script>
```

- [ ] **Step 2: Wrap the search input in a `<form>` with IDs**

Replace lines 149-160:

```html
        <div class="topbar-search">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input type="text" placeholder="Search movies, shows, genres…" />
        </div>
```

With:

```html
        <div class="topbar-search" id="searchContainer">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <form id="searchForm" autocomplete="off">
            <input
              type="text"
              id="searchInput"
              name="q"
              placeholder="Search movies, shows, genres…"
            />
          </form>
          <button id="searchClear" class="search-clear" aria-label="Clear search" style="display:none;">&times;</button>
        </div>
```

Note: the `<svg>` stays where it is, but now the `<input>` is inside a `<form>` for proper semantics, and we add a clear button after it.

- [ ] **Step 3: Commit**

```bash
git add core/templates/core/home.html
git commit -m "feat: add fuse.js CDN and wire search bar with form + clear button"
```

---

### Task 3: JavaScript — Search module inside the IIFE

**Files:**
- Modify: `core/templates/core/home.html` — replace the search placeholder with real implementation

- [ ] **Step 1: Remove placeholder comments and add search module**

Replace the placeholder block (lines 593-599):

```javascript
        /* ─── SEARCH MODULE (PLACEHOLDER) ─── */
        /*
          To add independent search for movies or series:
          1. Create a function here that reads from state.moviesCache / state.seriesCache
          2. Filter by user query and call fillRow(DOM.moviesRow, filtered) or fillRow(DOM.seriesRow, filtered)
          3. Wire it to an input event or a dedicated search endpoint via fetchFromIMDb()
        */
```

With:

```javascript
        /* ─── SEARCH MODULE ─── */
        var searchDebounce = null;
        var searchActive = false;
        var searchResultsHeader = null;

        function buildFuse(data) {
          return new Fuse(data || [], {
            keys: ["title", "primaryTitle"],
            threshold: 0.4,
            ignoreLocation: true,
            minMatchCharLength: 2,
          });
        }

        function renderSearchResults(query, localMovies, localSeries) {
          var total = (localMovies ? localMovies.length : 0) + (localSeries ? localSeries.length : 0);

          var hero = document.querySelector(".hero-section");
          var genres = document.querySelector(".genre-strip");
          if (hero) hero.style.display = total > 0 ? "none" : "";
          if (genres) genres.style.display = total > 0 ? "none" : "";

          if (!searchResultsHeader) {
            searchResultsHeader = document.createElement("div");
            searchResultsHeader.className = "search-results-header";
            var moviesSection = document.querySelector('[data-od-id="movies"]');
            if (moviesSection && moviesSection.parentNode) {
              moviesSection.parentNode.insertBefore(searchResultsHeader, moviesSection);
            }
          }

          if (total > 0) {
            searchResultsHeader.innerHTML = 'Results for "' + esc(query) + '" <span class="search-count">(' + total + ')</span>';
            searchResultsHeader.style.display = "";
          } else {
            searchResultsHeader.innerHTML = 'No results found for "' + esc(query) + '"';
            searchResultsHeader.style.display = "";
          }

          fillRow(DOM.moviesRow, localMovies || []);
          fillRow(DOM.seriesRow, localSeries || []);
          searchActive = true;
        }

        function restoreDefaultView() {
          searchActive = false;
          var hero = document.querySelector(".hero-section");
          var genres = document.querySelector(".genre-strip");
          if (hero) hero.style.display = "";
          if (genres) genres.style.display = "";
          if (searchResultsHeader) searchResultsHeader.style.display = "none";
          fillRow(DOM.moviesRow, state.moviesCache);
          fillRow(DOM.seriesRow, state.seriesCache);
          document.getElementById("searchInput").value = "";
          document.getElementById("searchClear").style.display = "none";
        }

        function performSearch(query) {
          query = (query || "").trim();
          var clearBtn = document.getElementById("searchClear");

          if (query.length < 2) {
            if (searchActive) restoreDefaultView();
            if (clearBtn) clearBtn.style.display = "none";
            return;
          }

          if (clearBtn) clearBtn.style.display = "block";

          // Client-side: fuzzy match on cached data
          var movieFuse = buildFuse(state.moviesCache);
          var seriesFuse = buildFuse(state.seriesCache);
          var movieResults = movieFuse.search(query).map(function (r) { return r.item; });
          var seriesResults = seriesFuse.search(query).map(function (r) { return r.item; });
          renderSearchResults(query, movieResults, seriesResults);

          // Server-side: fetch full catalog from RapidAPI via Django
          fetch("/search/?q=" + encodeURIComponent(query))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
              if (!data || !data.results || data.results.length === 0) return;
              // If server returned more results than local cache, use them
              if (data.results.length > movieResults.length + seriesResults.length) {
                renderSearchResults(query, data.results, []);
              }
            })
            .catch(function () {
              // Graceful degradation: keep client-side results
            });
        }

        function initSearch() {
          var input = document.getElementById("searchInput");
          var clearBtn = document.getElementById("searchClear");
          if (!input) return;

          input.addEventListener("input", function () {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(function () {
              performSearch(input.value);
            }, 300);
          });

          input.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
              restoreDefaultView();
              input.blur();
            }
          });

          if (clearBtn) {
            clearBtn.addEventListener("click", function () {
              restoreDefaultView();
              input.focus();
            });
          }
        }
```

- [ ] **Step 2: Wire `initSearch()` in the boot section**

Find the boot section (lines 642-646):

```javascript
        /* ─── BOOT ─── */
        bindDots();
        resetTimer();
        init();
```

Replace with:

```javascript
        /* ─── BOOT ─── */
        bindDots();
        resetTimer();
        init();
        initSearch();
```

- [ ] **Step 3: Commit**

```bash
git add core/templates/core/home.html
git commit -m "feat: implement search module with fuse.js client-side + server-side fallback"
```

---

### Task 4: CSS — Search results state

**Files:**
- Modify: `core/static/core/style.css` — add styles for search elements

- [ ] **Step 1: Add search-related CSS rules**

Append at the end of `style.css`:

```css
/* ─── SEARCH ─── */
.search-clear {
  background: none;
  border: none;
  color: var(--color-text-secondary, #94a3b8);
  font-size: 1.4rem;
  cursor: pointer;
  padding: 0 8px;
  line-height: 1;
}
.search-clear:hover {
  color: var(--color-text, #f1f5f9);
}
.search-results-header {
  padding: 24px 32px 8px;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text, #f1f5f9);
}
.search-results-header .search-count {
  color: var(--color-text-secondary, #94a3b8);
  font-weight: 400;
  font-size: 0.9rem;
}
```

- [ ] **Step 2: Commit**

```bash
git add core/static/core/style.css
git commit -m "feat: add search results CSS styles"
```

---

### Task 5: Verification

- [ ] **Step 1: Run Django system checks**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: Start dev server and smoke-test**

Run: `python manage.py runserver`
- Open browser to `http://localhost:8000/`
- Page loads with hero, movies, series
- Type "star" in search bar → see filtered results within 300ms
- Clear button (X) appears → click it → hero and full rows restore
- Type a nonsense query → see "No results found" message
- Press Escape → view restores

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete hybrid search implementation"
```
