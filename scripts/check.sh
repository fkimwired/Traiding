#!/usr/bin/env sh
set -eu

verify_phase="${FABLE5_VERIFY_PHASE:-21}"
case "$verify_phase" in
  1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|18|19|20|21) ;;
  *)
    echo "FABLE5_VERIFY_PHASE must be one of 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, or 21." >&2
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
