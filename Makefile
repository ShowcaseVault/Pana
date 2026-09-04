DATASTORES ?= docker compose -f docker-compose.datastores.yml
COMPOSE    ?= docker compose
UV         ?= uv

CELERY := $(UV) run celery -A celery_service.celery_app worker --loglevel=info

# Windows cannot fork, so Celery needs the solo pool there.
ifeq ($(OS),Windows_NT)
CELERY_POOL ?= solo
else
CELERY_POOL ?= prefork
endif

.DEFAULT_GOAL := help
.PHONY: help install up down logs api celery celery-high celery-default lint format check test alembic-up alembic-create deploy-build deploy-up deploy-down

install:
	$(UV) sync --group dev

# --- Development datastores -------------------------------------------------

up:
	$(DATASTORES) up -d

down:
	$(DATASTORES) down

# --- Application processes (run on the host) --------------------------------

api:
	$(UV) run python backend.py

celery:
	$(CELERY) -P $(CELERY_POOL) -Q high_priority,default -n worker@%h

celery-high:
	$(CELERY) -P $(CELERY_POOL) -Q high_priority -n high_worker@%h

celery-default:
	$(CELERY) -P $(CELERY_POOL) -Q default -n default_worker@%h

# --- Code quality -----------------------------------------------------------

lint:
	$(UV) run ruff check --fix .

format:
	$(UV) run ruff format .

test:
	$(UV) run pytest

check:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

# --- Migrations -------------------------------------------------------------

alembic-up:
	$(UV) run alembic upgrade head

alembic-create:
ifndef MSG
	$(error MSG is required, e.g. make alembic-create MSG="add users table")
endif
	$(UV) run alembic revision -m "$(MSG)"

# --- Deployment stack (datastores + pana-image) -----------------------------

deploy-build:
	$(COMPOSE) build

deploy-up:
	$(COMPOSE) up -d

deploy-down:
	$(COMPOSE) down

# --- Make Help -----------------------------
help:
	@echo "make install         sync the Python environment with uv"
	@echo "make up              start Postgres and Redis for development"
	@echo "make down            stop the development datastores"
	@echo "make logs            tail the datastore logs"
	@echo "make api             run the FastAPI server"
	@echo "make celery          run one worker consuming both queues"
	@echo "make celery-high     run the high priority worker only"
	@echo "make celery-default  run the default priority worker only"
	@echo "make lint            check code with ruff"
	@echo "make format          format code with ruff"
	@echo "make test            run the test suite"
	@echo "make check           lint and format check, no writes (CI)"
	@echo "make alembic-up      apply migrations up to head"
	@echo "make alembic-create MSG=\"...\"  create an empty revision"
	@echo "make deploy-build    build the deployment images"
	@echo "make deploy-up       start the full deployment stack"
	@echo "make deploy-down     stop the full deployment stack"
