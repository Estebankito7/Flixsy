document.addEventListener('DOMContentLoaded', () => {
  const mainEl = document.querySelector('main[data-imdb-id]');
  if (!mainEl) return;

  const imdbId = mainEl.dataset.imdbId;
  const apiUrl = `/api/detail/${imdbId}/`;

  /* ─── Helpers ─── */

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  /* ─── Server definitions ─── */

  const SERVERS = {
    tv: (id, numericId, season, episode) => [
      { name: 'VidSrc', url: `https://vidsrc.to/embed/tv/${id}/${season}/${episode}` },
      { name: 'VidLink', url: `https://vidlink.org/embed/tv/${numericId}/${season}/${episode}` },
      { name: 'VidFast', url: `https://vidfast.to/embed/tv/${id}/${season}/${episode}` },
    ],
    movie: (id, numericId) => [
      { name: 'VidSrc', url: `https://vidsrc.to/embed/movie/${id}` },
      { name: 'VidLink', url: `https://vidlink.org/embed/movie/${numericId}` },
      { name: 'VidFast', url: `https://www.vidfast.net/movie/${id}` },
    ],
  };

  const mediaColumn = document.getElementById('mediaColumn');

  /* ─── Saved items (localStorage) ─── */

  let savedItems = (() => {
    try { return JSON.parse(localStorage.getItem('flixsy_saved') || '[]'); } catch { return []; }
  })();

  function getPlayButton() {
    return document.querySelector('.btn-stadium.primary');
  }

  function isTVType(type) {
    return (type || '').toLowerCase().includes('tv') || (type || '').toLowerCase().includes('series');
  }

  function createPlayerElement(id, type, season, episode) {
    const isTV = isTVType(type);
    const numericId = id.replace(/^tt/, '');
    const container = document.createElement('div');
    container.id = 'playerContainer';

    const serverBar = document.createElement('div');
    serverBar.className = 'server-bar';

    const player = document.createElement('div');
    player.className = 'video-player';

    const wrapper = document.createElement('div');
    wrapper.className = 'video-wrapper';

    const iframe = document.createElement('iframe');
    iframe.allow = 'autoplay; encrypted-media; gyroscope; picture-in-picture';
    iframe.allowFullscreen = true;
    wrapper.appendChild(iframe);
    player.appendChild(wrapper);

    const servers = isTV
      ? SERVERS.tv(id, numericId, season, episode)
      : SERVERS.movie(id, numericId);

    servers.forEach((server, index) => {
      const button = document.createElement('button');
      button.className = `btn-stadium${index === 0 ? ' active' : ''}`;
      button.textContent = server.name;
      button.addEventListener('click', () => {
        serverBar.querySelectorAll('.btn-stadium').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        iframe.src = server.url;
      });
      serverBar.appendChild(button);
    });

    iframe.src = servers[0].url;
    container.appendChild(serverBar);
    container.appendChild(player);
    return container;
  }

  function replacePlayer(btn) {
    const existing = document.getElementById('playerContainer');
    if (existing) existing.remove();
    const id = btn.dataset.imdbId;
    const type = btn.dataset.type;
    const season = parseInt(btn.dataset.season, 10) || 1;
    const episode = parseInt(btn.dataset.episode, 10) || 1;
    mediaColumn.appendChild(createPlayerElement(id, type, season, episode));
  }

  function attachPlayer(btn) {
    if (!btn || !mediaColumn) return;
    btn.addEventListener('click', () => {
      if (document.getElementById('playerContainer')) return;
      replacePlayer(btn);
    });
  }

  /* ─── Season / Episode Selector ─── */

  const episodeSelector = document.getElementById('episodeSelector');

  function populateEpisodeSelect(selectEl, seasons, seasonNumber) {
    const season = seasons.find(s => s.seasonNumber === seasonNumber);
    const count = season ? season.episodeCount : 1;
    selectEl.innerHTML = '';
    for (let i = 1; i <= count; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = 'Episode ' + i;
      if (i === 1) opt.selected = true;
      selectEl.appendChild(opt);
    }
  }

  function syncPlayButton(seasonEl, episodeEl) {
    const btn = getPlayButton();
    if (!btn) return;
    btn.dataset.season = seasonEl.value;
    btn.dataset.episode = episodeEl.value;
  }

  function reloadPlayerIfActive() {
    const btn = getPlayButton();
    if (btn && document.getElementById('playerContainer')) replacePlayer(btn);
  }

  function setupEpisodeSelector(data) {
    if (!episodeSelector) return;
    if (!data.isSeries) { episodeSelector.hidden = true; return; }

    const seasons = data.seasons || [];
    if (!seasons.length) { episodeSelector.hidden = true; return; }

    episodeSelector.innerHTML = '';
    episodeSelector.hidden = false;

    const seasonSelect = document.createElement('select');
    seasonSelect.className = 'episode-select';
    seasonSelect.setAttribute('aria-label', 'Select season');

    seasons.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.seasonNumber;
      opt.textContent = 'Season ' + s.seasonNumber;
      if (s.seasonNumber === 1) opt.selected = true;
      seasonSelect.appendChild(opt);
    });

    const episodeSelect = document.createElement('select');
    episodeSelect.className = 'episode-select';
    episodeSelect.setAttribute('aria-label', 'Select episode');

    populateEpisodeSelect(episodeSelect, seasons, 1);

    const seasonLabel = document.createElement('span');
    seasonLabel.className = 'episode-label';
    seasonLabel.textContent = 'Season';
    const episodeLabel = document.createElement('span');
    episodeLabel.className = 'episode-label';
    episodeLabel.textContent = 'Episode';

    episodeSelector.appendChild(seasonLabel);
    episodeSelector.appendChild(seasonSelect);
    episodeSelector.appendChild(episodeLabel);
    episodeSelector.appendChild(episodeSelect);

    seasonSelect.addEventListener('change', () => {
      populateEpisodeSelect(episodeSelect, seasons, parseInt(seasonSelect.value, 10));
      syncPlayButton(seasonSelect, episodeSelect);
      reloadPlayerIfActive();
    });

    episodeSelect.addEventListener('change', () => {
      syncPlayButton(seasonSelect, episodeSelect);
      reloadPlayerIfActive();
    });
  }

  /* ─── API fetch & render ─── */

  function renderMovie(movie) {
    /* Backdrop */
    const backdropImg = document.querySelector('.detail-backdrop img');
    const backdrop = document.querySelector('.detail-backdrop');
    if (backdrop && movie.primaryImage) {
      backdropImg.src = movie.primaryImage;
      backdropImg.alt = movie.title || '';
    } else if (backdrop && !movie.primaryImage) {
      backdrop.remove();
    }

    /* Poster */
    const posterImg = document.querySelector('.detail-poster img');
    const poster = document.querySelector('.detail-poster');
    if (poster && movie.primaryImage) {
      posterImg.src = movie.primaryImage;
      posterImg.alt = movie.title || '';
    } else if (poster && !movie.primaryImage) {
      poster.remove();
    }

    /* Title */
    const titleEl = document.querySelector('.detail-info h1');
    if (titleEl) titleEl.textContent = movie.title || '';

    /* Meta */
    const metaEl = document.querySelector('.detail-meta');
    if (metaEl) {
      metaEl.innerHTML = '';
      if (movie.startYear) {
        metaEl.innerHTML += `<span class="badge">${escapeHtml(movie.startYear)}</span>`;
      }
      if (movie.type) {
        metaEl.innerHTML += `<span class="badge">${escapeHtml(movie.type)}</span>`;
      }
      if (movie.averageRating) {
        metaEl.innerHTML += `
          <span class="rating">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
            ${escapeHtml(String(movie.averageRating))}
          </span>`;
      }
    }

    /* Description */
    const descEl = document.querySelector('.detail-info .desc');
    if (descEl) {
      if (movie.description) {
        descEl.textContent = movie.description;
      } else {
        descEl.remove();
      }
    }

    /* Sidebar */
    const sidebar = document.querySelector('.detail-content aside');
    if (sidebar) {
      sidebar.innerHTML = '';

      if (movie.directors && movie.directors.length > 0) {
        sidebar.innerHTML += `
          <div class="sidebar-block">
            <h4>Directors</h4>
            <div class="chip-list">
              ${movie.directors.map(d => `<span class="chip active">${escapeHtml(d.fullName || d)}</span>`).join('')}
            </div>
          </div>`;
      }

      if (movie.writers && movie.writers.length > 0) {
        sidebar.innerHTML += `
          <div class="sidebar-block">
            <h4>Writers</h4>
            <div class="chip-list">
              ${movie.writers.map(w => `<span class="chip active">${escapeHtml(w.fullName || w)}</span>`).join('')}
            </div>
          </div>`;
      }

      if (movie.genres && movie.genres.length > 0) {
        sidebar.innerHTML += `
          <div class="sidebar-block">
            <h4>Genres</h4>
            <div class="chip-list">
              ${movie.genres.map(g => `<span class="chip active">${escapeHtml(g)}</span>`).join('')}
            </div>
          </div>`;
      }

      if (movie.releaseDate) {
        sidebar.innerHTML += `
          <div class="sidebar-block">
            <h4>Release Date</h4>
            <p>${escapeHtml(movie.releaseDate)}</p>
          </div>`;
      }
    }

    /* Re-attach player with fresh data */
    const playBtn = getPlayButton();
    if (playBtn) {
      playBtn.dataset.imdbId = movie.id || '';
      playBtn.dataset.type = movie.type || '';
      playBtn.dataset.season = movie.season != null ? movie.season : '1';
      playBtn.dataset.episode = movie.episode != null ? movie.episode : '1';
    }
    attachPlayer(playBtn);

    setupEpisodeSelector(movie);

    /* Save / Unsave toggle */
    const saveToggle = document.getElementById('saveToggle');
    const saveIcon = document.getElementById('saveIcon');
    const saveLabel = document.getElementById('saveLabel');
    if (saveToggle) {
      const isSaved = savedItems.some(s => String(s.id) === String(movie.id));
      saveIcon.setAttribute('fill', isSaved ? 'currentColor' : 'none');
      saveLabel.textContent = isSaved ? 'Saved' : 'Save';

      saveToggle.addEventListener('click', () => {
        const wasSaved = savedItems.some(s => String(s.id) === String(movie.id));
        if (wasSaved) {
          savedItems = savedItems.filter(s => String(s.id) !== String(movie.id));
        } else {
          savedItems.push({
            id: movie.id, imdb_id: movie.imdb_id || '', title: movie.title || '',
            type: movie.type || '', primaryImage: movie.primaryImage || '',
            startYear: movie.startYear || '', averageRating: movie.averageRating || '',
            savedAt: new Date().toISOString(),
          });
        }
        localStorage.setItem('flixsy_saved', JSON.stringify(savedItems));
        saveIcon.setAttribute('fill', wasSaved ? 'none' : 'currentColor');
        saveLabel.textContent = wasSaved ? 'Save' : 'Saved';
      });
    }
  }

  /* ─── Fetch ─── */

  fetch(apiUrl)
    .then(response => {
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      return response.json();
    })
    .then(data => {
      if (data.error) throw new Error(data.error);
      renderMovie(data);
    })
    .catch(err => {
      console.error('Flixsy detail API error:', err);
    });

  /* Fallback: attach player even if fetch fails */
  attachPlayer(getPlayButton());
});
