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

  /* ─── Player (unchanged) ─── */

  const mediaColumn = document.getElementById('mediaColumn');

  function getServerList(id, numericId, isTV, season, episode) {
    if (isTV) {
      return [
        { name: 'VidSrc', url: `https://vidsrc.to/embed/tv/${id}/${season}/${episode}` },
        { name: 'VidLink', url: `https://vidlink.org/embed/tv/${numericId}/${season}/${episode}` },
        { name: 'VidFast', url: `https://vidfast.to/embed/tv/${id}/${season}/${episode}` },
      ];
    }
    return [
      { name: 'VidSrc', url: `https://vidsrc.to/embed/movie/${id}` },
      { name: 'VidLink', url: `https://vidlink.org/embed/movie/${numericId}` },
      { name: 'VidFast', url: `https://www.vidfast.net/movie/${id}` },
    ];
  }

  function createPlayerElement(id, type, season, episode) {
    const isTV = (type || '').toLowerCase().includes('tv') || (type || '').toLowerCase().includes('series');
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

    const servers = getServerList(id, numericId, isTV, season, episode);
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

  function attachPlayer(btn) {
    if (!btn || !mediaColumn) return;
    const id = btn.dataset.imdbId;
    const type = btn.dataset.type;
    const season = parseInt(btn.dataset.season, 10) || 1;
    const episode = parseInt(btn.dataset.episode, 10) || 1;

    btn.addEventListener('click', () => {
      if (document.getElementById('playerContainer')) return;
      mediaColumn.appendChild(createPlayerElement(id, type, season, episode));
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
    const playBtn = document.querySelector('.btn-stadium.primary');
    if (playBtn) {
      playBtn.dataset.imdbId = movie.id || '';
      playBtn.dataset.type = movie.type || '';
      playBtn.dataset.season = movie.season != null ? movie.season : '1';
      playBtn.dataset.episode = movie.episode != null ? movie.episode : '1';
    }
    attachPlayer(playBtn);
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

  /* Fallback: attach player even if fetch fails (SSR data already in the DOM) */
  const existingBtn = document.querySelector('.btn-stadium.primary');
  attachPlayer(existingBtn);
});
