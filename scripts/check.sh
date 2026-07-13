#!/usr/bin/env sh
set -eu

python -m ruff check .
python -m ruff format --check .
python -m mypy
npm run lint
npm run typecheck
npm run contracts:check
python scripts/verify_phase1.py --static-only

