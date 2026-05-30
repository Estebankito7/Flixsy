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
