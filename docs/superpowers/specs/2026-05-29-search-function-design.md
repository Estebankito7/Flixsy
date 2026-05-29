# Búsqueda Híbrida en Flixsy

## Resumen

Implementar búsqueda de películas y series en Flixsy usando un enfoque híbrido: **filtrado client-side instantáneo** sobre datos cacheados (moviesCache/seriesCache) + **endpoint server-side** que consulta RapidAPI para el catálogo completo. La "inteligencia" se basa en fuzzy matching con tolerancia a typos + ranking por rating, evitando dependencias pesadas.

## Arquitectura

```
[Input búsqueda] → evento 'input' con debounce 300ms
     │
     ├─→ JS filtra state.moviesCache + state.seriesCache (instantáneo)
     │    └─ fuzzy match por título (fuse.js liviano)
     │    └─ ordena por averageRating descendente
     │    └─ renderiza con fillRow()
     │
     └─→ fetch GET /search/?q=... (catálogo completo vía RapidAPI)
          └─ views.py → RapidAPI /search/... 
          └─ devuelve JSON con resultados + rating
          └─ JS reemplaza filas con resultados completos
```

## Componentes

### 1. Template (`home.html`)

**Cambios en la barra actual (líneas 149-160):**
- Envolver `<input>` en un `<form>` con `id="searchForm"` y `autocomplete="off"`
- Agregar `id="searchInput"` y `name="q"` al `<input>`
- Agregar botón "X" dentro del searchbar (visible solo cuando hay query activa) que limpia y restaura la vista por defecto

No se agregan nuevos elementos visuales — la barra ya existe, solo se le da comportamiento.

### 2. JavaScript (`home.html` — IIFE existente, ~líneas 593-599)

**Nuevo módulo "search":**

- **`initSearch()`**: Enlaza evento `input` con debounce de 300ms al `#searchInput`
- **`performSearch(query)`**: 
  1. Si query < 2 caracteres → restaura vista normal (hero + rows completas)
  2. Si query >= 2 chars → filtra `state.moviesCache` + `state.seriesCache` con fuse.js
  3. Oculta hero section (`hero-section`), genre strip
  4. Renderiza resultados en `moviesRow` y `seriesRow` con `fillRow()`
  5. Muestra label "Resultados para: X" y contador
- **`clearSearch()`**: Restaura hero, genre strip, rows completas
- **Botón "X"**: Se muestra solo cuando hay búsqueda activa

**Dependencia externa:** fuse.js v7 (CDN) — liviana (~8KB gzip), sin dependencias.

### 3. Vista Django (`views.py`)

**Nueva función `search_movies(request)`:**
- Decorada con `@require_GET`
- Lee `request.GET.get('q', '')`
- Si query < 2 chars → JSON vacío
- Consulta RapidAPI: `GET {IMDB_API_BASE}/search/{encoded_query}`
- Cachea resultados por 5 minutos (clave: `search_cache:{query}`)
- Retorna `JsonResponse({results: [...]})`
- Cada resultado incluye: `id`, `title`, `primaryImage`, `averageRating`, `genres`, `startYear`, `description`

### 4. URL (`urls.py`)

Agregar:
```python
path("search/", views.search_movies, name="search"),
```

## Flujo de datos

1. Usuario escribe en el input
2. Tras 300ms de inactividad:
   - **Client-side**: `fuse.js` busca en `moviesCache` + `seriesCache` por título. Ordena por `averageRating` descendente. Renderizado inmediato con `fillRow()`.
   - **Server-side**: Fetch a `/search/?q=...`. El servidor consulta RapidAPI (con cache de 5 min), devuelve JSON.
3. Cuando llega la respuesta server-side:
   - Los resultados server-side reemplazan a los client-side (el servidor tiene el catálogo completo)
   - Se muestra un indicador "Mostrando X de Y resultados"
   - Si el servidor responde con 0 resultados pero el cliente sí encontró, se conservan los resultados client-side
4. Si el servidor falla (RapidAPI down): el usuario sigue viendo los resultados client-side — degradación graceful.

## Vista de resultados

Cuando hay búsqueda activa:
- **Hero section** se oculta (`display: none`)
- **Genre strip** se oculta
- Aparece un encabezado: `"Resultados para \"{query}\" ({count})"`
- **Movies Row** muestra resultados de películas
- **Series Row** muestra resultados de series
- Cada card mantiene el mismo diseño existente (`createMediaCard`)
- Si no hay resultados: mensaje "No se encontraron resultados para \"{query}\""
- Botón "X" o "Limpiar" restaura la vista original

## Dependencias

- **fuse.js** v7 — vía CDN (`<script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0"></script>`)
- Sin cambios en Django ni Python dependencies (usa `requests` ya existente)

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `core/templates/core/home.html` | Envolver input en form, agregar ids, agregar CDN fuse.js, implementar módulo search en IIFE |
| `core/views.py` | Agregar `search_movies()` view |
| `core/urls.py` | Agregar ruta `/search/` |
| `core/static/core/style.css` | Estilos para el estado de búsqueda (opcional: encabezado de resultados, responsive) |

## No incluido (por ahora)

- Búsqueda semántica con embeddings (requiere sentence-transformers, demasiado pesado para este alcance)
- Paginación de resultados server-side (la API de RapidAPI no la soporta de forma consistente)
- Historial de búsquedas recientes
- Búsqueda por voz

## Pruebas

1. Escribir "star" → debe mostrar películas con "Star" en el título (fuzzy match)
2. Escribir "sTr" → debe funcionar con typos (case insensitive)
3. Escribir "xyzzy" → debe mostrar "No se encontraron resultados"
4. Borrar el input → debe restaurar la vista original
5. Verificar que el botón "X" funciona correctamente
6. Verificar que los resultados mantienen links funcionales a `/detail/{imdb_id}/`
7. RapidAPI caído + búsqueda → debe mostrar resultados client-side sin error visible
