.PHONY: install test lint typecheck dev frontend sandbox-image compose

install:
	uv sync
	cd frontend && npm install

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy backend/app

dev:
	PYTHONPATH=backend uv run uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

sandbox-image:
	docker build -f backend/sandbox.Dockerfile -t repojudge-sandbox:py312-v1 .

compose:
	docker compose up --build
