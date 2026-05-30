# Scroll Arrows for Home Page Card Rows

## Summary
Add overlaid floating arrow buttons to the Movies and Series card rows on the home page to make horizontal scrolling discoverable and intuitive.

## Design

### CSS (`style.css`)
- `.section-wrap` gets `position: relative`
- `.scroll-arrow` — 40px circle button, dark semi-transparent bg, accent hover, vertically centered on card row, z-index above cards, chevron SVG
- `.scroll-arrow.hidden` — opacity 0, pointer-events none
- Left arrow at `left: 0`, right arrow at `right: 0`

### JS (`home.js`)
- `setupRowArrows()` creates left/right arrow buttons per `.section-wrap[data-od-id]` with a `.card-row`
- Click scrolls by one card width (first card offsetWidth + computed gap)
- `updateArrowVisibility()` hides arrows at scroll boundaries
- Recalculates on window resize
- Called in `init()` after data loads

### Template
- No changes needed — arrows injected by JS
