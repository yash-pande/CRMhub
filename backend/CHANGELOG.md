# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-01-13

### Added
- Created `project_rules.md` to define interaction guidelines.
- Created `task.md` to track project progress.
- Initialized `requirements.txt` with FastAPI, SQLModel, SQLAlchemy, Psycopg2-binary, Pytest, Requests, and HTTPX.
- Created `src/` directory structure.
- Implemented core application files in `src/`:
    - `main.py`: FastAPI application with CRUD endpoints.
    - `models.py`: SQLModel database schemas (Contact, Lead).
    - `database.py`: SQLite database connection and session management.
    - `__init__.py`: Package initialization.

### Changed
- Refactored project structure from flat file layout to `src/` package layout.
- Updated `main.py` imports to use relative imports (`from .database`).
- Cleaned up previous artifacts (`crm.db`, `__pycache__`) and restarted with a fresh structure.
- Implemented "FastAPI Best Practices" architecture:
    - Decoupled configuration into `src/config.py`.
    - Created `src/contacts/` module (Domain Driven Design).
    - Split `models.py` into `schemas` (Pydantic) and `models` (DB).
    - Created `service.py` for business logic separation.
    - Updated `main.py` to use `include_router`.
- Removed `src/contacts` module and reset project to clean skeleton.
- Created `.env` file for environment variables.




