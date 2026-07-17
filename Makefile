.PHONY: install test lint typecheck contract-check check smoke up down

install:
	python -m pip install --constraint requirements.lock -e ".[dev]"
	npm ci

test:
	python -m pytest
	npm test

lint:
	python -m ruff check .
	python -m ruff format --check .
	npm run lint

typecheck:
	python -m mypy
	npm run typecheck

contract-check:
	npm run contracts:check

check: lint typecheck contract-check test
	@phase="$${FABLE5_VERIFY_PHASE:-10}"; \
	case "$$phase" in 1|2|3|4|5|6|7|8|9|10) ;; *) echo "FABLE5_VERIFY_PHASE must be one of 1, 2, 3, 4, 5, 6, 7, 8, 9, or 10." >&2; exit 2 ;; esac; \
	python scripts/verify_phase1.py --static-only --phase "$$phase"

up:
	docker compose up --build --wait

down:
	docker compose down

smoke:
	@phase="$${FABLE5_VERIFY_PHASE:-10}"; \
	case "$$phase" in 1|2|3|4|5|6|7|8|9|10) ;; *) echo "FABLE5_VERIFY_PHASE must be one of 1, 2, 3, 4, 5, 6, 7, 8, 9, or 10." >&2; exit 2 ;; esac; \
	python scripts/verify_phase1.py --phase "$$phase"
