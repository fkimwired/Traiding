#!/usr/bin/env sh
set -eu

verify_phase="${FABLE5_VERIFY_PHASE:-8}"
case "$verify_phase" in
  1|2|3|4|5|6|7|8) ;;
  *)
    echo "FABLE5_VERIFY_PHASE must be one of 1, 2, 3, 4, 5, 6, 7, or 8." >&2
    exit 2
    ;;
esac

python -m ruff check .
python -m ruff format --check .
python -m mypy
npm run lint
npm run typecheck
npm run contracts:check
python scripts/verify_phase1.py --static-only --phase "$verify_phase"
