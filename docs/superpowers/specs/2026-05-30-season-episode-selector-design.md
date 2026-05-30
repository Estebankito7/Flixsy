# Season/Episode Selector for Series Detail Page

## Summary
Add season and episode dropdown selectors to the series detail page, positioned between the info display and the video player. Allows users to navigate episodes within a series before clicking play.

## Design

### Backend — `tmdb.py`
- `_normalize_detail` for TV includes `number_of_seasons` and `seasons` array from TMDB's `/tv/{id}` response
- Each season: `{"seasonNumber": int, "episodeCount": int}`
- Excludes season 0 (Specials)

### Backend — `views.py`
- No changes needed — `movie_api_json` already returns normalized data which now includes `seasons`

### Template — `detail.html`
- Add `<div id="episodeSelector" class="episode-selector" hidden></div>` inside `#mediaColumn`, before the player container

### Frontend — `detail.js`
- `setupEpisodeSelector(data)` reads `data.seasons`, renders two `<select>` elements (season + episode)
- Only shows when `data.isSeries === true`
- On season change → rebuild episode options from `episodeCount`, reset to episode 1, reload player
- On episode change → reload player
- Player reload: if `#playerContainer` exists → remove it, re-attach with new season/episode

### CSS — `detail.css`
- `.episode-selector` — flex row, gap, styled selects matching server bar buttons
