(function () {
  "use strict";

  /* ========================================================================
   * CONFIGURATION
   * ======================================================================== */
  const API = {
    TRENDING: "/api/trending/",
    HERO_COUNT: 5,
    SLIDE_MS: 5500,
  };

  /* ========================================================================
   * SVG ICONS
   * ======================================================================== */
  const ICONS = {
    play: '<polygon points="5 3 19 12 5 21 5 3" />',
    info: '<circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />',
    star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />',
    chevronLeft: '<path d="M15 18l-6-6 6-6"/>',
    chevronRight: '<path d="M9 18l6-6-6-6"/>',
  };

  function svg(viewBox, inner, fill) {
    const fillAttr = fill === "currentColor" ? 'fill="currentColor"' : `fill="${fill || "none"}"`;
    return `<svg viewBox="${viewBox}" ${fillAttr} stroke="currentColor" stroke-width="1.8">${inner}</svg>`;
  }

  /* ========================================================================
   * DOM REFERENCES
   * ======================================================================== */
  const DOM = {
    heroSlides: document.getElementById("heroSlides"),
    heroDots: document.getElementById("heroDots"),
    moviesRow: document.getElementById("moviesRow"),
    moviesSection: document.querySelector('[data-od-id="movies"]'),
    seriesRow: document.getElementById("seriesRow"),
    seriesSection: document.querySelector('[data-od-id="series"]'),
    genreChips: document.querySelectorAll(".chip"),
    navItems: document.querySelectorAll(".nav-rail-item, .bottom-nav-item"),
  };

  /* ========================================================================
   * STATE
   * ======================================================================== */
  const state = {
    slideIdx: 0,
    slideTimer: null,
    moviesCache: [],
    seriesCache: [],
  };

  /* ========================================================================
   * API SERVICE
   * ======================================================================== */
  async function fetchFromDjango(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error("Django API error: " + r.status);
    return r.json();
  }

  /* ========================================================================
   * FORMATTING HELPERS
   * ======================================================================== */
  function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = String(text);
    return d.innerHTML;
  }

  /* ========================================================================
   * RENDERERS — Media Card
   * ======================================================================== */
  function createMediaCard(item) {
    const id = item.id;
    const thumbnail = item.primaryImage
      ? `<img src="${escapeHtml(item.primaryImage)}" alt="${escapeHtml(item.title)}" style="object-fit:cover;position:absolute;inset:0;width:100%;height:100%;" loading="lazy">`
      : `<div class="card-icon">${svg("0 0 24 24", ICONS.play, "currentColor")}</div>`;

    return (
      `<div class="media-card">` +
      `<a href="/detail/${id}/">` +
      `<div class="media-card-thumb" style="position:relative;overflow:hidden;">${thumbnail}</div>` +
      `<div class="media-card-info"><h3>${escapeHtml(item.title)}</h3></div>` +
      `</a></div>`
    );
  }

  /* ========================================================================
   * RENDERERS — Hero Carousel
   * ======================================================================== */
  function createHeroSlide(item) {
    const genres = (item.genres || []).slice(0, 2);
    const id = item.id;
    const yearBadge = item.startYear
      ? `<span class="badge">${escapeHtml(item.startYear)}</span>`
      : "";
    const background = item.primaryImage
      ? `<img src="${escapeHtml(item.primaryImage)}" alt="" loading="lazy">`
      : "";

    return (
      `<div class="hero-slide">` +
      `<div class="hero-slide-bg" style="background:linear-gradient(135deg,#111827,#1e293b);">${background}</div>` +
      `<div class="hero-slide-content">` +
      `<span class="eyebrow">&#9679; Now Streaming</span>` +
      `<h1>${escapeHtml(item.title)}</h1>` +
      `<div class="meta-row">${yearBadge}` +
      `<span class="rating">${svg("0 0 24 24", ICONS.star, "currentColor")}${item.averageRating || "N/A"}</span>` +
      genres.map(g => `<span class="badge">${escapeHtml(g)}</span>`).join("") +
      `</div>` +
      `<p class="desc">${escapeHtml(item.description || "")}</p>` +
      `<div class="hero-actions">` +
      `<a href="/detail/${id}/" class="btn-primary">${svg("0 0 24 24", ICONS.play, "currentColor")}Play</a>` +
      `<a href="/detail/${id}/" class="btn-secondary">${svg("0 0 24 24", ICONS.info, "none")}More Info</a>` +
      `</div></div></div>`
    );
  }

  /* ========================================================================
   * HERO CAROUSEL CONTROLS
   * ======================================================================== */
  function buildHero(movies) {
    DOM.heroSlides.innerHTML = movies.map(createHeroSlide).join("");
    DOM.heroDots.innerHTML = movies
      .map((_, i) => `<span class="hero-dot${i === 0 ? " active" : ""}" data-index="${i}"></span>`)
      .join("");
    state.slideIdx = 0;
    DOM.heroSlides.style.transform = "translateX(0)";
    bindHeroDots();
    resetSlideTimer();
  }

  function goToSlide(index) {
    const slides = DOM.heroSlides.children;
    if (index === state.slideIdx || !slides.length) return;
    state.slideIdx = index;
    DOM.heroSlides.style.transform = `translateX(-${index * 100}%)`;
    Array.from(document.querySelectorAll(".hero-dot")).forEach(
      (dot, i) => dot.classList.toggle("active", i === index)
    );
    resetSlideTimer();
  }

  function advanceSlide() {
    const count = DOM.heroSlides.children.length;
    if (count) goToSlide((state.slideIdx + 1) % count);
  }

  function resetSlideTimer() {
    clearInterval(state.slideTimer);
    state.slideTimer = setInterval(advanceSlide, API.SLIDE_MS);
  }

  function bindHeroDots() {
    document.querySelectorAll(".hero-dot").forEach(dot => {
      dot.addEventListener("click", () => goToSlide(parseInt(dot.dataset.index)));
    });
  }

  /* ========================================================================
   * SECTION ROW MANAGEMENT
   * ======================================================================== */
  function populateRow(container, items) {
    if (!container) return;
    const section = container.closest("[data-od-id]");
    if (!items || !items.length) {
      if (section?.isConnected) section.remove();
      return;
    }
    if (section && !section.isConnected) {
      const ref = document.querySelector(".genre-strip");
      if (ref) ref.after(section);
    }
    container.innerHTML = items.map(createMediaCard).join("");
  }

  /* ========================================================================
   * SCROLL ARROWS
   * ======================================================================== */
  /** Tracks all active arrow instances for visibility updates. */
  const arrowState = [];

  /** Returns the computed gap of a flex container in pixels. */
  function getGap(element) {
    const style = getComputedStyle(element);
    return parseFloat(style.gap || style.columnGap || "0");
  }

  /** Toggles arrow visibility based on the row's scroll boundaries. */
  function updateArrowVisibility(row, leftBtn, rightBtn) {
    const { scrollLeft, scrollWidth, clientWidth } = row;
    leftBtn.classList.toggle("hidden", scrollLeft <= 2);
    rightBtn.classList.toggle("hidden", scrollLeft + clientWidth >= scrollWidth - 2);
  }

  /** Creates a scroll arrow button element. */
  function createArrow(dir, label) {
    const btn = document.createElement("button");
    btn.className = "scroll-arrow " + dir;
    btn.setAttribute("aria-label", label);
    const icon = dir === "left" ? ICONS.chevronLeft : ICONS.chevronRight;
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">' + icon + '</svg>';
    return btn;
  }

  /** Injects scroll arrow buttons into each populated card row section. */
  function setupRowArrows() {
    document.querySelectorAll(".section-wrap[data-od-id]").forEach(section => {
      const row = section.querySelector(".card-row");
      if (!row || !row.children.length) return;

      const leftBtn = createArrow("left", "Scroll left");
      const rightBtn = createArrow("right", "Scroll right");
      section.appendChild(leftBtn);
      section.appendChild(rightBtn);

      arrowState.push({ row, leftBtn, rightBtn });

      function getStep() {
        const first = row.querySelector(".media-card");
        if (!first) return row.clientWidth * 0.8;
        return first.offsetWidth + getGap(row);
      }

      leftBtn.addEventListener("click", () => {
        row.scrollBy({ left: -getStep(), behavior: "smooth" });
      });
      rightBtn.addEventListener("click", () => {
        row.scrollBy({ left: getStep(), behavior: "smooth" });
      });

      const update = () => updateArrowVisibility(row, leftBtn, rightBtn);
      row.addEventListener("scroll", update, { passive: true });
      update();

      window.addEventListener("resize", update);
    });
  }

  /** Refreshes visibility for all arrow instances (e.g., after content changes). */
  function refreshArrows() {
    arrowState.forEach(({ row, leftBtn, rightBtn }) => {
      updateArrowVisibility(row, leftBtn, rightBtn);
    });
  }

  /* ========================================================================
   * DATA LOADING
   * ======================================================================== */
  async function loadMovies() {
    const data = await fetchFromDjango(API.TRENDING + "?media_type=movie&time_window=day");
    const raw = data.results || [];
    if (!Array.isArray(raw)) throw new Error("Invalid trending response");
    state.moviesCache = raw;
    const heroCandidates = state.moviesCache.filter(m => m.primaryImage);
    if (heroCandidates.length) {
      buildHero(heroCandidates.slice(0, API.HERO_COUNT));
    }
    populateRow(DOM.moviesRow, state.moviesCache);
  }

  async function loadSeries() {
    const data = await fetchFromDjango(API.TRENDING + "?media_type=tv&time_window=day");
    const raw = data.results || [];
    if (!Array.isArray(raw)) throw new Error("Invalid trending series response");
    state.seriesCache = raw;
    populateRow(DOM.seriesRow, state.seriesCache);
  }

  /* ========================================================================
   * GENRE FILTERING
   * ======================================================================== */
  async function loadByGenre(mediaType, genre, container) {
    const url = `${API.TRENDING}?media_type=${mediaType}&genre=${encodeURIComponent(genre)}`;
    try {
      const data = await fetchFromDjango(url);
      populateRow(container, data.results || []);
    } catch {
      populateRow(container, []);
    }
  }

  function setupGenreFiltering() {
    DOM.genreChips.forEach(chip => {
      chip.addEventListener("click", () => {
        DOM.genreChips.forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        const genre = chip.textContent.trim();
        if (genre === "All") {
          loadMovies();
          loadSeries();
        } else {
          loadByGenre("movie", genre, DOM.moviesRow);
          loadByGenre("tv", genre, DOM.seriesRow);
        }
        refreshArrows();
      });
    });
  }

  /* ========================================================================
   * NAVIGATION
   * ======================================================================== */
  function setupNavigation() {
    DOM.navItems.forEach(item => {
      item.addEventListener("click", () => {
        const parent = item.closest(".nav-rail-items, .bottom-nav-inner") || item.parentNode;
        parent.querySelectorAll(".nav-rail-item, .bottom-nav-item").forEach(i => i.classList.remove("active"));
        item.classList.add("active");
      });
    });
  }

  /* ========================================================================
   * INIT
   * ======================================================================== */
  async function init() {
    setupNavigation();
    setupGenreFiltering();
    bindHeroDots();
    resetSlideTimer();
    try {
      await Promise.all([loadMovies(), loadSeries()]);
      setupRowArrows();
    } catch (e) {
      console.warn("Flixsy: Trending API unavailable", e);
    }
  }

  init();
})();
