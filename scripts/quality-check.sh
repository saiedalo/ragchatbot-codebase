#!/usr/bin/env bash
# Run all frontend code quality checks.
# Usage: ./scripts/quality-check.sh [--fix]

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
FIX=false

for arg in "$@"; do
    if [[ "$arg" == "--fix" ]]; then
        FIX=true
    fi
done

echo "==> Frontend quality checks ($(pwd))"
cd "$FRONTEND_DIR"

if $FIX; then
    echo "--- ESLint (fix) ---"
    npx eslint --fix script.js
    echo "--- Prettier (write) ---"
    npx prettier --write "**/*.{js,css,html}"
    echo "All issues fixed."
else
    echo "--- ESLint ---"
    npx eslint script.js
    echo "--- Prettier ---"
    npx prettier --check "**/*.{js,css,html}"
    echo "All checks passed."
fi
