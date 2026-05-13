# Frontend Changes

## Code Quality Tooling

### New files

| File | Purpose |
|---|---|
| `frontend/package.json` | npm project config; declares Prettier & ESLint dev-dependencies and npm scripts |
| `frontend/.prettierrc` | Prettier configuration (single quotes, 4-space indent, 88-char line width) |
| `frontend/eslint.config.js` | ESLint flat config (ES2022, browser globals, recommended rules + curly/eqeqeq/no-var) |
| `scripts/quality-check.sh` | Shell script to run all frontend checks from the project root |

### npm scripts (run from `frontend/`)

| Script | What it does |
|---|---|
| `npm run format` | Formats all `.js`, `.css`, `.html` files with Prettier |
| `npm run format:check` | Checks formatting without writing changes (CI-safe) |
| `npm run lint` | Lints `script.js` with ESLint |
| `npm run lint:fix` | Auto-fixes lint issues in `script.js` |
| `npm run quality` | Runs `lint` then `format:check` (full read-only check) |
| `npm run quality:fix` | Runs `lint:fix` then `format` (auto-fix everything) |

### Project-root script

```bash
./scripts/quality-check.sh          # check only (exits non-zero on issues)
./scripts/quality-check.sh --fix    # auto-fix all issues
```

### Formatting applied to existing source

All three existing frontend files were reformatted by Prettier to match the new style rules:

- `frontend/script.js` — whitespace normalised; single-line `if` statements wrapped in curly braces (ESLint `curly` rule)
- `frontend/style.css` — whitespace/spacing normalised
- `frontend/index.html` — whitespace/attribute quoting normalised

No logic was changed; only formatting.
