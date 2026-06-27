# RepoJudge Implementation Plan

## 1. Foundation
- Files: `pyproject.toml`, `.env.example`, `.gitignore`, backend package skeleton.
- Acceptance: dependencies resolve with uv; settings load without secrets.

## 2. Analysis engine
- Files: repository tools, README claim extractor, engineering and security scanners.
- Acceptance: local Python fixture can be analyzed without network or an LLM; all findings include evidence.

## 3. Agent workflow
- Files: one LangGraph node per stage, typed state, graph builder.
- Acceptance: workflow degrades cleanly when LLM or Docker is unavailable and records stage errors.

## 4. Scoring and reports
- Files: deterministic scoring rules, score engine, JSON/Markdown report generator.
- Acceptance: scores stay in 0–100, are deterministic, and expose additions/deductions.

## 5. API and persistence
- Files: SQLAlchemy models, services, FastAPI routes.
- Acceptance: create/status/report/Markdown/health/demo endpoints work; task concurrency is bounded.

## 6. Frontend and demo
- Files: Vite React TypeScript UI and sample report.
- Acceptance: responsive dark UI builds and can display both live tasks and the offline demo.

## 7. Delivery assets
- Files: Dockerfiles, compose, CI, README, license, Makefile, tests.
- Acceptance: public-repository documentation and safety limitations are explicit.

## 8. Verification
- Commands: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run mypy backend/app`,
  `npm install`, `npm run build`, backend health smoke test.
- Acceptance: fix all actionable failures; accurately record unavailable external capabilities.

## Completion status

- Backend workflow, scanners, scoring, reports, API, persistence, frontend, Demo Mode and delivery assets are implemented.
- The restricted Docker fixture test has been executed successfully with networking disabled.
- Final acceptance commands are rerun after each implementation pass; see the final handoff for exact results.
