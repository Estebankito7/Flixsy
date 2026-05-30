# Saved Watchlist — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a localStorage-based watchlist so users can save movies/series from the detail page and browse them on a `/saved/` page.

**Architecture:** All save data lives in `localStorage` under key `flixsy_saved`. The detail page's "More Info" button becomes a bookmark toggle. The Saved page reads localStorage client-side and renders cards. No backend persistence.

**Tech Stack:** Vanilla JS, Django (minimal view + route), CSS custom properties

---

### Task 1: Add `saved_list` view and URL route

**Files:**
- Modify: `core/views.py`
- Modify: `core/urls.py`

- [ ] **Step 1: Add import and view in `core/views.py`**

Add `require_GET` import is already present. Add this function after `search_api`:

```python
@require_GET
def saved_list(request: HttpRequest) -> HttpResponse:
    return render(request, "core/saved.html")
```

- [ ] **Step 2: Add route in `core/urls.py`**

```python
path("saved/", views.saved_list, name="saved"),
```

- [ ] **Step 3: Verify**

Run: `.\venv\Scripts\python.exe manage.py check`
Expected: "System check identified no issues (0 silenced)."

- [ ] **Step 4: Commit**

```bash
git add core/views.py core/urls.py
git commit -m "feat: add saved-list view and route"
```

---

### Task 2: Update nav — change Saved from `<button>` to `<a>` in all templates

**Files:**
- Modify: `core/templates/core/home.html`
- Modify: `core/templates/core/search_results.html`
- Modify: `core/templates/core/detail.html`

Each template has two Saved buttons: one in `.nav-rail-items` (desktop sidebar) and one in `.bottom-nav-inner` (mobile). Both are `<button class="nav-rail-item">` / `<button class="bottom-nav-item">`. Change them to `<a>` tags pointing to `{% url 'core:saved' %}`.

- [ ] **Step 1: Update `core/templates/core/home.html`**

Replace:
```html
<button class="nav-rail-item">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
    <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/>
  </svg>
  <span class="nav-rail-label">Saved</span>
</button>
```
With:
```html
<a href="{% url 'core:saved' %}" class="nav-rail-item">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
    <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/>
  </svg>
  <span class="nav-rail-label">Saved</span>
</a>
```

Same for the bottom-nav Saved button (change `<button>` to `<a>`).

- [ ] **Step 2: Repeat for `core/templates/core/search_results.html`**

Same two changes.

- [ ] **Step 3: Repeat for `core/templates/core/detail.html`**

Same two changes.

- [ ] **Step 4: Commit**

```bash
git add core/templates/core/home.html core/templates/core/search_results.html core/templates/core/detail.html
git commit -m "feat: update Saved nav buttons to links"
```

---

### Task 3: Create saved page template (`saved.html`)

**Files:**
- Create: `core/templates/core/saved.html`

- [ ] **Step 1: Create `core/templates/core/saved.html`**

```html
{% load static %}
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Saved · Flixsy</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="{% static 'core/css/base.css' %}" />
    <link rel="stylesheet" href="{% static 'core/css/saved.css' %}" />
  </head>
  <body>
    <nav class="nav-rail" aria-label="Main">
      <div class="nav-rail-header">
        <a href="{% url 'core:home' %}" class="nav-rail-logo">F</a>
        <span class="nav-rail-brand">Flaire</span>
      </div>
      <div class="nav-rail-items">
        <a href="{% url 'core:home' %}" class="nav-rail-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
          </svg>
          <span class="nav-rail-label">Home</span>
        </a>
        <a href="{% url 'core:search' %}" class="nav-rail-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <span class="nav-rail-label">Search</span>
        </a>
        <a href="{% url 'core:saved' %}" class="nav-rail-item active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/>
          </svg>
          <span class="nav-rail-label">Saved</span>
        </a>
      </div>
    </nav>

    <nav class="bottom-nav" aria-label="Mobile">
      <div class="bottom-nav-inner">
        <a href="{% url 'core:home' %}" class="bottom-nav-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
          </svg>
          <span>Home</span>
        </a>
        <a href="{% url 'core:search' %}" class="bottom-nav-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <span>Search</span>
        </a>
        <a href="{% url 'core:saved' %}" class="bottom-nav-item active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/>
          </svg>
          <span>Saved</span>
        </a>
      </div>
    </nav>

    <div class="page-wrapper">
      <header class="topbar">
        <div class="topbar-search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
          </svg>
          <input type="text" placeholder="Search movies, shows, genres…" />
        </div>
        <div class="topbar-actions">
          <button aria-label="Notifications">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" />
            </svg>
          </button>
          <div class="avatar">J</div>
        </div>
      </header>

      <main class="main">
        <div class="saved-wrap">
          <h1 class="saved-title">Saved</h1>
          <div id="savedGrid" class="saved-grid"></div>
          <div id="savedEmpty" class="saved-empty" hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="saved-empty-icon">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M15 3v18"/>
            </svg>
            <h2>Nothing saved yet</h2>
            <p>Browse movies and shows, then save them to watch later.</p>
            <a href="{% url 'core:home' %}" class="btn-stadium primary">Browse</a>
          </div>
        </div>
      </main>
    </div>

    <script src="{% static 'core/js/saved.js' %}"></script>
  </body>
</html>
```

- [ ] **Step 2: Verify**

Run: `.\venv\Scripts\python.exe manage.py check`
Expected: "System check identified no issues (0 silenced)."

- [ ] **Step 3: Commit**

```bash
git add core/templates/core/saved.html
git commit -m "feat: create saved page template"
```

---

### Task 4: Create saved page CSS (`saved.css`)

**Files:**
- Create: `core/static/core/css/saved.css`

- [ ] **Step 1: Create `core/static/core/css/saved.css`**

```css
.saved-wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--gap-xl) var(--gap-xl) var(--gap-2xl);
}

.saved-title {
  font-size: var(--fs-h1);
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: var(--gap-lg);
}

.saved-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--gap-lg);
}

.saved-card {
  display: block;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface);
  transition: transform var(--motion-base) var(--ease-out);
  text-decoration: none;
  color: inherit;
}

.saved-card:hover {
  transform: translateY(-4px);
}

.saved-card-poster {
  width: 100%;
  aspect-ratio: 2/3;
  object-fit: cover;
  background: var(--surface);
}

.saved-card-body {
  padding: var(--gap-sm) var(--gap-md) var(--gap-md);
}

.saved-card-title {
  font-size: var(--fs-body);
  font-weight: 600;
  margin-bottom: var(--gap-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.saved-card-meta {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  font-size: var(--fs-small);
  color: var(--fg-secondary);
}

.saved-card-badge {
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: var(--radius-pill);
  padding: 1px 8px;
  font-weight: 500;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.saved-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--gap-2xl) var(--gap-xl);
  color: var(--fg-secondary);
}

.saved-empty-icon {
  width: 48px;
  height: 48px;
  color: var(--muted);
  margin-bottom: var(--gap-md);
}

.saved-empty h2 {
  font-size: var(--fs-h2);
  font-weight: 600;
  margin-bottom: var(--gap-sm);
  color: var(--fg);
}

.saved-empty p {
  font-size: var(--fs-body);
  margin-bottom: var(--gap-lg);
  max-width: 32ch;
}

@media (max-width: 720px) {
  .saved-wrap {
    padding: var(--gap-md);
  }
  .saved-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: var(--gap-md);
  }
}
```

- [ ] **Step 2: Verify file exists**

- [ ] **Step 3: Commit**

```bash
git add core/static/core/css/saved.css
git commit -m "feat: add saved page styles"
```

---

### Task 5: Create saved page JS (`saved.js`)

**Files:**
- Create: `core/static/core/js/saved.js`

- [ ] **Step 1: Create `core/static/core/js/saved.js`**

```javascript
document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('savedGrid');
  const empty = document.getElementById('savedEmpty');
  if (!grid || !empty) return;

  let items;
  try {
    items = JSON.parse(localStorage.getItem('flixsy_saved') || '[]');
  } catch {
    items = [];
  }

  if (!items.length) {
    grid.hidden = true;
    empty.hidden = false;
    return;
  }

  empty.hidden = true;
  grid.hidden = false;

  items.forEach(item => {
    const card = document.createElement('a');
    card.className = 'saved-card';
    card.href = `/detail/${item.imdb_id || item.id}/`;

    const poster = item.primaryImage
      ? `<img class="saved-card-poster" src="${item.primaryImage}" alt="${item.title}" loading="lazy" />`
      : `<div class="saved-card-poster" style="display:grid;place-items:center;color:var(--muted);font-size:28px;font-weight:700;">${(item.title || '?')[0]}</div>`;

    card.innerHTML = `
      ${poster}
      <div class="saved-card-body">
        <div class="saved-card-title">${item.title || ''}</div>
        <div class="saved-card-meta">
          ${item.type ? `<span class="saved-card-badge">${item.type}</span>` : ''}
          ${item.startYear ? `<span>${item.startYear}</span>` : ''}
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add core/static/core/js/saved.js
git commit -m "feat: add saved page JS to render localStorage items"
```

---

### Task 6: Update detail page — replace More Info with save toggle

**Files:**
- Modify: `core/templates/core/detail.html`
- Modify: `core/static/core/js/detail.js`

- [ ] **Step 1: Replace the More Info button in `detail.html`**

Replace:
```html
<button class="btn-stadium secondary">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
    <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
  </svg>
  More Info
</button>
```
With:
```html
<button class="btn-stadium secondary" id="saveToggle">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" id="saveIcon">
    <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2v16z"/>
  </svg>
  <span id="saveLabel">Save</span>
</button>
```

- [ ] **Step 2: Add save logic in `detail.js` — after `setupEpisodeSelector(movie)` call, before the closing of `renderMovie`**

Add after `setupEpisodeSelector(movie);` inside `renderMovie`:

```javascript
    /* Save / Unsave toggle */
    const saveToggle = document.getElementById('saveToggle');
    const saveIcon = document.getElementById('saveIcon');
    const saveLabel = document.getElementById('saveLabel');
    if (saveToggle) {
      function updateSaveState() {
        let saved;
        try { saved = JSON.parse(localStorage.getItem('flixsy_saved') || '[]'); } catch { saved = []; }
        const idx = saved.findIndex(s => String(s.id) === String(movie.id));
        const isSaved = idx !== -1;
        saveIcon.setAttribute('fill', isSaved ? 'currentColor' : 'none');
        saveLabel.textContent = isSaved ? 'Saved' : 'Save';
      }
      updateSaveState();
      saveToggle.addEventListener('click', () => {
        let saved;
        try { saved = JSON.parse(localStorage.getItem('flixsy_saved') || '[]'); } catch { saved = []; }
        const idx = saved.findIndex(s => String(s.id) === String(movie.id));
        if (idx !== -1) {
          saved.splice(idx, 1);
        } else {
          saved.push({
            id: movie.id,
            imdb_id: movie.imdb_id || '',
            title: movie.title || '',
            type: movie.type || '',
            primaryImage: movie.primaryImage || '',
            startYear: movie.startYear || '',
            averageRating: movie.averageRating || '',
            savedAt: new Date().toISOString(),
          });
        }
        localStorage.setItem('flixsy_saved', JSON.stringify(saved));
        updateSaveState();
      });
    }
```

- [ ] **Step 3: Verify syntax**

Run: `node -e "const fs=require('fs');const c=fs.readFileSync('core/static/core/js/detail.js','utf-8');try{new Function(c);console.log('OK')}catch(e){console.log('FAIL:',e.message)}"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add core/templates/core/detail.html core/static/core/js/detail.js
git commit -m "feat: replace More Info with save toggle on detail page"
```

---

### Task 7: Run Django checks and verify

- [ ] **Step 1: Django system check**

Run: `.\venv\Scripts\python.exe manage.py check`
Expected: "System check identified no issues (0 silenced)."

- [ ] **Step 2: Run development server and smoke test**

Run: `.\venv\Scripts\python.exe manage.py runserver`
Visit `http://127.0.0.1:8000/saved/` — should show empty state with "Nothing saved yet".
Visit a detail page — should see bookmark button.
