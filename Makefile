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
	python scripts/verify_phase1.py --static-only --phase 4

up:
	docker compose up --build --wait

down:
	docker compose down

smoke:
	python scripts/verify_phase1.py --phase 4
