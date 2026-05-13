# Frontend Changes: Dark / Light Theme Toggle

## Files Modified

- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

---

## index.html

- Bumped cache-busting version query string on `style.css` and `script.js` links (`?v=9` → `?v=10`).
- Added a `<button class="theme-toggle" id="themeToggle">` element immediately inside `<body>`, before `.container`. Contains two inline SVGs:
  - `.icon-moon` — shown in dark mode (default).
  - `.icon-sun` — shown in light mode.
- Button has `aria-label="Toggle theme"` for accessibility.

---

## style.css

### New CSS variables

Added the following variables to `:root` (dark theme defaults):

| Variable | Value | Purpose |
|---|---|---|
| `--code-bg` | `rgba(0,0,0,0.2)` | Code / pre block background |
| `--source-pill-bg` | `#1e3a5f` | Source pill background |
| `--source-pill-color` | `#93c5fd` | Source pill text |
| `--source-pill-border` | `rgba(37,99,235,0.33)` | Source pill border |
| `--theme-toggle-bg` | `#1e293b` | Toggle button background |
| `--theme-toggle-hover` | `#334155` | Toggle button hover background |
| `--theme-toggle-border` | `#334155` | Toggle button border |

### Light theme overrides (`[data-theme="light"]`)

Overrides the following variables for the light theme:

| Variable | Light value |
|---|---|
| `--background` | `#f8fafc` |
| `--surface` | `#ffffff` |
| `--surface-hover` | `#f1f5f9` |
| `--text-primary` | `#0f172a` |
| `--text-secondary` | `#475569` |
| `--border-color` | `#e2e8f0` |
| `--assistant-message` | `#f1f5f9` |
| `--shadow` | lighter rgba shadow |
| `--focus-ring` | lighter blue tint |
| `--welcome-bg` | `#eff6ff` |
| `--code-bg` | `rgba(0,0,0,0.05)` |
| `--source-pill-bg` | `#eff6ff` |
| `--source-pill-color` | `#1d4ed8` |
| `--source-pill-border` | `#bfdbfe` |
| `--theme-toggle-bg` | `#ffffff` |
| `--theme-toggle-hover` | `#f1f5f9` |
| `--theme-toggle-border` | `#e2e8f0` |

### Theme toggle button styles (`.theme-toggle`)

- `position: fixed; top: 1rem; right: 1rem; z-index: 1000` — top-right corner, always on top.
- Circular (40 × 40 px, `border-radius: 50%`).
- Uses theme variables for background, border, and color so it adapts to both themes.
- Smooth CSS transitions on background, color, border, transform, and box-shadow (0.2 s ease).
- Hover: slight scale-up + blue glow.
- Focus: 3 px `--focus-ring` outline (keyboard navigable).
- Active: slight scale-down for tactile feedback.

### Icon switching

```css
/* dark mode (default): show moon, hide sun */
.theme-toggle .icon-sun  { display: none; }
.theme-toggle .icon-moon { display: block; }

/* light mode: show sun, hide moon */
[data-theme="light"] .theme-toggle .icon-sun  { display: block; }
[data-theme="light"] .theme-toggle .icon-moon { display: none; }
```

### Body transition

Added `transition: background-color 0.25s ease, color 0.25s ease` to `body` for a smooth fade between themes.

### Hardcoded color → CSS variable replacements

- `.source-pill`: replaced `#1e3a5f`, `#93c5fd`, `#2563eb55` with `--source-pill-bg`, `--source-pill-color`, `--source-pill-border`.
- `.message-content code` and `.message-content pre`: replaced `rgba(0,0,0,0.2)` with `--code-bg`.

---

## script.js

### `initTheme()`

Reads `localStorage.getItem('theme')`. If `'light'`, sets `data-theme="light"` on `<html>`. Called immediately (before `DOMContentLoaded`) so there is no flash of the wrong theme.

### `toggleTheme()`

- Checks current `data-theme` attribute on `<html>`.
- Toggles between removing the attribute (dark) and setting `data-theme="light"`.
- Persists choice to `localStorage` under the key `'theme'`.

### Event binding

Inside the `DOMContentLoaded` listener, after existing setup calls:

```js
document.getElementById('themeToggle').addEventListener('click', toggleTheme);
```
